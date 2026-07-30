# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
from __future__ import annotations

from typing import TYPE_CHECKING

from domain.organizations.capabilities import Capability
from domain.organizations.models import Organization
from domain.organizations.policies import has_capability

if TYPE_CHECKING:
    from domain.identity.models import User

from .models import CourseEnrollment


def can_manage_cohorts(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.LEARNING_COHORT_MANAGE)


def can_manage_enrollments(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.LEARNING_ENROLLMENT_MANAGE)


def can_view_cohorts(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.LEARNING_COHORT_VIEW)


def can_view_enrollments(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.LEARNING_ENROLLMENT_VIEW)


def can_view_progress(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.LEARNING_PROGRESS_VIEW)


def can_access_enrollment_learning(
    actor: User | None, enrollment: CourseEnrollment
) -> bool:
    return bool(
        actor
        and actor.is_authenticated
        and actor.is_active
        and not actor.is_superuser
        and enrollment.membership.user_id == actor.id
    )


def can_update_own_progress(actor: User | None, enrollment: CourseEnrollment) -> bool:
    return can_access_enrollment_learning(actor, enrollment)
