# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from domain.learning.choices import (
    AcademicGroupLevel,
    AcademicGroupRole,
    AccessState,
    EnrollmentStatus,
    ProgressStatus,
)
from domain.learning.models import AcademicGroup, CourseEnrollment, LearningCohort


class ErrorSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()
    current_version = serializers.IntegerField(required=False)


class AcademicGroupMemberSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField(source="membership.id")
    email = serializers.EmailField(source="membership.user.email")
    role = serializers.ChoiceField(choices=AcademicGroupRole.choices)
    status = serializers.CharField()


class AcademicGroupReadSerializer(serializers.ModelSerializer):
    roster = AcademicGroupMemberSerializer(many=True, read_only=True)
    linked_cohort_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = AcademicGroup
        fields = (
            "id",
            "name",
            "slug",
            "academic_year",
            "level",
            "section",
            "description",
            "status",
            "roster",
            "linked_cohort_count",
            "created_at",
            "updated_at",
        )


class AcademicGroupCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    slug = serializers.SlugField(max_length=100, required=False)
    academic_year = serializers.IntegerField(min_value=2000, max_value=2200)
    level = serializers.ChoiceField(choices=AcademicGroupLevel.choices)
    section = serializers.CharField(max_length=40, required=False, allow_blank=True)
    description = serializers.CharField(
        max_length=2_000, required=False, allow_blank=True
    )


class AcademicGroupRosterEntrySerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=AcademicGroupRole.choices)


class AcademicGroupRosterSerializer(serializers.Serializer):
    members = AcademicGroupRosterEntrySerializer(many=True, allow_empty=True)

    def validate_members(
        self, value: list[dict[str, object]]
    ) -> list[dict[str, object]]:
        membership_ids = [entry["membership_id"] for entry in value]
        if len(membership_ids) != len(set(membership_ids)):
            raise serializers.ValidationError(
                "Una persona no puede aparecer más de una vez en el grupo."
            )
        if len(value) > 200:
            raise serializers.ValidationError(
                "El grupo no puede superar 200 integrantes."
            )
        return value


class PaginatedAcademicGroupSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = AcademicGroupReadSerializer(many=True)


class CohortReadSerializer(serializers.ModelSerializer):
    course_slug = serializers.CharField(source="course.slug")
    course_title = serializers.CharField(source="release.title")
    release_number = serializers.IntegerField(source="release.number")
    enrollment_count = serializers.IntegerField(read_only=True, required=False)
    academic_group_id = serializers.UUIDField(read_only=True, allow_null=True)
    academic_group_name = serializers.CharField(
        source="academic_group.name", read_only=True, allow_null=True
    )

    class Meta:
        model = LearningCohort
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "status",
            "course_slug",
            "course_title",
            "release_number",
            "academic_group_id",
            "academic_group_name",
            "access_starts_at",
            "access_ends_at",
            "enrollment_count",
            "created_at",
            "updated_at",
        )


class CohortCreateSerializer(serializers.Serializer):
    course_slug = serializers.SlugField()
    release_number = serializers.IntegerField(min_value=1)
    academic_group_id = serializers.UUIDField(required=False, allow_null=True)
    name = serializers.CharField(max_length=200)
    slug = serializers.SlugField(max_length=80, required=False)
    description = serializers.CharField(
        max_length=2_000, required=False, allow_blank=True
    )
    access_starts_at = serializers.DateTimeField(required=False, allow_null=True)
    access_ends_at = serializers.DateTimeField(required=False, allow_null=True)


class CohortUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(max_length=2_000, allow_blank=True)
    access_starts_at = serializers.DateTimeField(allow_null=True)
    access_ends_at = serializers.DateTimeField(allow_null=True)


class ProgressSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ProgressStatus.choices)
    completed_units = serializers.IntegerField()
    total_units = serializers.IntegerField()
    completed_required_activities = serializers.IntegerField()
    total_required_activities = serializers.IntegerField()
    percent_basis_points = serializers.IntegerField()
    percent = serializers.DecimalField(max_digits=5, decimal_places=2)
    progress_version = serializers.IntegerField()
    started_at = serializers.DateTimeField(allow_null=True)
    last_activity_at = serializers.DateTimeField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)


class CourseSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    slug = serializers.SlugField()
    title = serializers.CharField()
    summary = serializers.CharField(required=False)


class CohortSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class ResumeSerializer(serializers.Serializer):
    unit_id = serializers.UUIDField(allow_null=True)
    node_id = serializers.UUIDField(allow_null=True)
    href = serializers.CharField(allow_null=True)


