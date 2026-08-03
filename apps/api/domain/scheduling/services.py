# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportUnnecessaryComparison=false
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from domain.courses.choices import CourseStatus
from domain.courses.models import Course
from domain.learning.contracts import (
    actor_has_course_group_staff_scope,
    deactivate_live_session_requirement,
    register_live_session_requirement,
)
from domain.organizations.capabilities import Capability
from domain.organizations.choices import MembershipStatus
from domain.organizations.models import Membership, Organization
from domain.organizations.policies import has_capability

from .choices import (
    EgressStatus,
    EventType,
    LiveSessionStatus,
    OccurrenceStatus,
    RecurrenceScope,
    SeriesStatus,
)
from .exceptions import (
    LiveKitRejected,
    LiveSessionClosed,
    LiveSessionOutsideWindow,
    SchedulingAccessDenied,
    SchedulingConflict,
    SchedulingInvalid,
)
from .livekit_gateway import LiveKitGateway
from .models import (
    AcademicEventOccurrence,
    AcademicEventParticipant,
    AcademicEventSeries,
    LiveRecordingAcknowledgement,
    LiveSession,
    LiveSessionRecording,
)
from .policies import (
    LiveAccess,
    actor_membership,
    can_create_schedule,
    can_edit_series,
    can_manage_schedule,
    live_access,
)
from .recurrence import materialized_windows, rule_until

if TYPE_CHECKING:
    from domain.learning.models import CourseGroupActivity, LearningCohort


def _validate_host(
    *,
    actor: object,
    organization: Organization,
    host: Membership,
    course_group: LearningCohort | None,
) -> None:
    if (
        host.organization_id != organization.id
        or host.status != MembershipStatus.ACTIVE
        or not has_capability(host.user, organization, Capability.LIVE_SESSION_HOST)
    ):
        raise SchedulingInvalid("El profesor no es una membresía docente activa.")
    actor_member = actor_membership(actor, organization)
    if not can_manage_schedule(actor, organization) and (
        actor_member is None or actor_member.id != host.id
    ):
        raise SchedulingAccessDenied("Sólo puedes programar clases propias.")
    if course_group is not None and not actor_has_course_group_staff_scope(
        actor=host.user, course_group=course_group
    ):
        raise SchedulingInvalid(
            "El profesor debe tener una asignación vigente en el grupo de curso."
        )
    if (
        course_group is not None
        and not can_manage_schedule(actor, organization)
        and not actor_has_course_group_staff_scope(
            actor=actor, course_group=course_group
        )
    ):
        raise SchedulingAccessDenied(
            "Sólo el equipo docente del grupo de curso puede programarlo."
        )


