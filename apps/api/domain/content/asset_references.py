# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from domain.assets.choices import AssetKind, AssetStatus, AssetVersionStatus
from domain.assets.models import AssetVersion
from domain.organizations.models import Organization

from .exceptions import ContentSchemaInvalid
from .extraction import iter_nodes
from .models import ContentAssetReference, UnitContentVersion

ASSET_NODE_KINDS = {
    "imageAsset": AssetKind.IMAGE,
    "audioAsset": AssetKind.AUDIO,
    "videoAsset": AssetKind.VIDEO,
    "documentAsset": AssetKind.DOCUMENT,
    "datasetAsset": AssetKind.DATASET,
}


@dataclass(frozen=True)
class PendingAssetReference:
    node_id: uuid.UUID
    asset_version: AssetVersion
    reference_role: str


def validate_asset_references(
    content: dict[str, Any], *, organization: Organization
) -> tuple[PendingAssetReference, ...]:
    requested: list[tuple[str, uuid.UUID, uuid.UUID, str, str]] = []
    all_ids: set[uuid.UUID] = set()
    for node, path in iter_nodes(content):
        node_type = str(node.get("type", ""))
        expected_kind = ASSET_NODE_KINDS.get(node_type)
        if expected_kind is None:
            continue
        attrs = node.get("attrs")
        if not isinstance(attrs, dict):
            raise ContentSchemaInvalid(
                "El nodo de asset no tiene atributos.", path=path
            )
        try:
            node_id = uuid.UUID(str(attrs["nodeId"]))
            version_id = uuid.UUID(str(attrs["assetVersionId"]))
        except (KeyError, TypeError, ValueError) as error:
            raise ContentSchemaInvalid(
                "La referencia de asset no contiene UUID válidos.", path=path
            ) from error
        requested.append(
            (node_type, node_id, version_id, "primary", expected_kind.value)
        )
        all_ids.add(version_id)
        captions_id = attrs.get("captionsAssetVersionId")
        if node_type == "videoAsset" and captions_id is not None:
            try:
                parsed_captions_id = uuid.UUID(str(captions_id))
            except ValueError as error:
                raise ContentSchemaInvalid(
                    "La referencia de captions no es un UUID válido.", path=path
                ) from error
            requested.append(
                (
                    node_type,
                    node_id,
                    parsed_captions_id,
                    "captions",
                    AssetKind.CAPTION,
                )
            )
            all_ids.add(parsed_captions_id)
    if not requested:
        return ()
    versions = {
        version.id: version
        for version in AssetVersion.objects.filter(id__in=all_ids).select_related(
            "asset"
        )
    }
    references: list[PendingAssetReference] = []
    for node_type, node_id, version_id, role, expected_kind in requested:
        version = versions.get(version_id)
        if version is None:
            raise ContentSchemaInvalid(
                "La versión de asset no existe.", path=f"asset:{node_id}"
            )
        if version.asset.organization_id != organization.id:
            raise ContentSchemaInvalid(
                "La versión de asset pertenece a otra organización.",
                path=f"asset:{node_id}",
            )
        if version.asset.status != AssetStatus.ACTIVE:
            raise ContentSchemaInvalid(
                "No se pueden crear referencias nuevas a un asset archivado.",
                path=f"asset:{node_id}",
            )
        if version.status != AssetVersionStatus.READY:
            raise ContentSchemaInvalid(
                "La versión de asset no está lista.", path=f"asset:{node_id}"
            )
        if version.asset.kind != expected_kind:
            raise ContentSchemaInvalid(
                f"El nodo {node_type} no coincide con el tipo del asset.",
                path=f"asset:{node_id}",
            )
        references.append(
            PendingAssetReference(
                node_id=node_id,
                asset_version=version,
                reference_role=role,
            )
        )
    return tuple(references)


def create_asset_references(
    content_version: UnitContentVersion,
    references: tuple[PendingAssetReference, ...],
) -> None:
    ContentAssetReference.objects.bulk_create(
        [
            ContentAssetReference(
                content_version=content_version,
                node_id=reference.node_id,
                asset_version=reference.asset_version,
                reference_role=reference.reference_role,
            )
            for reference in references
        ]
    )
