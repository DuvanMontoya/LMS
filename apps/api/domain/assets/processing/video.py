# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

from fractions import Fraction
from pathlib import Path

from domain.assets.exceptions import AssetFormatInvalid
from domain.assets.limits import (
    MAX_VIDEO_DURATION_MS,
    MAX_VIDEO_HEIGHT,
    MAX_VIDEO_WIDTH,
)

from .common import (
    ProcessingResult,
    VariantArtifact,
    duration_ms,
    ffprobe_json,
    run_process,
)

_VIDEO_CONTAINERS = {
    "mov,mp4,m4a,3gp,3g2,mj2": ("video/mp4", ".mp4"),
    "matroska,webm": ("video/webm", ".webm"),
}


def process_video(
    source: Path, workdir: Path, *, ffmpeg_path: str, ffprobe_path: str
) -> ProcessingResult:
    payload = ffprobe_json(source, ffprobe_path=ffprobe_path)
    streams = payload.get("streams")
    if not isinstance(streams, list):
        raise AssetFormatInvalid("Video streams are invalid.")
    video_streams = [
        stream
        for stream in streams
        if isinstance(stream, dict) and stream.get("codec_type") == "video"
    ]
    if not video_streams:
        raise AssetFormatInvalid("The file does not contain video.")
    if any(
        isinstance(stream, dict) and stream.get("codec_type") in {"attachment", "data"}
        for stream in streams
    ):
        raise AssetFormatInvalid("Video contains unsupported streams.")
    primary = video_streams[0]
    width = int(primary.get("width") or 0)
    height = int(primary.get("height") or 0)
    if width < 1 or height < 1 or width > MAX_VIDEO_WIDTH or height > MAX_VIDEO_HEIGHT:
        raise AssetFormatInvalid("Video resolution exceeds the limit.")
    try:
        frame_rate = float(Fraction(str(primary.get("avg_frame_rate", "0/1"))))
    except (ValueError, ZeroDivisionError) as error:
        raise AssetFormatInvalid("Video frame rate is invalid.") from error
    if frame_rate <= 0 or frame_rate > 240:
        raise AssetFormatInvalid("Video frame rate is invalid.")
    duration = duration_ms(payload)
    if duration > MAX_VIDEO_DURATION_MS:
        raise AssetFormatInvalid("Video duration exceeds the limit.")
    format_payload = payload.get("format")
    format_name = (
        str(format_payload.get("format_name", ""))
        if isinstance(format_payload, dict)
        else ""
    )
    source_contract = next(
        (
            contract
            for name, contract in _VIDEO_CONTAINERS.items()
            if any(part in name.split(",") for part in format_name.split(","))
        ),
        None,
    )
    if source_contract is None:
        raise AssetFormatInvalid("Unsupported video container.")
    playback = workdir / "video_playback.mp4"
    scale = (
        "scale=w='min(1920,iw)':h='min(1080,ih)':force_original_aspect_ratio=decrease"
    )
    audio_stream = any(
        isinstance(stream, dict) and stream.get("codec_type") == "audio"
        for stream in streams
    )
    arguments = [
        ffmpeg_path,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-map",
        "0:v:0",
    ]
    if audio_stream:
        arguments.extend(["-map", "0:a:0?"])
    arguments.extend(
        [
            "-map_metadata",
            "-1",
            "-vf",
            scale,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
        ]
    )
    if audio_stream:
        arguments.extend(["-c:a", "aac", "-b:a", "160k"])
    else:
        arguments.append("-an")
    arguments.extend(["-y", str(playback)])
    run_process(arguments, timeout_seconds=8 * 60 * 60)
    poster = workdir / "video_poster.jpg"
    seek_seconds = min(max(duration / 1000 * 0.1, 0.0), max(duration / 1000 - 0.1, 0.0))
    run_process(
        [
            ffmpeg_path,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{seek_seconds:.3f}",
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-vf",
            "scale=w='min(1280,iw)':h=-2",
            "-map_metadata",
            "-1",
            "-c:v",
            "mjpeg",
            "-q:v",
            "3",
            "-y",
            str(poster),
        ],
        timeout_seconds=10 * 60,
    )
    output_width = min(width, 1920)
    output_height = round(height * output_width / width)
    if output_height > 1080:
        output_height = 1080
        output_width = round(width * output_height / height)
    return ProcessingResult(
        detected_mime_type=source_contract[0],
        extension=source_contract[1],
        width=width,
        height=height,
        duration_milliseconds=duration,
        technical_metadata={
            "container": format_name,
            "source_codec": str(primary.get("codec_name", "")),
            "frame_rate": frame_rate,
            "has_audio": audio_stream,
        },
        variants=(
            VariantArtifact(
                role="video_playback",
                path=playback,
                mime_type="video/mp4",
                extension=".mp4",
                width=output_width,
                height=output_height,
                duration_milliseconds=duration,
                technical_metadata={"video_codec": "h264", "audio_codec": "aac"},
            ),
            VariantArtifact(
                role="video_poster",
                path=poster,
                mime_type="image/jpeg",
                extension=".jpg",
                width=min(width, 1280),
                height=round(height * min(width, 1280) / width),
            ),
        ),
    )