@transaction.atomic
def create_event_series(
    *,
    actor: object,
    organization: Organization,
    course: Course | None,
    course_group: LearningCohort | None = None,
    course_group_activity: CourseGroupActivity | None = None,
    host_membership: Membership,
    participant_memberships: list[Membership] | None = None,
    title: str,
    description: str,
    event_type: str,
    timezone_name: str,
    first_starts_at: datetime,
    duration_minutes: int,
    recurrence_rule: str = "",
    counts_toward_progress: bool = False,
    contributes_to_activity_progress: bool | None = None,
    attendance_threshold_minutes: int | None = None,
) -> AcademicEventSeries:
    if not can_create_schedule(actor, organization):
        raise SchedulingAccessDenied("No puedes crear eventos académicos.")
    if course is not None and (
        course.organization_id != organization.id
        or course.status != CourseStatus.ACTIVE
    ):
        raise SchedulingInvalid("El curso no está activo en esta organización.")
    if course_group is not None and (
        course is None
        or course_group.organization_id != organization.id
        or course_group.course_id != course.id
    ):
        raise SchedulingInvalid("El grupo de curso no corresponde al curso activo.")
    if course_group_activity is not None and (
        course_group is None
        or course_group_activity.course_group_id != course_group.id
        or course_group_activity.course_release_id != course_group.release_id
        or course_group_activity.activity_type != "live_class"
        or course_group_activity.migration_review_required
    ):
        raise SchedulingInvalid("La actividad en vivo no corresponde al grupo activo.")
    if (
        course is not None
        and course_group is None
        and not can_manage_schedule(actor, organization)
    ):
        raise SchedulingAccessDenied(
            "Selecciona un grupo de curso que tengas asignado."
        )
    participants = participant_memberships or []
    if course is None and not participants:
        raise SchedulingInvalid(
            "Una sesión independiente necesita al menos un participante invitado."
        )
    if course is not None and participants:
        raise SchedulingInvalid(
            "Las sesiones de curso usan las matrículas; no mezcles invitados explícitos."
        )
    contributes_to_activity = (
        course_group_activity is not None
        if contributes_to_activity_progress is None
        else contributes_to_activity_progress
    )
    if contributes_to_activity and course_group_activity is None:
        raise SchedulingInvalid(
            "Sólo una actividad curricular puede recibir evidencia de asistencia."
        )
    if counts_toward_progress and course is None:
        raise SchedulingInvalid(
            "Sólo una sesión vinculada a un curso puede contar para el progreso."
        )
    if counts_toward_progress and (
        attendance_threshold_minutes is None
        or attendance_threshold_minutes < 1
        or attendance_threshold_minutes > duration_minutes
    ):
        raise SchedulingInvalid(
            "Define un umbral de asistencia entre 1 minuto y la duración de la clase."
        )
    if not counts_toward_progress and attendance_threshold_minutes is not None:
        raise SchedulingInvalid(
            "El umbral sólo aplica cuando la clase cuenta para el progreso."
        )
    participant_ids: set[uuid.UUID] = set()
    for participant in participants:
        if (
            participant.organization_id != organization.id
            or participant.status != MembershipStatus.ACTIVE
        ):
            raise SchedulingInvalid(
                "Todos los participantes deben ser membresías activas de la organización."
            )
        if participant.id in participant_ids:
            raise SchedulingInvalid("No repitas participantes invitados.")
        participant_ids.add(participant.id)
    _validate_host(
        actor=actor,
        organization=organization,
        host=host_membership,
        course_group=course_group,
    )
    windows = materialized_windows(
        first_starts_at=first_starts_at,
        duration_minutes=duration_minutes,
        timezone_name=timezone_name,
        recurrence_rule=recurrence_rule,
    )
    normalized_rule = recurrence_rule.strip().removeprefix("RRULE:").upper()
    series = AcademicEventSeries(
        organization=organization,
        course=course,
        course_group=course_group,
        course_group_activity=course_group_activity,
        host_membership=host_membership,
        title=title,
        description=description,
        event_type=event_type,
        timezone_name=timezone_name,
        first_starts_at=windows[0][0],
        duration_minutes=duration_minutes,
        rrule=normalized_rule,
        recurrence_count=len(windows),
        recurrence_until=rule_until(normalized_rule, windows),
        counts_toward_progress=counts_toward_progress,
        activity_progress_contribution=contributes_to_activity,
        attendance_threshold_minutes=(
            attendance_threshold_minutes if counts_toward_progress else None
        ),
        created_by=actor,
        updated_by=actor,
    )
    series.full_clean()
    series.save()
    AcademicEventParticipant.objects.bulk_create(
        [
            AcademicEventParticipant(
                series=series, membership=participant, added_by=actor
            )
            for participant in participants
        ]
    )
    recording_requested = bool(
        course_group_activity
        and course_group_activity.binding_snapshot.get("provider") == "scheduling"
        and course_group_activity.binding_snapshot.get("recording_mode", "off") != "off"
    )
    egress_status = (
        EgressStatus.IDLE
        if settings.LIVEKIT_EGRESS_ENABLED and recording_requested
        else EgressStatus.DISABLED
    )
    for starts_at, ends_at in windows:
        occurrence = AcademicEventOccurrence.objects.create(
            series=series,
            original_starts_at=starts_at,
            starts_at=starts_at,
            ends_at=ends_at,
        )
        if event_type == EventType.LIVE_CLASS:
            live_session = LiveSession.objects.create(
                occurrence=occurrence,
                egress_status=egress_status,
                created_by=actor,
            )
            if (
                counts_toward_progress
                and course is not None
                and course_group_activity is None
            ):
                register_live_session_requirement(
                    actor=actor,
                    organization=organization,
                    course=course,
                    source_id=live_session.id,
                    title=title,
                )
    return series


