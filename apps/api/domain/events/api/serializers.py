# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportMissingTypeArgument=false
from rest_framework import serializers

from ..models import DomainEvent, EventConsumerDelivery, EventReplayRequest
from ..registry import registered_consumers


class DomainEventSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = DomainEvent
        fields = (
            "id",
            "event_type",
            "schema_version",
            "organization_id",
            "aggregate_type",
            "aggregate_id",
            "correlation_id",
            "causation_id",
            "occurred_at",
            "created_at",
        )
        read_only_fields = fields


class DomainEventDetailSerializer(DomainEventSummarySerializer):
    payload = serializers.JSONField(read_only=True)

    class Meta(DomainEventSummarySerializer.Meta):
        fields = DomainEventSummarySerializer.Meta.fields + ("payload",)


class EventConsumerDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = EventConsumerDelivery
        fields = (
            "id",
            "event_id",
            "consumer_name",
            "status",
            "attempt_count",
            "claimed_at",
            "lease_expires_at",
            "next_attempt_at",
            "last_error_code",
            "processed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class EventReplayCreateSerializer(serializers.Serializer):
    consumer_name = serializers.CharField(max_length=120)
    organization_slug = serializers.SlugField()
    event_type = serializers.CharField(max_length=160, required=False, allow_blank=True)
    from_event_id = serializers.UUIDField(required=False, allow_null=True)
    to_event_id = serializers.UUIDField(required=False, allow_null=True)
    reason = serializers.CharField(min_length=10, max_length=1000)

    def validate_consumer_name(self, value: str) -> str:
        if value not in registered_consumers():
            raise serializers.ValidationError("Consumer desconocido.")
        return value


class EventReplaySerializer(serializers.ModelSerializer):
    class Meta:
        model = EventReplayRequest
        fields = (
            "id",
            "consumer_name",
            "organization_id",
            "event_type",
            "from_event_id",
            "to_event_id",
            "status",
            "total_events",
            "processed_events",
            "failed_events",
            "reason",
            "created_at",
            "started_at",
            "completed_at",
        )
        read_only_fields = fields
