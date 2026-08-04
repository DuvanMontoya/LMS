# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportMissingParameterType=false
from rest_framework import serializers

from domain.scheduling.choices import EventType, RecurrenceScope


class SchedulingErrorSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()


class LiveClassActivityBindingInputSerializer(serializers.Serializer):
    expected_revision_version = serializers.IntegerField(min_value=1)
    minimum_attended_occurrences = serializers.IntegerField(min_value=1, max_value=100)
    minimum_attendance_minutes = serializers.IntegerField(
        min_value=1, max_value=720, required=False, allow_null=True
    )


class LiveClassActivityBindingListQuerySerializer(serializers.Serializer):
    revision_id = serializers.UUIDField()


class LiveClassCourseActivityConfigurationSerializer(serializers.Serializer):
    expected_revision_version = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=200)
    summary = serializers.CharField(max_length=1200, required=False, allow_blank=True)
    estimated_duration_minutes = serializers.IntegerField(min_value=1, max_value=720)
    required = serializers.BooleanField(default=True)
    minimum_attendance_basis_points = serializers.IntegerField(
        min_value=1, max_value=10_000
    )
    learning_objective_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, max_length=100
    )
    session_mode = serializers.ChoiceField(choices=("interactive", "webinar"))
    chat_enabled = serializers.BooleanField(default=True)
    student_audio_enabled = serializers.BooleanField(default=True)
    student_video_enabled = serializers.BooleanField(default=True)
    student_screen_share_enabled = serializers.BooleanField(default=False)
    recording_mode = serializers.ChoiceField(choices=("off", "manual"), default="off")
    recording_layout = serializers.ChoiceField(
        choices=("screen_share", "grid", "speaker"), default="screen_share"
    )
    recording_resolution = serializers.ChoiceField(
        choices=("720p", "1080p"), default="1080p"
    )
    max_participants = serializers.IntegerField(min_value=2, max_value=1_000)
    room_empty_timeout_seconds = serializers.IntegerField(min_value=60, max_value=3_600)
    room_departure_timeout_seconds = serializers.IntegerField(
        min_value=0, max_value=600
    )
    join_before_minutes = serializers.IntegerField(min_value=0, max_value=120)
    join_after_minutes = serializers.IntegerField(min_value=0, max_value=120)


class LiveClassCourseActivityCreateSerializer(
    LiveClassCourseActivityConfigurationSerializer
):
    module_id = serializers.UUIDField()


class LiveClassActivityBindingSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    activity_id = serializers.UUIDField()
    minimum_attended_occurrences = serializers.IntegerField()
    minimum_attendance_minutes = serializers.IntegerField(allow_null=True)
    session_mode = serializers.CharField()
    chat_enabled = serializers.BooleanField()
    student_audio_enabled = serializers.BooleanField()
    student_video_enabled = serializers.BooleanField()
    student_screen_share_enabled = serializers.BooleanField()
    recording_mode = serializers.CharField()
    recording_layout = serializers.CharField()
    recording_resolution = serializers.CharField()
    max_participants = serializers.IntegerField()
    room_empty_timeout_seconds = serializers.IntegerField()
    room_departure_timeout_seconds = serializers.IntegerField()
    join_before_minutes = serializers.IntegerField()
    join_after_minutes = serializers.IntegerField()
    revision_lock_version = serializers.IntegerField()


class CourseGroupLiveClassSlotSerializer(serializers.Serializer):
    weekday = serializers.IntegerField(min_value=0, max_value=6)
    starts_at = serializers.TimeField()


class MaterializeCourseGroupLiveClassesSerializer(serializers.Serializer):
    first_week_starts_on = serializers.DateField()
    timezone_name = serializers.CharField(max_length=64)
    slots = CourseGroupLiveClassSlotSerializer(many=True, min_length=1, max_length=12)

    def validate_slots(self, value: list[dict[str, object]]) -> list[dict[str, object]]:
        keys = [(row["weekday"], row["starts_at"]) for row in value]
        if len(keys) != len(set(keys)):
            raise serializers.ValidationError("No repitas el mismo horario semanal.")
        return value


class MaterializeCourseGroupLiveClassesResultSerializer(serializers.Serializer):
    created_count = serializers.IntegerField()
    already_scheduled_count = serializers.IntegerField()


class ParticipantOptionSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    display = serializers.CharField()
    can_host = serializers.BooleanField()


class CalendarRangeSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    timeZone = serializers.CharField(max_length=64)
    course = serializers.UUIDField(required=False)


class EventCreateSerializer(serializers.Serializer):
    course_slug = serializers.SlugField(
        required=False, allow_null=True, allow_blank=True
    )
    course_group_id = serializers.UUIDField(required=False, allow_null=True)
    course_group_activity_id = serializers.UUIDField(required=False, allow_null=True)
    host_membership_id = serializers.UUIDField(required=False)
    participant_membership_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        max_length=100,
    )
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(
        max_length=2_000, required=False, allow_blank=True
    )
    event_type = serializers.ChoiceField(
        choices=EventType.choices, default=EventType.LIVE_CLASS
    )
    timezone_name = serializers.CharField(max_length=64)
    starts_at = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField(min_value=5, max_value=720)
    rrule = serializers.CharField(max_length=1_000, required=False, allow_blank=True)
    counts_toward_progress = serializers.BooleanField(default=False)
    contributes_to_activity_progress = serializers.BooleanField(
        required=False, allow_null=True
    )
    attendance_threshold_minutes = serializers.IntegerField(
        min_value=1, max_value=720, required=False, allow_null=True
    )

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        if attrs.get("counts_toward_progress"):
            raise serializers.ValidationError(
                "Selecciona una actividad curricular en vivo; el escritor global está cerrado."
            )
        return attrs