@transaction.atomic
def materialize_course_group_live_classes(
    *,
    actor: object,
    organization: Organization,
    course_group: LearningCohort,
    first_week_starts_on: date,
    timezone_name: str,
    slots: list[dict[str, object]],
) -> dict[str, int]:
    """Schedule the release-pinned live activities of one course group.

    A course revision defines a LiveKit policy, while the cohort owns the real
    date, host and occurrence. This operation materializes each pending live
    activity exactly once instead of leaving a learner-facing activity without
    a LiveKit room to enter.
    """
    from domain.courses.models import CourseActivity
    from domain.learning.models import CohortStaffAssignment, CourseGroupActivity

    if not can_create_schedule(actor, organization):
        raise SchedulingAccessDenied("No puedes programar clases del grupo.")
    if (
        course_group.organization_id != organization.id
        or course_group.status != "active"
        or course_group.migration_review_required
    ):
        raise SchedulingInvalid("El grupo de curso no está disponible.")
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise SchedulingInvalid("La zona horaria no es válida.") from error

    normalized_slots: list[tuple[int, time]] = []
    seen_slots: set[tuple[int, time]] = set()
    for slot in slots:
        weekday = slot.get("weekday")
        starts_at = slot.get("starts_at")
        if (
            not isinstance(weekday, int)
            or weekday < 0
            or weekday > 6
            or not isinstance(starts_at, time)
        ):
            raise SchedulingInvalid("Cada horario semanal es inválido.")
        key = (weekday, starts_at)
        if key in seen_slots:
            raise SchedulingInvalid("No repitas el mismo horario semanal.")
        seen_slots.add(key)
        normalized_slots.append(key)
    if not normalized_slots:
        raise SchedulingInvalid("Define al menos un horario semanal.")

    staff_rows = list(
        CohortStaffAssignment.objects.select_related("membership__user")
        .filter(cohort=course_group, ended_at__isnull=True)
        .order_by("started_at", "id")
    )
    host = next(
        (
            row.membership
            for row in staff_rows
            if row.membership.status == MembershipStatus.ACTIVE
            and has_capability(
                row.membership.user, organization, Capability.LIVE_SESSION_HOST
            )
        ),
        None,
    )
    if host is None:
        raise SchedulingInvalid(
            "Asigna primero un docente activo con capacidad para conducir clases en vivo."
        )

    live_activities = list(
        CourseGroupActivity.objects.select_for_update()
        .filter(
            course_group=course_group,
            course_release=course_group.release,
            activity_type=EventType.LIVE_CLASS,
            migration_review_required=False,
        )
        .order_by("module_position", "position", "id")
    )
    if not live_activities:
        raise SchedulingInvalid("El grupo no tiene clases en vivo en su release.")

    per_module: dict[int, int] = {}
    for activity in live_activities:
        per_module[activity.module_position] = (
            per_module.get(activity.module_position, 0) + 1
        )
    max_per_module = max(per_module.values())
    if len(normalized_slots) < max_per_module:
        raise SchedulingInvalid(
            "Define al menos un horario por cada clase en vivo de la semana más cargada."
        )

    source_durations = {
        row.id: row.estimated_duration_minutes
        for row in CourseActivity.objects.filter(
            pk__in=[activity.source_activity_id for activity in live_activities]
        ).only("id", "estimated_duration_minutes")
    }
    missing_duration = next(
        (
            activity.title
            for activity in live_activities
            if not source_durations.get(activity.source_activity_id)
        ),
        None,
    )
    if missing_duration:
        raise SchedulingInvalid(
            f"La clase «{missing_duration}» no tiene una duración configurada."
        )

    week_zero = first_week_starts_on - timedelta(days=first_week_starts_on.weekday())
    first_module_position = min(per_module)
    scheduled_by_module: dict[int, int] = {}
    created_count = 0
    already_scheduled_count = 0
    for activity in live_activities:
        if AcademicEventSeries.objects.filter(course_group_activity=activity).exists():
            already_scheduled_count += 1
            continue
        slot_index = scheduled_by_module.get(activity.module_position, 0)
        scheduled_by_module[activity.module_position] = slot_index + 1
        weekday, starts_at = normalized_slots[slot_index]
        starts_on = week_zero + timedelta(
            weeks=activity.module_position - first_module_position,
            days=weekday,
        )
        create_event_series(
            actor=actor,
            organization=organization,
            course=course_group.course,
            course_group=course_group,
            course_group_activity=activity,
            host_membership=host,
            title=activity.title,
            description=activity.summary,
            event_type=EventType.LIVE_CLASS,
            timezone_name=timezone_name,
            first_starts_at=datetime.combine(starts_on, starts_at, tzinfo=zone),
            duration_minutes=source_durations[activity.source_activity_id] or 60,
            contributes_to_activity_progress=True,
        )
        created_count += 1
    return {
        "created_count": created_count,
        "already_scheduled_count": already_scheduled_count,
    }


