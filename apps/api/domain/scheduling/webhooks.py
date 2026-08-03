# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, cast

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from livekit import api

from domain.learning.contracts import (
    complete_group_activity_attendance,
    complete_live_session_requirement,
)

from .choices import (
    AttendanceRole,
    EgressStatus,
    LiveSessionStatus,
    WebhookProcessingStatus,
)
from .exceptions import LiveKitWebhookInvalid
from .livekit_gateway import LiveKitGateway
from .models import (
    AcademicEventSeries,
    AttendanceSegment,
    LiveKitWebhookEvent,
    LiveSession,
    LiveSessionRecording,
)

PARTICIPANT_END_EVENTS = frozenset(
    {"participant_left", "participant_connection_aborted"}
)


def _event_time(seconds: int) -> datetime:
    return datetime.fromtimestamp(seconds, tz=UTC)


def _minimal_payload(event: api.WebhookEvent) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if event.room and event.room.name:
        payload.update({"roomName": event.room.name, "roomSid": event.room.sid})
    if event.participant and event.participant.identity:
        payload.update(
            {
                "participantIdentity": event.participant.identity,
                "participantSid": event.participant.sid,
                "disconnectReason": str(event.participant.disconnect_reason),
                "participantRole": event.participant.attributes.get("lms.role", ""),
            }
        )
    if event.egress_info and event.egress_info.egress_id:
        payload.update(
            {
                "egressId": event.egress_info.egress_id,
                "roomName": event.egress_info.room_name,
            }
        )
    return payload


def _session_for_event(event: api.WebhookEvent) -> LiveSession | None:
    room_name = ""
    if event.room:
        room_name = event.room.name
    if not room_name and event.egress_info:
        room_name = event.egress_info.room_name
    if not room_name:
        return None
    return (
        LiveSession.objects.select_for_update()
        .select_related("occurrence__series__host_membership")
        .filter(room_name=room_name)
        .first()
    )


def _participant_user(identity: str):
    if not identity.startswith("user:"):
        return None
    try:
        user_id = uuid.UUID(identity.removeprefix("user:"))
    except ValueError:
        return None
    return get_user_model().objects.filter(pk=user_id).first()


def _attendance_role(event: api.WebhookEvent, session: LiveSession) -> str:
    raw = event.participant.attributes.get("lms.role", "")
    if raw in AttendanceRole.values:
        return raw
    user = _participant_user(event.participant.identity)
    if user and user.id == session.occurrence.series.host_membership.user_id:
        return AttendanceRole.HOST
    return AttendanceRole.STUDENT


def _close_segment(
    segment: AttendanceSegment,
    *,
    webhook: LiveKitWebhookEvent,
    left_at: datetime,
    reason: str,
) -> None:
    effective_left = max(left_at, segment.joined_at)
    segment.left_at = effective_left
    segment.duration_seconds = int((effective_left - segment.joined_at).total_seconds())
    segment.disconnect_reason = reason[:80]
    segment.left_event = webhook
    segment.save(
        update_fields=(
            "left_at",
            "duration_seconds",
            "disconnect_reason",
            "left_event",
            "updated_at",
        )
    )
    _complete_progress_requirement_if_eligible(segment, effective_left)


