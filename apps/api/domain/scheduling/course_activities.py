# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from domain.courses.choices import ActivityType, AuthoringStatus
from domain.courses.models import CourseActivity, CourseRevision
from domain.courses.policies import (
    can_manage_course,
    has_course_academic_responsibility,
)
from domain.organizations.models import Organization

from .exceptions import SchedulingAccessDenied, SchedulingConflict, SchedulingInvalid
from .models import LiveClassActivityBinding


@transaction.atomic
def bind_live_class_activity(
    *,
    actor: Any,
    organization: Organization,
    activity: CourseActivity,
    expected_revision_version: int,
    minimum_attended_occurrences: int,
    minimum_attendance_minutes: int | None,
) -> tuple[LiveClassActivityBinding, int]:
    locked_revision = CourseRevision.objects.select_for_update().get(
        pk=activity.module.revision_id
    )
    if not can_manage_course(
        actor, organization
    ) or not has_course_academic_responsibility(
        actor, organization, course=locked_revision.course
    ):
        raise SchedulingAccessDenied("No puedes vincular esta actividad.")
    if locked_revision.lock_version != expected_revision_version:
        raise SchedulingConflict("La revisión cambió; actualiza antes de vincular.")
    if locked_revision.authoring_status not in {
        AuthoringStatus.DRAFT,
        AuthoringStatus.CHANGES_REQUESTED,
    }:
        raise SchedulingInvalid("La revisión del curso no es editable.")
    if (
        activity.activity_type != ActivityType.LIVE_CLASS
        or activity.module.revision_id != locked_revision.id
        or locked_revision.course.organization_id != organization.id
    ):
        raise SchedulingInvalid("La vinculación curricular no es válida.")
    if LiveClassActivityBinding.objects.filter(activity=activity).exists():
        raise SchedulingConflict("La actividad ya tiene una política vinculada.")
    binding = LiveClassActivityBinding(
        activity=activity,
        minimum_attended_occurrences=minimum_attended_occurrences,
        minimum_attendance_minutes=minimum_attendance_minutes,
        created_by=actor,
    )
    try:
        binding.full_clean()
    except ValidationError as error:
        raise SchedulingInvalid("La política de asistencia no es válida.") from error
    binding.save()
    locked_revision.lock_version += 1
    locked_revision.updated_by = actor
    locked_revision.save(update_fields=["lock_version", "updated_by", "updated_at"])
    return binding, locked_revision.lock_version


def readiness_issues(revision: CourseRevision) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    cached_activities = getattr(revision, "_readiness_active_activities", None)
    activities = (
        [
            activity
            for activity in cached_activities
            if activity.activity_type == ActivityType.LIVE_CLASS
        ]
        if cached_activities is not None
        else list(
            CourseActivity.objects.filter(
                module__revision=revision,
                activity_type=ActivityType.LIVE_CLASS,
                status="active",
            )
        )
    )
    if not activities:
        return issues
    bound_ids = set(
        LiveClassActivityBinding.objects.filter(activity__in=activities).values_list(
            "activity_id", flat=True
        )
    )
    for activity in activities:
        if activity.id not in bound_ids:
            issues.append(
                {
                    "code": "live_class_binding_required",
                    "path": f"activities.{activity.id}",
                    "message": "La clase en vivo no tiene política operativa.",
                }
            )
    return issues


def snapshot_binding(activity: CourseActivity) -> dict[str, Any]:
    binding = LiveClassActivityBinding.objects.get(activity=activity)
    return {
        "provider": "scheduling",
        "minimum_attended_occurrences": binding.minimum_attended_occurrences,
        "minimum_attendance_minutes": binding.minimum_attendance_minutes,
    }


def clone_binding(source: CourseActivity, target: CourseActivity, actor: Any) -> None:
    binding = LiveClassActivityBinding.objects.get(activity=source)
    LiveClassActivityBinding.objects.create(
        activity=target,
        minimum_attended_occurrences=binding.minimum_attended_occurrences,
        minimum_attendance_minutes=binding.minimum_attendance_minutes,
        created_by=actor,
    )
