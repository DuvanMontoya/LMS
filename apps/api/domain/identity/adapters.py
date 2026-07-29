from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from allauth.headless.adapter import DefaultHeadlessAdapter
from django.contrib.auth.base_user import AbstractBaseUser


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
