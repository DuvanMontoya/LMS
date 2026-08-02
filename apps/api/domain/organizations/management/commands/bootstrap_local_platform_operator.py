from __future__ import annotations

import os
from typing import TYPE_CHECKING, cast

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from domain.organizations.models import Membership

if TYPE_CHECKING:
    from domain.identity.managers import UserManager


class Command(BaseCommand):
    help = (
        "Crea o sincroniza el operador local de plataforma desde variables de "
        "entorno, sin concederle membresías institucionales."
    )

    def handle(self, *args: object, **options: object) -> None:
        del args, options
        if not settings.DEBUG:
            raise CommandError(
                "El operador local de plataforma sólo se permite con DEBUG=True."
            )
        email = os.environ.get("LMS_LOCAL_PLATFORM_OPERATOR_EMAIL", "").strip().lower()
        password = os.environ.get("LMS_LOCAL_PLATFORM_OPERATOR_PASSWORD", "")
        first_name = os.environ.get(
            "LMS_LOCAL_PLATFORM_OPERATOR_FIRST_NAME", ""
        ).strip()
        last_name = os.environ.get("LMS_LOCAL_PLATFORM_OPERATOR_LAST_NAME", "").strip()
        if not email or not password:
            raise CommandError(
                "LMS_LOCAL_PLATFORM_OPERATOR_EMAIL y "
                "LMS_LOCAL_PLATFORM_OPERATOR_PASSWORD son obligatorios."
            )

        manager = cast("UserManager", get_user_model().objects)
        with transaction.atomic():
            user = manager.filter(email__iexact=email).first()
            if user and Membership.objects.filter(user=user).exists():
                raise CommandError(
                    "La identidad del operador local tiene membresías institucionales. "
                    "Usa una cuenta exclusiva para el control de plataforma."
                )
            if user is None:
                user = manager.create_superuser(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                )
            else:
                update_fields: list[str] = []
                for field, value in (
                    ("first_name", first_name),
                    ("last_name", last_name),
                    ("is_active", True),
                    ("is_staff", True),
                    ("is_superuser", True),
                ):
                    if getattr(user, field) != value:
                        setattr(user, field, value)
                        update_fields.append(field)
                if not user.check_password(password):
                    user.set_password(password)
                    update_fields.append("password")
                if update_fields:
                    user.save(update_fields=update_fields)
            EmailAddress.objects.update_or_create(
                user=user,
                email=user.email,
                defaults={"primary": True, "verified": True},
            )

        message = "Operador local de plataforma sincronizado sin membresías."
        self.stdout.write(self.style.SUCCESS(message))