class EnrollmentReadSerializer(serializers.ModelSerializer):
    student_email = serializers.EmailField(source="membership.user.email")
    course_id = serializers.UUIDField()
    course_slug = serializers.CharField(source="course.slug")
    course_title = serializers.CharField(
        source="current_release_assignment.release.title"
    )
    release_number = serializers.IntegerField(
        source="current_release_assignment.release.number"
    )
    cohort_name = serializers.CharField(source="cohort.name", allow_null=True)
    access_state = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    enrollment_version = serializers.IntegerField(source="lock_version")
    current_release_assignment_id = serializers.UUIDField(
        read_only=True, allow_null=True
    )
    current_release_id = serializers.UUIDField(
        source="current_release_assignment.release_id",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = CourseEnrollment
        fields = (
            "id",
            "student_email",
            "course_id",
            "course_slug",
            "course_title",
            "release_number",
            "cohort_id",
            "cohort_name",
            "status",
            "access_state",
            "access_starts_at",
            "access_ends_at",
            "enrollment_version",
            "current_release_assignment_id",
            "current_release_id",
            "progress",
            "created_at",
        )

    def get_access_state(self, instance: CourseEnrollment) -> str:
        from domain.learning.access import access_state

        return access_state(instance)

    @extend_schema_field(ProgressSerializer)
    def get_progress(self, instance: CourseEnrollment) -> dict[str, object]:
        from domain.learning.selectors import progress_payload

        assignment = instance.current_release_assignment
        return progress_payload(assignment.progress) if assignment else {}


class EnrollmentCreateSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    course_slug = serializers.SlugField()
    cohort_id = serializers.UUIDField(required=False, allow_null=True)
    release_number = serializers.IntegerField(required=False, min_value=1)
    access_starts_at = serializers.DateTimeField(required=False, allow_null=True)
    access_ends_at = serializers.DateTimeField(required=False, allow_null=True)


class CohortEnrollmentBatchSerializer(serializers.Serializer):
    membership_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, max_length=100
    )


class EnrollmentLifecycleSerializer(serializers.Serializer):
    expected_enrollment_version = serializers.IntegerField(min_value=1)


class ReleaseUpgradeSerializer(EnrollmentLifecycleSerializer):
    target_release_number = serializers.IntegerField(min_value=1)


class MyLearningSerializer(serializers.Serializer):
    enrollment_id = serializers.UUIDField()
    course = CourseSummarySerializer()
    release_number = serializers.IntegerField()
    status = serializers.ChoiceField(choices=EnrollmentStatus.choices)
    access_state = serializers.ChoiceField(choices=AccessState.choices)
    progress = ProgressSerializer()
    resume = ResumeSerializer()
    cohort = CohortSummarySerializer(allow_null=True)


class UnitOutlineSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    summary = serializers.CharField()
    estimated_duration_minutes = serializers.IntegerField(allow_null=True)
    position = serializers.IntegerField()
    status = serializers.CharField()
    is_current = serializers.BooleanField()
    href = serializers.CharField()


class ModuleOutlineSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField()
    position = serializers.IntegerField()
    units = UnitOutlineSerializer(many=True)


class LearningOutlineSerializer(serializers.Serializer):
    course = CourseSummarySerializer()
    release_number = serializers.IntegerField()
    progress = ProgressSerializer()
    cohort = CohortSummarySerializer(allow_null=True)
    resume = ResumeSerializer()
    modules = ModuleOutlineSerializer(many=True)


class LearningUnitSerializer(serializers.Serializer):
    course = serializers.DictField()
    module = serializers.DictField()
    unit = serializers.DictField()
    release_number = serializers.IntegerField()
    topics = serializers.ListField(child=serializers.DictField())
    learning_objectives = serializers.ListField(child=serializers.DictField())
    content = serializers.DictField()
    progress = ProgressSerializer()
    navigation = serializers.DictField()
    assets = serializers.ListField(child=serializers.DictField(), required=False)


class LearningAssetAccessSerializer(serializers.Serializer):
    unit_id = serializers.UUIDField()
    asset_version_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, max_length=50
    )

    def validate_asset_version_ids(self, value: list[object]) -> list[object]:
        if len(set(value)) != len(value):
            raise serializers.ValidationError("No repitas versiones de asset.")
        return value


class LearningAssetAccessResponseSerializer(serializers.Serializer):
    assets = serializers.ListField(child=serializers.DictField())


class CompleteUnitSerializer(serializers.Serializer):
    expected_progress_version = serializers.IntegerField(min_value=1)


class PositionSerializer(serializers.Serializer):
    unit_id = serializers.UUIDField()
    node_id = serializers.UUIDField()


class CompletionResultSerializer(serializers.Serializer):
    progress = ProgressSerializer()
    already_completed = serializers.BooleanField()


class CohortProgressSummarySerializer(serializers.Serializer):
    total_enrollments = serializers.IntegerField()
    active = serializers.IntegerField()
    suspended = serializers.IntegerField()
    revoked = serializers.IntegerField()
    not_started = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    completed = serializers.IntegerField()
    average_percent = serializers.DecimalField(max_digits=5, decimal_places=2)


class PaginatedCohortSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = CohortReadSerializer(many=True)


class PaginatedEnrollmentSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = EnrollmentReadSerializer(many=True)


class PaginatedCohortProgressSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    summary = CohortProgressSummarySerializer()
    results = EnrollmentReadSerializer(many=True)
