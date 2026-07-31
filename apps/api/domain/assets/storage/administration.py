# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

import uuid
from dataclasses import dataclass
from urllib.parse import urlparse

from botocore.client import BaseClient
from botocore.exceptions import ClientError
from django.conf import settings

from domain.assets.exceptions import AssetStorageError

from .boto3_gateway import build_s3_client


@dataclass(frozen=True)
class BucketState:
    name: str
    versioning: str
    encryption: str
    blocked_public: bool
    lifecycle_rules: int


def validate_storage_configuration() -> None:
    if settings.ASSET_QUARANTINE_BUCKET == settings.ASSET_PRIVATE_BUCKET:
        raise AssetStorageError("Quarantine and private buckets must differ.")
    for bucket in (
        settings.ASSET_QUARANTINE_BUCKET,
        settings.ASSET_PRIVATE_BUCKET,
    ):
        if len(bucket) < 3 or len(bucket) > 63:
            raise AssetStorageError("Invalid S3 bucket name.")
    if bool(settings.ASSET_S3_ACCESS_KEY_ID) != bool(
        settings.ASSET_S3_SECRET_ACCESS_KEY
    ):
        raise AssetStorageError("Explicit S3 credentials must be a complete pair.")
    if settings.ASSET_S3_PUBLIC_ENDPOINT:
        parsed = urlparse(settings.ASSET_S3_PUBLIC_ENDPOINT)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise AssetStorageError("Invalid public S3 endpoint.")


def initialize_storage() -> tuple[BucketState, BucketState]:
    validate_storage_configuration()
    client = build_s3_client(settings.ASSET_S3_INTERNAL_ENDPOINT or None)
    for bucket in (
        settings.ASSET_QUARANTINE_BUCKET,
        settings.ASSET_PRIVATE_BUCKET,
    ):
        _ensure_bucket(client, bucket)
        client.put_public_access_block(
            Bucket=bucket,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )
        client.put_bucket_encryption(
            Bucket=bucket,
            ServerSideEncryptionConfiguration={
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {
                            "SSEAlgorithm": settings.ASSET_S3_SERVER_SIDE_ENCRYPTION
                        },
                        "BucketKeyEnabled": False,
                    }
                ]
            },
        )
    client.put_bucket_versioning(
        Bucket=settings.ASSET_PRIVATE_BUCKET,
        VersioningConfiguration={"Status": "Enabled"},
    )
    client.put_bucket_cors(
        Bucket=settings.ASSET_QUARANTINE_BUCKET,
        CORSConfiguration={
            "CORSRules": [
                {
                    "AllowedHeaders": [
                        "content-type",
                        "x-amz-checksum-sha256",
                        "x-amz-meta-upload-session",
                    ],
                    "AllowedMethods": ["POST", "PUT"],
                    "AllowedOrigins": list(settings.ASSET_S3_ALLOWED_ORIGINS),
                    "ExposeHeaders": ["ETag", "x-amz-checksum-sha256"],
                    "MaxAgeSeconds": 300,
                }
            ]
        },
    )
    client.put_bucket_cors(
        Bucket=settings.ASSET_PRIVATE_BUCKET,
        CORSConfiguration={
            "CORSRules": [
                {
                    "AllowedHeaders": ["range"],
                    "AllowedMethods": ["GET", "HEAD"],
                    "AllowedOrigins": list(settings.ASSET_S3_ALLOWED_ORIGINS),
                    "ExposeHeaders": [
                        "Accept-Ranges",
                        "Content-Length",
                        "Content-Range",
                        "ETag",
                    ],
                    "MaxAgeSeconds": 300,
                }
            ]
        },
    )
    client.put_bucket_lifecycle_configuration(
        Bucket=settings.ASSET_QUARANTINE_BUCKET,
        LifecycleConfiguration={
            "Rules": [
                {
                    "ID": "expire-quarantine",
                    "Status": "Enabled",
                    "Filter": {"Prefix": "uploads/"},
                    "Expiration": {"Days": 1},
                    "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1},
                }
            ]
        },
    )
    client.put_bucket_lifecycle_configuration(
        Bucket=settings.ASSET_PRIVATE_BUCKET,
        LifecycleConfiguration={
            "Rules": [
                {
                    "ID": "abort-incomplete-private-multipart",
                    "Status": "Enabled",
                    "Filter": {"Prefix": "organizations/"},
                    "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1},
                }
            ]
        },
    )
    return storage_status()


