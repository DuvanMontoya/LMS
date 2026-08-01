from rest_framework import serializers

from domain.scheduling.choices import EventType, RecurrenceScope


class SchedulingErrorSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()


class ParticipantOptionSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    display = serializers.CharField()


class CalendarRangeSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    timeZone = serializers.CharField(max_length=64)
    course = serializers.UUIDField(required=False)


class EventCreateSerializer(serializers.Serializer):
    course_slug = serializers.SlugField(
        required=False, allow_null=True, allow_blank=True
    )
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
    attendance_threshold_minutes = serializers.IntegerField(
        min_value=1, max_value=720, required=False, allow_null=True
    )


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


class LiveConnectionSerializer(serializers.Serializer):
    serverUrl = serializers.CharField()
    token = serializers.CharField()
    session = LiveSessionSummarySerializer()


class LiveSessionDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField()
    course = serializers.DictField(allow_null=True)
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
    canEdit = serializers.BooleanField()
    canDelete = serializers.BooleanField()


class ParticipantPermissionSerializer(serializers.Serializer):
    can_publish_audio = serializers.BooleanField()
    can_publish_video = serializers.BooleanField()
    can_share_screen = serializers.BooleanField()


class AttendanceSummarySerializer(serializers.Serializer):
    user_id = serializers.UUIDField(allow_null=True)
    participant_identity = serializers.CharField()
    role = serializers.CharField()
    duration_seconds = serializers.IntegerField(allow_null=True)


class OperationAcceptedSerializer(serializers.Serializer):
    status = serializers.CharField()


class WebhookResultSerializer(serializers.Serializer):
    status = serializers.CharField()
    duplicate = serializers.BooleanField()
