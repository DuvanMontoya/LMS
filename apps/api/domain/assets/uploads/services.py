# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportCallIssue=false
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from domain.organizations.models import Organization

from ..choices import (
    AssetEventType,
    AssetKind,
    AssetStatus,
    AssetVersionStatus,
    ProcessingJobStatus,
    ProcessingJobType,
    ProcessingStage,
    UploadMethod,
    UploadStatus,
)
from ..exceptions import (
    AssetAccessDenied,
    AssetConflict,
    AssetUploadExpired,
    AssetUploadInvalid,
    AssetUploadRateLimited,
)
from ..limits import (
    KIND_LIMITS,
    MAX_ACTIVE_UPLOADS_PER_USER_ORGANIZATION,
    MAX_MULTIPART_PARTS,
    MAX_UPLOADS_PER_USER_HOUR,
    MULTIPART_PART_SIZE_BYTES,
    SINGLE_UPLOAD_MAX_BYTES,
    UPLOAD_SESSION_TTL_SECONDS,
)
from ..models import (
    Asset,
    AssetEvent,
    AssetProcessingJob,
    AssetUploadPart,
    AssetUploadSession,
    AssetVersion,
)
from ..policies import can_upload_asset
from ..storage.boto3_gateway import storage_gateway
from ..storage.gateway import MultipartPart, ObjectStorageGateway, PresignedPost
from ..storage.keys import (
    normalize_filename,
    normalized_extension,
    quarantine_key,
)
from .multipart import normalize_etag, validate_checksum_sha256, validate_part_number


@dataclass(frozen=True)
class UploadInstructions:
    session: AssetUploadSession
    post: PresignedPost | None
    part_size_bytes: int | None


def _require_upload_access(actor: Any, organization: Organization) -> None:
    if not can_upload_asset(actor, organization):
        raise AssetAccessDenied("No tienes capacidad para cargar assets.")


def _apply_rate_limit(actor: Any, organization: Organization) -> None:
    active = AssetUploadSession.objects.filter(
        organization=organization,
        created_by=actor,
        status__in=[
            UploadStatus.INITIATED,
            UploadStatus.UPLOADING,
            UploadStatus.UPLOADED,
        ],
        expires_at__gt=timezone.now(),
    ).count()
    if active >= MAX_ACTIVE_UPLOADS_PER_USER_ORGANIZATION:
        raise AssetUploadRateLimited("Ya tienes demasiadas cargas activas.")
    bucket = timezone.now().strftime("%Y%m%d%H")
    key = f"asset-upload-rate:{organization.id}:{actor.pk}:{bucket}"
    try:
        if cache.add(key, 1, timeout=3700):
            count = 1
        else:
            count = int(cache.incr(key))
    except Exception as error:
        raise AssetUploadRateLimited(
            "No fue posible verificar el límite de cargas."
        ) from error
    if count > MAX_UPLOADS_PER_USER_HOUR:
        raise AssetUploadRateLimited("Superaste el límite horario de cargas.")


def _validate_input(
    *, kind: str, filename: str, declared_mime_type: str, size_bytes: int
) -> tuple[AssetKind, str, str]:
    try:
        parsed_kind = AssetKind(kind)
    except ValueError as error:
        raise AssetUploadInvalid("El tipo de asset no es válido.") from error
    clean_filename = normalize_filename(filename)
    extension = normalized_extension(clean_filename)
    limits = KIND_LIMITS[parsed_kind.value]
    if size_bytes <= 0 or size_bytes > limits.maximum_size_bytes:
        raise AssetUploadInvalid("El tamaño del archivo no está permitido.")
    if declared_mime_type not in limits.declared_mime_types:
        raise AssetUploadInvalid("El MIME declarado no está permitido.")
    if extension not in limits.extensions:
        raise AssetUploadInvalid("La extensión declarada no está permitida.")
    return parsed_kind, clean_filename, extension


def _validate_expected_sha256(value: str) -> str:
    normalized = value.strip().lower()
    if normalized and (
        len(normalized) != 64
        or any(character not in "0123456789abcdef" for character in normalized)
    ):
        raise AssetUploadInvalid("El SHA-256 esperado es inválido.")
    return normalized


