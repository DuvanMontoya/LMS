# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import uuid
from typing import Any

from django.db.models import Avg, Count, F, Q, QuerySet
from django.http import Http404
from django.shortcuts import get_object_or_404

from domain.organizations.models import Organization

from .access import access_state
from .choices import EnrollmentStatus, ProgressStatus
from .models import (
    AcademicGroup,
    CourseEnrollment,
    CourseProgress,
    LearningCohort,
    UnitProgress,
)
from .policies import can_view_cohorts, can_view_enrollments, can_view_progress
from .services import resolve_resume_target
from .snapshots import snapshot_navigation, snapshot_outline, snapshot_unit


def cohorts_visible_to_actor(
    actor: object, organization: Organization
) -> QuerySet[LearningCohort]:
    if not can_view_cohorts(actor, organization):  # type: ignore[arg-type]
        return LearningCohort.objects.none()
    return LearningCohort.objects.filter(organization=organization).select_related(
        "course", "release", "academic_group", "created_by", "updated_by"
    )


def academic_groups_visible_to_actor(
    actor: object, organization: Organization
) -> QuerySet[AcademicGroup]:
    if not can_view_cohorts(actor, organization):  # type: ignore[arg-type]
        return AcademicGroup.objects.none()
    return AcademicGroup.objects.filter(organization=organization).prefetch_related(
        "roster__membership__user", "course_cohorts__course"
    )


def enrollments_visible_to_actor(
    actor: object, organization: Organization
) -> QuerySet[CourseEnrollment]:
    if not can_view_enrollments(actor, organization):  # type: ignore[arg-type]
        return CourseEnrollment.objects.none()
    return CourseEnrollment.objects.filter(organization=organization).select_related(
        "membership__user",
        "course__publication",
        "cohort",
        "current_release_assignment__release",
        "current_release_assignment__progress",
    )


def progress_visible_to_actor(
    actor: object, organization: Organization
) -> QuerySet[CourseProgress]:
    if not can_view_progress(actor, organization):  # type: ignore[arg-type]
        return CourseProgress.objects.none()
    return CourseProgress.objects.filter(
        release_assignment__enrollment__organization=organization
    ).select_related(
        "release_assignment__release",
        "release_assignment__enrollment__membership__user",
        "release_assignment__enrollment__course__publication",
        "release_assignment__enrollment__cohort",
        "release_assignment__enrollment__current_release_assignment__release",
        "release_assignment__enrollment__current_release_assignment__progress",
    )


def enrollment_visible_to_actor(
    actor: object, organization: Organization, enrollment_id: uuid.UUID
) -> CourseEnrollment:
    return get_object_or_404(
        enrollments_visible_to_actor(actor, organization), pk=enrollment_id
    )


def cohort_visible_to_actor(
    actor: object, organization: Organization, cohort_id: uuid.UUID
) -> LearningCohort:
    return get_object_or_404(
        cohorts_visible_to_actor(actor, organization), pk=cohort_id
    )


def my_active_enrollments(
    actor: object, organization: Organization
) -> QuerySet[CourseEnrollment]:
    actor_id = getattr(actor, "id", None)
    if actor_id is None or not getattr(actor, "is_active", False):
        return CourseEnrollment.objects.none()
    return (
        CourseEnrollment.objects.filter(
            organization=organization,
            membership__user_id=actor_id,
        )
        .exclude(status=EnrollmentStatus.REVOKED)
        .select_related(
            "organization",
            "membership__user",
            "course__publication",
            "cohort",
            "current_release_assignment__release__source_revision",
            "current_release_assignment__release__previous_release",
            "current_release_assignment__progress",
        )
    )


def my_enrollment(
    actor: object, organization: Organization, enrollment_id: uuid.UUID
) -> CourseEnrollment:
    return get_object_or_404(
        my_active_enrollments(actor, organization), pk=enrollment_id
    )


def my_course_enrollment(
    actor: object, organization: Organization, course_slug: str
) -> CourseEnrollment:
    return get_object_or_404(
        my_active_enrollments(actor, organization), course__slug=course_slug
    )


def progress_payload(progress: CourseProgress) -> dict[str, Any]:
    return {
        "status": progress.status,
        "completed_units": progress.completed_units,
        "total_units": progress.total_units,
        "completed_required_activities": progress.completed_required_activities,
        "total_required_activities": progress.total_required_activities,
        "percent_basis_points": progress.percent_basis_points,
        "percent": progress.percent_basis_points / 100,
        "progress_version": progress.lock_version,
        "started_at": progress.started_at,
        "last_activity_at": progress.last_activity_at,
        "completed_at": progress.completed_at,
    }


def resume_payload(enrollment: CourseEnrollment) -> dict[str, Any]:
    assignment = enrollment.current_release_assignment
    if assignment is None:
        return {"unit_id": None, "node_id": None, "href": None}
    progress = assignment.progress
    unit_id, node_id = resolve_resume_target(progress)
    href = (
        f"/organizaciones/{enrollment.organization.slug}/aprender/"
        f"{enrollment.course.slug}/unidades/{unit_id}"
    )
    if node_id:
        href += f"#node-{node_id}"
    return {"unit_id": unit_id, "node_id": node_id, "href": href}


