# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

from pathlib import Path

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings

from domain.assets.exceptions import AssetStorageError

from .gateway import (
    MultipartPart,
    ObjectHead,
    ObjectStorageGateway,
    PresignedPost,
)


class Boto3ObjectStorageGateway(ObjectStorageGateway):
    def __init__(self) -> None:
        self._internal = build_s3_client(settings.ASSET_S3_INTERNAL_ENDPOINT or None)
        self._public = build_s3_client(
            settings.ASSET_S3_PUBLIC_ENDPOINT
            or settings.ASSET_S3_INTERNAL_ENDPOINT
            or None
        )

    @staticmethod
    def _translate(error: Exception) -> AssetStorageError:
        return AssetStorageError("Object storage operation failed.")

    def generate_upload_post(
        self,
        *,
        bucket: str,
        key: str,
        size_bytes: int,
        expires_seconds: int,
        session_id: str,
    ) -> PresignedPost:
        fields = {
            "Content-Type": "application/octet-stream",
            "x-amz-meta-upload-session": session_id,
        }
        conditions: list[dict[str, str] | list[object]] = [
            {"Content-Type": "application/octet-stream"},
            {"x-amz-meta-upload-session": session_id},
            ["content-length-range", size_bytes, size_bytes],
        ]
        try:
            response = self._public.generate_presigned_post(
                Bucket=bucket,
                Key=key,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=expires_seconds,
            )
        except (BotoCoreError, ClientError) as error:
            raise self._translate(error) from error
        return PresignedPost(
            url=str(response["url"]),
            fields={
                str(name): str(value) for name, value in response["fields"].items()
            },
        )

    def create_multipart_upload(self, *, bucket: str, key: str, session_id: str) -> str:
        try:
            response = self._internal.create_multipart_upload(
                Bucket=bucket,
                Key=key,
                ContentType="application/octet-stream",
                Metadata={"upload-session": session_id},
                ChecksumAlgorithm="SHA256",
                ChecksumType="COMPOSITE",
                ServerSideEncryption=settings.ASSET_S3_SERVER_SIDE_ENCRYPTION,
            )
            return str(response["UploadId"])
        except (BotoCoreError, ClientError) as error:
            raise self._translate(error) from error

    def generate_part_upload_url(
        self,
        *,
        bucket: str,
        key: str,
        upload_id: str,
        part_number: int,
        checksum_sha256: str,
        expires_seconds: int,
    ) -> str:
        try:
            return str(
                self._public.generate_presigned_url(
                    "upload_part",
                    Params={
                        "Bucket": bucket,
                        "Key": key,
                        "UploadId": upload_id,
                        "PartNumber": part_number,
                        "ChecksumSHA256": checksum_sha256,
                    },
                    ExpiresIn=expires_seconds,
                    HttpMethod="PUT",
                )
            )
        except (BotoCoreError, ClientError) as error:
            raise self._translate(error) from error

    def complete_multipart_upload(
        self,
        *,
        bucket: str,
        key: str,
        upload_id: str,
        parts: list[MultipartPart],
    ) -> None:
        payload = {
            "Parts": [
                {
                    "ETag": part.etag,
                    "PartNumber": part.part_number,
                    "ChecksumSHA256": part.checksum_sha256,
                }
                for part in parts
            ]
        }
        try:
            self._internal.complete_multipart_upload(
                Bucket=bucket,
                Key=key,
                UploadId=upload_id,
                MultipartUpload=payload,
            )
        except (BotoCoreError, ClientError) as error:
            raise self._translate(error) from error

    def abort_multipart_upload(self, *, bucket: str, key: str, upload_id: str) -> None:
        try:
            self._internal.abort_multipart_upload(
                Bucket=bucket, Key=key, UploadId=upload_id
            )
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") == "NoSuchUpload":
                return
            raise self._translate(error) from error
        except BotoCoreError as error:
            raise self._translate(error) from error

    def head_object(self, *, bucket: str, key: str) -> ObjectHead:
        try:
            response = self._internal.head_object(
                Bucket=bucket, Key=key, ChecksumMode="ENABLED"
            )
        except (BotoCoreError, ClientError) as error:
            raise self._translate(error) from error
        checksum_fields = (
            ("SHA256", "ChecksumSHA256"),
            ("CRC64NVME", "ChecksumCRC64NVME"),
            ("CRC32C", "ChecksumCRC32C"),
            ("CRC32", "ChecksumCRC32"),
            ("SHA1", "ChecksumSHA1"),
        )
        algorithm = ""
        value = ""
        for candidate, field in checksum_fields:
            if response.get(field):
                algorithm = candidate
                value = str(response[field])
                break
        return ObjectHead(
            size_bytes=int(response["ContentLength"]),
            etag=str(response.get("ETag", "")).strip('"'),
            checksum_algorithm=algorithm,
            checksum_value=value,
            content_type=str(response.get("ContentType", "")),
            metadata={
                str(name): str(metadata_value)
                for name, metadata_value in response.get("Metadata", {}).items()
            },
            version_id=str(response.get("VersionId", "")),
        )

    def download_to_path(self, *, bucket: str, key: str, path: Path) -> None:
        try:
            with path.open("xb") as target:
                self._internal.download_fileobj(bucket, key, target)
        except (BotoCoreError, ClientError, OSError) as error:
            raise self._translate(error) from error

    def upload_path(
        self, *, bucket: str, key: str, path: Path, content_type: str
    ) -> ObjectHead:
        try:
            with path.open("rb") as source:
                self._internal.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=source,
                    ContentType=content_type,
                    ServerSideEncryption=settings.ASSET_S3_SERVER_SIDE_ENCRYPTION,
                    ChecksumAlgorithm="SHA256",
                )
        except (BotoCoreError, ClientError, OSError) as error:
            raise self._translate(error) from error
        return self.head_object(bucket=bucket, key=key)

    def copy_object(
        self,
        *,
        source_bucket: str,
        source_key: str,
        destination_bucket: str,
        destination_key: str,
        content_type: str,
    ) -> ObjectHead:
        try:
            self._internal.copy_object(
                Bucket=destination_bucket,
                Key=destination_key,
                CopySource={"Bucket": source_bucket, "Key": source_key},
                ContentType=content_type,
                MetadataDirective="REPLACE",
                ServerSideEncryption=settings.ASSET_S3_SERVER_SIDE_ENCRYPTION,
                ChecksumAlgorithm="SHA256",
            )
        except (BotoCoreError, ClientError) as error:
            raise self._translate(error) from error
        return self.head_object(bucket=destination_bucket, key=destination_key)

    def delete_object(self, *, bucket: str, key: str) -> None:
        try:
            self._internal.delete_object(Bucket=bucket, Key=key)
        except (BotoCoreError, ClientError) as error:
            raise self._translate(error) from error

    def generate_download_url(
        self,
        *,
        bucket: str,
        key: str,
        expires_seconds: int,
        content_type: str,
        content_disposition: str,
    ) -> str:
        try:
            return str(
                self._public.generate_presigned_url(
                    "get_object",
                    Params={
                        "Bucket": bucket,
                        "Key": key,
                        "ResponseContentType": content_type,
                        "ResponseContentDisposition": content_disposition,
                    },
                    ExpiresIn=expires_seconds,
                    HttpMethod="GET",
                )
            )
        except (BotoCoreError, ClientError) as error:
            raise self._translate(error) from error


def storage_gateway() -> ObjectStorageGateway:
    return Boto3ObjectStorageGateway()


def build_s3_client(endpoint_url: str | None) -> BaseClient:
    credentials: dict[str, str] = {}
    if settings.ASSET_S3_ACCESS_KEY_ID:
        credentials["aws_access_key_id"] = settings.ASSET_S3_ACCESS_KEY_ID
        credentials["aws_secret_access_key"] = settings.ASSET_S3_SECRET_ACCESS_KEY
    style = "path" if settings.ASSET_S3_FORCE_PATH_STYLE else "virtual"
    return boto3.client(
        "s3",
        region_name=settings.ASSET_S3_REGION,
        endpoint_url=endpoint_url,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": style},
            retries={"mode": "standard", "max_attempts": 3},
            connect_timeout=5,
            read_timeout=30,
        ),
        **credentials,
    )
