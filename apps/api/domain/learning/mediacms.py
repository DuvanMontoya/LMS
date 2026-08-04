# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
"""Release-pinned MediaCMS LTI launch descriptors and platform assertions."""

from __future__ import annotations

import base64
import json
import time
import uuid
from functools import lru_cache
from typing import Any, cast
from urllib.parse import urlencode

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from django.conf import settings
from django.core import signing

from domain.identity.models import User

from .access import LearningAccess, require_learning_access
from .exceptions import LearningAccessDenied, LearningReleaseInvalid
from .models import CourseEnrollment
from .snapshots import snapshot_unit

LTI_CLAIM = "https://purl.imsglobal.org/spec/lti/claim"
LAUNCH_SALT = "lms.learning.mediacms-launch.v1"


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _media_from_snapshot(release: object, unit_id: uuid.UUID) -> dict[str, str]:
    unit = snapshot_unit(cast(Any, release), unit_id)
    media = unit.get("media")
    if (
        not isinstance(media, dict)
        or media.get("provider") != "mediacms_lti"
        or not isinstance(media.get("media_friendly_token"), str)
    ):
        raise LearningReleaseInvalid("La unidad no tiene un vídeo MediaCMS publicable.")
    return cast(dict[str, str], media)


def _assert_enabled() -> None:
    if not settings.MEDIACMS_LTI_ENABLED:
        raise LearningAccessDenied("La entrega de vídeo MediaCMS no está habilitada.")


def issue_mediacms_launch(
    *, actor: User, access: LearningAccess, unit_id: uuid.UUID
) -> dict[str, object]:
    """Issue an opaque, user-bound descriptor after current access is checked."""

    _assert_enabled()
    media = _media_from_snapshot(access.assignment.release, unit_id)
    payload = {
        "v": 1,
        "sub": str(actor.id),
        "enrollment_id": str(access.enrollment.id),
        "release_id": str(access.assignment.release_id),
        "unit_id": str(unit_id),
        "media_friendly_token": media["media_friendly_token"],
    }
    hint = signing.dumps(payload, salt=LAUNCH_SALT, compress=True)
    query = urlencode(
        {
            "client_id": settings.LMS_LTI_CLIENT_ID,
            "iss": settings.LMS_LTI_ISSUER,
            "login_hint": hint,
            "target_link_uri": f"{settings.MEDIACMS_LTI_TOOL_ORIGIN}/lti/launch/",
        }
    )
    return {
        "expires_in_seconds": settings.LMS_LTI_LAUNCH_TTL_SECONDS,
        "launch_url": (f"{settings.MEDIACMS_LTI_TOOL_ORIGIN}/lti/oidc/login/?{query}"),
        "provider": "mediacms_lti",
    }


def _load_launch_hint(value: str) -> dict[str, str]:
    try:
        payload = signing.loads(
            value,
            salt=LAUNCH_SALT,
            max_age=settings.LMS_LTI_LAUNCH_TTL_SECONDS,
        )
    except signing.BadSignature as error:
        raise LearningAccessDenied(
            "El lanzamiento de vídeo ya no es válido."
        ) from error
    expected_keys = {
        "v",
        "sub",
        "enrollment_id",
        "release_id",
        "unit_id",
        "media_friendly_token",
    }
    if (
        not isinstance(payload, dict)
        or set(payload) != expected_keys
        or payload["v"] != 1
    ):
        raise LearningAccessDenied("El lanzamiento de vídeo es inválido.")
    if not all(isinstance(payload[key], str) for key in expected_keys - {"v"}):
        raise LearningAccessDenied("El lanzamiento de vídeo es inválido.")
    return cast(dict[str, str], payload)


def authorize_mediacms_launch(*, actor: User, login_hint: str) -> dict[str, Any]:
    """Revalidate current enrolment before producing an LTI resource launch."""

    _assert_enabled()
    payload = _load_launch_hint(login_hint)
    if str(actor.id) != payload["sub"]:
        raise LearningAccessDenied("El lanzamiento no pertenece a este usuario.")
    try:
        enrollment = CourseEnrollment.objects.select_related(
            "membership__user",
            "organization",
            "course",
            "current_release_assignment__release",
        ).get(pk=payload["enrollment_id"], membership__user=actor)
        unit_id = uuid.UUID(payload["unit_id"])
    except (CourseEnrollment.DoesNotExist, ValueError) as error:
        raise LearningAccessDenied(
            "El lanzamiento no tiene una matrícula válida."
        ) from error
    access = require_learning_access(actor=actor, enrollment=enrollment)
    if str(access.assignment.release_id) != payload["release_id"]:
        raise LearningAccessDenied("La matrícula ya no apunta a este release.")
    media = _media_from_snapshot(access.assignment.release, unit_id)
    if media["media_friendly_token"] != payload["media_friendly_token"]:
        raise LearningAccessDenied("El recurso de vídeo ya no coincide con el release.")
    return {
        "access": access,
        "media": media,
        "unit": snapshot_unit(access.assignment.release, unit_id),
        "unit_id": unit_id,
    }


