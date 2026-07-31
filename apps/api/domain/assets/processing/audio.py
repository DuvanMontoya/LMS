# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

from pathlib import Path

from domain.assets.exceptions import AssetFormatInvalid
from domain.assets.limits import MAX_AUDIO_DURATION_MS

from .common import (
    ProcessingResult,
    VariantArtifact,
    duration_ms,
    ffprobe_json,
    run_process,
)

_AUDIO_CONTAINERS = {
    "mp3": ("audio/mpeg", ".mp3"),
    "mov,mp4,m4a,3gp,3g2,mj2": ("audio/mp4", ".m4a"),
    "wav": ("audio/wav", ".wav"),
    "ogg": ("audio/ogg", ".ogg"),
}


def process_audio(
    source: Path, workdir: Path, *, ffmpeg_path: str, ffprobe_path: str
) -> ProcessingResult:
    payload = ffprobe_json(source, ffprobe_path=ffprobe_path)
    streams = payload.get("streams")
    if not isinstance(streams, list):
        raise AssetFormatInvalid("Audio streams are invalid.")
    audio_streams = [
        stream
        for stream in streams
        if isinstance(stream, dict) and stream.get("codec_type") == "audio"
    ]
    if not audio_streams or any(
        isinstance(stream, dict) and stream.get("codec_type") == "video"
        for stream in streams
    ):
        raise AssetFormatInvalid("The file is not an audio-only asset.")
    format_payload = payload.get("format")
    format_name = (
        str(format_payload.get("format_name", ""))
        if isinstance(format_payload, dict)
        else ""
    )
    source_contract = next(
        (
            contract
            for name, contract in _AUDIO_CONTAINERS.items()
            if name in format_name.split(",") or format_name == name
        ),
        None,
    )
    if source_contract is None:
        raise AssetFormatInvalid("Unsupported audio container.")
    duration = duration_ms(payload)
    if duration > MAX_AUDIO_DURATION_MS:
        raise AssetFormatInvalid("Audio duration exceeds the limit.")
    primary = audio_streams[0]
    channels = int(primary.get("channels") or 0)
    sample_rate = int(primary.get("sample_rate") or 0)
    if channels < 1 or channels > 8 or sample_rate < 8_000 or sample_rate > 192_000:
        raise AssetFormatInvalid("Audio channel or sample-rate metadata is invalid.")
    output = workdir / "audio_playback.m4a"
    run_process(
        [
            ffmpeg_path,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-map",
            "0:a:0",
            "-vn",
            "-map_metadata",
            "-1",
            "-c:a",
            "aac",
            "-profile:a",
            "aac_low",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            "-y",
            str(output),
        ],
        timeout_seconds=60 * 60,
    )
    return ProcessingResult(
        detected_mime_type=source_contract[0],
        extension=source_contract[1],
        duration_milliseconds=duration,
        technical_metadata={
            "container": format_name,
            "source_codec": str(primary.get("codec_name", "")),
            "channels": channels,
            "sample_rate": sample_rate,
        },
        variants=(
            VariantArtifact(
                role="audio_playback",
                path=output,
                mime_type="audio/mp4",
                extension=".m4a",
                duration_milliseconds=duration,
                bitrate=160_000,
                technical_metadata={"codec": "aac", "profile": "aac_low"},
            ),
        ),
    )
