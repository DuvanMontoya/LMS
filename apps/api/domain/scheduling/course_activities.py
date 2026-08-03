# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from domain.catalog.models import LearningObjective
from domain.courses.choices import (
    ActivityCompletionMethod,
    ActivityType,
    AuthoringStatus,
)
from domain.courses.exceptions import (
    CourseAccessDenied,
    CourseDomainError,
    CourseRevisionConflict,
)
from domain.courses.models import CourseActivity, CourseModule, CourseRevision
from domain.courses.policies import (
    can_manage_course,
    has_course_academic_responsibility,
)
from domain.courses.services import (
    create_activity,
    replace_activity_learning_objectives,
    update_activity_configuration,
)
from domain.organizations.models import Organization

from .exceptions import SchedulingAccessDenied, SchedulingConflict, SchedulingInvalid
from .models import LiveClassActivityBinding


@transaction.atomic
def create_and_bind_live_class_activity(
    *,
    actor: Any,
    organization: Organization,
    module: CourseModule,
    expected_revision_version: int,
    title: str,
    summary: str,
    estimated_duration_minutes: int,
    required: bool,
    minimum_attendance_basis_points: int,
    learning_objective_ids: list[Any],
    session_mode: str,
    chat_enabled: bool,
    student_audio_enabled: bool,
    student_video_enabled: bool,
    student_screen_share_enabled: bool,
    recording_mode: str,
    recording_layout: str,
    recording_resolution: str,
    max_participants: int,
    room_empty_timeout_seconds: int,
    room_departure_timeout_seconds: int,
    join_before_minutes: int,
    join_after_minutes: int,
    minimum_attended_occurrences: int = 1,
) -> tuple[LiveClassActivityBinding, CourseActivity, int]:
    objective_rows = list(
        LearningObjective.objects.filter(
            id__in=learning_objective_ids,
            status="active",
            subject__discipline__area__organization=organization,
            course_revision_alignments__revision=module.revision,
        ).distinct()
    )
    objectives_by_id = {objective.id: objective for objective in objective_rows}
    objectives = [
        objectives_by_id[objective_id]
        for objective_id in learning_objective_ids
        if objective_id in objectives_by_id
    ]
    if not objectives or len(objectives) != len(set(learning_objective_ids)):
        raise SchedulingInvalid(
            "Selecciona al menos un objetivo activo y alineado con el curso."
        )
    try:
        activity, revision = create_activity(
            actor=actor,
            organization=organization,
            module=module,
            expected_version=expected_revision_version,
            activity_type=ActivityType.LIVE_CLASS,
            title=title,
            summary=summary,
            estimated_duration_minutes=estimated_duration_minutes,
            required=required,
            completion_method=ActivityCompletionMethod.ATTENDANCE,
            minimum_attendance_basis_points=minimum_attendance_basis_points,
            minimum_grade_basis_points=None,
        )
    except CourseRevisionConflict as error:
        raise SchedulingConflict(str(error)) from error
    except CourseAccessDenied as error:
        raise SchedulingAccessDenied(str(error)) from error
    except CourseDomainError as error:
        raise SchedulingInvalid(str(error)) from error
    try:
        aligned_revision = replace_activity_learning_objectives(
            actor=actor,
            organization=organization,
            activity=activity,
            expected_version=revision.lock_version,
            learning_objectives=objectives,
        )
    except CourseDomainError as error:
        raise SchedulingInvalid(str(error)) from error
    binding, lock_version = bind_live_class_activity(
        actor=actor,
        organization=organization,
        activity=activity,
        expected_revision_version=aligned_revision.lock_version,
        minimum_attended_occurrences=minimum_attended_occurrences,
        minimum_attendance_minutes=max(
            1,
            (estimated_duration_minutes * minimum_attendance_basis_points + 9_999)
            // 10_000,
        ),
        session_mode=session_mode,
        chat_enabled=chat_enabled,
        student_audio_enabled=student_audio_enabled,
        student_video_enabled=student_video_enabled,
        student_screen_share_enabled=student_screen_share_enabled,
        recording_mode=recording_mode,
        recording_layout=recording_layout,
        recording_resolution=recording_resolution,
        max_participants=max_participants,
        room_empty_timeout_seconds=room_empty_timeout_seconds,
        room_departure_timeout_seconds=room_departure_timeout_seconds,
        join_before_minutes=join_before_minutes,
        join_after_minutes=join_after_minutes,
    )
    return binding, activity, lock_version


