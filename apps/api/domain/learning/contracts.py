from __future__ import annotations

import uuid
from datetime import datetime

from django.db.models import Q, QuerySet
from django.utils import timezone

from domain.courses.models import Course
from domain.organizations.choices import MembershipStatus
from domain.organizations.models import Organization
from domain.publishing.choices import PublicationStatus

from .access import access_state
from .choices import AccessState, EnrollmentStatus, EnrollmentWindowMode
from .models import (
    ActivityProgress,
    CohortStaffAssignment,
    CourseEnrollment,
    EnrollmentCohortAssignment,
    ExternalLearningRequirement,
    LearningCohort,
)

EXTERNAL_REQUIREMENT_LIVE_SESSION = "live_session"


def group_activity_available_for_release_assignment(
    *, group_activity_id: uuid.UUID, release_assignment_id: uuid.UUID
) -> bool:
    return ActivityProgress.objects.filter(
        group_activity_id=group_activity_id,
        course_progress__release_assignment_id=release_assignment_id,
        status__in=[
            "available",
            "in_progress",
            "completed",
            "passed",
            "failed",
            "waived",
        ],
    ).exists()


def register_live_session_requirement(
    *,
    actor: object,
    organization: Organization,
    course: Course,
    source_id: uuid.UUID,
    title: str,
) -> ExternalLearningRequirement:
    from .services import register_external_requirement

    return register_external_requirement(
        actor=actor,
        organization=organization,
        course=course,
        source_type=EXTERNAL_REQUIREMENT_LIVE_SESSION,
        source_id=source_id,
        title=title,
    )


def deactivate_live_session_requirement(*, actor: object, source_id: uuid.UUID) -> None:
    from .services import deactivate_external_requirement

    deactivate_external_requirement(
        actor=actor,
        source_type=EXTERNAL_REQUIREMENT_LIVE_SESSION,
        source_id=source_id,
    )


def complete_live_session_requirement(
    *,
    actor: object,
    source_id: uuid.UUID,
    completed_at: datetime,
    evidence: dict[str, object],
) -> bool:
    from .services import complete_external_requirement

    return complete_external_requirement(
        actor=actor,
        source_type=EXTERNAL_REQUIREMENT_LIVE_SESSION,
        source_id=source_id,
        completed_at=completed_at,
        evidence=evidence,
    )


def complete_group_activity_attendance(
    *,
    actor: object,
    group_activity_id: uuid.UUID,
    completed_at: datetime,
    evidence: dict[str, object],
) -> bool:
    from .services import complete_activity_from_attendance

    return complete_activity_from_attendance(
        actor=actor,
        group_activity_id=group_activity_id,
        completed_at=completed_at,
        evidence=evidence,
    )


def record_group_activity_assessment_result(
    *,
    actor: object | None,
    group_activity_id: uuid.UUID,
    release_assignment_id: uuid.UUID,
    grade_version_id: uuid.UUID,
    occurred_at: datetime,
    grade_basis_points: int | None,
    passed: bool | None,
    mastered_objective_ids: list[str] | None = None,
) -> bool:
    from .services import record_activity_from_assessment

    return record_activity_from_assessment(
        actor=actor,
        group_activity_id=group_activity_id,
        release_assignment_id=release_assignment_id,
        grade_version_id=grade_version_id,
        occurred_at=occurred_at,
        grade_basis_points=grade_basis_points,
        passed=passed,
        mastered_objective_ids=mastered_objective_ids,
    )