def initialize_asset_upload(
    *,
    actor: Any,
    organization: Organization,
    asset_id: uuid.UUID | None,
    kind: str,
    name: str,
    description: str,
    filename: str,
    declared_mime_type: str,
    size_bytes: int,
    expected_sha256: str = "",
    gateway: ObjectStorageGateway | None = None,
) -> UploadInstructions:
    _require_upload_access(actor, organization)
    parsed_kind, clean_filename, extension = _validate_input(
        kind=kind,
        filename=filename,
        declared_mime_type=declared_mime_type,
        size_bytes=size_bytes,
    )
    expected_sha256 = _validate_expected_sha256(expected_sha256)
    clean_name = name.strip()
    clean_description = description.strip()
    if not clean_name:
        raise AssetUploadInvalid("El nombre del asset es obligatorio.")
    _apply_rate_limit(actor, organization)
    gateway = gateway or storage_gateway()
    session_id = uuid.uuid4()
    session_key = quarantine_key(
        organization_id=organization.id, upload_session_id=session_id
    )
    upload_method = (
        UploadMethod.SINGLE
        if size_bytes <= SINGLE_UPLOAD_MAX_BYTES
        else UploadMethod.MULTIPART
    )
    multipart_upload_id = ""
    if upload_method == UploadMethod.MULTIPART:
        required_parts = (size_bytes + MULTIPART_PART_SIZE_BYTES - 1) // (
            MULTIPART_PART_SIZE_BYTES
        )
        if required_parts > MAX_MULTIPART_PARTS:
            raise AssetUploadInvalid("El archivo requiere demasiadas partes.")
        multipart_upload_id = gateway.create_multipart_upload(
            bucket=settings.ASSET_QUARANTINE_BUCKET,
            key=session_key,
            session_id=str(session_id),
        )
    try:
        with transaction.atomic():
            if asset_id is None:
                asset = Asset.objects.create(
                    organization=organization,
                    kind=parsed_kind,
                    name=clean_name,
                    description=clean_description,
                    created_by=actor,
                    updated_by=actor,
                )
                AssetEvent.objects.create(
                    organization=organization,
                    asset=asset,
                    event_type=AssetEventType.ASSET_CREATED,
                    actor=actor,
                )
                number = 1
            else:
                asset = (
                    Asset.objects.select_for_update()
                    .filter(pk=asset_id, organization=organization)
                    .first()
                )
                if asset is None:
                    raise AssetAccessDenied("El asset no existe.")
                if asset.status != AssetStatus.ACTIVE:
                    raise AssetConflict("El asset está archivado.")
                if asset.kind != parsed_kind:
                    raise AssetUploadInvalid("No se puede cambiar el tipo del asset.")
                number = (
                    AssetVersion.objects.filter(asset=asset).aggregate(
                        maximum=Max("number")
                    )["maximum"]
                    or 0
                ) + 1
            version = AssetVersion.objects.create(
                asset=asset,
                number=number,
                original_filename=clean_filename,
                declared_mime_type=declared_mime_type,
                extension=extension,
                expected_asset_lock_version=asset.lock_version,
                created_by=actor,
            )
            session = AssetUploadSession.objects.create(
                id=session_id,
                organization=organization,
                asset=asset,
                asset_version=version,
                upload_method=upload_method,
                quarantine_bucket=settings.ASSET_QUARANTINE_BUCKET,
                quarantine_key=session_key,
                declared_filename=clean_filename,
                declared_mime_type=declared_mime_type,
                expected_size_bytes=size_bytes,
                expected_sha256=expected_sha256,
                multipart_upload_id=multipart_upload_id,
                part_size_bytes=(
                    MULTIPART_PART_SIZE_BYTES
                    if upload_method == UploadMethod.MULTIPART
                    else None
                ),
                expires_at=timezone.now()
                + timedelta(seconds=UPLOAD_SESSION_TTL_SECONDS),
                created_by=actor,
            )
            AssetEvent.objects.create(
                organization=organization,
                asset=asset,
                asset_version=version,
                upload_session=session,
                event_type=AssetEventType.UPLOAD_INITIALIZED,
                actor=actor,
            )
    except Exception:
        if multipart_upload_id:
            gateway.abort_multipart_upload(
                bucket=settings.ASSET_QUARANTINE_BUCKET,
                key=session_key,
                upload_id=multipart_upload_id,
            )
        raise
    post = None
    if upload_method == UploadMethod.SINGLE:
        post = gateway.generate_upload_post(
            bucket=settings.ASSET_QUARANTINE_BUCKET,
            key=session_key,
            size_bytes=size_bytes,
            expires_seconds=settings.ASSET_UPLOAD_URL_TTL_SECONDS,
            session_id=str(session_id),
        )
    return UploadInstructions(
        session=session,
        post=post,
        part_size_bytes=session.part_size_bytes,
    )


