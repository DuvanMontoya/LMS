from __future__ import annotations

import uuid
from typing import Any

from .models import AssessmentAssetReference


def assessment_asset_usage(asset_id: uuid.UUID) -> dict[str, Any]:
    references = (
        AssessmentAssetReference.objects.filter(asset_version__asset_id=asset_id)
        .select_related("question_version__question__bank")
        .order_by("-created_at")[:500]
    )
    return {
        "assessment_versions": [
            {
                "question_version_id": str(reference.question_version_id),
                "question_code": reference.question_version.question.code,
                "bank_id": str(reference.question_version.question.bank_id),
                "location": reference.location,
                "reference_role": reference.reference_role,
            }
            for reference in references
        ],
        "content_versions": [],
        "releases": [],
    }
