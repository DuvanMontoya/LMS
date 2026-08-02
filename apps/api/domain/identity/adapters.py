from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import cast

from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.models import EmailAddress
from allauth.headless.adapter import DefaultHeadlessAdapter
from django.contrib.auth.base_user import AbstractBaseUser
from django.http import HttpRequest

# allauth's request adapter boundary is untyped by the upstream package.
# pyright: reportUnknownMemberType=false


@dataclass
class AuthenticatedUserPayload:
    """Stable, minimal browser payload reflected in allauth's OpenAPI schema."""

    id: str | None = field(
        metadata={
            "description": "The user UUID.",
            "example": "00000000-0000-0000-0000-000000000000",
        }
    )
    email: str | None = field(
        metadata={
            "description": "The primary email address.",
            "example": "student@example.test",
        }
    )
    display: str = field(
        metadata={
            "description": "A neutral display value.",
            "example": "student@example.test",
        }
    )
    has_usable_password: bool = field(
        metadata={"description": "Whether the account has a password.", "example": True}
    )


class LMSHeadlessAdapter(DefaultHeadlessAdapter):
    """Expose only data required by the browser client, never account privileges."""

    def get_user_dataclass(self):
        return AuthenticatedUserPayload

    def user_as_dataclass(self, user: AbstractBaseUser) -> AuthenticatedUserPayload:
        email = cast(str, getattr(user, "email", "")) if user.pk else None
        return AuthenticatedUserPayload(
            id=str(user.pk) if user.pk else None,
            email=email,
            display=email or "",
            has_usable_password=user.has_usable_password(),
        )


class LMSAccountAdapter(DefaultAccountAdapter):
    """Keep allauth authoritative while evaluating live registration policy."""

    def is_open_for_signup(self, request: HttpRequest) -> bool:
        from domain.organizations.services import session_signup_invitation

        from .models import PlatformRegistrationSettings

        registration = PlatformRegistrationSettings.current()
        if (
            registration.signup_mode
            == PlatformRegistrationSettings.SignupMode.OPEN.value
        ):
            return True
        invitation = session_signup_invitation(request)
        if invitation is None:
            return False
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return False
        submitted_email = payload.get("email") if isinstance(payload, dict) else None
        return isinstance(submitted_email, str) and (
            submitted_email.strip().casefold() == invitation.email.casefold()
        )

    def confirm_email(self, request: HttpRequest, email_address: EmailAddress) -> bool:
        confirmed = super().confirm_email(request, email_address)
        if confirmed:
            from domain.organizations.services import (
                complete_onboarding_after_email_verification,
            )

            complete_onboarding_after_email_verification(
                request=request,
                user=cast("AbstractBaseUser", email_address.user),  # type: ignore[arg-type]
            )
        return confirmed
