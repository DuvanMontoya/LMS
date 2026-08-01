# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from dataclasses import dataclass

from .models import NotificationCategory, NotificationPreference


@dataclass(frozen=True)
class EffectivePreference:
    in_app_enabled: bool
    email_enabled: bool


DEFAULTS = {
    category: EffectivePreference(in_app_enabled=True, email_enabled=True)
    for category in NotificationCategory.values
}
MANDATORY_IN_APP_TEMPLATES = frozenset(
    {"enrollment_suspended", "enrollment_revoked", "publication_withdrawn"}
)


def effective_preference(user: object, category: str) -> EffectivePreference:
    default = DEFAULTS[category]
    override = NotificationPreference.objects.filter(
        user=user, category=category
    ).first()
    if override is None:
        return default
    return EffectivePreference(override.in_app_enabled, override.email_enabled)
