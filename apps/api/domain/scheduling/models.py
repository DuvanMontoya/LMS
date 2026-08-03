# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportIncompatibleVariableOverride=false
from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Trim

from domain.courses.choices import ActivityType
from domain.courses.models import Course, CourseActivity
from domain.learning.models import CourseGroupActivity
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


class LiveClassActivityBinding(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity = models.OneToOneField(
        CourseActivity,
        on_delete=models.PROTECT,
        related_name="live_class_binding",
    )
    minimum_attended_occurrences = models.PositiveSmallIntegerField(default=1)
    minimum_attendance_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    session_mode = models.CharField(
        max_length=16,
        choices=(("interactive", "Interactive"), ("webinar", "Webinar")),
        default="interactive",
    )
    chat_enabled = models.BooleanField(default=True)
    student_audio_enabled = models.BooleanField(default=True)
    student_video_enabled = models.BooleanField(default=True)
    student_screen_share_enabled = models.BooleanField(default=False)
    recording_mode = models.CharField(
        max_length=16,
        choices=(("off", "Off"), ("manual", "Manual")),
        default="off",
    )
    recording_layout = models.CharField(
        max_length=16,
        choices=(
            ("screen_share", "Screen share only"),
            ("grid", "Grid"),
            ("speaker", "Speaker"),
        ),
        default="screen_share",
    )
    recording_resolution = models.CharField(
        max_length=8,
        choices=(("720p", "720p"), ("1080p", "1080p")),
        default="1080p",
    )
    max_participants = models.PositiveSmallIntegerField(default=100)
    room_empty_timeout_seconds = models.PositiveSmallIntegerField(default=600)
    room_departure_timeout_seconds = models.PositiveSmallIntegerField(default=30)
    join_before_minutes = models.PositiveSmallIntegerField(default=15)
    join_after_minutes = models.PositiveSmallIntegerField(default=15)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="live_class_activity_bindings_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.PROTECT,
        related_name="live_class_activity_bindings_updated",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(minimum_attended_occurrences__gt=0),
                name="sched_binding_occurrences_positive",
            ),
            models.CheckConstraint(
                condition=Q(minimum_attendance_minutes__isnull=True)
                | Q(minimum_attendance_minutes__gt=0),
                name="sched_binding_minutes_positive",
            ),
            models.CheckConstraint(
                condition=Q(max_participants__gte=2) & Q(max_participants__lte=1_000),
                name="sched_binding_max_participants_range",
            ),
            models.CheckConstraint(
                condition=Q(room_empty_timeout_seconds__gte=60)
                & Q(room_empty_timeout_seconds__lte=3_600),
                name="sched_binding_empty_timeout_range",
            ),
            models.CheckConstraint(
                condition=Q(room_departure_timeout_seconds__lte=600),
                name="sched_binding_departure_timeout_range",
            ),
            models.CheckConstraint(
                condition=Q(join_before_minutes__lte=120),
                name="sched_binding_join_before_range",
            ),
            models.CheckConstraint(
                condition=Q(join_after_minutes__lte=120),
                name="sched_binding_join_after_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.activity_id}:live-class"

    def clean(self) -> None:
        super().clean()
        if self.activity.activity_type != ActivityType.LIVE_CLASS:
            raise ValidationError({"activity": "La actividad no es una clase en vivo."})


class AcademicEventSeries(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="academic_event_series"
    )
    course = models.ForeignKey(
        Course,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="academic_event_series",
    )
    course_group = models.ForeignKey(
        "learning.LearningCohort",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="scheduled_event_series",
    )
    course_group_activity = models.ForeignKey(
        CourseGroupActivity,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="live_event_series_set",
    )
    migration_review_required = models.BooleanField(default=False)
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
    counts_toward_progress = models.BooleanField(default=False)
    activity_progress_contribution = models.BooleanField(default=False)
    attendance_threshold_minutes = models.PositiveSmallIntegerField(
        null=True, blank=True
    )
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
            models.CheckConstraint(
                condition=(
                    Q(
                        counts_toward_progress=False,
                        attendance_threshold_minutes__isnull=True,
                    )
                    | Q(
                        counts_toward_progress=True,
                        course__isnull=False,
                        attendance_threshold_minutes__gte=1,
                        attendance_threshold_minutes__lte=720,
                    )
                ),
                name="sched_series_progress_configuration",
            ),
            models.CheckConstraint(
                condition=Q(course_group__isnull=True) | Q(course__isnull=False),
                name="sched_series_group_requires_course",
            ),
            models.CheckConstraint(
                condition=(
                    Q(course_group_activity__isnull=False)
                    | Q(activity_progress_contribution=False)
                ),
                name="sched_series_activity_contribution_scope",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "status"], name="sched_series_org_state_ix"
            ),
            models.Index(
                fields=["course", "status"], name="sched_series_course_state_ix"
            ),
            models.Index(
                fields=["course_group", "status"],
                name="sched_series_group_state_ix",
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
        if self.course_group_id and (
            self.course_group.organization_id != self.organization_id
            or self.course_group.course_id != self.course_id
        ):
            raise ValidationError(
                {"course_group": "El grupo de curso no corresponde al curso."}
            )
        if self.course_group_activity_id:
            activity = self.course_group_activity
            if (
                self.course_group_id != activity.course_group_id
                or activity.course_group.course_id != self.course_id
                or activity.activity_type != "live_class"
                or activity.migration_review_required
                or activity.binding_snapshot.get("provider") != "scheduling"
                or self.counts_toward_progress
            ):
                raise ValidationError(
                    {
                        "course_group_activity": (
                            "La actividad en vivo no corresponde al grupo o usa el escritor legado."
                        )
                    }
                )
        elif self.activity_progress_contribution:
            raise ValidationError(
                {
                    "activity_progress_contribution": (
                        "Sólo una actividad curricular puede recibir evidencia."
                    )
                }
            )
        if (
            self.host_membership_id
            and self.host_membership.organization_id != self.organization_id
        ):
            raise ValidationError(
                {"host_membership": "El profesor pertenece a otra organización."}
            )


class AcademicEventParticipant(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    series = models.ForeignKey(
        AcademicEventSeries, on_delete=models.PROTECT, related_name="participants"
    )
    membership = models.ForeignKey(
        Membership,
        on_delete=models.PROTECT,
        related_name="scheduled_event_participations",
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="scheduled_event_participants_added",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("series", "membership"),
                name="sched_series_participant_unique",
            )
        ]
        indexes = [
            models.Index(
                fields=("membership", "series"),
                name="sched_participant_member_ix",
            )
        ]

    def __str__(self) -> str:
        return f"{self.series_id}:{self.membership_id}"

    def clean(self) -> None:
        super().clean()
        if (
            self.series_id
            and self.membership_id
            and self.series.organization_id != self.membership.organization_id
        ):
            raise ValidationError(
                {"membership": "El participante pertenece a otra organización."}
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
    recording_layout = models.CharField(max_length=16, blank=True)
    recording_resolution = models.CharField(max_length=8, blank=True)
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


class LiveSessionRecording(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        LiveSession,
        on_delete=models.PROTECT,
        related_name="recordings",
    )
    egress_id = models.CharField(max_length=128, unique=True)
    status = models.CharField(
        max_length=16,
        choices=EgressStatus.choices,
        default=EgressStatus.STARTING,
    )
    layout = models.CharField(
        max_length=16,
        choices=(
            ("screen_share", "Screen share only"),
            ("grid", "Grid"),
            ("speaker", "Speaker"),
        ),
    )
    resolution = models.CharField(
        max_length=8,
        choices=(("720p", "720p"), ("1080p", "1080p")),
    )
    filepath = models.CharField(max_length=255)
    failure_message = models.TextField(blank=True)
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="live_recordings_started",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    stopped_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("started_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("session",),
                condition=Q(status__in=(EgressStatus.STARTING, EgressStatus.ACTIVE)),
                name="sched_one_active_recording_per_session",
            )
        ]


class LiveRecordingAcknowledgement(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        LiveSession,
        on_delete=models.PROTECT,
        related_name="recording_acknowledgements",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="live_recording_acknowledgements",
    )
    acknowledged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("session", "user"),
                name="sched_recording_ack_session_user_unique",
            )
        ]

    def __str__(self) -> str:
        return f"{self.session_id}:{self.user_id}"


class LiveKitWebhookEvent(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.CharField(max_length=64, unique=True)
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