def _scoped_occurrences(
    *, occurrence: AcademicEventOccurrence, scope: str
) -> list[AcademicEventOccurrence]:
    try:
        normalized_scope = RecurrenceScope(scope)
    except ValueError as error:
        raise SchedulingInvalid("El alcance de recurrencia no es válido.") from error
    queryset = AcademicEventOccurrence.objects.select_for_update(of=("self",)).filter(
        series=occurrence.series
    )
    if normalized_scope == RecurrenceScope.OCCURRENCE:
        queryset = queryset.filter(pk=occurrence.pk)
    elif normalized_scope == RecurrenceScope.FOLLOWING:
        queryset = queryset.filter(
            original_starts_at__gte=occurrence.original_starts_at
        )
    return list(queryset.select_related("live_session").order_by("original_starts_at"))


@transaction.atomic
def reschedule_occurrence(
    *,
    actor: object,
    occurrence_id: uuid.UUID,
    expected_version: int,
    starts_at: datetime,
    ends_at: datetime,
    scope: str,
) -> AcademicEventOccurrence:
    occurrence = (
        AcademicEventOccurrence.objects.select_for_update()
        .select_related("series__organization")
        .get(pk=occurrence_id)
    )
    if not can_edit_series(actor, occurrence.series):
        raise SchedulingAccessDenied("No puedes modificar este evento.")
    if occurrence.lock_version != expected_version:
        raise SchedulingConflict("La ocurrencia cambió; vuelve a cargarla.")
    if starts_at.tzinfo is None or ends_at.tzinfo is None or starts_at >= ends_at:
        raise SchedulingInvalid("El nuevo intervalo no es válido.")
    selected = _scoped_occurrences(occurrence=occurrence, scope=scope)
    delta = starts_at - occurrence.starts_at
    duration = ends_at - starts_at
    for item in selected:
        session = getattr(item, "live_session", None)
        if session and session.status != LiveSessionStatus.SCHEDULED:
            raise SchedulingConflict(
                "Una clase iniciada o finalizada no se reprograma."
            )
    for item in selected:
        item.starts_at += delta
        item.ends_at = item.starts_at + duration
        item.is_exception = True
        item.lock_version += 1
        item.save(
            update_fields=(
                "starts_at",
                "ends_at",
                "is_exception",
                "lock_version",
                "updated_at",
            )
        )
    return AcademicEventOccurrence.objects.select_related(
        "series__course", "series__host_membership__user", "live_session"
    ).get(pk=occurrence_id)


