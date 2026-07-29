# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportMissingTypeArgument=false, reportAttributeAccessIssue=false
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from domain.catalog.models import LearningObjective, Subject, Topic

from ..choices import SubjectAlignmentType
from ..models import (
    Course,
    CourseModule,
    CourseRevision,
    CourseRevisionLearningObjective,
    CourseRevisionSubject,
    CourseRevisionTransition,
    CourseUnit,
    CourseUnitLearningObjective,
    CourseUnitTopic,
)


class ExpectedVersionSerializer(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)


class CourseCreateSerializer(serializers.Serializer):
    slug = serializers.SlugField(max_length=80)
    title = serializers.CharField(max_length=200)
    subtitle = serializers.CharField(max_length=240, required=False, allow_blank=True)
    summary = serializers.CharField(max_length=1200)
    description = serializers.CharField(
        max_length=5000, required=False, allow_blank=True
    )
    language_code = serializers.CharField(max_length=12, default="es")
    estimated_duration_minutes = serializers.IntegerField(
        min_value=1, required=False, allow_null=True
    )
    primary_subject_id = serializers.UUIDField()
    supporting_subject_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list, max_length=50
    )
    learning_objective_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list, max_length=200
    )


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ("id", "slug", "status", "created_at", "archived_at")
        read_only_fields = fields


class PrimarySubjectSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class CourseListSerializer(CourseSerializer):
    title = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    authoring_status = serializers.SerializerMethodField()
    primary_subject = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta(CourseSerializer.Meta):
        fields = (
            *CourseSerializer.Meta.fields,
            "title",
            "summary",
            "authoring_status",
            "primary_subject",
            "updated_at",
        )

    def _revision(self, course: Course) -> CourseRevision | None:
        revisions = getattr(course, "visible_revisions", None)
        if revisions is None:
            revisions = list(course.revisions.all())
        return max(revisions, key=lambda item: item.number) if revisions else None

    def get_title(self, course: Course) -> str:
        revision = self._revision(course)
        return revision.title if revision else ""

    def get_summary(self, course: Course) -> str:
        revision = self._revision(course)
        return revision.summary if revision else ""

    def get_authoring_status(self, course: Course) -> str:
        revision = self._revision(course)
        return revision.authoring_status if revision else ""

    def get_updated_at(self, course: Course) -> str | None:
        revision = self._revision(course)
        return revision.updated_at.isoformat() if revision else None

    @extend_schema_field(PrimarySubjectSerializer(allow_null=True))
    def get_primary_subject(self, course: Course) -> dict[str, object] | None:
        revision = self._revision(course)
        if not revision:
            return None
        alignment = next(
            (
                item
                for item in revision.subject_alignments.all()
                if item.alignment_type == SubjectAlignmentType.PRIMARY
            ),
            None,
        )
        if not alignment:
            return None
        return {"id": alignment.subject_id, "name": alignment.subject.name}


class CoursePageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = CourseListSerializer(many=True)


class RevisionSerializer(serializers.ModelSerializer):
    course_slug = serializers.CharField(source="course.slug", read_only=True)

    class Meta:
        model = CourseRevision
        fields = (
            "id",
            "course_slug",
            "number",
            "based_on_revision_id",
            "title",
            "subtitle",
            "summary",
            "description",
            "language_code",
            "estimated_duration_minutes",
            "authoring_status",
            "lock_version",
            "status_changed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class RevisionMetadataUpdateSerializer(ExpectedVersionSerializer):
    title = serializers.CharField(max_length=200, required=False)
    subtitle = serializers.CharField(max_length=240, required=False, allow_blank=True)
    summary = serializers.CharField(max_length=1200, required=False)
    description = serializers.CharField(
        max_length=5000, required=False, allow_blank=True
    )
    language_code = serializers.CharField(max_length=12, required=False)
    estimated_duration_minutes = serializers.IntegerField(
        min_value=1, required=False, allow_null=True
    )


class TransitionSerializer(serializers.ModelSerializer):
    actor_display = serializers.SerializerMethodField()

    class Meta:
        model = CourseRevisionTransition
        fields = (
            "id",
            "from_status",
            "to_status",
            "actor_display",
            "note",
            "created_at",
        )
        read_only_fields = fields

    def get_actor_display(self, transition: CourseRevisionTransition) -> str:
        return transition.actor.get_full_name() or transition.actor.email


class SubjectSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ("id", "name", "slug", "status")
        read_only_fields = fields


class ObjectiveSummarySerializer(serializers.ModelSerializer):
    subject_id = serializers.UUIDField(source="subject.id", read_only=True)

    class Meta:
        model = LearningObjective
        fields = ("id", "subject_id", "code", "statement", "status")
        read_only_fields = fields


class TopicSummarySerializer(serializers.ModelSerializer):
    subject_id = serializers.UUIDField(source="subject.id", read_only=True)

    class Meta:
        model = Topic
        fields = ("id", "subject_id", "title", "slug", "status")
        read_only_fields = fields


class RevisionSubjectSerializer(serializers.ModelSerializer):
    subject = SubjectSummarySerializer(read_only=True)

    class Meta:
        model = CourseRevisionSubject
        fields = ("id", "subject", "alignment_type", "position")
        read_only_fields = fields


class ReplaceSubjectsSerializer(ExpectedVersionSerializer):
    primary_subject_id = serializers.UUIDField()
    supporting_subject_ids = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=True, max_length=50
    )


