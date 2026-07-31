# pyright: reportAttributeAccessIssue=false, reportMissingTypeArgument=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.http import HttpRequest

from .models import (
    Asset,
    AssetEvent,
    AssetProcessingJob,
    AssetUploadPart,
    AssetUploadSession,
    AssetVariant,
    AssetVersion,
)


class ImmutableAdmin(admin.ModelAdmin):
    actions = None

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: Any | None = None
    ) -> bool:
        return request.user.is_active and request.user.is_superuser

    def has_delete_permission(
        self, request: HttpRequest, obj: Any | None = None
    ) -> bool:
        return False

    def get_readonly_fields(
        self, request: HttpRequest, obj: Any | None = None
    ) -> tuple[str, ...]:
        return tuple(field.name for field in self.model._meta.fields)


@admin.register(Asset)
class AssetAdmin(ImmutableAdmin):
    list_display = ("id", "organization", "kind", "name", "status", "updated_at")
    list_filter = ("kind", "status")
    search_fields = ("id", "name")


@admin.register(AssetVersion)
class AssetVersionAdmin(ImmutableAdmin):
    list_display = ("id", "asset", "number", "status", "size_bytes", "created_at")
    list_filter = ("status",)
    search_fields = ("id", "asset__id", "asset__name", "sha256")


@admin.register(AssetVariant)
class AssetVariantAdmin(ImmutableAdmin):
    list_display = (
        "id",
        "asset_version",
        "role",
        "pipeline_version",
        "size_bytes",
        "created_at",
    )
    list_filter = ("role", "pipeline_name", "pipeline_version")
    search_fields = ("id", "asset_version__id", "sha256")


@admin.register(AssetUploadSession)
class AssetUploadSessionAdmin(ImmutableAdmin):
    list_display = ("id", "asset", "upload_method", "status", "expires_at")
    list_filter = ("upload_method", "status")
    search_fields = ("id", "asset__id", "asset_version__id")


@admin.register(AssetUploadPart)
class AssetUploadPartAdmin(ImmutableAdmin):
    list_display = ("id", "upload_session", "part_number", "size_bytes", "recorded_at")
    search_fields = ("id", "upload_session__id")


@admin.register(AssetProcessingJob)
class AssetProcessingJobAdmin(ImmutableAdmin):
    list_display = (
        "id",
        "asset_version",
        "job_type",
        "status",
        "stage",
        "updated_at",
    )
    list_filter = ("job_type", "status", "stage")
    search_fields = ("id", "asset_version__id", "task_id")


@admin.register(AssetEvent)
class AssetEventAdmin(ImmutableAdmin):
    list_display = ("id", "organization", "asset", "event_type", "created_at")
    list_filter = ("event_type",)
    search_fields = ("id", "asset__id", "asset_version__id")