@transaction.atomic
def cancel_occurrence(
    *, actor: object, occurrence_id: uuid.UUID, expected_version: int, scope: str
) -> AcademicEventOccurrence:
    occurrence = (
        AcademicEventOccurrence.objects.select_for_update()
        .select_related("series__organization")
        .get(pk=occurrence_id)
    )
    if not can_edit_series(actor, occurrence.series):
        raise SchedulingAccessDenied("No puedes cancelar este evento.")
    if occurrence.lock_version != expected_version:
        raise SchedulingConflict("La ocurrencia cambió; vuelve a cargarla.")
    selected = _scoped_occurrences(occurrence=occurrence, scope=scope)
    now = timezone.now()
    for item in selected:
        session = getattr(item, "live_session", None)
        if session and session.status == LiveSessionStatus.LIVE:
            raise SchedulingConflict("Finaliza la clase en vivo antes de cancelarla.")
        item.status = OccurrenceStatus.CANCELLED
        item.is_exception = True
        item.lock_version += 1
        item.save(
            update_fields=("status", "is_exception", "lock_version", "updated_at")
        )
        if session and session.status != LiveSessionStatus.ENDED:
            session.status = LiveSessionStatus.CANCELLED
            session.actual_ended_at = now
            session.lock_version += 1
            session.save(
                update_fields=(
                    "status",
                    "actual_ended_at",
                    "lock_version",
                    "updated_at",
                )
            )
            deactivate_live_session_requirement(actor=actor, source_id=session.id)
    if scope == RecurrenceScope.SERIES:
        occurrence.series.status = SeriesStatus.CANCELLED
        occurrence.series.lock_version += 1
        occurrence.series.updated_by = actor
        occurrence.series.save(
            update_fields=("status", "lock_version", "updated_by", "updated_at")
        )
    return AcademicEventOccurrence.objects.select_related(
        "series__course", "series__host_membership__user", "live_session"
    ).get(pk=occurrence_id)


def _session_with_context(session_id: uuid.UUID, *, lock: bool = False) -> LiveSession:
    queryset = LiveSession.objects
    if lock:
        queryset = queryset.select_for_update(of=("self",))
    return queryset.select_related(
        "occurrence__series__organization",
        "occurrence__series__course",
        "occurrence__series__host_membership__user",
    ).get(pk=session_id)


def _window_allows(session: LiveSession, now: datetime) -> bool:
    occurrence = session.occurrence
    policy = _live_policy(session)
    return (
        occurrence.starts_at
        - timedelta(
            minutes=policy.get("join_before_minutes", 0),
            seconds=(
                0
                if "join_before_minutes" in policy
                else settings.LIVEKIT_JOIN_BEFORE_START_SECONDS
            ),
        )
        <= now
        < occurrence.ends_at
        + timedelta(
            minutes=policy.get("join_after_minutes", 0),
            seconds=(
                0
                if "join_after_minutes" in policy
                else settings.LIVEKIT_JOIN_AFTER_END_SECONDS
            ),
        )
    )


def _live_policy(session: LiveSession) -> dict[str, Any]:
    activity = session.occurrence.series.course_group_activity
    if activity is None or activity.binding_snapshot.get("provider") != "scheduling":
        return {}
    policy = dict(activity.binding_snapshot)
    if policy.get("recording_mode") == "automatic":
        policy["recording_mode"] = "manual"
    return policy


def _require_live_access(
    *, actor: object, session: LiveSession, now: datetime
) -> LiveAccess:
    access = live_access(actor=actor, session=session, at=now)
    if access is None:
        raise SchedulingAccessDenied("La clase no está disponible.")
    return access


def connection_payload(
    *, actor: object, session: LiveSession, access: LiveAccess, gateway: LiveKitGateway
) -> dict[str, Any]:
    occurrence = session.occurrence
    policy = _live_policy(session)
    return {
        "serverUrl": gateway.config.server_url,
        "token": gateway.issue_token(
            user_id=actor.id,
            participant_name=(
                actor.get_full_name().strip()  # type: ignore[attr-defined]
                or "Participante"
            ),
            room_name=session.room_name,
            access=access,
            chat_enabled=policy.get("chat_enabled", False),
            student_audio_enabled=policy.get("student_audio_enabled", True),
            student_video_enabled=policy.get("student_video_enabled", True),
            student_screen_share_enabled=policy.get(
                "student_screen_share_enabled", False
            ),
        ),
        "session": {
            "id": str(session.id),
            "title": occurrence.title_override or occurrence.series.title,
            "status": session.status,
            "scheduledStart": occurrence.starts_at,
            "scheduledEnd": occurrence.ends_at,
            "role": access.role,
            "canShareScreen": access.can_share_screen,
            "canModerate": access.can_moderate,
            "canPublishAudio": access.role != "student"
            or policy.get("student_audio_enabled", True),
            "canPublishVideo": access.role != "student"
            or policy.get("student_video_enabled", True),
            "chatEnabled": policy.get("chat_enabled", False),
            "recordingMode": policy.get("recording_mode", "off"),
            "recordingLayout": policy.get("recording_layout", "screen_share"),
            "recordingResolution": policy.get("recording_resolution", "1080p"),
            "recordingStatus": session.egress_status,
        },
    }


