# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import uuid
from dataclasses import asdict
from typing import Any

from domain.assets.delivery.services import asset_access_descriptor
from domain.assets.models import AssetVersion

from .exceptions import AssessmentInvalid
from .models import Attempt, Question

MAX_ASSESSMENT_ASSETS_PER_REQUEST = 50


def _asset_ids_in_payloads(payloads: list[object]) -> frozenset[uuid.UUID]:
    found: set[uuid.UUID] = set()
    pending = list(payloads)
    while pending:
        current = pending.pop()
        if isinstance(current, list):
            pending.extend(current)
            continue
        if not isinstance(current, dict):
            continue
        attrs = current.get("attrs")
        if isinstance(attrs, dict):
            for field in ("assetVersionId", "captionsAssetVersionId"):
                value = attrs.get(field)
                if isinstance(value, str):
                    try:
                        found.add(uuid.UUID(value))
                    except ValueError:
                        continue
        media = current.get("media")
        if isinstance(media, dict) and isinstance(media.get("asset_version_id"), str):
            try:
                found.add(uuid.UUID(media["asset_version_id"]))
            except ValueError:
                pass
        pending.extend(current.values())
    return frozenset(found)


def _asset_ids_in_attempt(attempt: Attempt) -> frozenset[uuid.UUID]:
    return _asset_ids_in_payloads(
        [item.public_snapshot for item in attempt.items.all()]
    )


def question_asset_descriptors(
    *, question: Question, public: dict[str, Any]
) -> list[dict[str, Any]]:
    selected = tuple(sorted(_asset_ids_in_payloads([public]), key=str))
    if not selected:
        return []
    if len(selected) > MAX_ASSESSMENT_ASSETS_PER_REQUEST:
        raise AssessmentInvalid("La pregunta contiene más de 50 recursos.")
    versions = {
        version.id: version
        for version in AssetVersion.objects.filter(
            id__in=selected,
            asset__organization_id=question.organization.id,
        )
        .select_related("asset__organization")
        .prefetch_related("variants")
    }
    if set(versions) != set(selected):
        raise AssessmentInvalid("Un recurso de la pregunta no está disponible.")
    return [
        asdict(asset_access_descriptor(version=versions[version_id]))
        for version_id in selected
    ]


def assessment_asset_descriptors(
    *, attempt: Attempt, requested_ids: tuple[uuid.UUID, ...] | None = None
) -> list[dict[str, Any]]:
    allowed = _asset_ids_in_attempt(attempt)
    if requested_ids is None and not allowed:
        return []
    selected = tuple(sorted(requested_ids or tuple(allowed), key=str))
    if not selected or len(selected) > MAX_ASSESSMENT_ASSETS_PER_REQUEST:
        raise AssessmentInvalid("Solicita entre 1 y 50 recursos de la evaluación.")
    if len(set(selected)) != len(selected) or not set(selected).issubset(allowed):
        raise AssessmentInvalid("Un recurso no pertenece a este intento.")
    organization_id = attempt.delivery_assignment.delivery.organization_id
    versions = {
        version.id: version
        for version in AssetVersion.objects.filter(
            id__in=selected,
            asset__organization_id=organization_id,
        )
        .select_related("asset__organization")
        .prefetch_related("variants")
    }
    if set(versions) != set(selected):
        raise AssessmentInvalid("Un recurso de la evaluación no está disponible.")
    return [
        asdict(asset_access_descriptor(version=versions[version_id]))
        for version_id in selected
    ]
