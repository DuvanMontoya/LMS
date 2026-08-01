# pyright: reportMissingTypeArgument=false, reportUnknownMemberType=false
from django.contrib import admin

from .models import SearchDocument, SearchGeneration, SearchIndexJob


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: object | None = None) -> bool:
        return False


@admin.register(SearchGeneration)
class SearchGenerationAdmin(ReadOnlyAdmin):
    list_display = ("organization", "number", "status", "document_count", "created_at")
    readonly_fields = tuple(field.name for field in SearchGeneration._meta.fields)


@admin.register(SearchIndexJob)
class SearchIndexJobAdmin(ReadOnlyAdmin):
    list_display = ("organization", "operation", "status", "created_at")
    readonly_fields = tuple(field.name for field in SearchIndexJob._meta.fields)


@admin.register(SearchDocument)
class SearchDocumentAdmin(ReadOnlyAdmin):
    list_display = ("title", "source_type", "audience", "is_active", "indexed_at")
    readonly_fields = tuple(field.name for field in SearchDocument._meta.fields)
