# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Trim

from domain.organizations.models import Organization

from .choices import (
    AssetEventType,
    AssetKind,
    AssetStatus,
    AssetVersionStatus,
    ProcessingJobStatus,
    ProcessingJobType,
    ProcessingStage,
    UploadMethod,
    UploadStatus,
    VariantRole,
)


class Asset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="assets"
    )
    kind = models.CharField(max_length=16, choices=AssetKind.choices)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=16, choices=AssetStatus.choices, default=AssetStatus.ACTIVE
    )
    current_version = models.OneToOneField(
        "AssetVersion",
        on_delete=models.PROTECT,
        related_name="current_for_asset",
        null=True,
        blank=True,
    )
    lock_version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assets_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assets_updated",
    )
    updated_at = models.DateTimeField(auto_now=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assets_archived",
        null=True,
        blank=True,
    )
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(name=Trim(F("name"))) & ~Q(name=""),
                name="assets_name_trimmed_nonempty",
            ),
            models.CheckConstraint(
                condition=Q(lock_version__gt=0), name="assets_lock_positive"
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=AssetStatus.ACTIVE,
                        archived_at__isnull=True,
                        archived_by__isnull=True,
                    )
                    | Q(
                        status=AssetStatus.ARCHIVED,
                        archived_at__isnull=False,
                        archived_by__isnull=False,
                    )
                ),
                name="assets_archive_state",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "kind", "status"],
                name="asset_org_kind_state_ix",
            ),
            models.Index(fields=["updated_at"], name="asset_updated_ix"),
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        self.name = self.name.strip()
        self.description = self.description.strip()
        if self.current_version_id:
            version = self.current_version
            if version.asset_id != self.id:
                raise ValidationError(
                    {"current_version": "La versión actual debe pertenecer al asset."}
                )


class AssetVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="versions")
    number = models.PositiveIntegerField()
    status = models.CharField(
        max_length=24,
        choices=AssetVersionStatus.choices,
        default=AssetVersionStatus.PENDING_UPLOAD,
    )
    original_filename = models.CharField(max_length=255)
    declared_mime_type = models.CharField(max_length=128)
    detected_mime_type = models.CharField(max_length=128, blank=True, default="")
    extension = models.CharField(max_length=16, blank=True, default="")
    size_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    sha256 = models.CharField(max_length=64, blank=True, default="")
    storage_bucket = models.CharField(max_length=255, blank=True, default="")
    storage_key = models.CharField(max_length=1024, blank=True, default="")
    storage_etag = models.CharField(max_length=255, blank=True, default="")
    storage_checksum_algorithm = models.CharField(max_length=32, blank=True, default="")
    storage_checksum_value = models.CharField(max_length=255, blank=True, default="")
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration_milliseconds = models.PositiveBigIntegerField(null=True, blank=True)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    row_count = models.PositiveBigIntegerField(null=True, blank=True)
    column_count = models.PositiveIntegerField(null=True, blank=True)
    technical_metadata = models.JSONField(default=dict, blank=True)
    pipeline_name = models.CharField(max_length=64, blank=True, default="")
    pipeline_version = models.CharField(max_length=32, blank=True, default="")
    expected_asset_lock_version = models.PositiveIntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="asset_versions_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(max_length=64, blank=True, default="")
    malware_signature = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["asset", "number"], name="assets_version_number_unique"
            ),
            models.CheckConstraint(
                condition=Q(number__gt=0), name="assets_version_number_positive"
            ),
            models.CheckConstraint(
                condition=Q(expected_asset_lock_version__gt=0),
                name="assets_version_expected_lock_positive",
            ),
            models.CheckConstraint(
                condition=Q(sha256="") | Q(sha256__regex=r"^[0-9a-f]{64}$"),
                name="assets_version_sha256_format",
            ),
            models.CheckConstraint(
                condition=Q(size_bytes__isnull=True) | Q(size_bytes__gt=0),
                name="assets_version_size_positive",
            ),
        ]
        indexes = [
            models.Index(
                fields=["asset", "status"], name="asset_version_asset_state_ix"
            ),
            models.Index(
                fields=["status", "created_at"], name="asset_version_state_created_ix"
            ),
            models.Index(fields=["sha256"], name="asset_version_sha_ix"),
        ]

    def __str__(self) -> str:
        return f"{self.asset_id}:v{self.number}"

    def clean(self) -> None:
        super().clean()
        if not isinstance(self.technical_metadata, dict):
            raise ValidationError(
                {"technical_metadata": "Los metadatos técnicos deben ser un objeto."}
            )


class AssetVariant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset_version = models.ForeignKey(
        AssetVersion, on_delete=models.PROTECT, related_name="variants"
    )
    role = models.CharField(max_length=32, choices=VariantRole.choices)
    pipeline_name = models.CharField(max_length=64)
    pipeline_version = models.CharField(max_length=32)
    mime_type = models.CharField(max_length=128)
    extension = models.CharField(max_length=16)
    storage_bucket = models.CharField(max_length=255)
    storage_key = models.CharField(max_length=1024)
    size_bytes = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration_milliseconds = models.PositiveBigIntegerField(null=True, blank=True)
    bitrate = models.PositiveIntegerField(null=True, blank=True)
    technical_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "asset_version",
                    "pipeline_name",
                    "pipeline_version",
                    "role",
                ],
                name="assets_variant_pipeline_role_unique",
            ),
            models.CheckConstraint(
                condition=Q(size_bytes__gt=0), name="assets_variant_size_positive"
            ),
            models.CheckConstraint(
                condition=Q(sha256__regex=r"^[0-9a-f]{64}$"),
                name="assets_variant_sha256_format",
            ),
        ]
        indexes = [
            models.Index(
                fields=["asset_version", "role"], name="asset_variant_version_role_ix"
            ),
            models.Index(fields=["sha256"], name="asset_variant_sha_ix"),
        ]

    def __str__(self) -> str:
        return f"{self.asset_version_id}:{self.role}:{self.pipeline_version}"


class AssetUploadSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="asset_upload_sessions"
    )
    asset = models.ForeignKey(
        Asset, on_delete=models.PROTECT, related_name="upload_sessions"
    )
    asset_version = models.ForeignKey(
        AssetVersion, on_delete=models.PROTECT, related_name="upload_sessions"
    )
    upload_method = models.CharField(max_length=16, choices=UploadMethod.choices)
    status = models.CharField(
        max_length=16, choices=UploadStatus.choices, default=UploadStatus.INITIATED
    )
    quarantine_bucket = models.CharField(max_length=255)
    quarantine_key = models.CharField(max_length=1024)
    declared_filename = models.CharField(max_length=255)
    declared_mime_type = models.CharField(max_length=128)
    expected_size_bytes = models.PositiveBigIntegerField()
    expected_sha256 = models.CharField(max_length=64, blank=True, default="")
    multipart_upload_id = models.TextField(blank=True, default="")
    part_size_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="asset_upload_sessions_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    aborted_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["asset_version"],
                condition=Q(
                    status__in=[
                        UploadStatus.INITIATED,
                        UploadStatus.UPLOADING,
                        UploadStatus.UPLOADED,
                    ]
                ),
                name="assets_one_active_upload_per_version",
            ),
            models.CheckConstraint(
                condition=Q(expected_size_bytes__gt=0),
                name="assets_upload_size_positive",
            ),
            models.CheckConstraint(
                condition=Q(expected_sha256="")
                | Q(expected_sha256__regex=r"^[0-9a-f]{64}$"),
                name="assets_upload_sha256_format",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "status"], name="asset_upload_org_state_ix"
            ),
            models.Index(
                fields=["created_by", "status"], name="asset_upload_user_state_ix"
            ),
            models.Index(fields=["expires_at"], name="asset_upload_expiry_ix"),
        ]

    def __str__(self) -> str:
        return f"{self.asset_id}:{self.status}:{self.id}"


class AssetUploadPart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    upload_session = models.ForeignKey(
        AssetUploadSession, on_delete=models.PROTECT, related_name="parts"
    )
    part_number = models.PositiveSmallIntegerField()
    etag = models.CharField(max_length=255)
    checksum_algorithm = models.CharField(max_length=32, blank=True, default="")
    checksum_value = models.CharField(max_length=255, blank=True, default="")
    size_bytes = models.PositiveBigIntegerField()
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["upload_session", "part_number"],
                name="assets_upload_part_number_unique",
            ),
            models.CheckConstraint(
                condition=Q(part_number__gte=1) & Q(part_number__lte=10_000),
                name="assets_upload_part_number_range",
            ),
            models.CheckConstraint(
                condition=Q(size_bytes__gt=0), name="assets_upload_part_size_positive"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.upload_session_id}:part-{self.part_number}"


class AssetProcessingJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset_version = models.ForeignKey(
        AssetVersion, on_delete=models.PROTECT, related_name="processing_jobs"
    )
    job_type = models.CharField(max_length=32, choices=ProcessingJobType.choices)
    status = models.CharField(
        max_length=32,
        choices=ProcessingJobStatus.choices,
        default=ProcessingJobStatus.QUEUED,
    )
    stage = models.CharField(
        max_length=32, choices=ProcessingStage.choices, default=ProcessingStage.QUEUED
    )
    task_id = models.CharField(max_length=255, blank=True, default="")
    attempt_count = models.PositiveIntegerField(default=0)
    pipeline_name = models.CharField(max_length=64)
    pipeline_version = models.CharField(max_length=32)
    last_error_code = models.CharField(max_length=64, blank=True, default="")
    claimed_at = models.DateTimeField(null=True, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["asset_version", "pipeline_name", "pipeline_version"],
                condition=Q(
                    status__in=[
                        ProcessingJobStatus.QUEUED,
                        ProcessingJobStatus.RUNNING,
                    ]
                ),
                name="assets_one_active_job_per_pipeline",
            )
        ]
        indexes = [
            models.Index(
                fields=["asset_version", "status"], name="asset_job_version_state_ix"
            ),
            models.Index(
                fields=["status", "created_at"], name="asset_job_state_created_ix"
            ),
            models.Index(fields=["task_id"], name="asset_job_task_ix"),
        ]

    def __str__(self) -> str:
        return f"{self.asset_version_id}:{self.pipeline_version}:{self.status}"


class AssetEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="asset_events"
    )
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="events")
    asset_version = models.ForeignKey(
        AssetVersion,
        on_delete=models.PROTECT,
        related_name="events",
        null=True,
        blank=True,
    )
    upload_session = models.ForeignKey(
        AssetUploadSession,
        on_delete=models.PROTECT,
        related_name="events",
        null=True,
        blank=True,
    )
    processing_job = models.ForeignKey(
        AssetProcessingJob,
        on_delete=models.PROTECT,
        related_name="events",
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=32, choices=AssetEventType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="asset_events",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["organization", "created_at"], name="asset_event_org_created_ix"
            ),
            models.Index(
                fields=["asset", "created_at"], name="asset_event_asset_created_ix"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.asset_id}:{self.event_type}:{self.created_at.isoformat()}"
