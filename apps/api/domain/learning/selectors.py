# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, cast

from django.db.models import Avg, Count, F, Prefetch, Q, QuerySet
from django.http import Http404
from django.shortcuts import get_object_or_404

from domain.organizations.capabilities import Capability
from domain.organizations.models import Membership, Organization

from .access import access_state
from .choices import ActivityProgressStatus, EnrollmentStatus, ProgressStatus
from .models import (
    AcademicGroup,
    ActivityProgress,
    CourseEnrollment,
    CourseGroupActivity,
    CourseProgress,
    LearningCohort,
    UnitProgress,
)
from .policies import (
    can_view_progress,
    has_institutional_learning_scope,
    learning_visibility_scope,
)
from .services import completion_projection, resolve_resume_target
from .snapshots import (
    snapshot_activity,
    snapshot_navigation,
    snapshot_outline,
    snapshot_unit,
)

if TYPE_CHECKING:
    from domain.identity.models import User


def cohorts_visible_to_actor(
    actor: object,
    organization: Organization,
    *,
    scope: tuple[Membership, bool] | None = None,
) -> QuerySet[LearningCohort]:
    scope = scope or learning_visibility_scope(
        cast("User | None", actor), organization, Capability.LEARNING_COHORT_VIEW
    )
    if scope is None:
        return LearningCohort.objects.none()
    membership, has_institutional_scope = scope
    queryset = LearningCohort.objects.filter(organization=organization).select_related(
        "course",
        "release",
        "academic_period",
        "academic_group",
        "created_by",
        "updated_by",
    )
    if has_institutional_scope:
        return queryset
    return queryset.filter(
        staff_assignments__membership=membership,
        staff_assignments__ended_at__isnull=True,
    ).distinct()


def academic_groups_visible_to_actor(
    actor: object, organization: Organization
) -> QuerySet[AcademicGroup]:
    if not has_institutional_learning_scope(actor, organization):  # type: ignore[arg-type]
        return AcademicGroup.objects.none()
    return AcademicGroup.objects.filter(organization=organization).prefetch_related(
        "roster__membership__user", "course_cohorts__course"
    )


def enrollments_visible_to_actor(
    actor: object,
    organization: Organization,
    *,
    scope: tuple[Membership, bool] | None = None,
) -> QuerySet[CourseEnrollment]:
    scope = scope or learning_visibility_scope(
        cast("User | None", actor), organization, Capability.LEARNING_ENROLLMENT_VIEW
    )
    if scope is None:
        return CourseEnrollment.objects.none()
    membership, has_institutional_scope = scope
    queryset = (
        CourseEnrollment.objects.filter(organization=organization)
        .select_related(
            "membership__user",
            "course__publication",
            "cohort",
            "cohort__academic_period",
            "current_release_assignment__release",
            "current_release_assignment__progress",
        )
        .prefetch_related(
            Prefetch(
                "current_release_assignment__progress__activity_progress",
                queryset=ActivityProgress.objects.select_related("group_activity"),
            )
        )
    )
    if has_institutional_scope:
        return queryset
    return queryset.filter(
        cohort_assignments__ended_at__isnull=True,
        cohort_assignments__cohort__staff_assignments__membership=membership,
        cohort_assignments__cohort__staff_assignments__ended_at__isnull=True,
    ).distinct()


def progress_visible_to_actor(
    actor: object,
    organization: Organization,
    *,
    scope: tuple[Membership, bool] | None = None,
) -> QuerySet[CourseProgress]:
    scope = scope or learning_visibility_scope(
        cast("User | None", actor), organization, Capability.LEARNING_PROGRESS_VIEW
    )
    if scope is None:
        return CourseProgress.objects.none()
    queryset = (
        CourseProgress.objects.filter(
            release_assignment__enrollment__organization=organization
        )
        .select_related(
            "release_assignment__release",
            "release_assignment__enrollment__membership__user",
            "release_assignment__enrollment__course__publication",
            "release_assignment__enrollment__cohort",
            "release_assignment__enrollment__current_release_assignment__release",
            "release_assignment__enrollment__current_release_assignment__progress",
        )
        .prefetch_related(
            Prefetch(
                "activity_progress",
                queryset=ActivityProgress.objects.select_related("group_activity"),
            )
        )
    )
    membership, has_institutional_scope = scope
    if has_institutional_scope:
        return queryset
    return queryset.filter(
        release_assignment__enrollment__cohort_assignments__ended_at__isnull=True,
        release_assignment__enrollment__cohort_assignments__cohort__staff_assignments__membership=membership,
        release_assignment__enrollment__cohort_assignments__cohort__staff_assignments__ended_at__isnull=True,
    ).distinct()


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
        .prefetch_related(
            Prefetch(
                "current_release_assignment__progress__activity_progress",
                queryset=ActivityProgress.objects.select_related("group_activity"),
            )
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
    projection = completion_projection(progress)
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
        "completion": projection["completion"],
        "mastery": projection["mastery"],
        "grade": projection["grade"],
        "attendance": projection["attendance"],
        "blockers": projection["blockers"],
        "is_complete": projection["is_complete"],
    }