@transaction.atomic
def update_live_class_activity(
    *,
    actor: Any,
    organization: Organization,
    activity: CourseActivity,
    expected_revision_version: int,
    title: str,
    summary: str,
    estimated_duration_minutes: int,
    required: bool,
    minimum_attendance_basis_points: int,
    learning_objective_ids: list[Any],
    session_mode: str,
    chat_enabled: bool,
    student_audio_enabled: bool,
    student_video_enabled: bool,
    student_screen_share_enabled: bool,
    recording_mode: str,
    recording_layout: str,
    recording_resolution: str,
    max_participants: int,
    room_empty_timeout_seconds: int,
    room_departure_timeout_seconds: int,
    join_before_minutes: int,
    join_after_minutes: int,
) -> tuple[LiveClassActivityBinding, CourseActivity, int]:
    objective_rows = list(
        LearningObjective.objects.filter(
            id__in=learning_objective_ids,
            status="active",
            subject__discipline__area__organization=organization,
            course_revision_alignments__revision=activity.module.revision,
        ).distinct()
    )
    objectives_by_id = {objective.id: objective for objective in objective_rows}
    objectives = [
        objectives_by_id[objective_id]
        for objective_id in learning_objective_ids
        if objective_id in objectives_by_id
    ]
    if not objectives or len(objectives) != len(set(learning_objective_ids)):
        raise SchedulingInvalid(
            "Selecciona al menos un objetivo activo y alineado con el curso."
        )
    try:
        updated_activity, revision = update_activity_configuration(
            actor=actor,
            organization=organization,
            activity=activity,
            expected_version=expected_revision_version,
            title=title,
            summary=summary,
            estimated_duration_minutes=estimated_duration_minutes,
            required=required,
            completion_method=ActivityCompletionMethod.ATTENDANCE,
            minimum_attendance_basis_points=minimum_attendance_basis_points,
            minimum_grade_basis_points=None,
        )
        aligned_revision = replace_activity_learning_objectives(
            actor=actor,
            organization=organization,
            activity=updated_activity,
            expected_version=revision.lock_version,
            learning_objectives=objectives,
        )
    except CourseRevisionConflict as error:
        raise SchedulingConflict(str(error)) from error
    except CourseAccessDenied as error:
        raise SchedulingAccessDenied(str(error)) from error
    except CourseDomainError as error:
        raise SchedulingInvalid(str(error)) from error
    binding, lock_version = _upsert_live_class_binding(
        actor=actor,
        organization=organization,
        activity=updated_activity,
        expected_revision_version=aligned_revision.lock_version,
        minimum_attendance_minutes=max(
            1,
            (estimated_duration_minutes * minimum_attendance_basis_points + 9_999)
            // 10_000,
        ),
        session_mode=session_mode,
        chat_enabled=chat_enabled,
        student_audio_enabled=student_audio_enabled,
        student_video_enabled=student_video_enabled,
        student_screen_share_enabled=student_screen_share_enabled,
        recording_mode=recording_mode,
        recording_layout=recording_layout,
        recording_resolution=recording_resolution,
        max_participants=max_participants,
        room_empty_timeout_seconds=room_empty_timeout_seconds,
        room_departure_timeout_seconds=room_departure_timeout_seconds,
        join_before_minutes=join_before_minutes,
        join_after_minutes=join_after_minutes,
    )
    return binding, updated_activity, lock_version


