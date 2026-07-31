# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUnknownArgumentType=false
from __future__ import annotations

import shutil
import tempfile
import uuid
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from domain.assets.choices import (
    AssetEventType,
    AssetKind,
    AssetVersionStatus,
    ProcessingJobStatus,
    ProcessingJobType,
    ProcessingStage,
)
from domain.assets.exceptions import (
    AssetChecksumMismatch,
    AssetDomainError,
    AssetFormatInvalid,
    AssetProcessingError,
)
from domain.assets.limits import KIND_LIMITS
from domain.assets.models import (
    Asset,
    AssetEvent,
    AssetProcessingJob,
    AssetUploadSession,
    AssetVariant,
    AssetVersion,
)
from domain.assets.storage.boto3_gateway import storage_gateway
from domain.assets.storage.gateway import ObjectStorageGateway
from domain.assets.storage.keys import private_original_key, private_variant_key

from .antivirus import ClamAVClient
from .audio import process_audio
from .captions import process_caption
from .common import ProcessingResult, calculate_sha256
from .datasets import process_dataset
from .images import process_image
from .pdf import process_pdf
from .video import process_video

JOB_LEASE_SECONDS = 60 * 60 * 9


def claim_processing_job(job_id: uuid.UUID) -> AssetProcessingJob | None:
    with transaction.atomic():
        job = (
            AssetProcessingJob.objects.select_for_update()
            .select_related("asset_version__asset__organization")
            .filter(pk=job_id)
            .first()
        )
        if job is None or job.status in {
            ProcessingJobStatus.COMPLETED,
            ProcessingJobStatus.COMPLETED_WITH_ERRORS,
        }:
            return None
        now = timezone.now()
        if (
            job.status == ProcessingJobStatus.RUNNING
            and job.lease_expires_at is not None
            and job.lease_expires_at > now
        ):
            return None
        job.status = ProcessingJobStatus.RUNNING
        job.stage = ProcessingStage.DOWNLOADING
        job.attempt_count += 1
        job.claimed_at = now
        job.lease_expires_at = now + timedelta(seconds=JOB_LEASE_SECONDS)
        job.started_at = job.started_at or now
        job.save(
            update_fields=[
                "status",
                "stage",
                "attempt_count",
                "claimed_at",
                "lease_expires_at",
                "started_at",
                "updated_at",
            ]
        )
        if job.job_type == ProcessingJobType.INITIAL:
            AssetVersion.objects.filter(pk=job.asset_version_id).update(
                status=AssetVersionStatus.SCANNING
            )
        AssetEvent.objects.create(
            organization=job.asset_version.asset.organization,
            asset=job.asset_version.asset,
            asset_version=job.asset_version,
            processing_job=job,
            event_type=AssetEventType.PROCESSING_STARTED,
        )
        return job


def _set_stage(job_id: uuid.UUID, stage: ProcessingStage) -> None:
    AssetProcessingJob.objects.filter(
        pk=job_id, status=ProcessingJobStatus.RUNNING
    ).update(stage=stage)


def _processor(version: AssetVersion) -> Callable[[Path, Path], ProcessingResult]:
    if version.asset.kind == AssetKind.IMAGE:
        return process_image
    if version.asset.kind == AssetKind.DOCUMENT:
        return lambda source, _workdir: process_pdf(source)
    if version.asset.kind == AssetKind.AUDIO:
        return lambda source, workdir: process_audio(
            source,
            workdir,
            ffmpeg_path=settings.ASSET_FFMPEG_PATH,
            ffprobe_path=settings.ASSET_FFPROBE_PATH,
        )
    if version.asset.kind == AssetKind.VIDEO:
        return lambda source, workdir: process_video(
            source,
            workdir,
            ffmpeg_path=settings.ASSET_FFMPEG_PATH,
            ffprobe_path=settings.ASSET_FFPROBE_PATH,
        )
    if version.asset.kind == AssetKind.CAPTION:
        return process_caption
    if version.asset.kind == AssetKind.DATASET:
        return lambda source, _workdir: process_dataset(
            source, version.declared_mime_type
        )
    raise AssetFormatInvalid("Unsupported asset kind.")


