# pyright: reportAssignmentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from rest_framework import serializers

from ..choices import (
    AssetKind,
    AssetStatus,
    AssetVersionStatus,
    ProcessingJobStatus,
    UploadMethod,
    UploadStatus,
    VariantRole,
)
from ..delivery.descriptors import AssetAccessDescriptor
from ..models import (
    Asset,
    AssetProcessingJob,
    AssetUploadPart,
    AssetUploadSession,
    AssetVariant,
    AssetVersion,
)


class AssetVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetVariant
        fields = (
            "id",
            "role",
            "pipeline_name",
            "pipeline_version",
            "mime_type",
            "extension",
            "size_bytes",
            "sha256",
            "width",
            "height",
            "duration_milliseconds",
            "bitrate",
            "technical_metadata",
            "created_at",
        )


class ProcessingJobSerializer(serializers.ModelSerializer):
    asset_version_id = serializers.UUIDField()

    class Meta:
        model = AssetProcessingJob
        fields = (
            "id",
            "asset_version_id",
            "job_type",
            "status",
            "stage",
            "attempt_count",
            "pipeline_name",
            "pipeline_version",
            "last_error_code",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
        )


class AssetVersionSerializer(serializers.ModelSerializer):
    variants = AssetVariantSerializer(many=True, read_only=True)
    processing_jobs = ProcessingJobSerializer(many=True, read_only=True)
    malware_signature = serializers.SerializerMethodField()

    class Meta:
        model = AssetVersion
        fields = (
            "id",
            "number",
            "status",
            "original_filename",
            "declared_mime_type",
            "detected_mime_type",
            "extension",
            "size_bytes",
            "sha256",
            "width",
            "height",
            "duration_milliseconds",
            "page_count",
            "row_count",
            "column_count",
            "technical_metadata",
            "pipeline_name",
            "pipeline_version",
            "created_at",
            "ready_at",
            "rejected_at",
            "failed_at",
            "failure_code",
            "malware_signature",
            "variants",
            "processing_jobs",
        )

    def get_malware_signature(self, obj: AssetVersion) -> str | None:
        return obj.malware_signature if self.context.get("show_security") else None

    def to_representation(self, instance: AssetVersion) -> dict[str, Any]:
        payload = super().to_representation(instance)
        if not self.context.get("show_security"):
            payload.pop("malware_signature", None)
        return payload


class AssetSummarySerializer(serializers.ModelSerializer):
    current_version = AssetVersionSerializer(read_only=True)

    class Meta:
        model = Asset
        fields = (
            "id",
            "kind",
            "name",
            "description",
            "status",
            "current_version",
            "lock_version",
            "created_at",
            "updated_at",
            "archived_at",
        )


class AssetDetailSerializer(AssetSummarySerializer):
    versions = AssetVersionSerializer(many=True, read_only=True)

    class Meta(AssetSummarySerializer.Meta):
        fields = AssetSummarySerializer.Meta.fields + ("versions",)


class AssetUpdateSerializer(serializers.Serializer):
    expected_lock_version = serializers.IntegerField(min_value=1)
    name = serializers.CharField(min_length=1, max_length=200, trim_whitespace=True)
    description = serializers.CharField(
        allow_blank=True, max_length=10_000, trim_whitespace=True
    )


class ExpectedLockSerializer(serializers.Serializer):
    expected_lock_version = serializers.IntegerField(min_value=1)


class UploadInitializeSerializer(serializers.Serializer):
    asset_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    kind = serializers.ChoiceField(choices=AssetKind.choices)
    name = serializers.CharField(min_length=1, max_length=200, trim_whitespace=True)
    description = serializers.CharField(
        required=False, default="", allow_blank=True, max_length=10_000
    )
    filename = serializers.CharField(min_length=1, max_length=255)
    declared_mime_type = serializers.CharField(min_length=1, max_length=128)
    size_bytes = serializers.IntegerField(min_value=1)
    expected_sha256 = serializers.RegexField(
        r"^[0-9a-fA-F]{64}$", required=False, default="", allow_blank=True
    )


class PresignedPostSerializer(serializers.Serializer):
    url = serializers.URLField()
    fields = serializers.DictField(child=serializers.CharField())


class UploadInstructionsSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    asset_id = serializers.UUIDField()
    asset_version_id = serializers.UUIDField()
    upload_method = serializers.ChoiceField(choices=UploadMethod.choices)
    expires_at = serializers.DateTimeField()
    post = PresignedPostSerializer(allow_null=True)
    part_size_bytes = serializers.IntegerField(min_value=1, allow_null=True)


class UploadPartSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetUploadPart
        fields = (
            "part_number",
            "etag",
            "checksum_algorithm",
            "checksum_value",
            "size_bytes",
            "recorded_at",
        )


class UploadSessionSerializer(serializers.ModelSerializer):
    session_id = serializers.UUIDField(source="id")
    asset_id = serializers.UUIDField()
    asset_version_id = serializers.UUIDField()
    parts = UploadPartSerializer(many=True, read_only=True)

    class Meta:
        model = AssetUploadSession
        fields = (
            "session_id",
            "asset_id",
            "asset_version_id",
            "upload_method",
            "status",
            "declared_filename",
            "declared_mime_type",
            "expected_size_bytes",
            "expected_sha256",
            "part_size_bytes",
            "expires_at",
            "created_at",
            "completed_at",
            "aborted_at",
            "failure_code",
            "parts",
        )


class SignPartSerializer(serializers.Serializer):
    checksum_sha256 = serializers.RegexField(r"^[0-9a-fA-F]{64}$")


class SignedPartSerializer(serializers.Serializer):
    part_number = serializers.IntegerField(min_value=1, max_value=10_000)
    url = serializers.URLField()


class RecordPartSerializer(SignPartSerializer):
    etag = serializers.CharField(min_length=1, max_length=255)
    size_bytes = serializers.IntegerField(min_value=1)


class DeliveredObjectSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=VariantRole.choices + [("original", "Original")]
    )
    url = serializers.URLField()
    mime_type = serializers.CharField()
    size_bytes = serializers.IntegerField(min_value=0)
    width = serializers.IntegerField(min_value=1, allow_null=True)
    height = serializers.IntegerField(min_value=1, allow_null=True)
    duration_milliseconds = serializers.IntegerField(min_value=0, allow_null=True)


class AssetAccessDescriptorSerializer(serializers.Serializer):
    asset_version_id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=AssetKind.choices)
    expires_at = serializers.DateTimeField()
    source = DeliveredObjectSerializer(allow_null=True)
    variants = DeliveredObjectSerializer(many=True)


class AssetUsageSerializer(serializers.Serializer):
    content_versions = serializers.ListField(child=serializers.JSONField())
    releases = serializers.ListField(child=serializers.JSONField())
    current_reference_count = serializers.IntegerField(min_value=0)


class AssetErrorSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()


def serialize_descriptor(descriptor: AssetAccessDescriptor) -> dict[str, Any]:
    return asdict(descriptor)


# Force schema enum discovery for the public state contracts.
PUBLIC_ENUMS = (
    AssetStatus,
    AssetVersionStatus,
    UploadStatus,
    ProcessingJobStatus,
)