class RevisionObjectiveSerializer(serializers.ModelSerializer):
    learning_objective = ObjectiveSummarySerializer(read_only=True)

    class Meta:
        model = CourseRevisionLearningObjective
        fields = ("id", "learning_objective", "position")
        read_only_fields = fields


class ReplaceObjectivesSerializer(ExpectedVersionSerializer):
    learning_objective_ids = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=True, max_length=200
    )


class ModuleSerializer(serializers.ModelSerializer):
    revision_id = serializers.UUIDField(source="revision.id", read_only=True)

    class Meta:
        model = CourseModule
        fields = (
            "id",
            "revision_id",
            "title",
            "description",
            "status",
            "position",
            "created_at",
            "updated_at",
            "archived_at",
        )
        read_only_fields = fields


class ModuleMutationSerializer(ModuleSerializer):
    lock_version = serializers.IntegerField(read_only=True)

    class Meta(ModuleSerializer.Meta):
        fields = (*ModuleSerializer.Meta.fields, "lock_version")
        read_only_fields = fields


class ModuleCreateSerializer(ExpectedVersionSerializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(
        max_length=3000, required=False, allow_blank=True
    )


class ModuleUpdateSerializer(ExpectedVersionSerializer):
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(
        max_length=3000, required=False, allow_blank=True
    )


class ReplaceOrderSerializer(ExpectedVersionSerializer):
    ordered_ids = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=True, max_length=200
    )


class UnitSerializer(serializers.ModelSerializer):
    module_id = serializers.UUIDField(source="module.id", read_only=True)

    class Meta:
        model = CourseUnit
        fields = (
            "id",
            "module_id",
            "title",
            "summary",
            "estimated_duration_minutes",
            "status",
            "position",
            "created_at",
            "updated_at",
            "archived_at",
        )
        read_only_fields = fields


class UnitMutationSerializer(UnitSerializer):
    lock_version = serializers.IntegerField(read_only=True)

    class Meta(UnitSerializer.Meta):
        fields = (*UnitSerializer.Meta.fields, "lock_version")
        read_only_fields = fields


class UnitCreateSerializer(ExpectedVersionSerializer):
    title = serializers.CharField(max_length=200)
    summary = serializers.CharField(max_length=1200, required=False, allow_blank=True)
    estimated_duration_minutes = serializers.IntegerField(
        min_value=1, required=False, allow_null=True
    )


class UnitUpdateSerializer(ExpectedVersionSerializer):
    title = serializers.CharField(max_length=200, required=False)
    summary = serializers.CharField(max_length=1200, required=False, allow_blank=True)
    estimated_duration_minutes = serializers.IntegerField(
        min_value=1, required=False, allow_null=True
    )


class UnitTopicSerializer(serializers.ModelSerializer):
    topic = TopicSummarySerializer(read_only=True)

    class Meta:
        model = CourseUnitTopic
        fields = ("id", "topic", "position")
        read_only_fields = fields


class ReplaceTopicsSerializer(ExpectedVersionSerializer):
    topic_ids = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=True, max_length=200
    )


class UnitObjectiveSerializer(serializers.ModelSerializer):
    learning_objective = ObjectiveSummarySerializer(read_only=True)

    class Meta:
        model = CourseUnitLearningObjective
        fields = ("id", "learning_objective", "position")
        read_only_fields = fields


class WorkflowActionSerializer(ExpectedVersionSerializer):
    note = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class RequestChangesSerializer(WorkflowActionSerializer):
    note = serializers.CharField(max_length=2000, allow_blank=False)


class MutationResultSerializer(serializers.Serializer):
    revision_id = serializers.UUIDField()
    lock_version = serializers.IntegerField(min_value=1)


class ReadinessIssueSerializer(serializers.Serializer):
    code = serializers.CharField()
    path = serializers.CharField()
    message = serializers.CharField()


class ReadinessSerializer(serializers.Serializer):
    ready = serializers.BooleanField()
    issues = ReadinessIssueSerializer(many=True)


class OutlineUnitSerializer(UnitSerializer):
    topics = UnitTopicSerializer(source="topic_alignments", many=True, read_only=True)
    learning_objectives = UnitObjectiveSerializer(
        source="objective_alignments", many=True, read_only=True
    )
    content_status = serializers.CharField(default="Contenido académico pendiente")

    class Meta(UnitSerializer.Meta):
        fields = (
            *UnitSerializer.Meta.fields,
            "topics",
            "learning_objectives",
            "content_status",
        )


class OutlineModuleSerializer(ModuleSerializer):
    units = OutlineUnitSerializer(many=True, read_only=True)

    class Meta(ModuleSerializer.Meta):
        fields = (*ModuleSerializer.Meta.fields, "units")


class OutlineSerializer(serializers.Serializer):
    course = CourseSerializer(read_only=True)
    revision = RevisionSerializer(source="*", read_only=True)
    subjects = RevisionSubjectSerializer(
        source="subject_alignments", many=True, read_only=True
    )
    learning_objectives = RevisionObjectiveSerializer(
        source="objective_alignments", many=True, read_only=True
    )
    modules = OutlineModuleSerializer(many=True, read_only=True)
