# pyright: reportArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnnecessaryIsInstance=false
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from domain.assets.exceptions import AssetProcessingError

STREAM_CHUNK_SIZE = 1024 * 1024
MAX_PROCESS_OUTPUT_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class VariantArtifact:
    role: str
    path: Path
    mime_type: str
    extension: str
    width: int | None = None
    height: int | None = None
    duration_milliseconds: int | None = None
    bitrate: int | None = None
    technical_metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class ProcessingResult:
    detected_mime_type: str
    extension: str
    technical_metadata: dict[str, Any]
    variants: tuple[VariantArtifact, ...] = ()
    width: int | None = None
    height: int | None = None
    duration_milliseconds: int | None = None
    page_count: int | None = None
    row_count: int | None = None
    column_count: int | None = None


def calculate_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(STREAM_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def run_process(
    arguments: list[str], *, timeout_seconds: int
) -> subprocess.CompletedProcess[bytes]:
    if not arguments or any(not isinstance(argument, str) for argument in arguments):
        raise AssetProcessingError("Invalid media command.")
    try:
        result = subprocess.run(
            arguments,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
            shell=False,
            env={
                "PATH": os.environ.get("PATH", ""),
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
            },
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AssetProcessingError("Media processor did not complete.") from error
    if (
        len(result.stdout) > MAX_PROCESS_OUTPUT_BYTES
        or len(result.stderr) > MAX_PROCESS_OUTPUT_BYTES
    ):
        raise AssetProcessingError("Media processor output exceeded its limit.")
    if result.returncode != 0:
        raise AssetProcessingError("Media processor rejected the file.")
    return result


def ffprobe_json(path: Path, *, ffprobe_path: str) -> dict[str, Any]:
    result = run_process(
        [
            ffprobe_path,
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(path),
        ],
        timeout_seconds=60,
    )
    try:
        payload = json.loads(result.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AssetProcessingError("ffprobe returned invalid metadata.") from error
    if not isinstance(payload, dict):
        raise AssetProcessingError("ffprobe returned invalid metadata.")
    return payload


def duration_ms(payload: dict[str, Any]) -> int:
    format_payload = payload.get("format")
    raw = format_payload.get("duration") if isinstance(format_payload, dict) else None
    try:
        milliseconds = round(float(raw) * 1000)
    except (TypeError, ValueError, OverflowError) as error:
        raise AssetProcessingError("Media duration is invalid.") from error
    if milliseconds <= 0:
        raise AssetProcessingError("Media duration is invalid.")
    return milliseconds