@transaction.atomic
def start_live_session(
    *,
    actor: object,
    session_id: uuid.UUID,
    recording_acknowledged: bool = False,
    gateway: LiveKitGateway | None = None,
) -> dict[str, Any]:
    session = _session_with_context(session_id, lock=True)
    now = timezone.now()
    access = _require_live_access(actor=actor, session=session, now=now)
    _acknowledge_recording(
        actor=actor, session=session, acknowledged=recording_acknowledged
    )
    if access.role == "student":
        raise SchedulingAccessDenied("Sólo el profesor puede iniciar la clase.")
    if session.status in {LiveSessionStatus.ENDED, LiveSessionStatus.CANCELLED}:
        raise LiveSessionClosed("La clase ya está cerrada.")
    if not _window_allows(session, now):
        raise LiveSessionOutsideWindow("La clase está fuera de su ventana de acceso.")
    adapter = gateway or LiveKitGateway()
    if session.status == LiveSessionStatus.SCHEDULED:
        policy = _live_policy(session)
        room = adapter.create_room(
            room_name=session.room_name,
            metadata=json.dumps({"liveSessionId": str(session.id)}),
            empty_timeout_seconds=policy.get("room_empty_timeout_seconds"),
            departure_timeout_seconds=policy.get("room_departure_timeout_seconds", 30),
            max_participants=policy.get("max_participants"),
        )
        session.status = LiveSessionStatus.LIVE
        session.actual_started_at = now
        session.room_sid = getattr(room, "sid", "")
        session.lock_version += 1
        session.save(
            update_fields=(
                "status",
                "actual_started_at",
                "room_sid",
                "lock_version",
                "updated_at",
            )
        )
    return connection_payload(
        actor=actor, session=session, access=access, gateway=adapter
    )


def join_live_session(
    *,
    actor: object,
    session_id: uuid.UUID,
    recording_acknowledged: bool = False,
    gateway: LiveKitGateway | None = None,
) -> dict[str, Any]:
    session = _session_with_context(session_id)
    now = timezone.now()
    access = _require_live_access(actor=actor, session=session, now=now)
    _acknowledge_recording(
        actor=actor, session=session, acknowledged=recording_acknowledged
    )
    if session.status in {LiveSessionStatus.ENDED, LiveSessionStatus.CANCELLED}:
        raise LiveSessionClosed("La clase ya está cerrada.")
    if session.status != LiveSessionStatus.LIVE:
        raise SchedulingConflict("El profesor aún no ha iniciado la clase.")
    if not _window_allows(session, now):
        raise LiveSessionOutsideWindow("La clase está fuera de su ventana de acceso.")
    adapter = gateway or LiveKitGateway()
    return connection_payload(
        actor=actor, session=session, access=access, gateway=adapter
    )


def _acknowledge_recording(
    *, actor: object, session: LiveSession, acknowledged: bool
) -> None:
    if _live_policy(session).get("recording_mode", "off") == "off":
        return
    if not acknowledged:
        raise SchedulingInvalid(
            "Reconoce el aviso de grabación antes de entrar a la sala."
        )
    LiveRecordingAcknowledgement.objects.get_or_create(
        session=session, user_id=actor.id
    )


