# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportMissingTypeArgument=false
from rest_framework import serializers

from ..models import SearchGeneration, SearchIndexJob


class SnippetSegmentSerializer(serializers.Serializer):
    text = serializers.CharField()
    highlighted = serializers.BooleanField()


class SearchResultSerializer(serializers.Serializer):
    source_type = serializers.CharField()
    source_id = serializers.UUIDField()
    title = serializers.CharField()
    subtitle = serializers.CharField()
    snippet_segments = SnippetSegmentSerializer(many=True)
    url_path = serializers.CharField()
    metadata = serializers.JSONField()
    rank_bucket = serializers.ChoiceField(choices=("high", "medium", "low"))


class SearchPaginationSerializer(serializers.Serializer):
    page = serializers.IntegerField(min_value=1)
    page_size = serializers.IntegerField(min_value=1, max_value=50)
    total = serializers.IntegerField(min_value=0)


class SearchResponseSerializer(serializers.Serializer):
    query = serializers.CharField()
    results = SearchResultSerializer(many=True)
    pagination = SearchPaginationSerializer()
    filters = serializers.ListField(child=serializers.CharField())
    timing_bucket = serializers.CharField()


class SearchSuggestionSerializer(serializers.Serializer):
    title = serializers.CharField()
    source_type = serializers.CharField()
    url_path = serializers.CharField()


class SearchGenerationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchGeneration
        fields = (
            "id",
            "organization_id",
            "number",
            "status",
            "document_count",
            "started_at",
            "completed_at",
            "failure_code",
            "created_at",
        )
        read_only_fields = fields


class SearchIndexJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchIndexJob
        fields = (
            "id",
            "organization_id",
            "generation_id",
            "source_type",
            "operation",
            "status",
            "attempt_count",
            "last_error_code",
            "created_at",
            "started_at",
            "completed_at",
        )
        read_only_fields = fields


class SearchRebuildSerializer(serializers.Serializer):
    organization_slug = serializers.SlugField()
