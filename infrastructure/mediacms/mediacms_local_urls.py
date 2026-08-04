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

import jwt
from django.http import HttpResponseForbidden
from django.urls import path, reverse
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt

from files.models import Media, MediaPermission
from files.views.media_auth import media_auth
from lti.handlers import validate_lti_session
from lti.models import LTIResourceLink
from lti.views import EmbedMediaLTIView, LaunchView, OIDCLoginView
from rbac.models import RBACMembership

# Django's LoginRequiredMiddleware honours this attribute (the same contract
# set by django.contrib.auth.decorators.login_not_required).
media_auth.login_required = False


class LMSLaunchView(LaunchView):
    """Persist the exact MediaCMS token validated in an LTI launch.

    The upstream launch view has already verified the signed id_token before
    it returns a successful response.  Retaining only the one custom token
    that it accepted lets the local integration deny a browser attempt to swap
    the subsequent ``/lti/embed/<token>/`` URL for another private video.
    """

    def post(self, request):
        response = super().post(request)
        if response.status_code != 200:
            return response
        try:
            claims = jwt.decode(
                request.POST.get("id_token", ""),
                options={"verify_signature": False, "verify_aud": False},
            )
            custom_claims = claims.get(
                "https://purl.imsglobal.org/spec/lti/claim/custom", {}
            )
            media_token = custom_claims.get("media_friendly_token")
            if not isinstance(media_token, str) or not re.fullmatch(
                r"[A-Za-z0-9_-]{1,64}", media_token
            ):
                raise ValueError("missing or malformed MediaCMS token")
            expected_embed_path = reverse("lti:embed_media", args=[media_token])
            if expected_embed_path.encode() not in response.content:
                raise ValueError("launch did not resolve to the signed media token")
        except (ValueError, jwt.PyJWTError, TypeError):
            request.session.pop("lms_lti_media_friendly_token", None)
        else:
            request.session["lms_lti_media_friendly_token"] = media_token
            request.session.modified = True
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
        if (
            not lti_session
            or request.session.get("lms_lti_media_friendly_token") != friendly_token
        ):
            return HttpResponseForbidden("La sesión LTI no autoriza este vídeo.")

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
            return HttpResponseForbidden("No perteneces al contexto académico del vídeo.")

        media = Media.objects.filter(friendly_token=friendly_token, state="private").first()
        if media is None:
            return HttpResponseForbidden("El vídeo no está disponible de forma privada.")

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
    path("lti/oidc/login/", lti_oidc_login, name="lti_oidc_login"),
    path("lti/launch/", lti_launch, name="lti_launch"),
    path(
        "lti/embed/<str:friendly_token>/",
        lti_embed_media,
        name="lti_embed_media",
    ),
    *mediacms_urlpatterns,
]