def _validate_detected_contract(
    version: AssetVersion, result: ProcessingResult
) -> None:
    limits = KIND_LIMITS[version.asset.kind]
    if (
        result.detected_mime_type not in limits.declared_mime_types
        or result.extension not in limits.extensions
        or version.declared_mime_type != result.detected_mime_type
        or version.extension != result.extension
    ):
        aliases = {
            ("image/jpeg", ".jpeg", ".jpg"),
            ("audio/mp4", ".mp4", ".m4a"),
            ("audio/mp4", ".m4a", ".m4a"),
            ("audio/m4a", ".m4a", ".m4a"),
            ("audio/x-m4a", ".m4a", ".m4a"),
            ("video/quicktime", ".mov", ".mp4"),
        }
        compatible_alias = any(
            version.declared_mime_type == mime_type
            and version.extension == declared_extension
            and result.extension == detected_extension
            for mime_type, declared_extension, detected_extension in aliases
        )
        if not compatible_alias:
            raise AssetFormatInvalid("Declared and detected file formats do not match.")


def _source_location(
    job: AssetProcessingJob,
) -> tuple[str, str, AssetUploadSession | None]:
    if job.job_type == ProcessingJobType.REPROCESS:
        version = job.asset_version
        if not version.storage_bucket or not version.storage_key:
            raise AssetProcessingError("Ready source object is missing.")
        return version.storage_bucket, version.storage_key, None
    session = (
        job.asset_version.upload_sessions.filter(status="completed")
        .order_by("-created_at")
        .first()
    )
    if session is None:
        raise AssetProcessingError("Completed upload session is missing.")
    return session.quarantine_bucket, session.quarantine_key, session


