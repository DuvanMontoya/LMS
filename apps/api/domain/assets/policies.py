# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

from domain.organizations.capabilities import Capability
from domain.organizations.models import Organization
from domain.organizations.policies import has_capability

from .choices import AssetStatus, AssetVersionStatus
from .models import AssetVersion


def can_view_asset_library(actor: object, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSET_LIBRARY_VIEW)  # type: ignore[arg-type]


def can_manage_assets(actor: object, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSET_LIBRARY_MANAGE)  # type: ignore[arg-type]


def can_upload_asset(actor: object, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSET_UPLOAD)  # type: ignore[arg-type]


def can_archive_asset(actor: object, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSET_ARCHIVE)  # type: ignore[arg-type]


def can_download_original(actor: object, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSET_ORIGINAL_DOWNLOAD)  # type: ignore[arg-type]


def can_reprocess_asset(actor: object, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSET_REPROCESS)  # type: ignore[arg-type]


def can_view_asset_security(actor: object, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSET_SECURITY_VIEW)  # type: ignore[arg-type]


def can_access_asset_version_in_authoring(actor: object, version: AssetVersion) -> bool:
    return (
        version.asset.status == AssetStatus.ACTIVE
        and version.status == AssetVersionStatus.READY
        and can_view_asset_library(actor, version.asset.organization)
    )


def can_access_asset_version_in_learning(
    version: AssetVersion, *, organization_id: object
) -> bool:
    return (
        version.asset.organization_id == organization_id
        and version.status == AssetVersionStatus.READY
    )
