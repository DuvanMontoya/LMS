# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportUnnecessaryComparison=false
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

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
    return activity.binding_snapshot


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
        if policy.get("recording_mode") == "automatic":
            try:
                _start_recording(session=session, gateway=adapter)
            except LiveKitRejected:
                session.egress_status = EgressStatus.FAILED
                session.save(update_fields=("egress_status", "updated_at"))
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


def _start_recording(*, session: LiveSession, gateway: LiveKitGateway) -> LiveSession:
    if not settings.LIVEKIT_EGRESS_ENABLED:
        raise SchedulingInvalid("La grabación no está habilitada en este entorno.")
    policy = _live_policy(session)
    if policy.get("recording_mode", "off") == "off":
        raise SchedulingInvalid("Esta clase no permite grabación.")
    if session.status != LiveSessionStatus.LIVE:
        raise SchedulingConflict("Inicia la sala antes de grabar.")
    if session.egress_status in {EgressStatus.STARTING, EgressStatus.ACTIVE}:
        return session
    info = gateway.start_room_recording(
        room_name=session.room_name,
        layout=policy.get("recording_layout", "speaker"),
        filepath=f"/out/{session.room_name}-{timezone.now():%Y%m%dT%H%M%SZ}.mp4",
    )
    session.egress_id = getattr(info, "egress_id", "")
    session.egress_status = EgressStatus.STARTING
    session.save(update_fields=("egress_id", "egress_status", "updated_at"))
    return session


@transaction.atomic
def start_live_recording(
    *, actor: object, session_id: uuid.UUID, gateway: LiveKitGateway | None = None
) -> LiveSession:
    session = _session_with_context(session_id, lock=True)
    access = _require_live_access(actor=actor, session=session, now=timezone.now())
    if not access.can_moderate:
        raise SchedulingAccessDenied("No puedes iniciar la grabación.")
    return _start_recording(session=session, gateway=gateway or LiveKitGateway())


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
    access = _require_live_access(actor=actor, session=session, now=timezone.now())
    if not access.can_moderate:
        raise SchedulingAccessDenied("No puedes moderar participantes.")
    if not identity.startswith("user:") or len(identity) > 160:
        raise SchedulingInvalid("La identidad de participante no es válida.")
    (gateway or LiveKitGateway()).update_participant_permissions(
        room_name=session.room_name,
        identity=identity,
        can_publish_audio=can_publish_audio,
        can_publish_video=can_publish_video,
        can_share_screen=can_share_screen,
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
    if not identity.startswith("user:") or len(identity) > 160:
        raise SchedulingInvalid("La identidad de participante no es válida.")
    (gateway or LiveKitGateway()).remove_participant(
        room_name=session.room_name, identity=identity
    )
