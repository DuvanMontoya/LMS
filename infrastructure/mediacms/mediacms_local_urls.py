"""Local URL integration points for the pinned MediaCMS instance.

Only the endpoints which must begin or complete an authenticated protocol are
exempt from Django's global login redirect:

* the internal Nginx authorization subrequest, which must return 403 (rather
  than a redirect) for an unauthenticated protected-file request; and
* the two public LTI 1.3 hand-off endpoints.  The OIDC initiation must reach
  the LMS and the launch endpoint must receive the LMS-signed id_token before
  MediaCMS can create its own authenticated session.

All media pages and protected-file URLs remain behind the global-login policy.
"""

import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import jwt
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt

from files.models import Media, MediaPermission
from files.views.media_auth import media_auth as upstream_media_auth
from lti.handlers import validate_lti_session
from lti.models import LTIResourceLink
from lti.views import EmbedMediaLTIView, LaunchView, OIDCLoginView
from rbac.models import RBACMembership

def _upstream_media_auth_cache_key(media, user) -> str:
    """Mirror MediaCMS' protected-file cache key for explicit invalidation."""

    return f"xaccel:auth:{media.uid}:{user.id if user.is_authenticated else 'anon'}"


def _lti_access_cache_key(request, lti_session) -> str:
    return ":".join(
        (
            "lms-lti-media-access",
            str(request.user.pk),
            str(lti_session.get("platform_id", "")),
            str(lti_session.get("context_id", "")),
            str(lti_session.get("resource_link_id", "")),
        )
    )


def _lti_access_claims(request, lti_session):
    if not lti_session:
        return None
    value = cache.get(_lti_access_cache_key(request, lti_session))
    if (
        not isinstance(value, dict)
        or set(value) != {"media_friendly_token", "media_access_token"}
        or not isinstance(value["media_friendly_token"], str)
        or not isinstance(value["media_access_token"], str)
    ):
        return None
    return value


def _lti_resource_link(request):
    lti_session = validate_lti_session(request)
    if not lti_session:
        return None, None
    resource_link = (
        LTIResourceLink.objects.filter(
            platform_id=lti_session.get("platform_id"),
            context_id=lti_session.get("context_id"),
            resource_link_id=lti_session.get("resource_link_id"),
        )
        .select_related("rbac_group", "category")
        .first()
    )
    if (
        resource_link is None
        or resource_link.rbac_group is None
        or resource_link.category is None
        or not RBACMembership.objects.filter(
            user=request.user, rbac_group=resource_link.rbac_group
        ).exists()
    ):
        return lti_session, None
    return lti_session, resource_link


def _live_lms_access_allowed(media_access_token) -> bool:
    if (
        not isinstance(media_access_token, str)
        or not media_access_token
        or len(media_access_token) > 8192
    ):
        return False
    try:
        validation_request = Request(
            settings.LMS_MEDIA_ACCESS_VALIDATION_URL,
            headers={"Authorization": f"Bearer {media_access_token}"},
            method="GET",
        )
        with urlopen(
            validation_request,
            timeout=settings.LMS_MEDIA_ACCESS_VALIDATION_TIMEOUT_SECONDS,
        ) as response:
            return response.status == 204
    except (HTTPError, URLError, TimeoutError, ValueError):
        # The data plane must never continue if the LMS authority is absent or
        # refuses the scoped capability.  No response body or token is logged.
        return False


def _revoke_local_lti_access(request, *, media=None, resource_link=None) -> None:
    """Remove the residual MediaCMS grant after LMS access ceased to exist."""

    if media is not None and request.user.is_authenticated:
        MediaPermission.objects.filter(
            user=request.user,
            media=media,
            source=MediaPermission.SOURCE_LTI_EMBED,
        ).delete()
        cache.delete(_upstream_media_auth_cache_key(media, request.user))
    if resource_link is not None and request.user.is_authenticated:
        RBACMembership.objects.filter(
            user=request.user,
            rbac_group=resource_link.rbac_group,
        ).delete()
    lti_session = validate_lti_session(request)
    if lti_session:
        cache.delete(_lti_access_cache_key(request, lti_session))
    request.session.pop("lms_lti_media_friendly_token", None)
    request.session.pop("lms_lti_media_access_token", None)
    request.session.modified = True


def lms_media_auth(request):
    """Require a still-effective LMS capability before upstream media ACLs."""

    lti_session, resource_link = _lti_resource_link(request)
    access_claims = _lti_access_claims(request, lti_session)
    friendly_token = (
        access_claims["media_friendly_token"] if access_claims is not None else None
    )
    media = (
        Media.objects.filter(friendly_token=friendly_token, state="private").first()
        if isinstance(friendly_token, str)
        else None
    )
    live_access = (
        access_claims is not None
        and _live_lms_access_allowed(access_claims["media_access_token"])
    )
    if (
        media is None
        or resource_link is None
        or access_claims is None
        or not live_access
    ):
        _revoke_local_lti_access(
            request, media=media, resource_link=resource_link
        )
        return HttpResponseForbidden("El acceso al vídeo ya no está vigente.")
    return upstream_media_auth(request)


# Django's LoginRequiredMiddleware honours this attribute (the same contract
# set by django.contrib.auth.decorators.login_not_required).
lms_media_auth.login_required = False


