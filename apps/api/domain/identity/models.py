from __future__ import annotations

import uuid
from datetime import datetime
from typing import ClassVar

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

from .managers import UserManager


class User(AbstractUser):
    """Minimal platform identity, intentionally separate from academic roles."""

    id: models.UUIDField[uuid.UUID, uuid.UUID] = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    username = None
    email: models.EmailField[str, str] = models.EmailField(unique=True)

    # django-stubs assumes AbstractUser's username manager; this project replaces it.
    objects: ClassVar[UserManager] = UserManager()  # pyright: ignore[reportIncompatibleVariableOverride]

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []  # pyright: ignore[reportIncompatibleVariableOverride]

    # Type-only declarations for fields inherited from Django's dynamic model base.
    password: str
    first_name: str
    last_name: str
    is_active: bool
    is_staff: bool
    is_superuser: bool

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="identity_user_email_ci_unique",
            )
        ]

    def __str__(self) -> str:
        return self.email

    def get_full_name(self) -> str:
        return " ".join(
            name.strip() for name in (self.first_name, self.last_name) if name.strip()
        )

    def get_short_name(self) -> str:
        return self.first_name.strip()


class PlatformRegistrationSettings(models.Model):  # noqa: DJ012
    """Singleton, database-backed policy evaluated by the allauth adapter."""

    class SignupMode(models.TextChoices):
        CLOSED = "closed", "Cerrado"
        INVITE_ONLY = "invite_only", "Sólo invitación"
        OPEN = "open", "Abierto"

    singleton: models.PositiveSmallIntegerField[int, int] = (
        models.PositiveSmallIntegerField(default=1, unique=True, editable=False)
    )
    public_signup_enabled: models.BooleanField[bool, bool] = models.BooleanField(
        default=True
    )
    signup_mode: models.CharField[str, str] = models.CharField(
        max_length=16, choices=SignupMode.choices, default=SignupMode.OPEN
    )
    require_email_verification: models.BooleanField[bool, bool] = models.BooleanField(
        default=True
    )
    default_locale: models.CharField[str, str] = models.CharField(
        max_length=16, default="es"
    )
    default_timezone: models.CharField[str, str] = models.CharField(
        max_length=64, default="UTC"
    )
    updated_by: models.ForeignKey[User | None, User | None] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="platform_registration_settings_updates",
    )
    updated_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(
        auto_now=True
    )
    lock_version: models.PositiveIntegerField[int, int] = models.PositiveIntegerField(
        default=1
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(singleton=1),
                name="identity_registration_settings_singleton_one",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(signup_mode="open", public_signup_enabled=True)
                    | models.Q(
                        signup_mode__in=["closed", "invite_only"],
                        public_signup_enabled=False,
                    )
                ),
                name="identity_registration_settings_mode_consistent",
            ),
            models.CheckConstraint(
                condition=models.Q(require_email_verification=True),
                name="identity_registration_settings_email_verification_required",
            ),
        ]
        permissions = [
            ("manage_platform_registration", "Can manage platform registration"),
        ]

    def __str__(self) -> str:
        return "platform-registration-settings"

    @classmethod
    def current(cls) -> PlatformRegistrationSettings:
        settings, _ = cls.objects.get_or_create(singleton=1)
        return settings
