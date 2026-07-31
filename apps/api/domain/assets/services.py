# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportCallIssue=false
from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from domain.organizations.models import Organization

from .choices import (
    AssetEventType,
    AssetStatus,
    AssetVersionStatus,
    ProcessingJobStatus,
    ProcessingJobType,
    ProcessingStage,
)
from .exceptions import AssetAccessDenied, AssetConflict, AssetUploadInvalid
from .models import Asset, AssetEvent, AssetProcessingJob, AssetVersion
from .policies import can_archive_asset, can_manage_assets, can_reprocess_asset


@transaction.atomic
def update_asset_metadata(
    *,
    actor: Any,
    organization: Organization,
    asset: Asset,
    expected_lock_version: int,
    name: str,
    description: str,
) -> Asset:
    if not can_manage_assets(actor, organization):
        raise AssetAccessDenied("No tienes capacidad para gestionar assets.")
    locked = (
        Asset.objects.select_for_update()
        .filter(pk=asset.pk, organization=organization)
        .first()
    )
    if locked is None:
        raise AssetAccessDenied("El asset no existe.")
    if locked.lock_version != expected_lock_version:
        raise AssetConflict("El asset cambió desde que abriste esta pantalla.")
    clean_name = name.strip()
    if not clean_name:
        raise AssetUploadInvalid("El nombre es obligatorio.")
    locked.name = clean_name
    locked.description = description.strip()
    locked.updated_by = actor
    locked.lock_version += 1
    locked.full_clean()
    locked.save()
    return locked


@transaction.atomic
def archive_asset(
    *,
    actor: Any,
    organization: Organization,
    asset: Asset,
    expected_lock_version: int,
) -> Asset:
    if not can_archive_asset(actor, organization):
        raise AssetAccessDenied("No tienes capacidad para archivar assets.")
    locked = (
        Asset.objects.select_for_update()
        .filter(pk=asset.pk, organization=organization)
        .first()
    )
    if locked is None:
        raise AssetAccessDenied("El asset no existe.")
    if locked.lock_version != expected_lock_version:
        raise AssetConflict("El asset cambió desde que abriste esta pantalla.")
    if locked.status == AssetStatus.ARCHIVED:
        return locked
    now = timezone.now()
    locked.status = AssetStatus.ARCHIVED
    locked.archived_by = actor
    locked.archived_at = now
    locked.updated_by = actor
    locked.lock_version += 1
    locked.save()
    AssetEvent.objects.create(
        organization=organization,
        asset=locked,
        event_type=AssetEventType.ASSET_ARCHIVED,
        actor=actor,
    )
    return locked


@transaction.atomic
def restore_asset(
    *,
    actor: Any,
    organization: Organization,
    asset: Asset,
    expected_lock_version: int,
) -> Asset:
    if not can_archive_asset(actor, organization):
        raise AssetAccessDenied("No tienes capacidad para restaurar assets.")
    locked = (
        Asset.objects.select_for_update()
        .filter(pk=asset.pk, organization=organization)
        .first()
    )
    if locked is None:
        raise AssetAccessDenied("El asset no existe.")
    if locked.lock_version != expected_lock_version:
        raise AssetConflict("El asset cambió desde que abriste esta pantalla.")
    if locked.status == AssetStatus.ACTIVE:
        return locked
    locked.status = AssetStatus.ACTIVE
    locked.archived_by = None
    locked.archived_at = None
    locked.updated_by = actor
    locked.lock_version += 1
    locked.save()
    AssetEvent.objects.create(
        organization=organization,
        asset=locked,
        event_type=AssetEventType.ASSET_RESTORED,
        actor=actor,
    )
    return locked


@transaction.atomic
def promote_asset_version(
    *,
    actor: Any,
    organization: Organization,
    version: AssetVersion,
    expected_lock_version: int,
) -> Asset:
    if not can_manage_assets(actor, organization):
        raise AssetAccessDenied("No tienes capacidad para promover versiones.")
    locked_version = (
        AssetVersion.objects.select_related("asset")
        .filter(pk=version.pk, asset__organization=organization)
        .first()
    )
    if locked_version is None:
        raise AssetAccessDenied("La versión no existe.")
    if locked_version.status != AssetVersionStatus.READY:
        raise AssetConflict("Sólo una versión lista puede promoverse.")
    asset = Asset.objects.select_for_update().get(pk=locked_version.asset_id)
    if asset.status != AssetStatus.ACTIVE:
        raise AssetConflict("El asset está archivado.")
    if asset.lock_version != expected_lock_version:
        raise AssetConflict("El asset cambió desde que abriste esta pantalla.")
    if asset.current_version_id == locked_version.id:
        return asset
    asset.current_version = locked_version
    asset.updated_by = actor
    asset.lock_version += 1
    asset.save(
        update_fields=[
            "current_version",
            "updated_by",
            "lock_version",
            "updated_at",
        ]
    )
    AssetEvent.objects.create(
        organization=organization,
        asset=asset,
        asset_version=locked_version,
        event_type=AssetEventType.VERSION_PROMOTED,
        actor=actor,
    )
    return asset


@transaction.atomic
def reprocess_asset_version(
    *,
    actor: Any,
    organization: Organization,
    version: AssetVersion,
) -> AssetProcessingJob:
    if not can_reprocess_asset(actor, organization):
        raise AssetAccessDenied("No tienes capacidad para reprocesar assets.")
    locked_version = (
        AssetVersion.objects.select_for_update()
        .select_related("asset")
        .filter(pk=version.pk, asset__organization=organization)
        .first()
    )
    if locked_version is None:
        raise AssetAccessDenied("La versión no existe.")
    if locked_version.status != AssetVersionStatus.READY:
        raise AssetConflict("Sólo una versión lista puede reprocesarse.")
    current_pipeline = locked_version.pipeline_version
    next_pipeline = (
        str(int(current_pipeline) + 1) if current_pipeline.isdecimal() else "2"
    )
    existing = AssetProcessingJob.objects.filter(
        asset_version=locked_version,
        pipeline_name=settings.ASSET_PIPELINE_NAME,
        pipeline_version=next_pipeline,
    ).first()
    if existing is not None:
        return existing
    job = AssetProcessingJob.objects.create(
        asset_version=locked_version,
        job_type=ProcessingJobType.REPROCESS,
        status=ProcessingJobStatus.QUEUED,
        stage=ProcessingStage.QUEUED,
        pipeline_name=settings.ASSET_PIPELINE_NAME,
        pipeline_version=next_pipeline,
    )
    AssetEvent.objects.create(
        organization=organization,
        asset=locked_version.asset,
        asset_version=locked_version,
        processing_job=job,
        event_type=AssetEventType.REPROCESS_REQUESTED,
        actor=actor,
    )

    def dispatch() -> None:
        from domain.assets.processing.tasks import process_asset_version_task

        result = process_asset_version_task.delay(str(job.id))
        AssetProcessingJob.objects.filter(pk=job.id).update(task_id=result.id or "")

    transaction.on_commit(dispatch)
    return job