def process_asset_version(
    job_id: uuid.UUID, *, gateway: ObjectStorageGateway | None = None
) -> None:
    job = claim_processing_job(job_id)
    if job is None:
        return
    gateway = gateway or storage_gateway()
    workdir = Path(tempfile.mkdtemp(prefix=f"lms-assets-{job.id}-"))
    source = workdir / "source.bin"
    uploaded_variant_keys: list[str] = []
    try:
        bucket, key, upload_session = _source_location(job)
        gateway.download_to_path(bucket=bucket, key=key, path=source)
        sha256 = calculate_sha256(source)
        if upload_session and (
            upload_session.expected_sha256 and upload_session.expected_sha256 != sha256
        ):
            raise AssetChecksumMismatch("Uploaded SHA-256 does not match.")
        _set_stage(job.id, ProcessingStage.SCANNING)
        scan = ClamAVClient(
            host=settings.ASSET_CLAMAV_HOST,
            port=settings.ASSET_CLAMAV_PORT,
            timeout_seconds=settings.ASSET_CLAMAV_TIMEOUT_SECONDS,
            maximum_size=KIND_LIMITS[job.asset_version.asset.kind].maximum_size_bytes,
        ).scan_path(source)
        if not scan.clean:
            assert upload_session is not None
            gateway.delete_object(
                bucket=upload_session.quarantine_bucket,
                key=upload_session.quarantine_key,
            )
            _reject_infected(job.id, sha256=sha256, signature=scan.signature)
            return
        _record_scan_passed(job.id)
        _set_stage(job.id, ProcessingStage.VALIDATING)
        if job.job_type == ProcessingJobType.INITIAL:
            AssetVersion.objects.filter(pk=job.asset_version_id).update(
                status=AssetVersionStatus.PROCESSING
            )
        result = _processor(job.asset_version)(source, workdir)
        _validate_detected_contract(job.asset_version, result)
        _set_stage(job.id, ProcessingStage.UPLOADING_VARIANTS)
        variant_records: list[dict[str, object]] = []
        for artifact in result.variants:
            artifact_sha = calculate_sha256(artifact.path)
            variant_key = private_variant_key(
                organization_id=job.asset_version.asset.organization_id,
                asset_id=job.asset_version.asset_id,
                asset_version_id=job.asset_version_id,
                pipeline_name=job.pipeline_name,
                pipeline_version=job.pipeline_version,
                role=artifact.role,
                sha256=artifact_sha,
                extension=artifact.extension,
            )
            head = gateway.upload_path(
                bucket=settings.ASSET_PRIVATE_BUCKET,
                key=variant_key,
                path=artifact.path,
                content_type=artifact.mime_type,
            )
            uploaded_variant_keys.append(variant_key)
            variant_records.append(
                {
                    "role": artifact.role,
                    "mime_type": artifact.mime_type,
                    "extension": artifact.extension,
                    "storage_bucket": settings.ASSET_PRIVATE_BUCKET,
                    "storage_key": variant_key,
                    "size_bytes": head.size_bytes,
                    "sha256": artifact_sha,
                    "width": artifact.width,
                    "height": artifact.height,
                    "duration_milliseconds": artifact.duration_milliseconds,
                    "bitrate": artifact.bitrate,
                    "technical_metadata": artifact.technical_metadata or {},
                }
            )
        _set_stage(job.id, ProcessingStage.PROMOTING_ORIGINAL)
        original_key = private_original_key(
            organization_id=job.asset_version.asset.organization_id,
            asset_id=job.asset_version.asset_id,
            asset_version_id=job.asset_version_id,
            sha256=sha256,
            extension=result.extension,
        )
        if job.job_type == ProcessingJobType.INITIAL:
            original_head = gateway.copy_object(
                source_bucket=bucket,
                source_key=key,
                destination_bucket=settings.ASSET_PRIVATE_BUCKET,
                destination_key=original_key,
                content_type=result.detected_mime_type,
            )
        else:
            original_key = job.asset_version.storage_key
            original_head = gateway.head_object(
                bucket=job.asset_version.storage_bucket, key=original_key
            )
        _finalize_ready(
            job.id,
            sha256=sha256,
            result=result,
            original_key=original_key,
            original_head=original_head,
            variant_records=variant_records,
        )
        if upload_session is not None:
            _set_stage(job.id, ProcessingStage.CLEANING_QUARANTINE)
            gateway.delete_object(
                bucket=upload_session.quarantine_bucket,
                key=upload_session.quarantine_key,
            )
    except Exception as error:
        for variant_key in uploaded_variant_keys:
            try:
                gateway.delete_object(
                    bucket=settings.ASSET_PRIVATE_BUCKET, key=variant_key
                )
            except AssetDomainError:
                pass
        _fail_job(job.id, error)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@transaction.atomic
def _record_scan_passed(job_id: uuid.UUID) -> None:
    job = AssetProcessingJob.objects.select_related(
        "asset_version__asset__organization"
    ).get(pk=job_id)
    AssetEvent.objects.create(
        organization=job.asset_version.asset.organization,
        asset=job.asset_version.asset,
        asset_version=job.asset_version,
        processing_job=job,
        event_type=AssetEventType.MALWARE_SCAN_PASSED,
    )


@transaction.atomic
def _reject_infected(job_id: uuid.UUID, *, sha256: str, signature: str) -> None:
    now = timezone.now()
    job = (
        AssetProcessingJob.objects.select_for_update()
        .select_related("asset_version__asset__organization")
        .get(pk=job_id)
    )
    version = AssetVersion.objects.select_for_update().get(pk=job.asset_version_id)
    version.status = AssetVersionStatus.REJECTED
    version.sha256 = sha256
    version.rejected_at = now
    version.failure_code = "malware_detected"
    version.malware_signature = signature
    version.save(
        update_fields=[
            "status",
            "sha256",
            "rejected_at",
            "failure_code",
            "malware_signature",
        ]
    )
    job.status = ProcessingJobStatus.COMPLETED
    job.stage = ProcessingStage.COMPLETED
    job.completed_at = now
    job.lease_expires_at = None
    job.save(
        update_fields=[
            "status",
            "stage",
            "completed_at",
            "lease_expires_at",
            "updated_at",
        ]
    )
    AssetEvent.objects.create(
        organization=job.asset_version.asset.organization,
        asset=job.asset_version.asset,
        asset_version=version,
        processing_job=job,
        event_type=AssetEventType.MALWARE_DETECTED,
    )


