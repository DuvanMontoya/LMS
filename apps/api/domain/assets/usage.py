from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

UsageProvider = Callable[[uuid.UUID], dict[str, Any]]

_providers: dict[str, UsageProvider] = {}


def register_asset_usage_provider(name: str, provider: UsageProvider) -> None:
    if not name.strip() or name in _providers:
        raise RuntimeError(f"Asset usage provider already registered: {name}")
    _providers[name] = provider


def collect_asset_usage(*, asset_id: uuid.UUID) -> dict[str, Any]:
    content_versions: list[dict[str, Any]] = []
    releases: list[dict[str, Any]] = []
    for provider in _providers.values():
        payload = provider(asset_id)
        content_versions.extend(payload.get("content_versions", []))
        releases.extend(payload.get("releases", []))
    return {
        "content_versions": content_versions,
        "releases": releases,
        "current_reference_count": len(content_versions),
    }