@transaction.atomic
def bind_live_class_activity(
    *,
    actor: Any,
    organization: Organization,
    activity: CourseActivity,
    expected_revision_version: int,
    minimum_attended_occurrences: int,
    minimum_attendance_minutes: int | None,
    session_mode: str = "interactive",
    chat_enabled: bool = True,
    student_audio_enabled: bool = True,
    student_video_enabled: bool = True,
    student_screen_share_enabled: bool = False,
    recording_mode: str = "off",
    recording_layout: str = "screen_share",
    recording_resolution: str = "1080p",
    max_participants: int = 100,
    room_empty_timeout_seconds: int = 600,
    room_departure_timeout_seconds: int = 30,
    join_before_minutes: int = 15,
    join_after_minutes: int = 15,
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
        session_mode=session_mode,
        chat_enabled=chat_enabled,
        student_audio_enabled=student_audio_enabled,
        student_video_enabled=student_video_enabled,
        student_screen_share_enabled=student_screen_share_enabled,
        recording_mode=recording_mode,
        recording_layout=recording_layout,
        recording_resolution=recording_resolution,
        max_participants=max_participants,
        room_empty_timeout_seconds=room_empty_timeout_seconds,
        room_departure_timeout_seconds=room_departure_timeout_seconds,
        join_before_minutes=join_before_minutes,
        join_after_minutes=join_after_minutes,
        created_by=actor,
        updated_by=actor,
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


@transaction.atomic
def update_live_class_binding(
    *,
    actor: Any,
    organization: Organization,
    activity: CourseActivity,
    expected_revision_version: int,
    minimum_attendance_minutes: int,
    session_mode: str,
    chat_enabled: bool,
    student_audio_enabled: bool,
    student_video_enabled: bool,
    student_screen_share_enabled: bool,
    recording_mode: str,
    recording_layout: str,
    recording_resolution: str,
    max_participants: int,
    room_empty_timeout_seconds: int,
    room_departure_timeout_seconds: int,
    join_before_minutes: int,
    join_after_minutes: int,
) -> tuple[LiveClassActivityBinding, int]:
    locked_revision = CourseRevision.objects.select_for_update().get(
        pk=activity.module.revision_id
    )
    if not can_manage_course(
        actor, organization
    ) or not has_course_academic_responsibility(
        actor, organization, course=locked_revision.course
    ):
        raise SchedulingAccessDenied("No puedes configurar esta actividad.")
    if locked_revision.lock_version != expected_revision_version:
        raise SchedulingConflict("La revisión cambió; actualiza antes de configurar.")
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
    try:
        binding = LiveClassActivityBinding.objects.select_for_update().get(
            activity=activity
        )
    except LiveClassActivityBinding.DoesNotExist as error:
        raise SchedulingInvalid("La clase no tiene una política LiveKit.") from error
    binding.minimum_attended_occurrences = 1
    binding.minimum_attendance_minutes = minimum_attendance_minutes
    binding.session_mode = session_mode
    binding.chat_enabled = chat_enabled
    binding.student_audio_enabled = student_audio_enabled
    binding.student_video_enabled = student_video_enabled
    binding.student_screen_share_enabled = student_screen_share_enabled
    binding.recording_mode = recording_mode
    binding.recording_layout = recording_layout
    binding.recording_resolution = recording_resolution
    binding.max_participants = max_participants
    binding.room_empty_timeout_seconds = room_empty_timeout_seconds
    binding.room_departure_timeout_seconds = room_departure_timeout_seconds
    binding.join_before_minutes = join_before_minutes
    binding.join_after_minutes = join_after_minutes
    binding.updated_by = actor
    try:
        binding.full_clean()
    except ValidationError as error:
        raise SchedulingInvalid("La política de la sala no es válida.") from error
    binding.save()
    locked_revision.lock_version += 1
    locked_revision.updated_by = actor
    locked_revision.save(update_fields=("lock_version", "updated_by", "updated_at"))
    return binding, locked_revision.lock_version


def _upsert_live_class_binding(
    *,
    actor: Any,
    organization: Organization,
    activity: CourseActivity,
    expected_revision_version: int,
    minimum_attendance_minutes: int,
    session_mode: str,
    chat_enabled: bool,
    student_audio_enabled: bool,
    student_video_enabled: bool,
    student_screen_share_enabled: bool,
    recording_mode: str,
    recording_layout: str,
    recording_resolution: str,
    max_participants: int,
    room_empty_timeout_seconds: int,
    room_departure_timeout_seconds: int,
    join_before_minutes: int,
    join_after_minutes: int,
) -> tuple[LiveClassActivityBinding, int]:
    arguments: dict[str, Any] = {
        "actor": actor,
        "organization": organization,
        "activity": activity,
        "expected_revision_version": expected_revision_version,
        "minimum_attendance_minutes": minimum_attendance_minutes,
        "session_mode": session_mode,
        "chat_enabled": chat_enabled,
        "student_audio_enabled": student_audio_enabled,
        "student_video_enabled": student_video_enabled,
        "student_screen_share_enabled": student_screen_share_enabled,
        "recording_mode": recording_mode,
        "recording_layout": recording_layout,
        "recording_resolution": recording_resolution,
        "max_participants": max_participants,
        "room_empty_timeout_seconds": room_empty_timeout_seconds,
        "room_departure_timeout_seconds": room_departure_timeout_seconds,
        "join_before_minutes": join_before_minutes,
        "join_after_minutes": join_after_minutes,
    }
    if LiveClassActivityBinding.objects.filter(activity=activity).exists():
        return update_live_class_binding(**arguments)
    return bind_live_class_activity(
        **arguments,
        minimum_attended_occurrences=1,
    )


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
        "session_mode": binding.session_mode,
        "chat_enabled": binding.chat_enabled,
        "student_audio_enabled": binding.student_audio_enabled,
        "student_video_enabled": binding.student_video_enabled,
        "student_screen_share_enabled": binding.student_screen_share_enabled,
        "recording_mode": binding.recording_mode,
        "recording_layout": binding.recording_layout,
        "recording_resolution": binding.recording_resolution,
        "max_participants": binding.max_participants,
        "room_empty_timeout_seconds": binding.room_empty_timeout_seconds,
        "room_departure_timeout_seconds": binding.room_departure_timeout_seconds,
        "join_before_minutes": binding.join_before_minutes,
        "join_after_minutes": binding.join_after_minutes,
    }


def clone_binding(source: CourseActivity, target: CourseActivity, actor: Any) -> None:
    binding = LiveClassActivityBinding.objects.get(activity=source)
    LiveClassActivityBinding.objects.create(
        activity=target,
        minimum_attended_occurrences=binding.minimum_attended_occurrences,
        minimum_attendance_minutes=binding.minimum_attendance_minutes,
        session_mode=binding.session_mode,
        chat_enabled=binding.chat_enabled,
        student_audio_enabled=binding.student_audio_enabled,
        student_video_enabled=binding.student_video_enabled,
        student_screen_share_enabled=binding.student_screen_share_enabled,
        recording_mode=binding.recording_mode,
        recording_layout=binding.recording_layout,
        recording_resolution=binding.recording_resolution,
        max_participants=binding.max_participants,
        room_empty_timeout_seconds=binding.room_empty_timeout_seconds,
        room_departure_timeout_seconds=binding.room_departure_timeout_seconds,
        join_before_minutes=binding.join_before_minutes,
        join_after_minutes=binding.join_after_minutes,
        created_by=actor,
    )
