# pyright: reportMissingTypeArgument=false, reportMissingParameterType=false, reportUnknownParameterType=false
from django.contrib import admin

from .models import (
    CourseEnrollment,
    CourseProgress,
    EnrollmentReleaseAssignment,
    LearningCohort,
    LearningEvent,
    UnitProgress,
)


class ReadOnlyHistoryAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LearningCohort)
class LearningCohortAdmin(ReadOnlyHistoryAdmin):
    list_display = ("name", "organization", "course", "release", "status")
    list_filter = ("status", "organization")
    search_fields = ("name", "slug", "course__slug")


@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(ReadOnlyHistoryAdmin):
    list_display = ("membership", "course", "status", "cohort", "created_at")
    list_filter = ("status", "organization")
    search_fields = ("membership__user__email", "course__slug")


@admin.register(EnrollmentReleaseAssignment)
class EnrollmentReleaseAssignmentAdmin(ReadOnlyHistoryAdmin):
    list_display = ("enrollment", "release", "sequence", "reason", "assigned_at")


@admin.register(CourseProgress)
class CourseProgressAdmin(ReadOnlyHistoryAdmin):
    list_display = (
        "release_assignment",
        "status",
        "completed_units",
        "total_units",
        "percent_basis_points",
    )


@admin.register(UnitProgress)
class UnitProgressAdmin(ReadOnlyHistoryAdmin):
    list_display = ("course_progress", "unit_id", "status", "last_opened_at")


@admin.register(LearningEvent)
class LearningEventAdmin(ReadOnlyHistoryAdmin):
    list_display = ("event_type", "enrollment", "unit_id", "actor", "occurred_at")
    list_filter = ("event_type",)
