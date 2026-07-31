from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ObjectHead:
    size_bytes: int
    etag: str
    checksum_algorithm: str
    checksum_value: str
    content_type: str
    metadata: dict[str, str]
    version_id: str


@dataclass(frozen=True)
class PresignedPost:
    url: str
    fields: dict[str, str]


@dataclass(frozen=True)
class MultipartPart:
    part_number: int
    etag: str
    checksum_sha256: str


class ObjectStorageGateway(Protocol):
    def generate_upload_post(
        self,
        *,
        bucket: str,
        key: str,
        size_bytes: int,
        expires_seconds: int,
        session_id: str,
    ) -> PresignedPost: ...

    def create_multipart_upload(
        self, *, bucket: str, key: str, session_id: str
    ) -> str: ...

    def generate_part_upload_url(
        self,
        *,
        bucket: str,
        key: str,
        upload_id: str,
        part_number: int,
        checksum_sha256: str,
        expires_seconds: int,
    ) -> str: ...

    def complete_multipart_upload(
        self,
        *,
        bucket: str,
        key: str,
        upload_id: str,
        parts: list[MultipartPart],
    ) -> None: ...

    def abort_multipart_upload(
        self, *, bucket: str, key: str, upload_id: str
    ) -> None: ...

    def head_object(self, *, bucket: str, key: str) -> ObjectHead: ...

    def download_to_path(self, *, bucket: str, key: str, path: Path) -> None: ...

    def upload_path(
        self, *, bucket: str, key: str, path: Path, content_type: str
    ) -> ObjectHead: ...

    def copy_object(
        self,
        *,
        source_bucket: str,
        source_key: str,
        destination_bucket: str,
        destination_key: str,
        content_type: str,
    ) -> ObjectHead: ...

    def delete_object(self, *, bucket: str, key: str) -> None: ...

    def generate_download_url(
        self,
        *,
        bucket: str,
        key: str,
        expires_seconds: int,
        content_type: str,
        content_disposition: str,
    ) -> str: ...
