from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_bytes(content: object) -> bytes:
    return json.dumps(
        content,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def content_digest(content: object) -> str:
    return hashlib.sha256(canonical_json_bytes(content)).hexdigest()


def deep_json_copy(content: Any) -> Any:
    return json.loads(canonical_json_bytes(content).decode("utf-8"))
