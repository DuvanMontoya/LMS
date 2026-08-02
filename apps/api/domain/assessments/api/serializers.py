# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from ..choices import FeedbackMode, ResponseStatus
from ..models import (
    Assessment,
    AssessmentDelivery,
    AssessmentItem,
    AssessmentRevision,
    AssessmentSection,
    AssessmentVersion,
    Attempt,
    AttemptItem,
    DeliveryAssignment,
    ManualGradeDecision,
    Question,
    QuestionBank,
    QuestionBankVersion,
    QuestionRevision,
    QuestionVersion,
    Response,
)


class StrictInputSerializer(serializers.Serializer):
    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if isinstance(data, Mapping):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError(
                    {key: ["Este campo no está permitido."] for key in sorted(unknown)}
                )
        return super().to_internal_value(data)


class AssessmentExpectedVersionSerializer(StrictInputSerializer):
    expected_version = serializers.IntegerField(min_value=1)


class QuestionBankCreateSerializer(StrictInputSerializer):
    name = serializers.CharField(max_length=200)
    slug = serializers.SlugField(max_length=80)
    description = serializers.CharField(
        max_length=5000, required=False, allow_blank=True
    )


class QuestionBankUpdateSerializer(AssessmentExpectedVersionSerializer):
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(max_length=5000, allow_blank=True)


class QuestionBankSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionBank
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "status",
            "lock_version",
            "created_at",
            "updated_at",
            "archived_at",
        )
        read_only_fields = fields


class QuestionBankPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = QuestionBankSerializer(many=True)


class QuestionCreateSerializer(StrictInputSerializer):
    code = serializers.CharField(max_length=64)
    type = serializers.CharField(max_length=24)
    definition = serializers.JSONField()


class QuestionSerializer(serializers.ModelSerializer):
    latest_version_number = serializers.SerializerMethodField()
    open_revision_id = serializers.SerializerMethodField()
    open_revision_status = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = (
            "id",
            "bank_id",
            "code",
            "status",
            "open_revision_id",
            "open_revision_status",
            "latest_version_number",
            "created_at",
            "archived_at",
        )
        read_only_fields = fields

    def get_latest_version_number(self, question: Question) -> int | None:
        version = question.versions.order_by("-number").first()
        return version.number if version else None

    def _open_revision(self, question: Question) -> QuestionRevision | None:
        return question.revisions.exclude(status="approved").order_by("-number").first()

    def get_open_revision_id(self, question: Question) -> str | None:
        revision = self._open_revision(question)
        return str(revision.id) if revision else None

    def get_open_revision_status(self, question: Question) -> str | None:
        revision = self._open_revision(question)
        return revision.status if revision else None


class QuestionPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = QuestionSerializer(many=True)


class QuestionRevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionRevision
        fields = (
            "id",
            "question_id",
            "number",
            "based_on_version_id",
            "type",
            "definition",
            "status",
            "lock_version",
            "status_changed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class QuestionRevisionUpdateSerializer(AssessmentExpectedVersionSerializer):
    definition = serializers.JSONField()


class AssessmentTransitionInputSerializer(AssessmentExpectedVersionSerializer):
    note = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class QuestionVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionVersion
        fields = (
            "id",
            "question_id",
            "number",
            "source_revision_id",
            "schema_version",
            "type",
            "public",
            "definition_digest",
            "public_digest",
            "created_at",
        )
        read_only_fields = fields


class QuestionBankVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionBankVersion
        fields = (
            "id",
            "bank_id",
            "number",
            "previous_version_id",
            "snapshot",
            "snapshot_digest",
            "question_count",
            "created_at",
        )
        read_only_fields = fields


class AssessmentCreateSerializer(StrictInputSerializer):
    slug = serializers.SlugField(max_length=80)
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(
        max_length=5000, required=False, allow_blank=True
    )
    instructions = serializers.CharField(
        max_length=10000, required=False, allow_blank=True
    )
    time_limit_minutes = serializers.IntegerField(
        min_value=1, max_value=10080, required=False, allow_null=True
    )
    attempt_limit = serializers.IntegerField(
        min_value=1, max_value=20, required=False, allow_null=True
    )
    pass_basis_points = serializers.IntegerField(
        min_value=0, max_value=10000, default=6000
    )
    shuffle_sections = serializers.BooleanField(default=False)
    shuffle_items = serializers.BooleanField(default=False)
    feedback_mode = serializers.ChoiceField(
        choices=FeedbackMode.choices,
        default="full_after_grading",
    )


class AssessmentSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    authoring_status = serializers.SerializerMethodField()
    latest_version_number = serializers.SerializerMethodField()
    latest_revision_id = serializers.SerializerMethodField()
    latest_revision_number = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = (
            "id",
            "slug",
            "status",
            "title",
            "authoring_status",
            "latest_revision_id",
            "latest_revision_number",
            "latest_version_number",
            "created_at",
            "archived_at",
        )
        read_only_fields = fields

    def _latest_revision(self, assessment: Assessment) -> AssessmentRevision | None:
        return assessment.revisions.order_by("-number").first()

    def get_title(self, assessment: Assessment) -> str:
        revision = self._latest_revision(assessment)
        return revision.title if revision else ""

    def get_authoring_status(self, assessment: Assessment) -> str:
        revision = self._latest_revision(assessment)
        return revision.status if revision else ""

    def get_latest_version_number(self, assessment: Assessment) -> int | None:
        version = assessment.versions.order_by("-number").first()
        return version.number if version else None

    def get_latest_revision_id(self, assessment: Assessment) -> str | None:
        revision = self._latest_revision(assessment)
        return str(revision.id) if revision else None

    def get_latest_revision_number(self, assessment: Assessment) -> int | None:
        revision = self._latest_revision(assessment)
        return revision.number if revision else None


class AssessmentPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = AssessmentSerializer(many=True)


class AssessmentRevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentRevision
        fields = (
            "id",
            "assessment_id",
            "number",
            "based_on_version_id",
            "title",
            "description",
            "instructions",
            "time_limit_minutes",
            "attempt_limit",
            "pass_basis_points",
            "shuffle_sections",
            "shuffle_items",
            "feedback_mode",
            "status",
            "lock_version",
            "status_changed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AssessmentRevisionUpdateSerializer(AssessmentExpectedVersionSerializer):
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(
        max_length=5000, required=False, allow_blank=True
    )
    instructions = serializers.CharField(
        max_length=10000, required=False, allow_blank=True
    )
    time_limit_minutes = serializers.IntegerField(
        min_value=1, max_value=10080, required=False, allow_null=True
    )
    attempt_limit = serializers.IntegerField(
        min_value=1, max_value=20, required=False, allow_null=True
    )
    pass_basis_points = serializers.IntegerField(
        min_value=0, max_value=10000, required=False
    )
    shuffle_sections = serializers.BooleanField(required=False)
    shuffle_items = serializers.BooleanField(required=False)
    feedback_mode = serializers.ChoiceField(
        choices=FeedbackMode.choices, required=False
    )


class ObjectiveReplaceSerializer(AssessmentExpectedVersionSerializer):
    objective_ids = serializers.ListField(child=serializers.UUIDField(), max_length=500)


class SectionCreateSerializer(AssessmentExpectedVersionSerializer):
    title = serializers.CharField(max_length=200)
    instructions = serializers.CharField(
        max_length=5000, required=False, allow_blank=True
    )


class SectionUpdateSerializer(AssessmentExpectedVersionSerializer):
    title = serializers.CharField(max_length=200)
    instructions = serializers.CharField(max_length=5000, allow_blank=True)


class OrderedIdsSerializer(AssessmentExpectedVersionSerializer):
    ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, max_length=500
    )


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentSection
        fields = (
            "id",
            "revision_id",
            "title",
            "instructions",
            "position",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ItemCreateSerializer(AssessmentExpectedVersionSerializer):
    question_version_id = serializers.UUIDField()
    points = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=0)
    required = serializers.BooleanField(default=True)
    objective_ids = serializers.ListField(child=serializers.UUIDField(), max_length=100)


class ItemUpdateSerializer(AssessmentExpectedVersionSerializer):
    points = serializers.DecimalField(
        max_digits=12, decimal_places=3, min_value=Decimal("0.001")
    )
    required = serializers.BooleanField()
    objective_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, max_length=100
    )