def sign_upload_part(
    *,
    actor: Any,
    organization: Organization,
    session_id: uuid.UUID,
    part_number: int,
    checksum_sha256: str,
    gateway: ObjectStorageGateway | None = None,
) -> str:
    _require_upload_access(actor, organization)
    part_number = validate_part_number(part_number)
    checksum_sha256 = validate_checksum_sha256(checksum_sha256)
    session = (
        AssetUploadSession.objects.filter(
            pk=session_id, organization=organization, created_by=actor
        )
        .select_related("asset_version")
        .first()
    )
    if session is None:
        raise AssetAccessDenied("La sesión no existe.")
    _require_active_multipart(session)
    gateway = gateway or storage_gateway()
    return gateway.generate_part_upload_url(
        bucket=session.quarantine_bucket,
        key=session.quarantine_key,
        upload_id=session.multipart_upload_id,
        part_number=part_number,
        checksum_sha256=checksum_sha256,
        expires_seconds=settings.ASSET_UPLOAD_URL_TTL_SECONDS,
    )


@transaction.atomic
def record_upload_part(
    *,
    actor: Any,
    organization: Organization,
    session_id: uuid.UUID,
    part_number: int,
    etag: str,
    checksum_sha256: str,
    size_bytes: int,
) -> AssetUploadPart:
    _require_upload_access(actor, organization)
    part_number = validate_part_number(part_number)
    checksum_sha256 = validate_checksum_sha256(checksum_sha256)
    etag = normalize_etag(etag)
    session = (
        AssetUploadSession.objects.select_for_update()
        .filter(pk=session_id, organization=organization, created_by=actor)
        .first()
    )
    if session is None:
        raise AssetAccessDenied("La sesión no existe.")
    _require_active_multipart(session)
    if size_bytes <= 0 or (
        size_bytes > int(session.part_size_bytes or 0)
        and part_number
        < (session.expected_size_bytes + int(session.part_size_bytes or 1) - 1)
        // int(session.part_size_bytes or 1)
    ):
        raise AssetUploadInvalid("El tamaño de la parte es inválido.")
    existing = AssetUploadPart.objects.filter(
        upload_session=session, part_number=part_number
    ).first()
    if existing is not None:
        if (
            existing.etag != etag
            or existing.checksum_value != checksum_sha256
            or existing.size_bytes != size_bytes
        ):
            raise AssetConflict("La parte ya fue registrada con otros valores.")
        return existing
    part = AssetUploadPart.objects.create(
        upload_session=session,
        part_number=part_number,
        etag=etag,
        checksum_algorithm="SHA256",
        checksum_value=checksum_sha256,
        size_bytes=size_bytes,
    )
    if session.status == UploadStatus.INITIATED:
        session.status = UploadStatus.UPLOADING
        session.save(update_fields=["status"])
    return part


def _require_active_multipart(session: AssetUploadSession) -> None:
    if session.upload_method != UploadMethod.MULTIPART:
        raise AssetUploadInvalid("La sesión no es multipart.")
    if session.expires_at <= timezone.now():
        raise AssetUploadExpired("La sesión expiró.")
    if session.status not in {UploadStatus.INITIATED, UploadStatus.UPLOADING}:
        raise AssetConflict("La sesión no admite nuevas partes.")


