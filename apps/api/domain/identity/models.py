from __future__ import annotations

import uuid
from typing import ClassVar

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
