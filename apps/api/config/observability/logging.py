# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
from __future__ import annotations

import logging
import os
import re
import sys
from collections.abc import Mapping, MutableMapping
from io import TextIOBase
from pathlib import Path
from typing import Any, TextIO, cast
from urllib.parse import urlsplit, urlunsplit

import structlog

from .context import current_context

REDACTED = "[REDACTED]"
SENSITIVE_KEYS = frozenset(
    {
        "password",
        "token",
        "secret",
        "authorization",
        "cookie",
        "set-cookie",
        "csrf",
        "code",
        "email",
        "grading_payload",
        "payload",
        "expected_mathjson",
        "response",
        "content",
        "snapshot",
        "storage_key",
        "body",
        "query",
        "q",
    }
)
_EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")


def _safe_string(value: str) -> str:
    value = _EMAIL_RE.sub(REDACTED, value)
    if "X-Amz-" in value or "x-amz-" in value:
        parsed = urlsplit(value)
        if parsed.scheme and parsed.netloc:
            return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
        return REDACTED
    return value


def redact(value: Any, *, key: str = "") -> Any:
    normalized = key.lower().replace("-", "_")
    if normalized in {item.replace("-", "_") for item in SENSITIVE_KEYS}:
        return REDACTED
    if isinstance(value, Mapping):
        return {
            str(child): redact(item, key=str(child)) for child, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return _safe_string(value)
    return value


def add_context(
    _logger: object, _method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    event_dict.update(current_context())
    return event_dict


def redact_event(
    _logger: object, _method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    return redact(event_dict)


def configure_structured_logging(*, environment: str) -> None:
    processors = [
        structlog.contextvars.merge_contextvars,
        add_context,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
        redact_event,
        structlog.processors.JSONRenderer(sort_keys=True),
    ]
    log_path = os.environ.get("STRUCTURED_LOG_PATH", "").strip()
    if log_path:
        logger_factory = structlog.PrintLoggerFactory(
            file=cast(TextIO, _TeeWriter(Path(log_path)))
        )
    else:
        logger_factory = structlog.PrintLoggerFactory()
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=logger_factory,
        cache_logger_on_first_use=True,
    )


class _TeeWriter(TextIOBase):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, value: str) -> int:
        sys.stdout.write(value)
        with self.path.open("a", encoding="utf-8", newline="") as output:
            output.write(value)
        return len(value)

    def writable(self) -> bool:
        return True

    def flush(self) -> None:
        sys.stdout.flush()