def my_learning_payload(enrollment: CourseEnrollment) -> dict[str, Any]:
    assignment = enrollment.current_release_assignment
    if assignment is None:
        raise ValueError("Enrollment has no current assignment.")
    release = assignment.release
    return {
        "enrollment_id": enrollment.id,
        "course": {
            "id": enrollment.course_id,
            "slug": enrollment.course.slug,
            "title": release.title,
            "summary": release.summary,
        },
        "release_number": release.number,
        "status": enrollment.status,
        "access_state": access_state(enrollment),
        "progress": progress_payload(assignment.progress),
        "resume": resume_payload(enrollment),
        "cohort": (
            {"id": enrollment.cohort_id, "name": enrollment.cohort.name}
            if enrollment.cohort_id
            else None
        ),
    }


def learning_outline(enrollment: CourseEnrollment) -> dict[str, Any]:
    assignment = enrollment.current_release_assignment
    if assignment is None:
        raise ValueError("Enrollment has no current assignment.")
    progress = assignment.progress
    states = {
        row.unit_id: row.status
        for row in UnitProgress.objects.filter(course_progress=progress).only(
            "unit_id", "status"
        )
    }
    modules = snapshot_outline(assignment.release)
    for module in modules:
        for unit in module["units"]:
            unit_id = uuid.UUID(unit["id"])
            unit["status"] = states.get(unit_id, ProgressStatus.NOT_STARTED)
            unit["is_current"] = progress.last_unit_id == unit_id
            unit["href"] = (
                f"/organizaciones/{enrollment.organization.slug}/aprender/"
                f"{enrollment.course.slug}/unidades/{unit_id}"
            )
    return {
        "course": {
            "id": enrollment.course_id,
            "slug": enrollment.course.slug,
            "title": assignment.release.title,
            "summary": assignment.release.summary,
        },
        "release_number": assignment.release.number,
        "progress": progress_payload(progress),
        "cohort": (
            {"id": enrollment.cohort_id, "name": enrollment.cohort.name}
            if enrollment.cohort_id
            else None
        ),
        "resume": resume_payload(enrollment),
        "modules": modules,
    }


def learning_unit(enrollment: CourseEnrollment, unit_id: uuid.UUID) -> dict[str, Any]:
    assignment = enrollment.current_release_assignment
    if assignment is None:
        raise ValueError("Enrollment has no current assignment.")
    progress = assignment.progress
    unit = snapshot_unit(assignment.release, unit_id)
    navigation = snapshot_navigation(assignment.release, unit_id)
    unit_progress = UnitProgress.objects.filter(
        course_progress=progress, unit_id=unit_id
    ).first()
    state = unit_progress.status if unit_progress else ProgressStatus.NOT_STARTED
    base = (
        f"/organizaciones/{enrollment.organization.slug}/aprender/"
        f"{enrollment.course.slug}"
    )
    for direction in ("previous", "next"):
        target = navigation[direction]
        if isinstance(target, dict):
            target["href"] = f"{base}/unidades/{target['id']}"
    navigation["outline"] = base
    return {
        "course": {
            "id": enrollment.course_id,
            "slug": enrollment.course.slug,
            "title": assignment.release.title,
        },
        "module": unit.pop("module"),
        "unit": {
            "id": unit["id"],
            "title": unit["title"],
            "summary": unit["summary"],
            "position": unit["position"],
            "status": state,
        },
        "release_number": assignment.release.number,
        "topics": unit["topics"],
        "learning_objectives": unit["learning_objectives"],
        "content": unit["content"]["document"],
        "progress": progress_payload(progress),
        "navigation": navigation,
    }


def progress_summary(
    actor: object, organization: Organization, enrollment_id: uuid.UUID
) -> CourseProgress:
    if not can_view_progress(actor, organization):  # type: ignore[arg-type]
        raise Http404
    enrollment = get_object_or_404(
        CourseEnrollment.objects.filter(organization=organization).select_related(
            "current_release_assignment__progress"
        ),
        pk=enrollment_id,
    )
    if enrollment.current_release_assignment_id is None:
        raise Http404
    return enrollment.current_release_assignment.progress


def cohort_progress_summary(
    actor: object, organization: Organization, cohort_id: uuid.UUID
) -> dict[str, Any]:
    cohort = cohort_visible_to_actor(actor, organization, cohort_id)
    rows = (
        progress_visible_to_actor(actor, organization)
        .filter(
            release_assignment__enrollment__cohort=cohort,
            release_assignment__enrollment__current_release_assignment=F(
                "release_assignment"
            ),
        )
        .order_by("-last_activity_at", "id")
    )
    aggregates = CourseEnrollment.objects.filter(cohort=cohort).aggregate(
        total_enrollments=Count("id"),
        active=Count("id", filter=Q(status=EnrollmentStatus.ACTIVE)),
        suspended=Count("id", filter=Q(status=EnrollmentStatus.SUSPENDED)),
        revoked=Count("id", filter=Q(status=EnrollmentStatus.REVOKED)),
        not_started=Count(
            "id",
            filter=Q(
                current_release_assignment__progress__status=ProgressStatus.NOT_STARTED
            ),
        ),
        in_progress=Count(
            "id",
            filter=Q(
                current_release_assignment__progress__status=ProgressStatus.IN_PROGRESS
            ),
        ),
        completed=Count(
            "id",
            filter=Q(
                current_release_assignment__progress__status=ProgressStatus.COMPLETED
            ),
        ),
        average_basis_points=Avg(
            "current_release_assignment__progress__percent_basis_points"
        ),
    )
    return {**aggregates, "rows": rows}
