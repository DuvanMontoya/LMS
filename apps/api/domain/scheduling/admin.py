from django.contrib import admin
from django.http import HttpRequest

from .models import (
    AcademicEventOccurrence,
    AcademicEventSeries,
    AttendanceSegment,
    LiveKitWebhookEvent,
    LiveSession,
)


class ReadOnlySchedulingAdmin(admin.ModelAdmin):  # pyright: ignore[reportMissingTypeArgument]
    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: object | None = None
    ) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: object | None = None
    ) -> bool:
        return False


admin.site.register(AcademicEventSeries, ReadOnlySchedulingAdmin)
admin.site.register(AcademicEventOccurrence, ReadOnlySchedulingAdmin)
admin.site.register(LiveSession, ReadOnlySchedulingAdmin)
admin.site.register(LiveKitWebhookEvent, ReadOnlySchedulingAdmin)
admin.site.register(AttendanceSegment, ReadOnlySchedulingAdmin)
