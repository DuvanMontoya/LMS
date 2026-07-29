from __future__ import annotations

from domain.organizations.capabilities import Capability
from domain.organizations.models import Organization
from domain.organizations.policies import has_capability


def can_view_catalog(actor: object, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.CATALOG_VIEW)  # type: ignore[arg-type]


def can_manage_catalog(actor: object, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.CATALOG_MANAGE)  # type: ignore[arg-type]


def can_manage_prerequisites(actor: object, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.CATALOG_MANAGE_PREREQUISITES)  # type: ignore[arg-type]


def can_view_entity(actor: object, organization: Organization, status: str) -> bool:
    return can_manage_catalog(actor, organization) or (
        status == "active" and can_view_catalog(actor, organization)
    )
