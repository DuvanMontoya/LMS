from rest_framework import serializers


class PublishSerializer(serializers.Serializer):
    expected_publication_version = serializers.IntegerField(min_value=0)


class WithdrawSerializer(PublishSerializer):
    note = serializers.CharField(min_length=1, max_length=2_000, trim_whitespace=True)


class CreateDraftSerializer(PublishSerializer):
    pass


class PublicationStateSerializer(serializers.Serializer):
    has_publication = serializers.BooleanField()
    status = serializers.CharField(allow_null=True)
    lock_version = serializers.IntegerField(min_value=0)
    current_release_number = serializers.IntegerField(min_value=1, allow_null=True)
    first_published_at = serializers.DateTimeField(allow_null=True)
    last_published_at = serializers.DateTimeField(allow_null=True)
    withdrawn_at = serializers.DateTimeField(allow_null=True)
    withdrawal_note = serializers.CharField(allow_blank=True)
    approved_revision_id = serializers.UUIDField(allow_null=True)


class PublishResultSerializer(serializers.Serializer):
    release_number = serializers.IntegerField(min_value=1)
    snapshot_digest = serializers.RegexField(r"^[0-9a-f]{64}$")
    publication_status = serializers.CharField()
    publication_version = serializers.IntegerField(min_value=1)
    already_released = serializers.BooleanField()
    is_current = serializers.BooleanField()


class ReleaseSummarySerializer(serializers.Serializer):
    number = serializers.IntegerField(min_value=1)
    title = serializers.CharField()
    summary = serializers.CharField()
    language_code = serializers.CharField()
    estimated_duration_minutes = serializers.IntegerField(min_value=1, allow_null=True)
    module_count = serializers.IntegerField(min_value=0)
    unit_count = serializers.IntegerField(min_value=0)
    word_count = serializers.IntegerField(min_value=0)
    snapshot_digest = serializers.RegexField(r"^[0-9a-f]{64}$")
    previous_release_number = serializers.IntegerField(min_value=1, allow_null=True)
    source_revision_id = serializers.UUIDField()
    source_revision_number = serializers.IntegerField(min_value=1)
    created_at = serializers.DateTimeField()
    is_current = serializers.BooleanField()


class ReleaseDetailSerializer(ReleaseSummarySerializer):
    schema_version = serializers.IntegerField(min_value=1)
    snapshot_size_bytes = serializers.IntegerField(min_value=1)
    course = serializers.JSONField()
    curriculum = serializers.JSONField()


class VerificationIssueSerializer(serializers.Serializer):
    code = serializers.CharField()
    release_number = serializers.IntegerField(min_value=1, allow_null=True)
    detail = serializers.CharField()


class VerificationSerializer(serializers.Serializer):
    valid = serializers.BooleanField()
    checked_releases = serializers.IntegerField(min_value=0)
    issues = VerificationIssueSerializer(many=True)


class DraftResultSerializer(serializers.Serializer):
    revision_id = serializers.UUIDField()
    revision_number = serializers.IntegerField(min_value=1)
    lock_version = serializers.IntegerField(min_value=1)


class PublishedOutlineUnitSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    summary = serializers.CharField(allow_blank=True)
    estimated_duration_minutes = serializers.IntegerField(min_value=1, allow_null=True)
    lesson_kind = serializers.CharField()
    position = serializers.IntegerField(min_value=1)


class PublishedOutlineModuleSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    position = serializers.IntegerField(min_value=1)
    units = PublishedOutlineUnitSerializer(many=True)


class ReleaseOutlineSerializer(serializers.Serializer):
    release_number = serializers.IntegerField(min_value=1)
    modules = PublishedOutlineModuleSerializer(many=True)


class ReaderNavigationItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    module_id = serializers.UUIDField()
    module_title = serializers.CharField()


class ReaderNavigationSerializer(serializers.Serializer):
    position = serializers.IntegerField(min_value=1)
    total = serializers.IntegerField(min_value=1)
    previous = ReaderNavigationItemSerializer(allow_null=True)
    next = ReaderNavigationItemSerializer(allow_null=True)


class ReleaseUnitSerializer(serializers.Serializer):
    release_number = serializers.IntegerField(min_value=1)
    course = serializers.JSONField()
    unit = serializers.JSONField()
    navigation = ReaderNavigationSerializer()


class LibraryCourseSerializer(serializers.Serializer):
    course_id = serializers.UUIDField()
    slug = serializers.SlugField()
    title = serializers.CharField()
    summary = serializers.CharField()
    language_code = serializers.CharField()
    estimated_duration_minutes = serializers.IntegerField(min_value=1, allow_null=True)
    module_count = serializers.IntegerField(min_value=0)
    unit_count = serializers.IntegerField(min_value=0)
    word_count = serializers.IntegerField(min_value=0)
    release_number = serializers.IntegerField(min_value=1)


class LibraryDetailSerializer(LibraryCourseSerializer):
    subtitle = serializers.CharField(allow_null=True)
    description = serializers.CharField(allow_blank=True)
    subjects = serializers.JSONField()
    learning_objectives = serializers.JSONField()
    outline = PublishedOutlineModuleSerializer(many=True)


class PublishingErrorSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()
