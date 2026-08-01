# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportUnnecessaryComparison=false
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from django.conf import settings
from django.db.models import Q, QuerySet, Sum
from django.utils import timezone

from domain.learning.contracts import effective_course_ids_for_actor
from domain.organizations.models import Organization

from .choices import LiveSessionStatus, OccurrenceStatus
from .models import AcademicEventOccurrence, AttendanceSegment, LiveSession
from .policies import (
    can_create_schedule,
    can_edit_series,
    can_manage_schedule,
    can_view_schedule,
    live_access,
)
from .recurrence import validated_timezone

MAX_FEED_DAYS = 93


def occurrences_visible_to_actor(
    *, actor: object, organization: Organization
) -> QuerySet[AcademicEventOccurrence]:
    if not can_view_schedule(actor, organization):
        return AcademicEventOccurrence.objects.none()
    queryset = AcademicEventOccurrence.objects.filter(
        series__organization=organization
    ).select_related(
        "series__course",
        "series__host_membership__user",
        "live_session",
    )
    if can_manage_schedule(actor, organization) or can_create_schedule(
        actor, organization
    ):
        return queryset
    course_ids = effective_course_ids_for_actor(actor=actor, organization=organization)
    actor_id = getattr(actor, "id", None)
    return queryset.filter(
        Q(series__course_id__in=course_ids)
        | Q(
            series__course__isnull=True,
            series__participants__membership__user_id=actor_id,
            series__participants__membership__status="active",
        )
    ).distinct()


def visible_occurrences_in_range(
    *,
    actor: object,
    organization: Organization,
    starts_at: datetime,
    ends_at: datetime,
    timezone_name: str,
) -> QuerySet[AcademicEventOccurrence]:
    if starts_at.tzinfo is None or ends_at.tzinfo is None or starts_at >= ends_at:
        raise ValueError("calendar_range_invalid")
    if ends_at - starts_at > timedelta(days=MAX_FEED_DAYS):
        raise ValueError("calendar_range_too_large")
    validated_timezone(timezone_name)
    return occurrences_visible_to_actor(actor=actor, organization=organization).filter(
        starts_at__lt=ends_at, ends_at__gt=starts_at
    )


def _availability(occurrence: AcademicEventOccurrence, actor: object) -> dict[str, Any]:
    session = getattr(occurrence, "live_session", None)
    can_edit = can_edit_series(actor, occurrence.series)
    if session is None:
        return {
            "sessionId": None,
            "liveStatus": None,
            "canJoin": False,
            "canStart": False,
            "canModerate": False,
            "canShareScreen": False,
            "canEdit": can_edit,
            "canDelete": can_edit,
        }
    access = live_access(actor=actor, session=session)
    now = timezone.now()
    within_window = (
        occurrence.starts_at
        - timedelta(seconds=settings.LIVEKIT_JOIN_BEFORE_START_SECONDS)
        <= now
        < occurrence.ends_at
        + timedelta(seconds=settings.LIVEKIT_JOIN_AFTER_END_SECONDS)
    )
    return {
        "sessionId": str(session.id),
        "liveStatus": session.status,
        "canJoin": bool(
            access
            and within_window
            and session.status == LiveSessionStatus.LIVE
            and occurrence.status != OccurrenceStatus.CANCELLED
        ),
        "canStart": bool(
            access
            and access.role != "student"
            and within_window
            and session.status == LiveSessionStatus.SCHEDULED
        ),
        "canModerate": bool(access and access.can_moderate),
        "canShareScreen": bool(access and access.can_share_screen),
        "canEdit": can_edit and session.status == LiveSessionStatus.SCHEDULED,
        "canDelete": can_edit and session.status == LiveSessionStatus.SCHEDULED,
    }