def _complete_progress_requirement_if_eligible(
    segment: AttendanceSegment, completed_at: datetime
) -> None:
    series = cast(AcademicEventSeries, segment.session.occurrence.series)
    if (
        segment.user is not None
        and segment.role == AttendanceRole.STUDENT
        and series.course_group_activity_id is not None
        and series.activity_progress_contribution
    ):
        binding = series.course_group_activity.binding_snapshot
        minimum_occurrences = int(binding.get("minimum_attended_occurrences") or 1)
        minimum_minutes = int(binding.get("minimum_attendance_minutes") or 0)
        totals = list(
            AttendanceSegment.objects.filter(
                session__occurrence__series=series,
                user=segment.user,
                role=AttendanceRole.STUDENT,
            )
            .values("session_id")
            .annotate(total=Sum("duration_seconds"))
        )
        qualifying = [
            row for row in totals if int(row["total"] or 0) >= minimum_minutes * 60
        ]
        if len(qualifying) >= minimum_occurrences:
            complete_group_activity_attendance(
                actor=segment.user,
                group_activity_id=series.course_group_activity_id,
                completed_at=completed_at,
                evidence={
                    "attendance_seconds": sum(int(row["total"] or 0) for row in totals),
                    "attended_occurrences": len(qualifying),
                },
            )
        return
    threshold = cast(int | None, series.attendance_threshold_minutes)
    if (
        segment.user is None
        or segment.role != AttendanceRole.STUDENT
        or not series.counts_toward_progress
        or threshold is None
    ):
        return
    duration_seconds = (
        AttendanceSegment.objects.filter(
            session=segment.session,
            user=segment.user,
            role=AttendanceRole.STUDENT,
        ).aggregate(total=Sum("duration_seconds"))["total"]
        or 0
    )
    if duration_seconds < threshold * 60:
        return
    complete_live_session_requirement(
        actor=segment.user,
        source_id=segment.session_id,
        completed_at=completed_at,
        evidence={"attendance_seconds": duration_seconds},
    )


def _process_participant_joined(
    event: api.WebhookEvent,
    webhook: LiveKitWebhookEvent,
    session: LiveSession,
) -> None:
    participant = event.participant
    segment, _ = AttendanceSegment.objects.get_or_create(
        joined_event=webhook,
        defaults={
            "session": session,
            "user": _participant_user(participant.identity),
            "participant_identity": participant.identity,
            "participant_sid": participant.sid,
            "role": _attendance_role(event, session),
            "joined_at": webhook.event_created_at,
        },
    )
    pending = (
        LiveKitWebhookEvent.objects.filter(
            event_type__in=PARTICIPANT_END_EVENTS,
            event_created_at__gte=segment.joined_at,
            payload__participantIdentity=segment.participant_identity,
            payload__participantSid=segment.participant_sid,
            payload__roomName=session.room_name,
        )
        .exclude(pk=webhook.pk)
        .order_by("event_created_at", "received_at")
        .first()
    )
    if pending and segment.left_at is None:
        _close_segment(
            segment,
            webhook=pending,
            left_at=pending.event_created_at,
            reason=str(pending.payload.get("disconnectReason", "")),
        )


def _process_participant_end(
    event: api.WebhookEvent,
    webhook: LiveKitWebhookEvent,
    session: LiveSession,
) -> None:
    participant = event.participant
    segment = (
        AttendanceSegment.objects.select_for_update()
        .filter(
            session=session,
            participant_identity=participant.identity,
            participant_sid=participant.sid,
            left_at__isnull=True,
        )
        .order_by("-joined_at")
        .first()
    )
    if segment:
        reason = str(participant.disconnect_reason)
        if event.event == "participant_connection_aborted":
            reason = reason or "connection_aborted"
        _close_segment(
            segment,
            webhook=webhook,
            left_at=webhook.event_created_at,
            reason=reason,
        )


def _process_room_started(webhook: LiveKitWebhookEvent, session: LiveSession) -> None:
    if session.status == LiveSessionStatus.SCHEDULED:
        session.status = LiveSessionStatus.LIVE
        session.actual_started_at = webhook.event_created_at
        session.room_sid = str(webhook.payload.get("roomSid", ""))
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


def _process_room_finished(webhook: LiveKitWebhookEvent, session: LiveSession) -> None:
    for segment in AttendanceSegment.objects.select_for_update().filter(
        session=session, left_at__isnull=True
    ):
        _close_segment(
            segment,
            webhook=webhook,
            left_at=webhook.event_created_at,
            reason="room_finished",
        )
    if session.status != LiveSessionStatus.CANCELLED:
        session.status = LiveSessionStatus.ENDED
        session.actual_started_at = (
            session.actual_started_at or webhook.event_created_at
        )
        session.actual_ended_at = webhook.event_created_at
        session.lock_version += 1
        session.save(
            update_fields=(
                "status",
                "actual_started_at",
                "actual_ended_at",
                "lock_version",
                "updated_at",
            )
        )


