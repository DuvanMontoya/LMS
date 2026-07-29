from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.base_user import BaseUserManager

if TYPE_CHECKING:
    from .models import User


class UserManager(BaseUserManager["User"]):
    """Creation and lookup policy for the email-based platform identity."""

    @staticmethod
    def normalize_email_address(email: str) -> str:
        normalized = BaseUserManager.normalize_email(email.strip())
        return normalized.lower()

    def _create_user(
        self,
        email: str,
        password: str | None,
        **extra_fields: object,
    ) -> User:
        if not email or not email.strip():
            raise ValueError("The email address is required.")

        user = self.model(email=self.normalize_email_address(email), **extra_fields)
        user.full_clean(exclude=["password"])
        if password is None:
            user.set_unusable_password()
        else:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: object,
    ) -> User:
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: object,
    ) -> User:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)

    def get_by_natural_key(self, username: str | None) -> User:
        if username is None:
            raise ValueError("The email address is required.")
        return self.get(**{f"{self.model.USERNAME_FIELD}__iexact": username.strip()})
