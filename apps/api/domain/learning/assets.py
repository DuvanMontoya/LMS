# pyright: reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

import uuid
from typing import Any

from domain.assets.delivery.services import asset_access_descriptor
from domain.assets.models import AssetVersion

from .access import LearningAccess
from .exceptions import LearningAssetAccessDenied, LearningAssetNotInRelease
from .snapshots import snapshot_unit, verified_snapshot

MAX_ASSETS_PER_ACCESS_REQUEST = 50


def _asset_ids_in_document(document: object) -> frozenset[uuid.UUID]:
    found: set[uuid.UUID] = set()
    pending = [document]
    while pending:
        current = pending.pop()
        if isinstance(current, dict):
            attrs = current.get("attrs")
            if isinstance(attrs, dict):
                for field in ("assetVersionId", "captionsAssetVersionId"):
                    value = attrs.get(field)
                    if isinstance(value, str):
                        try:
                            found.add(uuid.UUID(value))
                        except ValueError:
                            continue
            content = current.get("content")
            if isinstance(content, list):
                pending.extend(content)
    return frozenset(found)


def learning_asset_descriptors(
    *,
    access: LearningAccess,
    unit_id: uuid.UUID,
    requested_ids: tuple[uuid.UUID, ...] | None = None,
) -> list[dict[str, Any]]:
    unit = snapshot_unit(access.assignment.release, unit_id)
    allowed_in_unit = _asset_ids_in_document(unit["content"]["document"])
    if requested_ids is None and not allowed_in_unit:
        return []
    selected = tuple(sorted(requested_ids or tuple(allowed_in_unit), key=str))
    if not selected or len(selected) > MAX_ASSETS_PER_ACCESS_REQUEST:
        raise LearningAssetAccessDenied("Solicita entre 1 y 50 assets por operación.")
    if len(set(selected)) != len(selected) or not set(selected).issubset(
        allowed_in_unit
    ):
        raise LearningAssetNotInRelease("Un asset no pertenece a la unidad asignada.")
    snapshot = verified_snapshot(access.assignment.release)
    manifest_ids = {
        uuid.UUID(item["asset_version_id"])
        for item in snapshot.get("assets", [])
        if isinstance(item, dict) and isinstance(item.get("asset_version_id"), str)
    }
    if not set(selected).issubset(manifest_ids):
        raise LearningAssetNotInRelease(
            "Un asset no pertenece al manifest del release asignado."
        )
    versions = {
        version.id: version
        for version in AssetVersion.objects.filter(
            id__in=selected,
            asset__organization_id=access.enrollment.organization_id,
        )
        .select_related("asset__organization")
        .prefetch_related("variants")
    }
    if set(versions) != set(selected):
        raise LearningAssetNotInRelease("Un asset del release no está disponible.")
    from dataclasses import asdict

    return [
        asdict(asset_access_descriptor(version=versions[version_id]))
        for version_id in selected
    ]