def effective_enrollments_for_actor(
    *, actor: object, organization: Organization, at: datetime | None = None
) -> QuerySet[CourseEnrollment]:
    actor_id = getattr(actor, "id", None)
    if actor_id is None or not getattr(actor, "is_active", False):
        return CourseEnrollment.objects.none()
    moment = at or timezone.now()
    enrollments = CourseEnrollment.objects.filter(
        organization=organization,
        membership__user_id=actor_id,
        membership__status=MembershipStatus.ACTIVE,
        status=EnrollmentStatus.ACTIVE,
        current_release_assignment__isnull=False,
        current_release_assignment__ended_at__isnull=True,
        course__publication__status=PublicationStatus.ACTIVE,
    )
    individual_window = (
        Q(access_window_mode=EnrollmentWindowMode.INDIVIDUAL)
        & (Q(access_starts_at__isnull=True) | Q(access_starts_at__lte=moment))
        & (Q(access_ends_at__isnull=True) | Q(access_ends_at__gt=moment))
    )
    inherited_window = (
        Q(
            access_window_mode=EnrollmentWindowMode.INHERIT,
            cohort_assignments__ended_at__isnull=True,
        )
        & (
            Q(cohort_assignments__cohort__access_starts_at__isnull=True)
            | Q(cohort_assignments__cohort__access_starts_at__lte=moment)
        )
        & (
            Q(cohort_assignments__cohort__access_ends_at__isnull=True)
            | Q(cohort_assignments__cohort__access_ends_at__gt=moment)
        )
    )
    return enrollments.filter(individual_window | inherited_window).distinct()


def effective_course_enrollment(
    *,
    actor: object,
    organization: Organization,
    course: Course,
    at: datetime | None = None,
) -> CourseEnrollment | None:
    enrollment = (
        effective_enrollments_for_actor(actor=actor, organization=organization, at=at)
        .filter(course=course)
        .select_related(
            "membership__user",
            "course__publication",
            "current_release_assignment__release",
        )
        .first()
    )
    if enrollment is None:
        return None
    return (
        enrollment if access_state(enrollment, at=at) == AccessState.AVAILABLE else None
    )


def effective_course_ids_for_actor(
    *, actor: object, organization: Organization, at: datetime | None = None
) -> set[object]:
    return set(
        effective_enrollments_for_actor(
            actor=actor, organization=organization, at=at
        ).values_list("course_id", flat=True)
    )


def course_group_for_scheduling(
    *, organization: Organization, course_group_id: uuid.UUID
) -> LearningCohort | None:
    """Stable lookup boundary for the scheduling module."""

    return (
        LearningCohort.objects.select_related("course", "release")
        .filter(pk=course_group_id, organization=organization, status="active")
        .first()
    )


def actor_has_course_group_staff_scope(
    *, actor: object, course_group: LearningCohort
) -> bool:
    actor_id = getattr(actor, "id", None)
    if actor_id is None:
        return False
    return CohortStaffAssignment.objects.filter(
        cohort=course_group,
        membership__user_id=actor_id,
        membership__status=MembershipStatus.ACTIVE,
        ended_at__isnull=True,
    ).exists()


def effective_course_group_enrollment(
    *,
    actor: object,
    organization: Organization,
    course_group: LearningCohort,
    at: datetime | None = None,
) -> CourseEnrollment | None:
    return (
        effective_enrollments_for_actor(actor=actor, organization=organization, at=at)
        .filter(
            cohort_assignments__cohort=course_group,
            cohort_assignments__ended_at__isnull=True,
        )
        .select_related(
            "membership__user",
            "course__publication",
            "current_release_assignment__release",
        )
        .first()
    )


def visible_course_group_ids_for_actor(
    *, actor: object, organization: Organization, at: datetime | None = None
) -> set[uuid.UUID]:
    actor_id = getattr(actor, "id", None)
    if actor_id is None or not getattr(actor, "is_active", False):
        return set()
    staff_ids = CohortStaffAssignment.objects.filter(
        cohort__organization=organization,
        membership__user_id=actor_id,
        membership__status=MembershipStatus.ACTIVE,
        ended_at__isnull=True,
    ).values_list("cohort_id", flat=True)
    learner_ids = EnrollmentCohortAssignment.objects.filter(
        enrollment__in=effective_enrollments_for_actor(
            actor=actor, organization=organization, at=at
        ),
        ended_at__isnull=True,
    ).values_list("cohort_id", flat=True)
    return {*(staff_ids), *(learner_ids)}