class LMSLaunchView(LaunchView):
    """Persist the exact MediaCMS token validated in an LTI launch.

    The upstream launch view has already verified the signed id_token before
    it returns a successful response.  Retaining only the one custom token
    that it accepted lets the local integration deny a browser attempt to swap
    the subsequent ``/lti/embed/<token>/`` URL for another private video.
    """

    def sanitize_claims(self, claims):
        """Keep the bearer out of MediaCMS' persistent LTI launch audit log.

        The upstream implementation persists a diagnostic copy of the launch
        claims.  The access capability is deliberately short-lived, but it is
        still a bearer credential and must remain only in the bounded server
        cache used for the current MediaCMS session.
        """

        safe_claims = super().sanitize_claims(claims)
        custom_claims = safe_claims.get(
            "https://purl.imsglobal.org/spec/lti/claim/custom"
        )
        if isinstance(custom_claims, dict):
            safe_claims = safe_claims.copy()
            safe_custom_claims = custom_claims.copy()
            safe_custom_claims.pop("lms_media_access_token", None)
            safe_claims[
                "https://purl.imsglobal.org/spec/lti/claim/custom"
            ] = safe_custom_claims
        return safe_claims

    def post(self, request):
        try:
            claims = jwt.decode(
                request.POST.get("id_token", ""),
                options={"verify_signature": False, "verify_aud": False},
            )
            custom_claims = claims.get(
                "https://purl.imsglobal.org/spec/lti/claim/custom", {}
            )
            media_token = custom_claims.get("media_friendly_token")
            media_access_token = custom_claims.get("lms_media_access_token")
            if not isinstance(media_token, str) or not re.fullmatch(
                r"[A-Za-z0-9_-]{1,64}", media_token
            ):
                raise ValueError("missing or malformed MediaCMS token")
            if (
                not isinstance(media_access_token, str)
                or not media_access_token
                or len(media_access_token) > 8192
            ):
                raise ValueError("missing or malformed LMS access token")
        except (ValueError, jwt.PyJWTError, TypeError):
            media_token = None
            media_access_token = None

        # The upstream implementation verifies this same id_token, provisions
        # its user/context and may rotate the Django session.  Save only after
        # that successful verification, but retain the pre-read custom claims:
        # some pyLTI adapters consume form data while resolving the launch.
        response = super().post(request)
        if response.status_code != 200:
            return response
        lti_session = validate_lti_session(request)
        if (
            media_token is not None
            and media_access_token is not None
            and lti_session is not None
        ):
            cache.set(
                _lti_access_cache_key(request, lti_session),
                {
                    "media_friendly_token": media_token,
                    "media_access_token": media_access_token,
                },
                timeout=settings.LMS_MEDIA_ACCESS_SESSION_TTL_SECONDS,
            )
        else:
            if lti_session:
                cache.delete(_lti_access_cache_key(request, lti_session))
        return response


@method_decorator(xframe_options_exempt, name="dispatch")
class LMSBoundEmbedMediaLTIView(EmbedMediaLTIView):
    """Authorize only the video bound to this valid LMS LTI launch.

    MediaCMS' generic LTI embed path checks that a user belongs to *an* LTI
    group, but does not compare a private video with the current resource
    link.  The local adapter closes that gap: it requires the exact token from
    the verified launch and the matching release-context group.  It then
    attaches the video to that private LTI category and grants the normal
    MediaCMS permission used by the protected Nginx media paths.
    """

    def get(self, request, friendly_token):
        lti_session = validate_lti_session(request)
        if not lti_session:
            return HttpResponseForbidden("La sesión LTI ya no está activa.")
        access_claims = _lti_access_claims(request, lti_session)
        if (
            access_claims is None
            or access_claims["media_friendly_token"] != friendly_token
        ):
            return HttpResponseForbidden("La sesión LTI no autoriza este vídeo.")

        _lti_session, resource_link = _lti_resource_link(request)
        if resource_link is None:
            return HttpResponseForbidden("No perteneces al contexto académico del vídeo.")

        media = Media.objects.filter(friendly_token=friendly_token, state="private").first()
        if media is None:
            return HttpResponseForbidden("El vídeo no está disponible de forma privada.")
        if not _live_lms_access_allowed(access_claims["media_access_token"]):
            _revoke_local_lti_access(
                request, media=media, resource_link=resource_link
            )
            return HttpResponseForbidden("El acceso al vídeo ya no está vigente.")

        # This association is release-context scoped and never changes the
        # publication state of the video.  It makes the upstream MediaCMS
        # permission and Nginx file-authorization path enforce the same group.
        media.category.add(resource_link.category)
        MediaPermission.objects.get_or_create(
            user=request.user,
            media=media,
            defaults={
                "owner_user": media.user,
                "permission": "viewer",
                "source": MediaPermission.SOURCE_LTI_EMBED,
            },
        )
        # MediaCMS caches a previous protected-file denial.  A new verified
        # launch must not inherit that denial, and a later revocation clears
        # the same key in ``_revoke_local_lti_access``.
        cache.delete(_upstream_media_auth_cache_key(media, request.user))
        return super().get(request, friendly_token)


# The upstream root configuration has a broad ``files.urls`` resolver before
# its LTI include.  Install these exact endpoints first and mark the *resolved
# view functions* as public; Django's LoginRequiredMiddleware receives those
# functions, rather than the view classes.
lti_oidc_login = OIDCLoginView.as_view()
lti_launch = LMSLaunchView.as_view()
lti_embed_media = LMSBoundEmbedMediaLTIView.as_view()
lti_oidc_login.login_required = False
lti_launch.login_required = False

from cms.urls import urlpatterns as mediacms_urlpatterns  # noqa: E402

urlpatterns = [
    path("api/v1/media-auth", lms_media_auth, name="lms_media_auth"),
    path("lti/oidc/login/", lti_oidc_login, name="lti_oidc_login"),
    path("lti/launch/", lti_launch, name="lti_launch"),
    path(
        "lti/embed/<str:friendly_token>/",
        lti_embed_media,
        name="lti_embed_media",
    ),
    *mediacms_urlpatterns,
]
