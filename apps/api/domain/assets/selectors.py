# pyright: reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

from django.db.models import Prefetch, QuerySet

from domain.organizations.models import Organization

from .choices import AssetVersionStatus
from .models import Asset, AssetProcessingJob, AssetVariant, AssetVersion


def assets_for_library(
    organization: Organization,
    *,
    kind: str = "",
    status: str = "",
    query: str = "",
) -> QuerySet[Asset]:
    queryset = (
        Asset.objects.filter(organization=organization)
        .select_related("current_version", "created_by", "updated_by")
        .order_by("-updated_at", "id")
    )
    if kind:
        queryset = queryset.filter(kind=kind)
    if status:
        queryset = queryset.filter(status=status)
    if query.strip():
        queryset = queryset.filter(name__icontains=query.strip()[:200])
    return queryset


def asset_detail(organization: Organization, asset_id: object) -> Asset | None:
    return (
        Asset.objects.filter(organization=organization, pk=asset_id)
        .select_related(
            "organization",
            "current_version",
            "created_by",
            "updated_by",
            "archived_by",
        )
        .prefetch_related(
            Prefetch(
                "versions",
                queryset=AssetVersion.objects.order_by("-number").prefetch_related(
                    Prefetch(
                        "variants", queryset=AssetVariant.objects.order_by("role")
                    ),
                    Prefetch(
                        "processing_jobs",
                        queryset=AssetProcessingJob.objects.order_by("-created_at"),
                    ),
                ),
            )
        )
        .first()
    )


def ready_asset_versions(
    organization: Organization, version_ids: set[object]
) -> QuerySet[AssetVersion]:
    return (
        AssetVersion.objects.filter(
            id__in=version_ids,
            asset__organization=organization,
            status=AssetVersionStatus.READY,
        )
        .select_related("asset__organization")
        .prefetch_related("variants")
    )


def preferred_variants(version: AssetVersion) -> tuple[AssetVariant, ...]:
    variants = list(version.variants.all())
    if not variants:
        return ()
    preferred_by_role: dict[str, AssetVariant] = {}
    for variant in variants:
        current = preferred_by_role.get(variant.role)
        if current is None or (
            variant.pipeline_name,
            _pipeline_sort_key(variant.pipeline_version),
            variant.created_at,
        ) > (
            current.pipeline_name,
            _pipeline_sort_key(current.pipeline_version),
            current.created_at,
        ):
            preferred_by_role[variant.role] = variant
    return tuple(preferred_by_role[role] for role in sorted(preferred_by_role))


def _pipeline_sort_key(value: str) -> tuple[int, str]:
    return (int(value), "") if value.isdecimal() else (-1, value)
