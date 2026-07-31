from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DeliveredObject:
    role: str
    url: str
    mime_type: str
    size_bytes: int
    width: int | None = None
    height: int | None = None
    duration_milliseconds: int | None = None


@dataclass(frozen=True)
class AssetAccessDescriptor:
    asset_version_id: str
    kind: str
    expires_at: datetime
    source: DeliveredObject | None
    variants: tuple[DeliveredObject, ...]
