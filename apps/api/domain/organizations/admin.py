from django.contrib import admin
from django.http import HttpRequest

from .models import Membership, MembershipEvent, MembershipRoleAssignment, Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):  # pyright: ignore[reportMissingTypeArgument]
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "slug")
    readonly_fields = ("id", "slug", "created_at", "updated_at")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: object | None = None
    ) -> bool:
        return False


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):  # pyright: ignore[reportMissingTypeArgument]
    list_display = ("user", "organization", "status", "joined_at")
    list_filter = ("status",)
    search_fields = ("user__email", "organization__name", "organization__slug")
    list_select_related = ("user", "organization")
    readonly_fields = (
        "id",
        "organization",
        "user",
        "status",
        "joined_at",
        "status_changed_at",
        "status_changed_by",
        "suspended_at",
        "revoked_at",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: object | None = None
    ) -> bool:
        return request.method in {"GET", "HEAD"}

    def has_delete_permission(
        self, request: HttpRequest, obj: object | None = None
    ) -> bool:
        return False


@admin.register(MembershipRoleAssignment)
class MembershipRoleAssignmentAdmin(admin.ModelAdmin):  # pyright: ignore[reportMissingTypeArgument]
    list_display = ("membership", "role", "assigned_at", "revoked_at")
    list_filter = ("role",)
    search_fields = ("membership__user__email", "membership__organization__slug")
    list_select_related = ("membership", "membership__user", "membership__organization")
    readonly_fields = (
        "id",
        "membership",
        "role",
        "assigned_at",
        "assigned_by",
        "revoked_at",
        "revoked_by",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: object | None = None
    ) -> bool:
        return request.method in {"GET", "HEAD"}

    def has_delete_permission(
        self, request: HttpRequest, obj: object | None = None
    ) -> bool:
        return False


@admin.register(MembershipEvent)
class MembershipEventAdmin(admin.ModelAdmin):  # pyright: ignore[reportMissingTypeArgument]
    list_display = ("event_type", "membership", "actor", "created_at")
    list_filter = ("event_type",)
    search_fields = ("membership__user__email", "organization__slug")
    list_select_related = ("membership", "organization", "actor")
    readonly_fields = (
        "id",
        "organization",
        "membership",
        "actor",
        "event_type",
        "role",
        "previous_status",
        "new_status",
        "created_at",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: object | None = None
    ) -> bool:
        return request.method in {"GET", "HEAD"}

    def has_delete_permission(
        self, request: HttpRequest, obj: object | None = None
    ) -> bool:
        return False