def resume_payload(enrollment: CourseEnrollment) -> dict[str, Any]:
    assignment = enrollment.current_release_assignment
    if assignment is None:
        return {
            "unit_id": None,
            "activity_instance_id": None,
            "node_id": None,
            "href": None,
        }
    progress = assignment.progress
    unit_id, node_id = resolve_resume_target(progress)
    cached_rows = getattr(progress, "_prefetched_objects_cache", {}).get(
        "activity_progress"
    )
    activity_instance = next(
        (
            row.group_activity
            for row in (cached_rows or [])
            if row.group_activity.activity_type == "lesson"
            and row.group_activity.binding_snapshot.get("unit_id") == str(unit_id)
        ),
        None,
    )
    if (
        activity_instance is None
        and cached_rows is None
        and enrollment.effective_cohort
    ):
        activity_instance = CourseGroupActivity.objects.filter(
            course_group=enrollment.effective_cohort,
            activity_type="lesson",
            binding_snapshot__unit_id=str(unit_id),
        ).first()
    href = f"/organizaciones/{enrollment.organization.slug}/aprender/{enrollment.course.slug}"
    href += (
        f"/actividades/{activity_instance.id}"
        if activity_instance
        else f"/unidades/{unit_id}"
    )
    if node_id:
        href += f"#node-{node_id}"
    return {
        "unit_id": unit_id,
        "activity_instance_id": activity_instance.id if activity_instance else None,
        "node_id": node_id,
        "href": href,
    }


def cohort_payload(enrollment: CourseEnrollment) -> dict[str, Any] | None:
    cohort = enrollment.effective_cohort
    return {"id": cohort.id, "name": cohort.name} if cohort else None


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
        "cohort": cohort_payload(enrollment),
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
    activity_rows = list(
        ActivityProgress.objects.filter(course_progress=progress).select_related(
            "group_activity"
        )
    )
    activity_progress_by_source = {
        row.group_activity.source_activity_id: row for row in activity_rows
    }
    activity_instance_by_source = {
        row.group_activity.source_activity_id: row.group_activity
        for row in activity_rows
    }
    modules = snapshot_outline(assignment.release)
    for module in modules:
        for activity in module["activities"]:
            source_activity_id = uuid.UUID(activity["id"])
            row = activity_progress_by_source.get(source_activity_id)
            instance = activity_instance_by_source.get(source_activity_id)
            activity["source_activity_id"] = source_activity_id
            activity["id"] = instance.id if instance else source_activity_id
            activity["status"] = row.status if row else ActivityProgressStatus.AVAILABLE
            activity["is_current"] = activity["type"] == "lesson" and activity[
                "binding"
            ].get("unit_id") == str(progress.last_unit_id)
            activity["blocked_reason"] = (
                "Debes cumplir las condiciones de disponibilidad."
                if activity["status"] == ActivityProgressStatus.LOCKED
                else None
            )
            activity["href"] = (
                f"/organizaciones/{enrollment.organization.slug}/aprender/"
                f"{enrollment.course.slug}/actividades/{activity['id']}"
            )
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
        "cohort": cohort_payload(enrollment),
        "resume": resume_payload(enrollment),
        "modules": modules,
    }


