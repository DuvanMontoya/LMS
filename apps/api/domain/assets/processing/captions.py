from __future__ import annotations

import re
from pathlib import Path

from domain.assets.exceptions import AssetFormatInvalid
from domain.assets.limits import MAX_CAPTION_CUES

from .common import ProcessingResult, VariantArtifact

_TIMING = re.compile(
    r"^(?P<start>(?:\d{2}:)?\d{2}:\d{2}\.\d{3}) --> "
    r"(?P<end>(?:\d{2}:)?\d{2}:\d{2}\.\d{3})(?: [^\r\n]+)?$"
)


def _milliseconds(value: str) -> int:
    parts = value.split(":")
    if len(parts) == 2:
        hours = 0
        minutes, seconds = parts
    elif len(parts) == 3:
        hours, minutes, seconds = parts
    else:
        raise AssetFormatInvalid("Invalid WebVTT timestamp.")
    second, millisecond = seconds.split(".")
    return (
        int(hours) * 3_600_000
        + int(minutes) * 60_000
        + int(second) * 1_000
        + int(millisecond)
    )


def process_caption(source: Path, workdir: Path) -> ProcessingResult:
    try:
        text = source.read_text(encoding="utf-8-sig")
    except (UnicodeDecodeError, OSError) as error:
        raise AssetFormatInvalid("Captions must be UTF-8.") from error
    if "\x00" in text:
        raise AssetFormatInvalid("Captions contain a null byte.")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not lines or lines[0].strip() != "WEBVTT":
        raise AssetFormatInvalid("Missing WEBVTT header.")
    cues = 0
    previous_start = -1
    normalized: list[str] = ["WEBVTT", ""]
    index = 1
    while index < len(lines):
        line = lines[index].strip()
        index += 1
        if not line:
            continue
        timing = _TIMING.fullmatch(line)
        if timing is None and index < len(lines):
            timing = _TIMING.fullmatch(lines[index].strip())
            if timing is not None:
                normalized.append(line)
                index += 1
        if timing is None:
            raise AssetFormatInvalid("Invalid WebVTT cue.")
        start = _milliseconds(timing.group("start"))
        end = _milliseconds(timing.group("end"))
        if start < previous_start or end <= start:
            raise AssetFormatInvalid("WebVTT cues are out of order.")
        previous_start = start
        cues += 1
        if cues > MAX_CAPTION_CUES:
            raise AssetFormatInvalid("Too many WebVTT cues.")
        normalized.append(f"{timing.group('start')} --> {timing.group('end')}")
        payload_lines = 0
        while index < len(lines) and lines[index].strip():
            payload = lines[index].strip()
            if "<" in payload or ">" in payload:
                raise AssetFormatInvalid("Captions contain unsafe markup.")
            normalized.append(payload)
            index += 1
            payload_lines += 1
        if payload_lines == 0:
            raise AssetFormatInvalid("Empty WebVTT cue.")
        normalized.append("")
    if cues == 0:
        raise AssetFormatInvalid("Captions must contain at least one cue.")
    output = workdir / "caption_normalized.vtt"
    output.write_text(
        "\n".join(normalized).rstrip() + "\n", encoding="utf-8", newline="\n"
    )
    return ProcessingResult(
        detected_mime_type="text/vtt",
        extension=".vtt",
        technical_metadata={"cue_count": cues, "encoding": "utf-8"},
        variants=(
            VariantArtifact(
                role="caption_normalized",
                path=output,
                mime_type="text/vtt",
                extension=".vtt",
                technical_metadata={"cue_count": cues},
            ),
        ),
    )
