# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

from rest_framework import serializers

from ..models import UnitContentVersion


class ContentWriteSerializer(serializers.Serializer):
    expected_document_version = serializers.IntegerField(min_value=0)
    schema_version = serializers.IntegerField(min_value=1)
    content = serializers.JSONField()


class ContentValidateSerializer(serializers.Serializer):
    schema_version = serializers.IntegerField(min_value=1)
    content = serializers.JSONField()


class ContentMetricsSerializer(serializers.Serializer):
    character_count = serializers.IntegerField(min_value=0)
    word_count = serializers.IntegerField(min_value=0)
    node_count = serializers.IntegerField(min_value=0)
    is_meaningful = serializers.BooleanField()


class ContentCurrentSerializer(ContentMetricsSerializer):
    document_id = serializers.UUIDField(allow_null=True)
    document_version = serializers.IntegerField(min_value=0)
    schema_version = serializers.IntegerField(min_value=1)
    content = serializers.JSONField()
    digest = serializers.CharField(allow_blank=True)
    updated_at = serializers.DateTimeField(allow_null=True)
    editable = serializers.BooleanField()
    no_op = serializers.BooleanField(default=False)


class ContentVersionSummarySerializer(serializers.ModelSerializer):
    created_by_display = serializers.SerializerMethodField()
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = UnitContentVersion
        fields = (
            "number",
            "schema_version",
            "created_at",
            "created_by_display",
            "character_count",
            "word_count",
            "node_count",
            "digest",
            "is_current",
        )
        read_only_fields = fields

    def get_created_by_display(self, obj: UnitContentVersion) -> str:
        display = obj.created_by.get_full_name().strip()
        return display or "Usuario de la organización"

    def get_is_current(self, obj: UnitContentVersion) -> bool:
        current_number = self.context.get("current_number")
        return obj.number == current_number


class ContentVersionDetailSerializer(ContentVersionSummarySerializer):
    content = serializers.JSONField(read_only=True)
    plain_text = serializers.CharField(read_only=True)

    class Meta(ContentVersionSummarySerializer.Meta):
        fields = (*ContentVersionSummarySerializer.Meta.fields, "content", "plain_text")


class RestoreContentSerializer(serializers.Serializer):
    expected_document_version = serializers.IntegerField(min_value=1)


class ContentErrorSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()
    path = serializers.CharField(required=False)
    current_document_version = serializers.IntegerField(required=False)