@transaction.atomic
def end_live_session(
    *, actor: object, session_id: uuid.UUID, gateway: LiveKitGateway | None = None
) -> LiveSession:
    session = _session_with_context(session_id, lock=True)
    access = _require_live_access(actor=actor, session=session, now=timezone.now())
    if access.role == "student":
        raise SchedulingAccessDenied("Sólo el profesor puede finalizar la clase.")
    if session.status == LiveSessionStatus.ENDED:
        return session
    if session.status == LiveSessionStatus.CANCELLED:
        raise LiveSessionClosed("La clase está cancelada.")
    adapter = gateway or LiveKitGateway()
    if session.egress_id and session.egress_status in {
        EgressStatus.STARTING,
        EgressStatus.ACTIVE,
    }:
        try:
            adapter.stop_recording(egress_id=session.egress_id)
            session.egress_status = EgressStatus.ENDED
        except LiveKitRejected:
            session.egress_status = EgressStatus.FAILED
        LiveSessionRecording.objects.filter(
            session=session,
            egress_id=session.egress_id,
            status__in=(EgressStatus.STARTING, EgressStatus.ACTIVE),
        ).update(
            status=session.egress_status,
            stopped_at=timezone.now(),
        )
    adapter.close_room(room_name=session.room_name)
    now = timezone.now()
    session.status = LiveSessionStatus.ENDED
    session.actual_started_at = session.actual_started_at or now
    session.actual_ended_at = now
    session.lock_version += 1
    session.save(
        update_fields=(
            "status",
            "actual_started_at",
            "actual_ended_at",
            "lock_version",
            "egress_status",
            "updated_at",
        )
    )
    return session


def _start_recording(
    *,
    actor: object,
    session: LiveSession,
    gateway: LiveKitGateway,
    recording_layout: str,
    recording_resolution: str | None = None,
) -> LiveSession:
    if not settings.LIVEKIT_EGRESS_ENABLED:
        raise SchedulingInvalid("La grabación no está habilitada en este entorno.")
    policy = _live_policy(session)
    if policy.get("recording_mode", "off") == "off":
        raise SchedulingInvalid("Esta clase no permite grabación.")
    if session.status != LiveSessionStatus.LIVE:
        raise SchedulingConflict("Inicia la sala antes de grabar.")
    if session.egress_status in {EgressStatus.STARTING, EgressStatus.ACTIVE}:
        return session
    resolution = recording_resolution or policy.get("recording_resolution", "1080p")
    if resolution not in {"720p", "1080p"}:
        raise SchedulingInvalid("Selecciona una resolución de grabación válida.")
    if recording_layout not in {"screen_share", "grid", "speaker"}:
        raise SchedulingInvalid("Selecciona una composición de grabación válida.")
    visual_sources = gateway.active_visual_sources(room_name=session.room_name)
    if recording_layout == "screen_share" and "screen_share" not in visual_sources:
        raise SchedulingConflict(
            "Comparte una pantalla antes de iniciar una grabación de pantalla sola."
        )
    if recording_layout in {"grid", "speaker"} and not visual_sources:
        raise SchedulingConflict(
            "Activa al menos una cámara o una pantalla antes de iniciar esta composición."
        )
    recording_id = uuid.uuid4()
    filepath = (
        f"/out/{session.room_name}-{timezone.now():%Y%m%dT%H%M%SZ}"
        f"-{recording_id}.mp4"
    )
    info = gateway.start_room_recording(
        room_name=session.room_name,
        layout=recording_layout,
        resolution=resolution,
        filepath=filepath,
    )
    session.egress_id = getattr(info, "egress_id", "")
    session.egress_status = EgressStatus.STARTING
    session.recording_layout = recording_layout
    session.recording_resolution = resolution
    LiveSessionRecording.objects.create(
        id=recording_id,
        session=session,
        egress_id=session.egress_id,
        status=EgressStatus.STARTING,
        layout=recording_layout,
        resolution=resolution,
        filepath=filepath,
        started_by_id=actor.id,
    )
    session.save(
        update_fields=(
            "egress_id",
            "egress_status",
            "recording_layout",
            "recording_resolution",
            "updated_at",
        )
    )
    return session


@transaction.atomic
def start_live_recording(
    *,
    actor: object,
    session_id: uuid.UUID,
    recording_layout: str,
    recording_resolution: str | None = None,
    gateway: LiveKitGateway | None = None,
) -> LiveSession:
    session = _session_with_context(session_id, lock=True)
    access = _require_live_access(actor=actor, session=session, now=timezone.now())
    if not access.can_moderate:
        raise SchedulingAccessDenied("No puedes iniciar la grabación.")
    return _start_recording(
        actor=actor,
        session=session,
        gateway=gateway or LiveKitGateway(),
        recording_layout=recording_layout,
        recording_resolution=recording_resolution,
    )