class RecurrenceMutationSerializer(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)
    scope = serializers.ChoiceField(choices=RecurrenceScope.choices)


class EventRescheduleSerializer(RecurrenceMutationSerializer):
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()


class EventCancelSerializer(RecurrenceMutationSerializer):
    pass


class CalendarExtendedPropsSerializer(serializers.Serializer):
    courseId = serializers.UUIDField(allow_null=True)
    courseSlug = serializers.CharField(allow_null=True)
    courseName = serializers.CharField()
    courseGroupId = serializers.UUIDField(allow_null=True)
    courseGroupName = serializers.CharField(allow_null=True)
    courseGroupActivityId = serializers.UUIDField(allow_null=True)
    activityRequired = serializers.BooleanField()
    countsTowardProgress = serializers.BooleanField()
    attendanceThresholdMinutes = serializers.IntegerField(allow_null=True)
    eventType = serializers.CharField()
    occurrenceStatus = serializers.CharField()
    sessionId = serializers.UUIDField(allow_null=True)
    liveStatus = serializers.CharField(allow_null=True)
    hostName = serializers.CharField()
    description = serializers.CharField()
    recurring = serializers.BooleanField()
    occurrenceVersion = serializers.IntegerField()
    canJoin = serializers.BooleanField()
    canStart = serializers.BooleanField()
    canModerate = serializers.BooleanField()
    canShareScreen = serializers.BooleanField()
    canEdit = serializers.BooleanField()
    canDelete = serializers.BooleanField()
    href = serializers.CharField(required=False, allow_null=True)


class CalendarEventSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    groupId = serializers.UUIDField()
    title = serializers.CharField()
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    allDay = serializers.BooleanField()
    editable = serializers.BooleanField()
    startEditable = serializers.BooleanField()
    durationEditable = serializers.BooleanField()
    extendedProps = CalendarExtendedPropsSerializer()


class LiveSessionSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    status = serializers.CharField()
    scheduledStart = serializers.DateTimeField()
    scheduledEnd = serializers.DateTimeField()
    role = serializers.CharField()
    canShareScreen = serializers.BooleanField()
    canModerate = serializers.BooleanField()
    canPublishAudio = serializers.BooleanField()
    canPublishVideo = serializers.BooleanField()
    chatEnabled = serializers.BooleanField()
    recordingMode = serializers.CharField()
    recordingLayout = serializers.CharField()
    recordingResolution = serializers.CharField()
    recordingStatus = serializers.CharField()


class LiveConnectionSerializer(serializers.Serializer):
    serverUrl = serializers.CharField()
    token = serializers.CharField()
    session = LiveSessionSummarySerializer()


class LiveConnectionRequestSerializer(serializers.Serializer):
    recording_acknowledged = serializers.BooleanField(default=False)


class LiveRecordingStartSerializer(serializers.Serializer):
    recording_layout = serializers.ChoiceField(
        choices=("screen_share", "grid", "speaker")
    )
    recording_resolution = serializers.ChoiceField(
        choices=("720p", "1080p"), default="1080p"
    )


class LiveSessionDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField()
    course = serializers.DictField(allow_null=True)
    course_group_id = serializers.UUIDField(allow_null=True)
    course_group_name = serializers.CharField(allow_null=True)
    course_group_activity_id = serializers.UUIDField(allow_null=True)
    activity_required = serializers.BooleanField()
    countsTowardProgress = serializers.BooleanField()
    attendanceThresholdMinutes = serializers.IntegerField(allow_null=True)
    hostName = serializers.CharField()
    scheduledStart = serializers.DateTimeField()
    scheduledEnd = serializers.DateTimeField()
    status = serializers.CharField()
    sessionId = serializers.UUIDField()
    liveStatus = serializers.CharField()
    canJoin = serializers.BooleanField()
    canStart = serializers.BooleanField()
    canModerate = serializers.BooleanField()
    canShareScreen = serializers.BooleanField()
    canPublishAudio = serializers.BooleanField()
    canPublishVideo = serializers.BooleanField()
    chatEnabled = serializers.BooleanField()
    recordingMode = serializers.CharField()
    recordingLayout = serializers.CharField()
    recordingResolution = serializers.CharField()
    recordingStatus = serializers.CharField()
    canEdit = serializers.BooleanField()
    canDelete = serializers.BooleanField()


class LiveSessionListQuerySerializer(serializers.Serializer):
    course_slug = serializers.SlugField(required=False, allow_blank=True)
    scope = serializers.ChoiceField(
        choices=("upcoming", "past", "all"), default="upcoming"
    )


class ParticipantPermissionSerializer(serializers.Serializer):
    can_publish_audio = serializers.BooleanField()
    can_publish_video = serializers.BooleanField()
    can_share_screen = serializers.BooleanField()


class AttendanceSummarySerializer(serializers.Serializer):
    user_id = serializers.UUIDField(allow_null=True)
    display_name = serializers.CharField(allow_blank=True)
    participant_identity = serializers.CharField()
    role = serializers.CharField()
    duration_seconds = serializers.IntegerField(allow_null=True)


class OperationAcceptedSerializer(serializers.Serializer):
    status = serializers.CharField()


class WebhookResultSerializer(serializers.Serializer):
    status = serializers.CharField()
    duplicate = serializers.BooleanField()
