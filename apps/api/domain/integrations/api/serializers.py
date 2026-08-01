from __future__ import annotations

from rest_framework import serializers

from domain.integrations.models import (
    IntegrationConnection,
    IntegrationHealthCheck,
    IntegrationProvider,
)


class IntegrationConnectionSerializer(serializers.ModelSerializer):
    last_four = serializers.CharField(
        source="credential.last_four", read_only=True, default=""
    )

    class Meta:
        model = IntegrationConnection
        fields = (
            "id",
            "provider",
            "status",
            "auth_type",
            "account_label",
            "capabilities",
            "granted_scopes",
            "allowed_models",
            "last_validated_at",
            "last_error_code",
            "lock_version",
            "last_four",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ApiKeyConnectSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(
        choices=[
            IntegrationProvider.OPENAI,
            IntegrationProvider.GEMINI,
            IntegrationProvider.DEEPSEEK,
        ]
    )
    api_key = serializers.CharField(
        write_only=True, trim_whitespace=True, max_length=2048
    )
    expected_version = serializers.IntegerField(min_value=1, required=False)


class ApiKeyRotateSerializer(serializers.Serializer):
    api_key = serializers.CharField(
        write_only=True, trim_whitespace=True, max_length=2048
    )
    expected_version = serializers.IntegerField(min_value=1)


class GoogleOAuthStartSerializer(serializers.Serializer):
    capabilities = serializers.ListField(
        child=serializers.ChoiceField(choices=("calendar", "meet", "drive", "youtube")),
        allow_empty=False,
    )

    def validate_capabilities(self, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise serializers.ValidationError("No repitas capacidades.")
        return values


class GoogleOAuthStartResponseSerializer(serializers.Serializer):
    authorization_url = serializers.URLField(read_only=True)


class HealthCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationHealthCheck
        fields = (
            "id",
            "status",
            "started_at",
            "completed_at",
            "capabilities",
            "error_code",
            "task_id",
            "created_at",
        )
        read_only_fields = fields
