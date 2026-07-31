from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model

from domain.assets.storage.gateway import (
    MultipartPart,
    ObjectHead,
    PresignedPost,
)
from domain.organizations.services import create_organization_with_owner


def owner_context(suffix: str = "assets"):
    owner = get_user_model().objects.create_user(
        email=f"owner-{suffix}@example.test",
        password="CorrectHorseBatteryStaple42!",
    )
    EmailAddress.objects.create(
        user=owner, email=owner.email, primary=True, verified=True
    )
    organization = create_organization_with_owner(
        actor=owner, name=f"Organization {suffix}", slug=f"organization-{suffix}"
    )
    return owner, organization


class FakeStorageGateway:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}
        self.metadata: dict[tuple[str, str], dict[str, str]] = {}
        self.multipart: dict[str, tuple[str, str]] = {}
        self.aborted: list[str] = []

    def generate_upload_post(
        self,
        *,
        bucket: str,
        key: str,
        size_bytes: int,
        expires_seconds: int,
        session_id: str,
    ) -> PresignedPost:
        del size_bytes, expires_seconds
        return PresignedPost(
            url="https://storage.example.test/upload",
            fields={
                "key": key,
                "x-amz-meta-upload-session": session_id,
                "bucket": bucket,
            },
        )

    def create_multipart_upload(self, *, bucket: str, key: str, session_id: str) -> str:
        upload_id = f"upload-{len(self.multipart) + 1}"
        self.multipart[upload_id] = (bucket, key)
        self.metadata[(bucket, key)] = {"upload-session": session_id}
        return upload_id

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
        del bucket, key, checksum_sha256, expires_seconds
        return f"https://storage.example.test/{upload_id}/{part_number}"

    def complete_multipart_upload(
        self,
        *,
        bucket: str,
        key: str,
        upload_id: str,
        parts: list[MultipartPart],
    ) -> None:
        del upload_id
        self.objects[(bucket, key)] = b"x" * sum(16 * 1024 * 1024 for _part in parts)

    def abort_multipart_upload(self, *, bucket: str, key: str, upload_id: str) -> None:
        del bucket, key
        self.aborted.append(upload_id)

    def head_object(self, *, bucket: str, key: str) -> ObjectHead:
        payload = self.objects[(bucket, key)]
        return ObjectHead(
            size_bytes=len(payload),
            etag=hashlib.md5(payload, usedforsecurity=False).hexdigest(),
            checksum_algorithm="SHA256",
            checksum_value=hashlib.sha256(payload).hexdigest(),
            content_type="application/octet-stream",
            metadata=self.metadata.get((bucket, key), {}),
            version_id="1",
        )

    def download_to_path(self, *, bucket: str, key: str, path: Path) -> None:
        path.write_bytes(self.objects[(bucket, key)])

    def upload_path(
        self, *, bucket: str, key: str, path: Path, content_type: str
    ) -> ObjectHead:
        del content_type
        self.objects[(bucket, key)] = path.read_bytes()
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
        del content_type
        self.objects[(destination_bucket, destination_key)] = self.objects[
            (source_bucket, source_key)
        ]
        return self.head_object(bucket=destination_bucket, key=destination_key)

    def delete_object(self, *, bucket: str, key: str) -> None:
        self.objects.pop((bucket, key), None)

    def generate_download_url(
        self,
        *,
        bucket: str,
        key: str,
        expires_seconds: int,
        content_type: str,
        content_disposition: str,
    ) -> str:
        del expires_seconds, content_type, content_disposition
        return f"https://storage.example.test/{bucket}/{key}?signature=test"


def celery_result():
    return SimpleNamespace(id="task-test")
