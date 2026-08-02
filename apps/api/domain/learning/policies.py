# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
from __future__ import annotations

from typing import TYPE_CHECKING

from domain.organizations.capabilities import Capability, capabilities_for_roles
from domain.organizations.choices import RoleCode
from domain.organizations.models import Membership, Organization
from domain.organizations.policies import (
    active_membership,
    active_roles,
    has_capability,
)

if TYPE_CHECKING:
    from domain.identity.models import User

from .models import CohortStaffAssignment, CourseEnrollment, LearningCohort


def has_institutional_learning_scope(
    actor: User | None, organization: Organization
) -> bool:
    """Owners and administrators retain institutional scope; nobody else does."""

    return bool(
        {RoleCode.OWNER, RoleCode.ADMINISTRATOR}
        & active_roles(active_membership(actor, organization))
    )


def active_staff_membership(
    actor: User | None, organization: Organization
) -> Membership | None:
    return active_membership(actor, organization)


def learning_visibility_scope(
    actor: User | None,
    organization: Organization,
    capability: Capability,
    *additional_capabilities: Capability,
) -> tuple[Membership, bool] | None:
    """Resolve an actor's learning scope with one membership/role lookup.

    List selectors need both the capability grant and whether the actor has
    institutional scope. Resolving those separately duplicates the same two
    organization queries for every request.
    """

    membership = active_membership(actor, organization)
    roles = active_roles(membership)
    capabilities = capabilities_for_roles(roles)
    if membership is None or any(
        required not in capabilities
        for required in (capability, *additional_capabilities)
    ):
        return None
    return membership, bool({RoleCode.OWNER, RoleCode.ADMINISTRATOR} & roles)


def has_course_group_staff_scope(actor: User | None, cohort: LearningCohort) -> bool:
    membership = active_staff_membership(actor, cohort.organization)
    return bool(
        membership
        and CohortStaffAssignment.objects.filter(
            cohort=cohort, membership=membership, ended_at__isnull=True
        ).exists()
    )


def can_manage_cohorts(actor: User | None, organization: Organization) -> bool:
    return has_institutional_learning_scope(actor, organization) and has_capability(
        actor, organization, Capability.LEARNING_COHORT_MANAGE
    )


def can_manage_enrollments(actor: User | None, organization: Organization) -> bool:
    return has_institutional_learning_scope(actor, organization) and has_capability(
        actor, organization, Capability.LEARNING_ENROLLMENT_MANAGE
    )


def can_view_cohorts(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.LEARNING_COHORT_VIEW)


def can_view_enrollments(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.LEARNING_ENROLLMENT_VIEW)


def can_view_progress(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.LEARNING_PROGRESS_VIEW)


def can_manage_course_group(actor: User | None, cohort: LearningCohort) -> bool:
    if can_manage_cohorts(actor, cohort.organization):
        return True
    return has_course_group_staff_scope(actor, cohort) and has_capability(
        actor, cohort.organization, Capability.LEARNING_COHORT_VIEW
    )


def can_manage_enrollment(actor: User | None, enrollment: CourseEnrollment) -> bool:
    if can_manage_enrollments(actor, enrollment.organization):
        return True
    cohort = enrollment.effective_cohort
    return bool(
        cohort
        and has_course_group_staff_scope(actor, cohort)
        and has_capability(
            actor, enrollment.organization, Capability.LEARNING_PROGRESS_VIEW
        )
    )


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
