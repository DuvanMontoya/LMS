# pyright: reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportUnknownMemberType=false
from __future__ import annotations

import uuid
from typing import Any

from .models import ContentAssetReference


def content_asset_usage(asset_id: uuid.UUID) -> dict[str, Any]:
    references = (
        ContentAssetReference.objects.filter(asset_version__asset_id=asset_id)
        .select_related("content_version__document__unit__module__revision__course")
        .order_by("-created_at")[:500]
    )
    return {
        "content_versions": [
            {
                "content_version_id": str(reference.content_version_id),
                "document_version": reference.content_version.number,
                "node_id": str(reference.node_id),
                "reference_role": reference.reference_role,
                "unit_id": str(reference.content_version.document.unit_id),
                "revision_id": str(
                    reference.content_version.document.unit.module.revision_id
                ),
                "course_id": str(
                    reference.content_version.document.unit.module.revision.course_id
                ),
            }
            for reference in references
        ],
        "releases": [],
    }
