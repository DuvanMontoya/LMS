# pyright: reportMissingTypeArgument=false, reportUnknownMemberType=false
from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest

from .models import UnitContentDocument, UnitContentVersion


class ReadOnlyContentAdmin(admin.ModelAdmin):
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


@admin.register(UnitContentDocument)
class UnitContentDocumentAdmin(ReadOnlyContentAdmin):
    list_display = ("id", "unit", "current_version", "updated_by", "updated_at")
    list_select_related = ("unit", "current_version", "updated_by")
    search_fields = ("unit__title",)


@admin.register(UnitContentVersion)
class UnitContentVersionAdmin(ReadOnlyContentAdmin):
    list_display = (
        "id",
        "document",
        "number",
        "schema_version",
        "short_digest",
        "character_count",
        "word_count",
        "node_count",
        "created_by",
        "created_at",
    )
    list_select_related = ("document", "created_by")
    exclude = ("content", "plain_text")

    @admin.display(description="Digest")
    def short_digest(self, obj: UnitContentVersion) -> str:
        return f"{obj.digest[:12]}…"
