# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportMissingTypeArgument=false
from rest_framework import serializers

from ..models import EmailDelivery, Notification, NotificationCategory


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            "id",
            "organization_id",
            "category",
            "template_key",
            "title",
            "body",
            "action_url",
            "created_at",
            "read_at",
            "archived_at",
        )
        read_only_fields = fields


class NotificationPaginationSerializer(serializers.Serializer):
    page = serializers.IntegerField(min_value=1)
    page_size = serializers.IntegerField(min_value=1, max_value=50)
    total = serializers.IntegerField(min_value=0)


class NotificationPageSerializer(serializers.Serializer):
    results = NotificationSerializer(many=True)
    pagination = NotificationPaginationSerializer()


class PreferenceValueSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=NotificationCategory.choices)
    in_app_enabled = serializers.BooleanField()
    email_enabled = serializers.BooleanField()


class PreferencesUpdateSerializer(serializers.Serializer):
    preferences = PreferenceValueSerializer(many=True)

    def validate_preferences(
        self, value: list[dict[str, object]]
    ) -> list[dict[str, object]]:
        categories = [item["category"] for item in value]
        if len(categories) != len(set(categories)):
            raise serializers.ValidationError("Cada categoría debe aparecer una vez.")
        return value


class PreferencesResponseSerializer(serializers.Serializer):
    preferences = PreferenceValueSerializer(many=True)


class CountSerializer(serializers.Serializer):
    count = serializers.IntegerField(min_value=0)


class UpdatedSerializer(serializers.Serializer):
    updated = serializers.IntegerField(min_value=0)


class EmailDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailDelivery
        fields = (
            "id",
            "notification_id",
            "template_key",
            "status",
            "attempt_count",
            "message_id",
            "last_error_code",
            "next_attempt_at",
            "created_at",
            "started_at",
            "sent_at",
            "failed_at",
        )
        read_only_fields = fields
