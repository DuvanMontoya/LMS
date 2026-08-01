# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportIncompatibleVariableOverride=false
from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Trim

from domain.courses.models import Course
from domain.organizations.models import Membership, Organization

from .choices import (
    AttendanceRole,
    EgressStatus,
    EventType,
    LiveSessionStatus,
    OccurrenceStatus,
    SeriesStatus,
    WebhookProcessingStatus,
)


def livekit_room_name() -> str:
    return f"lk_{uuid.uuid4().hex}"


class NoPhysicalDeleteModel(models.Model):
    class Meta:
        abstract = True

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("El historial de calendario no se elimina físicamente.")


class AcademicEventSeries(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="academic_event_series"
    )
    course = models.ForeignKey(
        Course, on_delete=models.PROTECT, related_name="academic_event_series"
    )
    host_membership = models.ForeignKey(
        Membership, on_delete=models.PROTECT, related_name="hosted_event_series"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=2_000, blank=True)
    event_type = models.CharField(
        max_length=32, choices=EventType.choices, default=EventType.LIVE_CLASS
    )
    timezone_name = models.CharField(max_length=64)
    first_starts_at = models.DateTimeField()
    duration_minutes = models.PositiveSmallIntegerField()
    rrule = models.CharField(max_length=1_000, blank=True)
    recurrence_count = models.PositiveSmallIntegerField(default=1)
    recurrence_until = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=SeriesStatus.choices, default=SeriesStatus.ACTIVE
    )
    lock_version = models.PositiveIntegerField(default=1, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="academic_event_series_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="academic_event_series_updated",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(title=Trim(F("title"))) & ~Q(title=""),
                name="sched_series_title_trimmed",
            ),
            models.CheckConstraint(
                condition=Q(duration_minutes__gte=5) & Q(duration_minutes__lte=720),
                name="sched_series_duration_range",
            ),
            models.CheckConstraint(
                condition=Q(recurrence_count__gte=1) & Q(recurrence_count__lte=366),
                name="sched_series_recurrence_range",
            ),
            models.CheckConstraint(
                condition=Q(lock_version__gt=0),
                name="sched_series_lock_positive",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "status"], name="sched_series_org_state_ix"
            ),
            models.Index(
                fields=["course", "status"], name="sched_series_course_state_ix"
            ),
            models.Index(fields=["host_membership"], name="sched_series_host_ix"),
        ]

    def __str__(self) -> str:
        return f"{self.organization.slug}:{self.title}"

    def clean(self) -> None:
        super().clean()
        self.title = self.title.strip()
        self.description = self.description.strip()
        self.timezone_name = self.timezone_name.strip()
        self.rrule = self.rrule.strip().removeprefix("RRULE:")
        if self.course_id and self.course.organization_id != self.organization_id:
            raise ValidationError({"course": "El curso pertenece a otra organización."})
        if (
            self.host_membership_id
            and self.host_membership.organization_id != self.organization_id
        ):
            raise ValidationError(
                {"host_membership": "El profesor pertenece a otra organización."}
            )


class AcademicEventOccurrence(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    series = models.ForeignKey(
        AcademicEventSeries, on_delete=models.PROTECT, related_name="occurrences"
    )
    original_starts_at = models.DateTimeField()
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(
        max_length=16,
        choices=OccurrenceStatus.choices,
        default=OccurrenceStatus.SCHEDULED,
    )
    is_exception = models.BooleanField(default=False)
    title_override = models.CharField(max_length=200, blank=True)
    description_override = models.TextField(max_length=2_000, blank=True)
    lock_version = models.PositiveIntegerField(default=1, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["series", "original_starts_at"],
                name="sched_occurrence_original_unique",
            ),
            models.CheckConstraint(
                condition=Q(starts_at__lt=F("ends_at")),
                name="sched_occurrence_window",
            ),
            models.CheckConstraint(
                condition=Q(lock_version__gt=0),
                name="sched_occurrence_lock_positive",
            ),
        ]
        indexes = [
            models.Index(fields=["starts_at", "ends_at"], name="sched_occ_window_ix"),
            models.Index(
                fields=["series", "status", "starts_at"],
                name="sched_occ_series_state_ix",
            ),
        ]
        ordering = ("starts_at", "id")

    def __str__(self) -> str:
        return f"{self.series_id}:{self.original_starts_at.isoformat()}"