class ItemSerializer(serializers.ModelSerializer):
    question_code = serializers.CharField(
        source="question_version.question.code", read_only=True
    )
    question_type = serializers.CharField(
        source="question_version.type", read_only=True
    )
    public = serializers.JSONField(source="question_version.public", read_only=True)
    objective_ids = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentItem
        fields = (
            "id",
            "section_id",
            "question_version_id",
            "question_code",
            "question_type",
            "public",
            "position",
            "points",
            "required",
            "objective_ids",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_objective_ids(self, item: AssessmentItem) -> list[str]:
        return [str(link.objective_id) for link in item.objective_links.all()]


class AssessmentOutlineSerializer(serializers.Serializer):
    revision = AssessmentRevisionSerializer()
    objective_ids = serializers.ListField(child=serializers.UUIDField())
    sections = serializers.ListField()


class AssessmentReadinessSerializer(serializers.Serializer):
    ready = serializers.BooleanField()
    issues = serializers.ListField(child=serializers.CharField())


class AssessmentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentVersion
        fields = (
            "id",
            "assessment_id",
            "number",
            "source_revision_id",
            "previous_version_id",
            "schema_version",
            "public_snapshot",
            "snapshot_digest",
            "title",
            "description",
            "section_count",
            "item_count",
            "maximum_score",
            "time_limit_minutes",
            "attempt_limit",
            "pass_basis_points",
            "feedback_mode",
            "created_at",
        )
        read_only_fields = fields


class VersionSourceSerializer(StrictInputSerializer):
    version_id = serializers.UUIDField()


class DeliveryCreateSerializer(StrictInputSerializer):
    assessment_version_id = serializers.UUIDField()
    name = serializers.CharField(max_length=200)
    course_release_id = serializers.UUIDField(required=False, allow_null=True)
    course_group_activity_id = serializers.UUIDField(required=False, allow_null=True)
    opens_at = serializers.DateTimeField(required=False, allow_null=True)
    closes_at = serializers.DateTimeField(required=False, allow_null=True)


class DeliverySerializer(serializers.ModelSerializer):
    assessment_title = serializers.CharField(
        source="assessment_version.title", read_only=True
    )
    assessment_version_number = serializers.IntegerField(
        source="assessment_version.number", read_only=True
    )
    course_release_title = serializers.CharField(
        source="course_release.title", read_only=True, allow_null=True
    )
    course_release_number = serializers.IntegerField(
        source="course_release.number", read_only=True, allow_null=True
    )

    class Meta:
        model = AssessmentDelivery
        fields = (
            "id",
            "assessment_version_id",
            "assessment_title",
            "assessment_version_number",
            "course_release_id",
            "course_release_title",
            "course_release_number",
            "course_group_activity_id",
            "migration_review_required",
            "unit_id",
            "name",
            "status",
            "opens_at",
            "closes_at",
            "lock_version",
            "created_at",
            "updated_at",
            "withdrawn_at",
            "withdrawal_note",
        )
        read_only_fields = fields


class DeliveryPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = DeliverySerializer(many=True)


class WithdrawalSerializer(AssessmentExpectedVersionSerializer):
    note = serializers.CharField(max_length=2000)


class AssignmentCreateSerializer(StrictInputSerializer):
    release_assignment_id = serializers.UUIDField(required=False)
    release_assignment_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=100,
        required=False,
    )

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        supplied = [
            key
            for key in ("release_assignment_id", "release_assignment_ids")
            if key in attrs
        ]
        if len(supplied) != 1:
            raise serializers.ValidationError(
                "Envía una matrícula individual o un lote, no ambos."
            )
        return attrs


class CohortAssignmentCreateSerializer(StrictInputSerializer):
    cohort_id = serializers.UUIDField()


class DeliveryAssignmentSerializer(serializers.ModelSerializer):
    learner_name = serializers.SerializerMethodField()
    release_number = serializers.IntegerField(
        source="release_assignment.release.number", read_only=True
    )

    class Meta:
        model = DeliveryAssignment
        fields = (
            "id",
            "delivery_id",
            "release_assignment_id",
            "cohort_id",
            "learner_name",
            "release_number",
            "status",
            "assigned_at",
            "revoked_at",
        )
        read_only_fields = fields

    def get_learner_name(self, assignment: DeliveryAssignment) -> str:
        user = assignment.release_assignment.enrollment.membership.user
        return user.get_full_name() or user.email


class LearnerDeliverySerializer(serializers.ModelSerializer):
    delivery = DeliverySerializer(read_only=True)
    attempts_used = serializers.SerializerMethodField()
    in_progress_attempt_id = serializers.SerializerMethodField()
    latest_attempt_id = serializers.SerializerMethodField()
    latest_attempt_status = serializers.SerializerMethodField()
    attempt_limit = serializers.IntegerField(
        source="delivery.assessment_version.attempt_limit", read_only=True
    )

    class Meta:
        model = DeliveryAssignment
        fields = (
            "id",
            "delivery",
            "status",
            "attempts_used",
            "attempt_limit",
            "in_progress_attempt_id",
            "latest_attempt_id",
            "latest_attempt_status",
            "assigned_at",
        )
        read_only_fields = fields

    def get_attempts_used(self, assignment: DeliveryAssignment) -> int:
        return assignment.attempts.count()

    @extend_schema_field(serializers.UUIDField(allow_null=True))
    def get_in_progress_attempt_id(self, assignment: DeliveryAssignment) -> str | None:
        attempt = next(
            (
                attempt
                for attempt in assignment.attempts.all()
                if attempt.status == "in_progress"
            ),
            None,
        )
        return str(attempt.id) if attempt else None

    def _latest_attempt(self, assignment: DeliveryAssignment) -> Attempt | None:
        latest: Attempt | None = None
        for attempt in assignment.attempts.all():
            if latest is None or attempt.attempt_number > latest.attempt_number:
                latest = attempt
        return latest

    @extend_schema_field(serializers.UUIDField(allow_null=True))
    def get_latest_attempt_id(self, assignment: DeliveryAssignment) -> str | None:
        attempt = self._latest_attempt(assignment)
        return str(attempt.id) if attempt else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_latest_attempt_status(self, assignment: DeliveryAssignment) -> str | None:
        attempt = self._latest_attempt(assignment)
        return attempt.status if attempt else None


