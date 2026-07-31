# pyright: reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportUnknownMemberType=false
from __future__ import annotations

import uuid
from typing import Any

from domain.assets.models import Asset

from .models import CourseRelease


def published_asset_usage(asset_id: uuid.UUID) -> dict[str, Any]:
    asset = Asset.objects.filter(pk=asset_id).first()
    if asset is None:
        return {"content_versions": [], "releases": []}
    releases: list[dict[str, Any]] = []
    for release in CourseRelease.objects.filter(
        course__organization_id=asset.organization_id
    ).only("id", "number", "course_id", "snapshot"):
        manifest = release.snapshot.get("assets", [])
        if any(
            isinstance(item, dict) and item.get("asset_id") == str(asset_id)
            for item in manifest
        ):
            releases.append(
                {
                    "release_id": str(release.id),
                    "release_number": release.number,
                    "course_id": str(release.course_id),
                }
            )
    return {"content_versions": [], "releases": releases}
