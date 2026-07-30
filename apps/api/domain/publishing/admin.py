# pyright: reportMissingTypeArgument=false, reportUnknownMemberType=false
from typing import cast

from django.contrib import admin
from django.http import HttpRequest

from .models import CoursePublication, CoursePublicationEvent, CourseRelease


class ReadOnlyPublishingAdmin(admin.ModelAdmin):
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


@admin.register(CoursePublication)
class CoursePublicationAdmin(ReadOnlyPublishingAdmin):
    list_display = (
        "course",
        "status",
        "current_release",
        "lock_version",
        "last_published_at",
    )
    list_filter = ("status",)


@admin.register(CourseRelease)
class CourseReleaseAdmin(ReadOnlyPublishingAdmin):
    list_display = (
        "course",
        "number",
        "short_digest",
        "module_count",
        "unit_count",
        "word_count",
        "created_at",
    )
    exclude = ("snapshot",)

    @admin.display(description="Digest")
    def short_digest(self, obj: CourseRelease) -> str:
        return f"{cast(str, obj.snapshot_digest)[:12]}…"


@admin.register(CoursePublicationEvent)
class CoursePublicationEventAdmin(ReadOnlyPublishingAdmin):
    list_display = (
        "course",
        "event_type",
        "release",
        "revision",
        "actor",
        "created_at",
    )
