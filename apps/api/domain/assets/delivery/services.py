# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from domain.assets.choices import AssetKind, AssetVersionStatus
from domain.assets.exceptions import AssetAccessDenied, AssetConflict
from domain.assets.models import AssetVariant, AssetVersion
from domain.assets.policies import can_download_original
from domain.assets.selectors import preferred_variants
from domain.assets.storage.boto3_gateway import storage_gateway
from domain.assets.storage.gateway import ObjectStorageGateway
from domain.assets.storage.presigning import content_disposition

from .descriptors import AssetAccessDescriptor, DeliveredObject


def asset_access_descriptor(
    *,
    version: AssetVersion,
    gateway: ObjectStorageGateway | None = None,
    include_original: bool = False,
) -> AssetAccessDescriptor:
    if version.status != AssetVersionStatus.READY:
        raise AssetConflict("La versión no está lista para entrega.")
    gateway = gateway or storage_gateway()
    expires_seconds = settings.ASSET_DOWNLOAD_URL_TTL_SECONDS
    expires_at = timezone.now() + timedelta(seconds=expires_seconds)
    delivered_variants = tuple(
        _deliver_variant(variant, gateway=gateway, expires_seconds=expires_seconds)
        for variant in preferred_variants(version)
    )
    source = None
    if include_original or version.asset.kind in {
        AssetKind.DOCUMENT,
        AssetKind.DATASET,
    }:
        source = _deliver_original(
            version,
            gateway=gateway,
            expires_seconds=expires_seconds,
            inline=version.asset.kind == AssetKind.DOCUMENT and not include_original,
        )
    return AssetAccessDescriptor(
        asset_version_id=str(version.id),
        kind=version.asset.kind,
        expires_at=expires_at,
        source=source,
        variants=delivered_variants,
    )


def authorized_original_descriptor(
    *,
    actor: object,
    version: AssetVersion,
    gateway: ObjectStorageGateway | None = None,
) -> AssetAccessDescriptor:
    if not can_download_original(actor, version.asset.organization):
        raise AssetAccessDenied("No tienes capacidad para descargar originales.")
    return asset_access_descriptor(
        version=version, gateway=gateway, include_original=True
    )


def _deliver_variant(
    variant: AssetVariant,
    *,
    gateway: ObjectStorageGateway,
    expires_seconds: int,
) -> DeliveredObject:
    url = gateway.generate_download_url(
        bucket=variant.storage_bucket,
        key=variant.storage_key,
        expires_seconds=expires_seconds,
        content_type=variant.mime_type,
        content_disposition=content_disposition(
            filename=f"{variant.role}{variant.extension}", inline=True
        ),
    )
    return DeliveredObject(
        role=variant.role,
        url=url,
        mime_type=variant.mime_type,
        size_bytes=variant.size_bytes,
        width=variant.width,
        height=variant.height,
        duration_milliseconds=variant.duration_milliseconds,
    )


def _deliver_original(
    version: AssetVersion,
    *,
    gateway: ObjectStorageGateway,
    expires_seconds: int,
    inline: bool,
) -> DeliveredObject:
    url = gateway.generate_download_url(
        bucket=version.storage_bucket,
        key=version.storage_key,
        expires_seconds=expires_seconds,
        content_type=version.detected_mime_type,
        content_disposition=content_disposition(
            filename=version.original_filename, inline=inline
        ),
    )
    return DeliveredObject(
        role="original",
        url=url,
        mime_type=version.detected_mime_type,
        size_bytes=int(version.size_bytes or 0),
        width=version.width,
        height=version.height,
        duration_milliseconds=version.duration_milliseconds,
    )