@lru_cache(maxsize=1)
def _private_key() -> rsa.RSAPrivateKey:
    value = settings.LMS_LTI_PRIVATE_KEY_PEM.strip()
    if value:
        loaded = serialization.load_pem_private_key(value.encode("utf-8"), None)
        if not isinstance(loaded, rsa.RSAPrivateKey):
            raise RuntimeError("LMS_LTI_PRIVATE_KEY_PEM debe ser una clave RSA.")
        return loaded
    if settings.DEBUG:
        return rsa.generate_private_key(public_exponent=65537, key_size=2048)
    raise RuntimeError("LMS_LTI_PRIVATE_KEY_PEM es obligatoria fuera de desarrollo.")


def lti_jwks() -> dict[str, list[dict[str, str]]]:
    numbers = _private_key().public_key().public_numbers()
    return {
        "keys": [
            {
                "alg": "RS256",
                "e": _b64url(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8)),
                "kid": settings.LMS_LTI_KEY_ID,
                "kty": "RSA",
                "n": _b64url(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8)),
                "use": "sig",
            }
        ]
    }


def _sign_jwt(claims: dict[str, object]) -> str:
    header = {"alg": "RS256", "kid": settings.LMS_LTI_KEY_ID, "typ": "JWT"}
    segments = [
        _b64url(json.dumps(value, separators=(",", ":"), sort_keys=True).encode())
        for value in (header, claims)
    ]
    signing_input = ".".join(segments).encode("ascii")
    signature = _private_key().sign(
        signing_input,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return f"{segments[0]}.{segments[1]}.{_b64url(signature)}"


def lti_id_token(*, actor: User, nonce: str, authorization: dict[str, Any]) -> str:
    """Build a minimal LTI 1.3 resource-link assertion for MediaCMS."""

    access = cast(LearningAccess, authorization["access"])
    unit = cast(dict[str, Any], authorization["unit"])
    unit_id = cast(uuid.UUID, authorization["unit_id"])
    media = cast(dict[str, str], authorization["media"])
    now = int(time.time())
    name = actor.get_full_name() or actor.email
    context_id = str(access.assignment.release_id)
    resource_link_id = f"release-{context_id}-unit-{unit_id}"
    claims: dict[str, object] = {
        "aud": settings.LMS_LTI_CLIENT_ID,
        "email": actor.email,
        "exp": now + settings.LMS_LTI_LAUNCH_TTL_SECONDS,
        "family_name": actor.last_name,
        "given_name": actor.first_name,
        "iat": now,
        "iss": settings.LMS_LTI_ISSUER,
        "name": name,
        "nonce": nonce,
        "sub": str(actor.id),
        f"{LTI_CLAIM}/context": {
            "id": context_id,
            "label": access.enrollment.course.slug,
            "title": access.assignment.release.title,
        },
        f"{LTI_CLAIM}/custom": {
            "embed_share_media": "0",
            "media_friendly_token": media["media_friendly_token"],
        },
        f"{LTI_CLAIM}/deployment_id": settings.LMS_LTI_DEPLOYMENT_ID,
        f"{LTI_CLAIM}/message_type": "LtiResourceLinkRequest",
        f"{LTI_CLAIM}/resource_link": {
            "id": resource_link_id,
            "title": unit["title"],
        },
        f"{LTI_CLAIM}/roles": [
            "http://purl.imsglobal.org/vocab/lis/v2/membership#Learner"
        ],
        f"{LTI_CLAIM}/target_link_uri": (
            f"{settings.MEDIACMS_LTI_TOOL_ORIGIN}/lti/launch/"
        ),
        f"{LTI_CLAIM}/version": "1.3.0",
    }
    return _sign_jwt(claims)


def lti_authorization_allowed(
    *,
    client_id: str,
    redirect_uri: str,
    response_mode: str,
    response_type: str,
    scope: str,
) -> bool:
    return (
        client_id == settings.LMS_LTI_CLIENT_ID
        and redirect_uri == f"{settings.MEDIACMS_LTI_TOOL_ORIGIN}/lti/launch/"
        and response_mode == "form_post"
        and response_type == "id_token"
        and "openid" in scope.split()
    )