class LiveSession(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    occurrence = models.OneToOneField(
        AcademicEventOccurrence,
        on_delete=models.PROTECT,
        related_name="live_session",
    )
    room_name = models.CharField(
        max_length=80, unique=True, default=livekit_room_name, editable=False
    )
    status = models.CharField(
        max_length=16,
        choices=LiveSessionStatus.choices,
        default=LiveSessionStatus.SCHEDULED,
    )
    room_sid = models.CharField(max_length=64, blank=True)
    actual_started_at = models.DateTimeField(null=True, blank=True)
    actual_ended_at = models.DateTimeField(null=True, blank=True)
    egress_id = models.CharField(max_length=128, blank=True)
    egress_status = models.CharField(
        max_length=16, choices=EgressStatus.choices, default=EgressStatus.DISABLED
    )
    lock_version = models.PositiveIntegerField(default=1, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="live_sessions_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(lock_version__gt=0),
                name="sched_live_lock_positive",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=LiveSessionStatus.SCHEDULED,
                        actual_ended_at__isnull=True,
                    )
                    | Q(
                        status=LiveSessionStatus.LIVE,
                        actual_started_at__isnull=False,
                        actual_ended_at__isnull=True,
                    )
                    | Q(
                        status=LiveSessionStatus.ENDED,
                        actual_started_at__isnull=False,
                        actual_ended_at__isnull=False,
                    )
                    | Q(
                        status=LiveSessionStatus.CANCELLED,
                        actual_ended_at__isnull=False,
                    )
                ),
                name="sched_live_lifecycle",
            ),
        ]
        indexes = [
            models.Index(fields=["status"], name="sched_live_state_ix"),
            models.Index(fields=["room_sid"], name="sched_live_sid_ix"),
        ]

    def __str__(self) -> str:
        return f"{self.occurrence_id}:{self.status}"


class LiveKitWebhookEvent(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.UUIDField(unique=True)
    event_type = models.CharField(max_length=64)
    event_created_at = models.DateTimeField()
    received_at = models.DateTimeField(auto_now_add=True)
    processing_status = models.CharField(
        max_length=16,
        choices=WebhookProcessingStatus.choices,
        default=WebhookProcessingStatus.PROCESSING,
    )
    session = models.ForeignKey(
        LiveSession,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="webhook_events",
    )
    payload = models.JSONField(default=dict)
    processing_error = models.CharField(max_length=500, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["event_type", "event_created_at"],
                name="sched_hook_type_time_ix",
            ),
            models.Index(
                fields=["processing_status", "received_at"],
                name="sched_hook_state_time_ix",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.event_type}:{self.event_id}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise ValidationError("Los eventos LiveKit son append-only.")
        super().save(*args, **kwargs)


class AttendanceSegment(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        LiveSession, on_delete=models.PROTECT, related_name="attendance_segments"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="live_attendance_segments",
    )
    participant_identity = models.CharField(max_length=160)
    participant_sid = models.CharField(max_length=64)
    role = models.CharField(max_length=20, choices=AttendanceRole.choices)
    joined_at = models.DateTimeField()
    left_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    disconnect_reason = models.CharField(max_length=80, blank=True)
    joined_event = models.OneToOneField(
        LiveKitWebhookEvent,
        on_delete=models.PROTECT,
        related_name="opened_attendance_segment",
    )
    left_event = models.ForeignKey(
        LiveKitWebhookEvent,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="closed_attendance_segments",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(left_at__isnull=True, duration_seconds__isnull=True)
                | Q(left_at__isnull=False, duration_seconds__isnull=False),
                name="sched_attendance_close_state",
            ),
            models.CheckConstraint(
                condition=Q(left_at__isnull=True) | Q(left_at__gte=F("joined_at")),
                name="sched_attendance_time_order",
            ),
        ]
        indexes = [
            models.Index(fields=["session", "joined_at"], name="sched_att_session_ix"),
            models.Index(fields=["user", "joined_at"], name="sched_att_user_ix"),
            models.Index(
                fields=["participant_identity", "joined_at"],
                name="sched_att_identity_ix",
            ),
            models.Index(
                fields=["participant_sid", "left_at"], name="sched_att_sid_ix"
            ),
        ]
        ordering = ("joined_at", "id")

    def __str__(self) -> str:
        return f"{self.session_id}:{self.participant_identity}:{self.joined_at}"