@transaction.atomic
def stop_live_recording(
    *, actor: object, session_id: uuid.UUID, gateway: LiveKitGateway | None = None
) -> LiveSession:
    session = _session_with_context(session_id, lock=True)
    access = _require_live_access(actor=actor, session=session, now=timezone.now())
    if not access.can_moderate:
        raise SchedulingAccessDenied("No puedes detener la grabación.")
    if not session.egress_id or session.egress_status not in {
        EgressStatus.STARTING,
        EgressStatus.ACTIVE,
    }:
        raise SchedulingConflict("No hay una grabación activa.")
    (gateway or LiveKitGateway()).stop_recording(egress_id=session.egress_id)
    session.egress_status = EgressStatus.ENDED
    session.save(update_fields=("egress_status", "updated_at"))
    LiveSessionRecording.objects.filter(
        session=session,
        egress_id=session.egress_id,
        status__in=(EgressStatus.STARTING, EgressStatus.ACTIVE),
    ).update(status=EgressStatus.ENDED, stopped_at=timezone.now())
    return session


def change_participant_permissions(
    *,
    actor: object,
    session_id: uuid.UUID,
    identity: str,
    can_publish_audio: bool,
    can_publish_video: bool,
    can_share_screen: bool,
    gateway: LiveKitGateway | None = None,
) -> None:
    session = _session_with_context(session_id)
    now = timezone.now()
    access = _require_live_access(actor=actor, session=session, now=now)
    if not access.can_moderate:
        raise SchedulingAccessDenied("No puedes moderar participantes.")
    target_access = _participant_access(session=session, identity=identity, at=now)
    policy = _live_policy(session)
    is_student = target_access.role == "student"
    audio_allowed = target_access.can_publish and (
        not is_student or policy.get("student_audio_enabled", True)
    )
    video_allowed = target_access.can_publish and (
        not is_student or policy.get("student_video_enabled", True)
    )
    screen_allowed = target_access.can_share_screen and (
        not is_student or policy.get("student_screen_share_enabled", False)
    )
    (gateway or LiveKitGateway()).update_participant_permissions(
        room_name=session.room_name,
        identity=identity,
        can_publish_audio=can_publish_audio and audio_allowed,
        can_publish_video=can_publish_video and video_allowed,
        can_share_screen=can_share_screen and screen_allowed,
        chat_enabled=policy.get("chat_enabled", False),
    )


def _participant_access(
    *, session: LiveSession, identity: str, at: datetime
) -> LiveAccess:
    if not identity.startswith("user:") or len(identity) > 160:
        raise SchedulingInvalid("La identidad de participante no es válida.")
    try:
        user_id = uuid.UUID(identity.removeprefix("user:"))
    except ValueError as error:
        raise SchedulingInvalid("La identidad de participante no es válida.") from error
    membership = (
        Membership.objects.select_related("user")
        .filter(
            organization=session.occurrence.series.organization,
            user_id=user_id,
            status=MembershipStatus.ACTIVE,
        )
        .first()
    )
    target_access = (
        live_access(actor=membership.user, session=session, at=at)
        if membership
        else None
    )
    if target_access is None:
        raise SchedulingAccessDenied("El participante no pertenece a esta sesión.")
    return target_access


def mute_participant_audio(
    *,
    actor: object,
    session_id: uuid.UUID,
    identity: str,
    gateway: LiveKitGateway | None = None,
) -> None:
    session = _session_with_context(session_id)
    now = timezone.now()
    access = _require_live_access(actor=actor, session=session, now=now)
    if not access.can_moderate:
        raise SchedulingAccessDenied("No puedes moderar participantes.")
    _participant_access(session=session, identity=identity, at=now)
    (gateway or LiveKitGateway()).mute_participant_microphone(
        room_name=session.room_name,
        identity=identity,
    )


def expel_participant(
    *,
    actor: object,
    session_id: uuid.UUID,
    identity: str,
    gateway: LiveKitGateway | None = None,
) -> None:
    session = _session_with_context(session_id)
    access = _require_live_access(actor=actor, session=session, now=timezone.now())
    if not access.can_moderate:
        raise SchedulingAccessDenied("No puedes expulsar participantes.")
    _participant_access(session=session, identity=identity, at=timezone.now())
    (gateway or LiveKitGateway()).remove_participant(
        room_name=session.room_name, identity=identity
    )
