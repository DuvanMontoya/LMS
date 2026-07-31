from __future__ import annotations

import base64
import re

from domain.assets.exceptions import AssetUploadInvalid
from domain.assets.limits import MAX_MULTIPART_PARTS


def validate_part_number(value: int) -> int:
    if value < 1 or value > MAX_MULTIPART_PARTS:
        raise AssetUploadInvalid("El número de parte está fuera del rango permitido.")
    return value


def validate_checksum_sha256(value: str) -> str:
    try:
        decoded = base64.b64decode(value, validate=True)
    except ValueError as error:
        raise AssetUploadInvalid("El checksum de la parte es inválido.") from error
    if len(decoded) != 32:
        raise AssetUploadInvalid("El checksum de la parte es inválido.")
    return value


def normalize_etag(value: str) -> str:
    normalized = value.strip().strip('"')
    if not re.fullmatch(r"[A-Za-z0-9+/=_-]{8,255}", normalized):
        raise AssetUploadInvalid("El ETag de la parte es inválido.")
    return normalized
