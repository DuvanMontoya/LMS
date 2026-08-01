from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

from .models import PlatformRegistrationSettings

if TYPE_CHECKING:
    from .models import User

# Django's ORM manager is dynamically typed at this boundary.
# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false


class RegistrationSettingsConflict(Exception):
    pass


class RegistrationSettingsDenied(Exception):
    pass


@transaction.atomic
def update_platform_registration_settings(
    *,
    actor: User,
    expected_version: int,
    signup_mode: str,
    default_locale: str,
    default_timezone: str,
) -> PlatformRegistrationSettings:
    permitted = actor.is_superuser or actor.has_perm(
        "identity.manage_platform_registration"
    )
    if not permitted:
        raise RegistrationSettingsDenied("No tienes permiso para esta operación.")
    current = PlatformRegistrationSettings.objects.select_for_update().get_or_create(
        singleton=1
    )[0]
    if current.lock_version != expected_version:
        raise RegistrationSettingsConflict("La configuración cambió antes de guardar.")
    if signup_mode not in {
        PlatformRegistrationSettings.SignupMode.CLOSED.value,
        PlatformRegistrationSettings.SignupMode.INVITE_ONLY.value,
        PlatformRegistrationSettings.SignupMode.OPEN.value,
    }:
        raise ValueError("Modo de registro inválido.")
    current.signup_mode = signup_mode
    current.public_signup_enabled = (
        signup_mode == PlatformRegistrationSettings.SignupMode.OPEN.value
    )
    current.default_locale = default_locale.strip() or "es"
    current.default_timezone = default_timezone.strip() or "UTC"
    current.updated_by = actor
    current.lock_version += 1
    current.full_clean()
    current.save()
    return current
