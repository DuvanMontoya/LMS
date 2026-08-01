# pyright: reportMissingTypeArgument=false, reportUnknownMemberType=false
from django.contrib import admin

from .models import (
    EmailDelivery,
    Notification,
    NotificationDeliveryEvent,
    NotificationPreference,
)


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: object | None = None) -> bool:
        return False


@admin.register(Notification)
class NotificationAdmin(ReadOnlyAdmin):
    list_display = ("title", "recipient", "category", "read_at", "created_at")
    readonly_fields = tuple(field.name for field in Notification._meta.fields)


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(ReadOnlyAdmin):
    list_display = ("user", "category", "in_app_enabled", "email_enabled")
    readonly_fields = tuple(field.name for field in NotificationPreference._meta.fields)


@admin.register(EmailDelivery)
class EmailDeliveryAdmin(ReadOnlyAdmin):
    list_display = ("notification", "status", "attempt_count", "sent_at")
    readonly_fields = tuple(field.name for field in EmailDelivery._meta.fields)


@admin.register(NotificationDeliveryEvent)
class NotificationDeliveryEventAdmin(ReadOnlyAdmin):
    list_display = ("delivery", "status", "error_code", "created_at")
    readonly_fields = tuple(
        field.name for field in NotificationDeliveryEvent._meta.fields
    )