def learning_activity(
    enrollment: CourseEnrollment, activity_instance_id: uuid.UUID
) -> dict[str, Any]:
    assignment = enrollment.current_release_assignment
    if assignment is None:
        raise ValueError("Enrollment has no current assignment.")
    progress = assignment.progress
    cohort = enrollment.effective_cohort
    if cohort is None:
        raise Http404
    instance = get_object_or_404(
        CourseGroupActivity.objects.filter(
            course_group=cohort,
            course_release=assignment.release,
            migration_review_required=False,
        ),
        pk=activity_instance_id,
    )
    snapshot = snapshot_activity(assignment.release, instance.source_activity_id)
    activity_progress = get_object_or_404(
        ActivityProgress, course_progress=progress, group_activity=instance
    )
    navigation = snapshot_navigation(assignment.release, instance.source_activity_id)
    base = (
        f"/organizaciones/{enrollment.organization.slug}/aprender/"
        f"{enrollment.course.slug}/actividades"
    )
    instance_ids = {
        row.source_activity_id: row.id
        for row in CourseGroupActivity.objects.filter(
            course_group=cohort, course_release=assignment.release
        )
    }
    for direction in ("previous", "next"):
        target = navigation[direction]
        if isinstance(target, dict):
            target_id = instance_ids.get(uuid.UUID(target["id"]))
            target["source_activity_id"] = target["id"]
            target["id"] = target_id
            target["href"] = f"{base}/{target_id}" if target_id else None
    navigation["outline"] = base.rsplit("/actividades", 1)[0]
    payload: dict[str, Any] = {
        "course": {
            "id": enrollment.course_id,
            "slug": enrollment.course.slug,
            "title": assignment.release.title,
        },
        "module": snapshot.pop("module"),
        "activity": {
            **snapshot,
            "id": instance.id,
            "source_activity_id": instance.source_activity_id,
            "status": activity_progress.status,
            "evidence": activity_progress.evidence,
            "blocked_reason": (
                "Debes cumplir las condiciones de disponibilidad."
                if activity_progress.status == ActivityProgressStatus.LOCKED
                else None
            ),
        },
        "release_number": assignment.release.number,
        "progress": progress_payload(progress),
        "navigation": navigation,
    }
    if instance.activity_type == "lesson":
        unit_id = uuid.UUID(instance.binding_snapshot["unit_id"])
        unit = snapshot_unit(assignment.release, unit_id)
        payload["lesson"] = {
            "unit_id": unit_id,
            "lesson_kind": unit["lesson_kind"],
            "topics": unit["topics"],
            "learning_objectives": unit["learning_objectives"],
            "delivery": unit["delivery"],
        }
    return payload


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
    activity_instance_ids = {
        row.group_activity.source_activity_id: row.group_activity_id
        for row in ActivityProgress.objects.filter(
            course_progress=progress
        ).select_related("group_activity")
    }
    for direction in ("previous", "next"):
        target = navigation[direction]
        if isinstance(target, dict):
            source_activity_id = uuid.UUID(target["id"])
            if target.get("type") == "lesson":
                target["href"] = f"{base}/unidades/{source_activity_id}"
            else:
                activity_instance_id = activity_instance_ids.get(source_activity_id)
                target["source_activity_id"] = source_activity_id
                target["id"] = activity_instance_id
                target["href"] = (
                    f"{base}/actividades/{activity_instance_id}"
                    if activity_instance_id
                    else None
                )
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
            "lesson_kind": unit["lesson_kind"],
            "position": unit["position"],
            "status": state,
        },
        "release_number": assignment.release.number,
        "topics": unit["topics"],
        "learning_objectives": unit["learning_objectives"],
        "delivery": unit["delivery"],
        "progress": progress_payload(progress),
        "navigation": navigation,
    }


def progress_summary(
    actor: object, organization: Organization, enrollment_id: uuid.UUID
) -> CourseProgress:
    if not can_view_progress(actor, organization):  # type: ignore[arg-type]
        raise Http404
    enrollment = get_object_or_404(
        enrollments_visible_to_actor(actor, organization), pk=enrollment_id
    )
    if enrollment.current_release_assignment_id is None:
        raise Http404
    return enrollment.current_release_assignment.progress


def cohort_progress_summary(
    actor: object, organization: Organization, cohort_id: uuid.UUID
) -> dict[str, Any]:
    scope = learning_visibility_scope(
        cast("User | None", actor),
        organization,
        Capability.LEARNING_COHORT_VIEW,
        Capability.LEARNING_ENROLLMENT_VIEW,
        Capability.LEARNING_PROGRESS_VIEW,
    )
    if scope is None:
        raise Http404
    cohort = get_object_or_404(
        cohorts_visible_to_actor(actor, organization, scope=scope), pk=cohort_id
    )
    rows = (
        progress_visible_to_actor(actor, organization, scope=scope)
        .filter(
            release_assignment__enrollment__cohort_assignments__cohort=cohort,
            release_assignment__enrollment__cohort_assignments__ended_at__isnull=True,
            release_assignment__enrollment__current_release_assignment=F(
                "release_assignment"
            ),
        )
        .order_by("-last_activity_at", "id")
    )
    aggregates = (
        enrollments_visible_to_actor(actor, organization, scope=scope)
        .filter(
            cohort_assignments__cohort=cohort,
            cohort_assignments__ended_at__isnull=True,
        )
        .aggregate(
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
    )
    return {**aggregates, "rows": rows}