class AttemptItemSerializer(serializers.ModelSerializer):
    response = serializers.SerializerMethodField()

    class Meta:
        model = AttemptItem
        fields = (
            "id",
            "display_position",
            "points",
            "required",
            "public_snapshot",
            "response",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_response(self, item: AttemptItem) -> dict[str, object] | None:
        try:
            response = item.response
        except Response.DoesNotExist:
            return None
        return {
            "value": response.response.get("value"),
            "status": response.status,
            "saved_at": response.saved_at,
        }


class AttemptSerializer(serializers.ModelSerializer):
    items = AttemptItemSerializer(many=True, read_only=True)

    class Meta:
        model = Attempt
        fields = (
            "id",
            "delivery_assignment_id",
            "assessment_version_id",
            "attempt_number",
            "status",
            "started_at",
            "expires_at",
            "submitted_at",
            "lock_version",
            "maximum_score",
            "items",
        )
        read_only_fields = fields


class ResponseSaveSerializer(AssessmentExpectedVersionSerializer):
    response = serializers.JSONField()


class AttemptResultSerializer(serializers.ModelSerializer):
    feedback = serializers.SerializerMethodField()

    class Meta:
        model = Attempt
        fields = (
            "id",
            "attempt_number",
            "status",
            "submitted_at",
            "graded_at",
            "auto_score",
            "manual_score",
            "total_score",
            "maximum_score",
            "basis_points",
            "passed",
            "feedback",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_feedback(self, attempt: Attempt) -> list[dict[str, object]]:
        if attempt.status != "graded":
            return []
        feedback_mode = attempt.assessment_version.feedback_mode
        if feedback_mode == FeedbackMode.NONE:
            return []
        result: list[dict[str, object]] = []
        for item in attempt.items.select_related("response").all():
            try:
                response = item.response
            except Response.DoesNotExist:
                continue
            feedback = item.feedback_snapshot
            entry: dict[str, object] = {
                "attempt_item_id": str(item.id),
                "score": response.score,
                "maximum": item.points,
            }
            if feedback_mode == FeedbackMode.FULL_AFTER_GRADING:
                general = feedback.get("general")
                if general:
                    entry["message"] = general
                decision = response.manual_decisions.order_by("-sequence").first()
                if decision and decision.feedback:
                    entry["manual_feedback"] = decision.feedback
            result.append(entry)
        return result


class AttemptResultPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = AttemptResultSerializer(many=True)


class ManualGradeSerializer(StrictInputSerializer):
    score = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=0)
    feedback = serializers.CharField(max_length=10000, required=False, allow_blank=True)


class ManualGradeDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManualGradeDecision
        fields = ("id", "response_id", "sequence", "score", "feedback", "created_at")
        read_only_fields = fields


class PendingManualSerializer(serializers.Serializer):
    response_id = serializers.UUIDField()
    attempt_id = serializers.UUIDField()
    attempt_item_id = serializers.UUIDField()
    points = serializers.DecimalField(max_digits=12, decimal_places=3)
    answer = serializers.CharField(allow_blank=True, allow_null=True)
    learner = serializers.CharField()
    response_status = serializers.ChoiceField(choices=ResponseStatus.choices)
    current_score = serializers.DecimalField(max_digits=12, decimal_places=3)
    decision_history = ManualGradeDecisionSerializer(many=True)


class AssessmentActivityBindingInputSerializer(serializers.Serializer):
    assessment_version_id = serializers.UUIDField()
    expected_revision_version = serializers.IntegerField(min_value=1)


class AssessmentActivityBindingSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    activity_id = serializers.UUIDField()
    assessment_version_id = serializers.UUIDField()
    revision_lock_version = serializers.IntegerField()
