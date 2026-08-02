# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportUnknownParameterType=false
from __future__ import annotations

from rest_framework import serializers

from ..choices import AttemptAggregation
from ..models import (
    AnalyticsRefreshJob,
    AssessmentAnalyticsSnapshot,
    AssessmentGradingPolicy,
    AssessmentGradingRevision,
    AssessmentItemPool,
    AssessmentPoolCandidate,
    CourseGradebook,
    GradebookColumn,
    GradebookEntry,
    GradebookSummary,
    ItemAnalyticsSnapshot,
    OptionAnalyticsSnapshot,
    RegradeJob,
    RegradeJobAttempt,
)
from .serializers import AssessmentExpectedVersionSerializer, StrictInputSerializer


class PoolCreateSerializer(AssessmentExpectedVersionSerializer):
    title = serializers.CharField(max_length=200)
    instructions = serializers.CharField(
        max_length=5000, required=False, allow_blank=True
    )
    selection_count = serializers.IntegerField(min_value=1, max_value=200)
    points_per_item = serializers.DecimalField(
        max_digits=12, decimal_places=3, min_value=0
    )
    shuffle_selected = serializers.BooleanField(default=False)
    question_version_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=2, max_length=200
    )


class PoolUpdateSerializer(AssessmentExpectedVersionSerializer):
    title = serializers.CharField(max_length=200)
    instructions = serializers.CharField(max_length=5000, allow_blank=True)
    selection_count = serializers.IntegerField(min_value=1, max_value=200)
    points_per_item = serializers.DecimalField(
        max_digits=12, decimal_places=3, min_value=0
    )
    shuffle_selected = serializers.BooleanField()


class PoolCandidatesSerializer(AssessmentExpectedVersionSerializer):
    question_version_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=2, max_length=200
    )


class AssessmentPoolCandidateSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="question_version.type", read_only=True)
    public = serializers.JSONField(source="question_version.public", read_only=True)

    class Meta:
        model = AssessmentPoolCandidate
        fields = (
            "id",
            "question_version_id",
            "position",
            "type",
            "public",
        )
        read_only_fields = fields