def complete_asset_upload(
    *,
    actor: Any,
    organization: Organization,
    session_id: uuid.UUID,
    gateway: ObjectStorageGateway | None = None,
) -> AssetProcessingJob:
    _require_upload_access(actor, organization)
    gateway = gateway or storage_gateway()
    with transaction.atomic():
        session = (
            AssetUploadSession.objects.select_for_update()
            .select_related("asset", "asset_version")
            .filter(pk=session_id, organization=organization, created_by=actor)
            .first()
        )
        if session is None:
            raise AssetAccessDenied("La sesión no existe.")
        existing_job = session.asset_version.processing_jobs.first()
        if session.status == UploadStatus.COMPLETED and existing_job is not None:
            return existing_job
        if session.expires_at <= timezone.now():
            raise AssetUploadExpired("La sesión expiró.")
        if session.status not in {
            UploadStatus.INITIATED,
            UploadStatus.UPLOADING,
            UploadStatus.UPLOADED,
        }:
            raise AssetConflict("La sesión no puede completarse.")
        if session.upload_method == UploadMethod.MULTIPART:
            parts = list(session.parts.order_by("part_number"))
            expected_count = (
                session.expected_size_bytes + int(session.part_size_bytes or 1) - 1
            ) // int(session.part_size_bytes or 1)
            if (
                len(parts) != expected_count
                or [part.part_number for part in parts]
                != list(range(1, expected_count + 1))
                or sum(part.size_bytes for part in parts) != session.expected_size_bytes
            ):
                raise AssetUploadInvalid("La lista de partes no está completa.")
            gateway.complete_multipart_upload(
                bucket=session.quarantine_bucket,
                key=session.quarantine_key,
                upload_id=session.multipart_upload_id,
                parts=[
                    MultipartPart(
                        part_number=part.part_number,
                        etag=part.etag,
                        checksum_sha256=part.checksum_value,
                    )
                    for part in parts
                ],
            )
        head = gateway.head_object(
            bucket=session.quarantine_bucket, key=session.quarantine_key
        )
        if head.size_bytes != session.expected_size_bytes or head.metadata.get(
            "upload-session"
        ) != str(session.id):
            raise AssetUploadInvalid("El objeto cargado no coincide con la sesión.")
        now = timezone.now()
        session.status = UploadStatus.COMPLETED
        session.completed_at = now
        session.save(update_fields=["status", "completed_at"])
        version = session.asset_version
        version.status = AssetVersionStatus.UPLOADED
        version.size_bytes = head.size_bytes
        version.storage_etag = head.etag
        version.storage_checksum_algorithm = head.checksum_algorithm
        version.storage_checksum_value = head.checksum_value
        version.save(
            update_fields=[
                "status",
                "size_bytes",
                "storage_etag",
                "storage_checksum_algorithm",
                "storage_checksum_value",
            ]
        )
        job = AssetProcessingJob.objects.create(
            asset_version=version,
            job_type=ProcessingJobType.INITIAL,
            status=ProcessingJobStatus.QUEUED,
            stage=ProcessingStage.QUEUED,
            pipeline_name=settings.ASSET_PIPELINE_NAME,
            pipeline_version=settings.ASSET_PIPELINE_VERSION,
        )
        AssetEvent.objects.create(
            organization=organization,
            asset=session.asset,
            asset_version=version,
            upload_session=session,
            processing_job=job,
            event_type=AssetEventType.UPLOAD_COMPLETED,
            actor=actor,
        )

        def dispatch() -> None:
            from domain.assets.processing.tasks import process_asset_version_task

            result = process_asset_version_task.delay(str(job.id))
            AssetProcessingJob.objects.filter(pk=job.id).update(task_id=result.id or "")

        transaction.on_commit(dispatch)
        return job


def abort_asset_upload(
    *,
    actor: Any,
    organization: Organization,
    session_id: uuid.UUID,
    gateway: ObjectStorageGateway | None = None,
) -> AssetUploadSession:
    _require_upload_access(actor, organization)
    gateway = gateway or storage_gateway()
    with transaction.atomic():
        session = (
            AssetUploadSession.objects.select_for_update()
            .select_related("asset", "asset_version")
            .filter(pk=session_id, organization=organization, created_by=actor)
            .first()
        )
        if session is None:
            raise AssetAccessDenied("La sesión no existe.")
        if session.status in {UploadStatus.ABORTED, UploadStatus.EXPIRED}:
            return session
        if session.status == UploadStatus.COMPLETED:
            raise AssetConflict("Una carga completada no puede abortarse.")
        if session.multipart_upload_id:
            gateway.abort_multipart_upload(
                bucket=session.quarantine_bucket,
                key=session.quarantine_key,
                upload_id=session.multipart_upload_id,
            )
        else:
            gateway.delete_object(
                bucket=session.quarantine_bucket, key=session.quarantine_key
            )
        now = timezone.now()
        session.status = UploadStatus.ABORTED
        session.aborted_at = now
        session.save(update_fields=["status", "aborted_at"])
        version = session.asset_version
        version.status = AssetVersionStatus.FAILED
        version.failed_at = now
        version.failure_code = "upload_aborted"
        version.save(update_fields=["status", "failed_at", "failure_code"])
        AssetEvent.objects.create(
            organization=organization,
            asset=session.asset,
            asset_version=version,
            upload_session=session,
            event_type=AssetEventType.PROCESSING_FAILED,
            actor=actor,
        )
        return session
