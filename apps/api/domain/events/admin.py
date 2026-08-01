# pyright: reportMissingTypeArgument=false, reportUnknownMemberType=false
from django.contrib import admin

from .models import DomainEvent, EventConsumerDelivery, EventReplayRequest


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: object | None = None) -> bool:
        return False


@admin.register(DomainEvent)
class DomainEventAdmin(ReadOnlyAdmin):
    list_display = (
        "event_type",
        "organization",
        "aggregate_type",
        "occurred_at",
        "correlation_id",
    )
    readonly_fields = tuple(field.name for field in DomainEvent._meta.fields)


@admin.register(EventConsumerDelivery)
class EventConsumerDeliveryAdmin(ReadOnlyAdmin):
    list_display = ("consumer_name", "event", "status", "attempt_count", "processed_at")
    readonly_fields = tuple(field.name for field in EventConsumerDelivery._meta.fields)


@admin.register(EventReplayRequest)
class EventReplayRequestAdmin(ReadOnlyAdmin):
    list_display = ("consumer_name", "organization", "status", "created_at")
    readonly_fields = tuple(field.name for field in EventReplayRequest._meta.fields)