def occurrence_payload(
    occurrence: AcademicEventOccurrence, actor: object
) -> dict[str, Any]:
    extended = _availability(occurrence, actor)
    extended.update(
        {
            "courseId": (
                str(occurrence.series.course_id)
                if occurrence.series.course_id
                else None
            ),
            "courseSlug": (
                occurrence.series.course.slug if occurrence.series.course_id else None
            ),
            "courseName": (
                occurrence.series.title
                if occurrence.series.course_id
                else "Sesión independiente"
            ),
            "countsTowardProgress": occurrence.series.counts_toward_progress,
            "attendanceThresholdMinutes": (
                occurrence.series.attendance_threshold_minutes
            ),
            "eventType": occurrence.series.event_type,
            "occurrenceStatus": occurrence.status,
            "hostName": f"Participante {str(occurrence.series.host_membership.user_id)[:8]}",
            "description": occurrence.description_override
            or occurrence.series.description,
            "recurring": bool(occurrence.series.rrule),
            "occurrenceVersion": occurrence.lock_version,
        }
    )
    return {
        "id": str(occurrence.id),
        "groupId": str(occurrence.series_id),
        "title": occurrence.title_override or occurrence.series.title,
        "start": occurrence.starts_at,
        "end": occurrence.ends_at,
        "allDay": False,
        "editable": extended["canEdit"],
        "startEditable": extended["canEdit"],
        "durationEditable": extended["canEdit"],
        "extendedProps": extended,
    }


def live_session_detail(
    *, actor: object, organization: Organization, session_id: uuid.UUID
) -> dict[str, Any]:
    session = (
        LiveSession.objects.select_related(
            "occurrence__series__organization",
            "occurrence__series__course",
            "occurrence__series__host_membership__user",
        )
        .filter(
            pk=session_id,
            occurrence__series__organization=organization,
            occurrence__in=occurrences_visible_to_actor(
                actor=actor, organization=organization
            ),
        )
        .first()
    )
    if session is None:
        raise LiveSession.DoesNotExist
    return _live_session_payload(session=session, actor=actor)


def _live_session_payload(*, session: LiveSession, actor: object) -> dict[str, Any]:
    occurrence = session.occurrence
    availability = _availability(occurrence, actor)
    return {
        "id": str(session.id),
        "title": occurrence.title_override or occurrence.series.title,
        "description": occurrence.description_override or occurrence.series.description,
        "course": (
            {
                "id": str(occurrence.series.course_id),
                "slug": occurrence.series.course.slug,
            }
            if occurrence.series.course_id
            else None
        ),
        "countsTowardProgress": occurrence.series.counts_toward_progress,
        "attendanceThresholdMinutes": occurrence.series.attendance_threshold_minutes,
        "hostName": f"Participante {str(occurrence.series.host_membership.user_id)[:8]}",
        "scheduledStart": occurrence.starts_at,
        "scheduledEnd": occurrence.ends_at,
        "status": session.status,
        **availability,
    }


def live_sessions_visible_to_actor(
    *,
    actor: object,
    organization: Organization,
    course_slug: str = "",
    scope: str = "upcoming",
) -> list[dict[str, Any]]:
    occurrences = occurrences_visible_to_actor(
        actor=actor, organization=organization
    ).filter(live_session__isnull=False)
    if course_slug:
        occurrences = occurrences.filter(series__course__slug=course_slug)
    now = timezone.now()
    if scope == "upcoming":
        occurrences = occurrences.filter(ends_at__gte=now).order_by("starts_at")
    elif scope == "past":
        occurrences = occurrences.filter(ends_at__lt=now).order_by("-starts_at")
    else:
        occurrences = occurrences.order_by("-starts_at")
    sessions = LiveSession.objects.filter(occurrence__in=occurrences).select_related(
        "occurrence__series__organization",
        "occurrence__series__course",
        "occurrence__series__host_membership__user",
    )
    sessions = sessions.order_by(
        "-occurrence__starts_at"
        if scope in {"past", "all"}
        else "occurrence__starts_at"
    )[:100]
    return [_live_session_payload(session=session, actor=actor) for session in sessions]


def attendance_summary(session: LiveSession) -> list[dict[str, Any]]:
    rows = (
        AttendanceSegment.objects.filter(session=session)
        .values("user_id", "participant_identity", "role")
        .annotate(duration_seconds=Sum("duration_seconds"))
        .order_by("participant_identity")
    )
    return list(rows)
