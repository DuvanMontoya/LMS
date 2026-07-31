from __future__ import annotations

import re
import unicodedata
import uuid
from pathlib import PurePath

from domain.assets.limits import MAX_FILENAME_LENGTH

_SAFE_EXTENSION = re.compile(r"^\.[a-z0-9]{1,15}$")


def normalize_filename(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    normalized = "".join(
        character
        for character in normalized
        if unicodedata.category(character) not in {"Cc", "Cf"}
    )
    normalized = normalized.replace("\\", "/")
    normalized = PurePath(normalized).name.strip().strip(".")
    if not normalized:
        normalized = "archivo"
    return normalized[:MAX_FILENAME_LENGTH]


def normalized_extension(filename: str) -> str:
    name = normalize_filename(filename)
    suffix = PurePath(name).suffix.lower()
    return suffix if _SAFE_EXTENSION.fullmatch(suffix) else ""


def quarantine_key(*, organization_id: uuid.UUID, upload_session_id: uuid.UUID) -> str:
    return f"uploads/{organization_id}/{upload_session_id}/{uuid.uuid4()}"


def private_original_key(
    *,
    organization_id: uuid.UUID,
    asset_id: uuid.UUID,
    asset_version_id: uuid.UUID,
    sha256: str,
    extension: str,
) -> str:
    _validate_sha256(sha256)
    extension = _validate_extension(extension)
    return (
        f"organizations/{organization_id}/assets/{asset_id}/versions/"
        f"{asset_version_id}/original/{sha256}{extension}"
    )


def private_variant_key(
    *,
    organization_id: uuid.UUID,
    asset_id: uuid.UUID,
    asset_version_id: uuid.UUID,
    pipeline_name: str,
    pipeline_version: str,
    role: str,
    sha256: str,
    extension: str,
) -> str:
    _validate_sha256(sha256)
    extension = _validate_extension(extension)
    safe_segments = (pipeline_name, pipeline_version, role)
    if any(
        not segment or not re.fullmatch(r"[a-zA-Z0-9_.-]+", segment) or ".." in segment
        for segment in safe_segments
    ):
        raise ValueError("Invalid generated storage-key segment.")
    return (
        f"organizations/{organization_id}/assets/{asset_id}/versions/"
        f"{asset_version_id}/variants/{pipeline_name}/{pipeline_version}/"
        f"{role}/{sha256}{extension}"
    )


def _validate_sha256(value: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("Invalid SHA-256.")


def _validate_extension(value: str) -> str:
    normalized = value.lower()
    if not _SAFE_EXTENSION.fullmatch(normalized):
        raise ValueError("Invalid generated extension.")
    return normalized
