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
from .choices import AccessState, EnrollmentStatus
from .models import CourseEnrollment, ExternalLearningRequirement

EXTERNAL_REQUIREMENT_LIVE_SESSION = "live_session"


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


def effective_enrollments_for_actor(
    *, actor: object, organization: Organization, at: datetime | None = None
) -> QuerySet[CourseEnrollment]:
    actor_id = getattr(actor, "id", None)
    if actor_id is None or not getattr(actor, "is_active", False):
        return CourseEnrollment.objects.none()
    moment = at or timezone.now()
    return CourseEnrollment.objects.filter(
        organization=organization,
        membership__user_id=actor_id,
        membership__status=MembershipStatus.ACTIVE,
        status=EnrollmentStatus.ACTIVE,
        current_release_assignment__isnull=False,
        current_release_assignment__ended_at__isnull=True,
        course__publication__status=PublicationStatus.ACTIVE,
    ).filter(
        Q(access_starts_at__isnull=True) | Q(access_starts_at__lte=moment),
        Q(access_ends_at__isnull=True) | Q(access_ends_at__gt=moment),
    )


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