def storage_status() -> tuple[BucketState, BucketState]:
    validate_storage_configuration()
    client = build_s3_client(settings.ASSET_S3_INTERNAL_ENDPOINT or None)
    return (
        _bucket_state(client, settings.ASSET_QUARANTINE_BUCKET),
        _bucket_state(client, settings.ASSET_PRIVATE_BUCKET),
    )


def storage_smoke() -> dict[str, object]:
    client = build_s3_client(settings.ASSET_S3_INTERNAL_ENDPOINT or None)
    key = f"smoke/{uuid.uuid4()}"
    body = b"lms-assets-storage-smoke"
    try:
        client.put_object(
            Bucket=settings.ASSET_QUARANTINE_BUCKET,
            Key=key,
            Body=body,
            ContentType="application/octet-stream",
            ServerSideEncryption=settings.ASSET_S3_SERVER_SIDE_ENCRYPTION,
            ChecksumAlgorithm="SHA256",
        )
        head = client.head_object(
            Bucket=settings.ASSET_QUARANTINE_BUCKET,
            Key=key,
            ChecksumMode="ENABLED",
        )
        signed = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.ASSET_QUARANTINE_BUCKET, "Key": key},
            ExpiresIn=60,
        )
        return {
            "size": int(head["ContentLength"]),
            "checksum_present": bool(head.get("ChecksumSHA256")),
            "signed_url_generated": bool(signed),
        }
    finally:
        client.delete_object(Bucket=settings.ASSET_QUARANTINE_BUCKET, Key=key)


def reset_local_storage() -> None:
    parsed = urlparse(settings.ASSET_S3_INTERNAL_ENDPOINT)
    if parsed.hostname not in {"127.0.0.1", "localhost", "localstack"}:
        raise AssetStorageError("ResetLocal is restricted to LocalStack.")
    client = build_s3_client(settings.ASSET_S3_INTERNAL_ENDPOINT)
    for bucket in (
        settings.ASSET_QUARANTINE_BUCKET,
        settings.ASSET_PRIVATE_BUCKET,
    ):
        _abort_all_multipart(client, bucket)
        _delete_all_objects(client, bucket)


def _ensure_bucket(client: BaseClient, bucket: str) -> None:
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") not in {
            "404",
            "NoSuchBucket",
            "NotFound",
        }:
            raise
        kwargs: dict[str, object] = {"Bucket": bucket}
        if settings.ASSET_S3_REGION != "us-east-1":
            kwargs["CreateBucketConfiguration"] = {
                "LocationConstraint": settings.ASSET_S3_REGION
            }
        client.create_bucket(**kwargs)


def _bucket_state(client: BaseClient, bucket: str) -> BucketState:
    client.head_bucket(Bucket=bucket)
    versioning = str(client.get_bucket_versioning(Bucket=bucket).get("Status", ""))
    encryption_response = client.get_bucket_encryption(Bucket=bucket)
    encryption = str(
        encryption_response["ServerSideEncryptionConfiguration"]["Rules"][0][
            "ApplyServerSideEncryptionByDefault"
        ]["SSEAlgorithm"]
    )
    block = client.get_public_access_block(Bucket=bucket)[
        "PublicAccessBlockConfiguration"
    ]
    lifecycle = client.get_bucket_lifecycle_configuration(Bucket=bucket)
    return BucketState(
        name=bucket,
        versioning=versioning,
        encryption=encryption,
        blocked_public=all(bool(value) for value in block.values()),
        lifecycle_rules=len(lifecycle.get("Rules", [])),
    )


def _abort_all_multipart(client: BaseClient, bucket: str) -> None:
    paginator = client.get_paginator("list_multipart_uploads")
    for page in paginator.paginate(Bucket=bucket):
        for upload in page.get("Uploads", []):
            client.abort_multipart_upload(
                Bucket=bucket, Key=upload["Key"], UploadId=upload["UploadId"]
            )


def _delete_all_objects(client: BaseClient, bucket: str) -> None:
    paginator = client.get_paginator("list_object_versions")
    for page in paginator.paginate(Bucket=bucket):
        objects = [
            {"Key": item["Key"], "VersionId": item["VersionId"]}
            for field in ("Versions", "DeleteMarkers")
            for item in page.get(field, [])
        ]
        for start in range(0, len(objects), 1_000):
            client.delete_objects(
                Bucket=bucket,
                Delete={"Objects": objects[start : start + 1_000], "Quiet": True},
            )
