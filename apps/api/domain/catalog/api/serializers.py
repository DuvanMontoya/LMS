# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from domain.catalog.models import (
    AcademicArea,
    Concept,
    Discipline,
    LearningObjective,
    Subject,
    Topic,
)


class AreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicArea
        fields = ("id", "name", "slug", "description", "status")
        read_only_fields = ("id", "status")


class DisciplineSerializer(serializers.ModelSerializer):
    area_id = serializers.UUIDField(source="area.id", read_only=True)

    class Meta:
        model = Discipline
        fields = ("id", "area_id", "name", "slug", "description", "status")
        read_only_fields = ("id", "area_id", "status")


class SubjectSerializer(serializers.ModelSerializer):
    discipline_id = serializers.UUIDField(source="discipline.id", read_only=True)

    class Meta:
        model = Subject
        fields = ("id", "discipline_id", "name", "slug", "description", "status")
        read_only_fields = ("id", "discipline_id", "status")


class TopicSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = ("id", "title", "slug", "description", "status", "depth", "children")
        read_only_fields = fields

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_children(self, topic: Topic) -> list[object]:
        return []


class ConceptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Concept
        fields = ("id", "name", "slug", "definition", "status")
        read_only_fields = ("id", "status")


class CreateAreaSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    slug = serializers.SlugField(max_length=80)
    description = serializers.CharField(
        max_length=2000, required=False, allow_blank=True
    )


class CreateConceptSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    slug = serializers.SlugField(max_length=80)
    definition = serializers.CharField(max_length=3000)


class UpdateAreaSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160, required=False)
    description = serializers.CharField(
        max_length=2000, required=False, allow_blank=True
    )


class UpdateConceptSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160, required=False)
    definition = serializers.CharField(max_length=3000, required=False)


class UpdateNamedEntitySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160, required=False)
    description = serializers.CharField(
        max_length=2000, required=False, allow_blank=True
    )


class ObjectiveSerializer(serializers.ModelSerializer):
    subject_id = serializers.UUIDField(source="subject.id", read_only=True)

    class Meta:
        model = LearningObjective
        fields = (
            "id",
            "subject_id",
            "code",
            "statement",
            "description",
            "cognitive_level",
            "status",
        )
        read_only_fields = ("id", "subject_id", "status")


class CreateDisciplineSerializer(serializers.Serializer):
    area_id = serializers.UUIDField()
    name = serializers.CharField(max_length=160)
    slug = serializers.SlugField(max_length=80)
    description = serializers.CharField(
        max_length=2000, required=False, allow_blank=True
    )


class CreateSubjectSerializer(serializers.Serializer):
    discipline_id = serializers.UUIDField()
    name = serializers.CharField(max_length=160)
    slug = serializers.SlugField(max_length=80)
    description = serializers.CharField(
        max_length=2000, required=False, allow_blank=True
    )


class CreateTopicSerializer(serializers.Serializer):
    parent_id = serializers.UUIDField(required=False)
    title = serializers.CharField(max_length=160)
    slug = serializers.SlugField(max_length=80)
    description = serializers.CharField(
        max_length=2000, required=False, allow_blank=True
    )


class UpdateTopicSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=160, required=False)
    description = serializers.CharField(
        max_length=2000, required=False, allow_blank=True
    )


class MoveTopicSerializer(serializers.Serializer):
    target_id = serializers.UUIDField()
    position = serializers.ChoiceField(
        choices=("left", "right", "first-child", "last-child", "sorted-child"),
        default="sorted-child",
    )


class CreateObjectiveSerializer(serializers.Serializer):
    subject_id = serializers.UUIDField()
    code = serializers.CharField(max_length=32)
    statement = serializers.CharField(max_length=1200)
    description = serializers.CharField(
        max_length=2000, required=False, allow_blank=True
    )
    cognitive_level = serializers.ChoiceField(
        choices=LearningObjective._meta.get_field("cognitive_level").choices,
        required=False,
        allow_blank=True,
    )


class UpdateObjectiveSerializer(serializers.Serializer):
    statement = serializers.CharField(max_length=1200, required=False)
    description = serializers.CharField(
        max_length=2000, required=False, allow_blank=True
    )
    cognitive_level = serializers.ChoiceField(
        choices=LearningObjective._meta.get_field("cognitive_level").choices,
        required=False,
        allow_blank=True,
    )


class SubjectPrerequisiteSerializer(serializers.Serializer):
    prerequisite_id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=("required", "recommended"))
    rationale = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class ReplaceSubjectPrerequisitesSerializer(serializers.Serializer):
    prerequisites = SubjectPrerequisiteSerializer(many=True)


class PrerequisiteGraphEntrySerializer(SubjectPrerequisiteSerializer):
    entity_id = serializers.UUIDField()


class ConceptAssociationEntrySerializer(serializers.Serializer):
    entity_id = serializers.UUIDField()
    concept_ids = serializers.ListField(child=serializers.UUIDField())


class ReplaceConceptAssociationsSerializer(serializers.Serializer):
    concept_ids = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=True, max_length=100
    )