@transaction.atomic
def _finalize_ready(
    job_id: uuid.UUID,
    *,
    sha256: str,
    result: ProcessingResult,
    original_key: str,
    original_head: object,
    variant_records: list[dict[str, object]],
) -> None:
    now = timezone.now()
    job = (
        AssetProcessingJob.objects.select_for_update()
        .select_related("asset_version__asset__organization")
        .get(pk=job_id)
    )
    version = AssetVersion.objects.select_for_update().get(pk=job.asset_version_id)
    for record in variant_records:
        AssetVariant.objects.get_or_create(
            asset_version=version,
            pipeline_name=job.pipeline_name,
            pipeline_version=job.pipeline_version,
            role=record["role"],
            defaults={key: value for key, value in record.items() if key != "role"},
        )
    asset = Asset.objects.select_for_update().get(pk=version.asset_id)
    if job.job_type == ProcessingJobType.INITIAL:
        version.status = AssetVersionStatus.READY
        version.detected_mime_type = result.detected_mime_type
        version.extension = result.extension
        version.sha256 = sha256
        version.storage_bucket = settings.ASSET_PRIVATE_BUCKET
        version.storage_key = original_key
        version.storage_etag = original_head.etag  # type: ignore[attr-defined]
        version.storage_checksum_algorithm = original_head.checksum_algorithm  # type: ignore[attr-defined]
        version.storage_checksum_value = original_head.checksum_value  # type: ignore[attr-defined]
        version.width = result.width
        version.height = result.height
        version.duration_milliseconds = result.duration_milliseconds
        version.page_count = result.page_count
        version.row_count = result.row_count
        version.column_count = result.column_count
        version.technical_metadata = result.technical_metadata
        version.pipeline_name = job.pipeline_name
        version.pipeline_version = job.pipeline_version
        version.ready_at = now
        version.save()
        promoted = (
            asset.status == "active"
            and asset.lock_version == version.expected_asset_lock_version
        )
        if promoted:
            asset.current_version = version
            asset.lock_version += 1
            asset.save(update_fields=["current_version", "lock_version", "updated_at"])
            AssetEvent.objects.create(
                organization=asset.organization,
                asset=asset,
                asset_version=version,
                processing_job=job,
                event_type=AssetEventType.VERSION_PROMOTED,
            )
    job.status = ProcessingJobStatus.COMPLETED
    job.stage = ProcessingStage.COMPLETED
    job.completed_at = now
    job.lease_expires_at = None
    job.save(
        update_fields=[
            "status",
            "stage",
            "completed_at",
            "lease_expires_at",
            "updated_at",
        ]
    )
    AssetEvent.objects.create(
        organization=asset.organization,
        asset=asset,
        asset_version=version,
        processing_job=job,
        event_type=AssetEventType.PROCESSING_COMPLETED,
    )


@transaction.atomic
def _fail_job(job_id: uuid.UUID, error: Exception) -> None:
    now = timezone.now()
    job = (
        AssetProcessingJob.objects.select_for_update()
        .select_related("asset_version__asset__organization")
        .get(pk=job_id)
    )
    if job.status != ProcessingJobStatus.RUNNING:
        return
    code = (
        error.code if isinstance(error, AssetDomainError) else "processing_unexpected"
    )
    version = AssetVersion.objects.select_for_update().get(pk=job.asset_version_id)
    if job.job_type == ProcessingJobType.INITIAL:
        version.status = AssetVersionStatus.FAILED
        version.failed_at = now
        version.failure_code = code
        version.save(update_fields=["status", "failed_at", "failure_code"])
    job.status = ProcessingJobStatus.FAILED
    job.last_error_code = code
    job.completed_at = now
    job.lease_expires_at = None
    job.save(
        update_fields=[
            "status",
            "last_error_code",
            "completed_at",
            "lease_expires_at",
            "updated_at",
        ]
    )
    AssetEvent.objects.create(
        organization=job.asset_version.asset.organization,
        asset=job.asset_version.asset,
        asset_version=version,
        processing_job=job,
        event_type=AssetEventType.PROCESSING_FAILED,
    )