class AssessmentPoolSerializer(serializers.ModelSerializer):
    candidates = AssessmentPoolCandidateSerializer(many=True, read_only=True)

    class Meta:
        model = AssessmentItemPool
        fields = (
            "id",
            "revision_id",
            "title",
            "instructions",
            "position",
            "selection_count",
            "points_per_item",
            "selection_strategy",
            "shuffle_selected",
            "candidates",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class StructureOrderSerializer(AssessmentExpectedVersionSerializer):
    section_ids = serializers.ListField(child=serializers.UUIDField())
    pool_ids = serializers.ListField(child=serializers.UUIDField())


class GradingRevisionSerializer(serializers.ModelSerializer):
    preserve_manual_grades = serializers.BooleanField(default=True, read_only=True)

    class Meta:
        model = AssessmentGradingRevision
        fields = (
            "id",
            "number",
            "previous_revision_id",
            "source",
            "reason",
            "grading_snapshot",
            "snapshot_digest",
            "preserve_manual_grades",
            "created_by_id",
            "created_at",
        )
        read_only_fields = fields


class GradingRevisionMetadataSerializer(serializers.ModelSerializer):
    preserve_manual_grades = serializers.BooleanField(default=True, read_only=True)

    class Meta:
        model = AssessmentGradingRevision
        fields = (
            "id",
            "number",
            "previous_revision_id",
            "source",
            "reason",
            "snapshot_digest",
            "preserve_manual_grades",
            "created_by_id",
            "created_at",
        )
        read_only_fields = fields


class GradingPolicySerializer(serializers.ModelSerializer):
    current_revision = GradingRevisionSerializer(read_only=True)

    class Meta:
        model = AssessmentGradingPolicy
        fields = (
            "id",
            "assessment_version_id",
            "lock_version",
            "current_revision",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ScoringCorrectionSerializer(AssessmentExpectedVersionSerializer):
    reason = serializers.CharField(max_length=2000)
    item_overrides = serializers.DictField(child=serializers.JSONField())


class RegradeJobCreateSerializer(StrictInputSerializer):
    assessment_version_id = serializers.UUIDField()
    grading_revision_id = serializers.UUIDField()
    delivery_id = serializers.UUIDField(required=False, allow_null=True)
    reason = serializers.CharField(max_length=2000)
    preserve_manual_grades = serializers.BooleanField(default=True)

    def validate_preserve_manual_grades(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError(
                "La preservación de notas manuales es obligatoria."
            )
        return value


class RegradeRetrySerializer(AssessmentExpectedVersionSerializer):
    pass


class RegradeJobSerializer(serializers.ModelSerializer):
    preserve_manual_grades = serializers.BooleanField(default=True, read_only=True)
    assessment_title = serializers.CharField(
        source="assessment_version.title", read_only=True
    )
    assessment_version_number = serializers.IntegerField(
        source="assessment_version.number", read_only=True
    )
    grading_revision_number = serializers.IntegerField(
        source="grading_revision.number", read_only=True
    )
    delivery_name = serializers.CharField(
        source="delivery.name", allow_null=True, read_only=True
    )

    class Meta:
        model = RegradeJob
        fields = (
            "id",
            "assessment_version_id",
            "assessment_title",
            "assessment_version_number",
            "grading_revision_id",
            "grading_revision_number",
            "delivery_id",
            "delivery_name",
            "status",
            "reason",
            "preserve_manual_grades",
            "total_attempts",
            "processed_attempts",
            "succeeded_attempts",
            "failed_attempts",
            "lock_version",
            "created_by_id",
            "created_at",
            "started_at",
            "completed_at",
        )
        read_only_fields = fields


class RegradeJobAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegradeJobAttempt
        fields = (
            "id",
            "attempt_id",
            "status",
            "previous_grade_id",
            "new_grade_id",
            "error_code",
            "processed_at",
        )
        read_only_fields = fields


class GradebookCreateSerializer(StrictInputSerializer):
    course_release_id = serializers.UUIDField()
    course_group_id = serializers.UUIDField()


class GradebookColumnCreateSerializer(AssessmentExpectedVersionSerializer):
    delivery_id = serializers.UUIDField()
    title = serializers.CharField(max_length=200)
    weight_basis_points = serializers.IntegerField(min_value=1, max_value=10_000)
    required = serializers.BooleanField(default=True)
    attempt_aggregation = serializers.ChoiceField(
        choices=AttemptAggregation.choices,
        default=AttemptAggregation.HIGHEST,
    )


class GradebookColumnUpdateSerializer(AssessmentExpectedVersionSerializer):
    title = serializers.CharField(max_length=200)
    weight_basis_points = serializers.IntegerField(min_value=1, max_value=10_000)
    required = serializers.BooleanField()
    attempt_aggregation = serializers.ChoiceField(choices=AttemptAggregation.choices)


class GradebookColumnOrderSerializer(AssessmentExpectedVersionSerializer):
    column_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1)


class GradebookColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradebookColumn
        fields = (
            "id",
            "delivery_id",
            "title",
            "position",
            "weight_basis_points",
            "required",
            "attempt_aggregation",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class GradebookSerializer(serializers.ModelSerializer):
    columns = GradebookColumnSerializer(many=True, read_only=True)
    course_title = serializers.CharField(source="course_release.title", read_only=True)
    release_number = serializers.IntegerField(
        source="course_release.number", read_only=True
    )

    class Meta:
        model = CourseGradebook
        fields = (
            "id",
            "course_release_id",
            "course_group_id",
            "academic_period_id",
            "migration_review_required",
            "course_title",
            "release_number",
            "status",
            "lock_version",
            "columns",
            "created_at",
            "updated_at",
            "activated_at",
        )
        read_only_fields = fields


class GradebookEntrySerializer(serializers.ModelSerializer):
    learner_name = serializers.SerializerMethodField()
    cohort_id = serializers.UUIDField(
        source="release_assignment.enrollment.cohort_id", read_only=True
    )
    cohort_name = serializers.CharField(
        source="release_assignment.enrollment.cohort.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = GradebookEntry
        fields = (
            "id",
            "column_id",
            "release_assignment_id",
            "learner_name",
            "cohort_id",
            "cohort_name",
            "attempt_id",
            "attempt_grade_id",
            "status",
            "score",
            "maximum_score",
            "percent_basis_points",
            "passed",
            "updated_at",
        )
        read_only_fields = fields

    def get_learner_name(self, entry: GradebookEntry) -> str:
        user = entry.release_assignment.enrollment.membership.user
        return user.get_full_name() or user.email


class GradebookSummarySerializer(serializers.ModelSerializer):
    learner_name = serializers.SerializerMethodField()
    cohort_id = serializers.UUIDField(
        source="release_assignment.enrollment.cohort_id", read_only=True
    )
    cohort_name = serializers.CharField(
        source="release_assignment.enrollment.cohort.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = GradebookSummary
        fields = (
            "id",
            "release_assignment_id",
            "learner_name",
            "cohort_id",
            "cohort_name",
            "status",
            "completed_columns",
            "total_columns",
            "weighted_percent_basis_points",
            "updated_at",
        )
        read_only_fields = fields

    def get_learner_name(self, summary: GradebookSummary) -> str:
        user = summary.release_assignment.enrollment.membership.user
        return user.get_full_name() or user.email


class GradebookStudentPayloadSerializer(serializers.Serializer):
    gradebook = GradebookSerializer()
    entries = GradebookEntrySerializer(many=True)
    summary = GradebookSummarySerializer()


class AnalyticsRefreshSerializer(StrictInputSerializer):
    assessment_version_id = serializers.UUIDField()
    grading_revision_id = serializers.UUIDField()
    delivery_id = serializers.UUIDField(required=False, allow_null=True)


class AnalyticsJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsRefreshJob
        fields = (
            "id",
            "assessment_version_id",
            "grading_revision_id",
            "delivery_id",
            "status",
            "created_at",
            "started_at",
            "completed_at",
            "error_code",
        )
        read_only_fields = fields


class OptionAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptionAnalyticsSnapshot
        fields = (
            "option_id",
            "selected_count",
            "selected_rate_basis_points",
        )
        read_only_fields = fields


class ItemAnalyticsSerializer(serializers.ModelSerializer):
    options = OptionAnalyticsSerializer(many=True, read_only=True)

    class Meta:
        model = ItemAnalyticsSnapshot
        fields = (
            "id",
            "assessment_item_id",
            "question_version_id",
            "question_type",
            "presented_count",
            "answered_count",
            "omitted_count",
            "mean_credit_basis_points",
            "difficulty_basis_points",
            "discrimination",
            "discrimination_sample_size",
            "discrimination_suppressed",
            "options",
            "created_at",
        )
        read_only_fields = fields


class AnalyticsSnapshotSerializer(serializers.ModelSerializer):
    items = ItemAnalyticsSerializer(many=True, read_only=True)
    insufficient_sample = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentAnalyticsSnapshot
        fields = (
            "id",
            "assessment_version_id",
            "grading_revision_id",
            "delivery_id",
            "sample_size",
            "mean_percent_basis_points",
            "median_percent_basis_points",
            "p25_percent_basis_points",
            "p75_percent_basis_points",
            "pass_rate_basis_points",
            "insufficient_sample",
            "items",
            "created_at",
        )
        read_only_fields = fields

    def get_insufficient_sample(self, snapshot: AssessmentAnalyticsSnapshot) -> bool:
        return snapshot.sample_size < 10
