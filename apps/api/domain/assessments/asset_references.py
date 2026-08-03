from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from domain.assets.choices import AssetKind, AssetStatus, AssetVersionStatus
from domain.assets.models import AssetVersion
from domain.organizations.models import Organization

from .exceptions import AssessmentInvalid

ASSET_NODE_KINDS = {
    "imageAsset": AssetKind.IMAGE,
    "audioAsset": AssetKind.AUDIO,
    "videoAsset": AssetKind.VIDEO,
    "documentAsset": AssetKind.DOCUMENT,
    "datasetAsset": AssetKind.DATASET,
}


@dataclass(frozen=True)
class PendingAssessmentAssetReference:
    location: str
    reference_role: str
    asset_version: AssetVersion


def _uuid(value: object, *, location: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as error:
        raise AssessmentInvalid(
            f"La referencia multimedia de {location} no contiene un UUID válido."
        ) from error


def _requested_references(
    public: dict[str, Any],
) -> list[tuple[str, str, uuid.UUID, str]]:
    requested: list[tuple[str, str, uuid.UUID, str]] = []
    pending: list[tuple[object, str]] = [(public.get("prompt"), "public.prompt")]
    while pending:
        current, path = pending.pop()
        if isinstance(current, list):
            pending.extend(
                (item, f"{path}.{index}") for index, item in enumerate(current)
            )
            continue
        if not isinstance(current, dict):
            continue
        node_type = str(current.get("type", ""))
        expected_kind = ASSET_NODE_KINDS.get(node_type)
        attrs = current.get("attrs")
        if expected_kind is not None:
            if not isinstance(attrs, dict):
                raise AssessmentInvalid(
                    f"El recurso de {path} no tiene atributos válidos."
                )
            version_id = _uuid(attrs.get("assetVersionId"), location=path)
            requested.append((path, "primary", version_id, expected_kind))
            captions_id = attrs.get("captionsAssetVersionId")
            if node_type == "videoAsset" and captions_id is not None:
                requested.append(
                    (
                        f"{path}.captions",
                        "captions",
                        _uuid(captions_id, location=f"{path}.captions"),
                        AssetKind.CAPTION,
                    )
                )
        pending.extend((value, f"{path}.{key}") for key, value in current.items())

    for collection in ("options", "left", "right"):
        entries = public.get(collection)
        if not isinstance(entries, list):
            continue
        for index, option in enumerate(entries):
            if not isinstance(option, dict) or not isinstance(
                option.get("media"), dict
            ):
                continue
            media = option["media"]
            path = f"public.{collection}.{index}.media"
            requested.append(
                (
                    path,
                    "choice",
                    _uuid(media.get("asset_version_id"), location=path),
                    AssetKind.IMAGE,
                )
            )
    return requested


def validate_assessment_asset_references(
    public: dict[str, Any], *, organization: Organization
) -> tuple[PendingAssessmentAssetReference, ...]:
    requested = _requested_references(public)
    if not requested:
        return ()
    ids = {version_id for _, _, version_id, _ in requested}
    versions = {
        version.id: version
        for version in AssetVersion.objects.filter(id__in=ids).select_related("asset")
    }
    references: list[PendingAssessmentAssetReference] = []
    for location, role, version_id, expected_kind in requested:
        version = versions.get(version_id)
        if version is None:
            raise AssessmentInvalid(f"La versión multimedia de {location} no existe.")
        if version.asset.organization_id != organization.id:
            raise AssessmentInvalid(
                f"La versión multimedia de {location} pertenece a otra organización."
            )
        if version.asset.status != AssetStatus.ACTIVE:
            raise AssessmentInvalid(
                f"La versión multimedia de {location} pertenece a un recurso archivado."
            )
        if version.status != AssetVersionStatus.READY:
            raise AssessmentInvalid(
                f"La versión multimedia de {location} todavía no está lista."
            )
        if version.asset.kind != expected_kind:
            raise AssessmentInvalid(
                f"El tipo multimedia de {location} no coincide con el recurso seleccionado."
            )
        references.append(
            PendingAssessmentAssetReference(
                location=location,
                reference_role=role,
                asset_version=version,
            )
        )
    return tuple(references)


def create_assessment_asset_references(
    *, question_version: object, references: tuple[PendingAssessmentAssetReference, ...]
) -> None:
    from .models import AssessmentAssetReference

    AssessmentAssetReference.objects.bulk_create(
        [
            AssessmentAssetReference(
                question_version=question_version,
                asset_version=reference.asset_version,
                location=reference.location,
                reference_role=reference.reference_role,
            )
            for reference in references
        ]
    )
