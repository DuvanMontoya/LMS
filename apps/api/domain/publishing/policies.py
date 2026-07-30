from __future__ import annotations

from typing import TYPE_CHECKING, cast

from domain.organizations.capabilities import Capability
from domain.organizations.models import Organization
from domain.organizations.policies import has_capability

if TYPE_CHECKING:
    from domain.identity.models import User


def _user(actor: object) -> User | None:
    return cast("User | None", actor)


def can_publish(actor: object, organization: Organization) -> bool:
    return has_capability(_user(actor), organization, Capability.COURSE_RELEASE_PUBLISH)


def can_withdraw(actor: object, organization: Organization) -> bool:
    return has_capability(
        _user(actor), organization, Capability.COURSE_RELEASE_WITHDRAW
    )


def can_view_history(actor: object, organization: Organization) -> bool:
    return has_capability(
        _user(actor),
        organization,
        Capability.COURSE_RELEASE_HISTORY_VIEW,
    )


def can_create_draft(actor: object, organization: Organization) -> bool:
    return has_capability(
        _user(actor),
        organization,
        Capability.COURSE_RELEASE_CREATE_DRAFT,
    )


def can_view_published(actor: object, organization: Organization) -> bool:
    return has_capability(_user(actor), organization, Capability.COURSE_PUBLISHED_VIEW)
