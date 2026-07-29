# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from django.contrib import admin
from django.http import HttpRequest

from .models import (
    Course,
    CourseModule,
    CourseRevision,
    CourseRevisionLearningObjective,
    CourseRevisionSubject,
    CourseRevisionTransition,
    CourseUnit,
    CourseUnitLearningObjective,
    CourseUnitTopic,
)


class ReadOnlyCourseAdmin(admin.ModelAdmin):  # pyright: ignore[reportMissingTypeArgument]
    """Permite inspección operativa sin crear un canal paralelo de escritura."""

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: object | None = None
    ) -> bool:
        return request.method in {"GET", "HEAD"} and request.user.is_superuser

    def has_delete_permission(
        self, request: HttpRequest, obj: object | None = None
    ) -> bool:
        return False


@admin.register(Course)
class CourseAdmin(ReadOnlyCourseAdmin):
    list_display = ("slug", "organization", "status", "created_at", "archived_at")
    list_filter = ("status",)
    search_fields = ("slug", "organization__slug", "organization__name")
    list_select_related = ("organization",)
    readonly_fields = (
        "id",
        "organization",
        "slug",
        "status",
        "created_by",
        "created_at",
        "archived_by",
        "archived_at",
    )


@admin.register(CourseRevision)
class CourseRevisionAdmin(ReadOnlyCourseAdmin):
    list_display = (
        "course",
        "number",
        "authoring_status",
        "lock_version",
        "updated_at",
    )
    list_filter = ("authoring_status",)
    search_fields = ("course__slug", "title", "summary")
    list_select_related = ("course", "course__organization")
    readonly_fields = tuple(
        field.name for field in CourseRevision._meta.get_fields() if field.concrete
    )


@admin.register(CourseModule)
class CourseModuleAdmin(ReadOnlyCourseAdmin):
    list_display = ("title", "revision", "status", "position", "updated_at")
    list_filter = ("status",)
    list_select_related = ("revision", "revision__course")
    readonly_fields = tuple(
        field.name for field in CourseModule._meta.get_fields() if field.concrete
    )


@admin.register(CourseUnit)
class CourseUnitAdmin(ReadOnlyCourseAdmin):
    list_display = ("title", "module", "status", "position", "updated_at")
    list_filter = ("status",)
    list_select_related = ("module", "module__revision")
    readonly_fields = tuple(
        field.name for field in CourseUnit._meta.get_fields() if field.concrete
    )


@admin.register(
    CourseRevisionTransition,
    CourseRevisionSubject,
    CourseRevisionLearningObjective,
    CourseUnitTopic,
    CourseUnitLearningObjective,
)
class CourseReadOnlyRelationAdmin(ReadOnlyCourseAdmin):
    list_display = ("__str__",)
    readonly_fields = ()

    def get_readonly_fields(
        self, request: HttpRequest, obj: object | None = None
    ) -> tuple[str, ...]:
        return tuple(
            field.name for field in self.model._meta.get_fields() if field.concrete
        )
