from __future__ import annotations

from datetime import datetime

from django.db.models import Q, QuerySet
from django.utils import timezone

from domain.courses.models import Course
from domain.organizations.choices import MembershipStatus
from domain.organizations.models import Organization
from domain.publishing.choices import PublicationStatus

from .access import access_state
from .choices import AccessState, EnrollmentStatus
from .models import CourseEnrollment


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