def _process_egress(event: api.WebhookEvent, session: LiveSession) -> None:
    if not event.egress_info:
        return
    status_map = {
        "egress_started": EgressStatus.ACTIVE,
        "egress_updated": EgressStatus.ACTIVE,
        "egress_ended": EgressStatus.ENDED,
    }
    session.egress_id = event.egress_info.egress_id
    session.egress_status = (
        EgressStatus.FAILED if event.egress_info.error else status_map[event.event]
    )
    session.save(update_fields=("egress_id", "egress_status", "updated_at"))
    recording = LiveSessionRecording.objects.filter(
        session=session,
        egress_id=event.egress_info.egress_id,
    ).first()
    if recording is None:
        return
    recording.status = session.egress_status
    recording.failure_message = event.egress_info.error or ""
    update_fields = ["status", "failure_message"]
    if event.event == "egress_ended":
        recording.stopped_at = timezone.now()
        update_fields.append("stopped_at")
    recording.save(update_fields=update_fields)


def _process_domain_event(
    event: api.WebhookEvent, webhook: LiveKitWebhookEvent
) -> None:
    session = _session_for_event(event)
    if session is None:
        return
    LiveKitWebhookEvent.objects.filter(pk=webhook.pk).update(session=session)
    webhook.session = session
    if event.event == "room_started":
        _process_room_started(webhook, session)
    elif event.event == "room_finished":
        _process_room_finished(webhook, session)
    elif event.event == "participant_joined":
        _process_participant_joined(event, webhook, session)
    elif event.event in PARTICIPANT_END_EVENTS:
        _process_participant_end(event, webhook, session)
    elif event.event in {"egress_started", "egress_updated", "egress_ended"}:
        _process_egress(event, session)


def receive_and_process_webhook(
    *, body: bytes, authorization: str, gateway: LiveKitGateway | None = None
) -> tuple[LiveKitWebhookEvent, bool]:
    try:
        raw = body.decode("utf-8")
        token = authorization.strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
        event = (gateway or LiveKitGateway()).webhook_receiver().receive(raw, token)
        event_id = event.id.strip()
        if not event_id or len(event_id) > 64:
            raise ValueError("LiveKit webhook event id is missing or too long")
    except Exception as error:
        raise LiveKitWebhookInvalid(
            "La firma o el cuerpo LiveKit no son válidos."
        ) from error
    created_at = _event_time(event.created_at)
    payload = _minimal_payload(event)
    processing_error: Exception | None = None
    with transaction.atomic():
        webhook, created = LiveKitWebhookEvent.objects.get_or_create(
            event_id=event_id,
            defaults={
                "event_type": event.event,
                "event_created_at": created_at,
                "payload": payload,
            },
        )
        if (
            not created
            and webhook.processing_status == WebhookProcessingStatus.PROCESSED
        ):
            return webhook, False
        if not created:
            LiveKitWebhookEvent.objects.filter(pk=webhook.pk).update(
                processing_status=WebhookProcessingStatus.PROCESSING,
                processing_error="",
            )
        try:
            with transaction.atomic():
                _process_domain_event(event, webhook)
        except Exception as error:
            LiveKitWebhookEvent.objects.filter(pk=webhook.pk).update(
                processing_status=WebhookProcessingStatus.FAILED,
                processing_error=str(error)[:500],
                processed_at=timezone.now(),
            )
            processing_error = error
        else:
            LiveKitWebhookEvent.objects.filter(pk=webhook.pk).update(
                processing_status=WebhookProcessingStatus.PROCESSED,
                processing_error="",
                processed_at=timezone.now(),
            )
    if processing_error is not None:
        raise processing_error
    webhook.refresh_from_db()
    return webhook, created
