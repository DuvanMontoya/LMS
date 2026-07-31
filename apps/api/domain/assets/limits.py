from dataclasses import dataclass

MIB = 1024 * 1024
GIB = 1024 * MIB

SINGLE_UPLOAD_MAX_BYTES = 64 * MIB
MULTIPART_PART_SIZE_BYTES = 16 * MIB
MAX_MULTIPART_PARTS = 10_000
UPLOAD_SESSION_TTL_SECONDS = 60 * 60
MAX_ACTIVE_UPLOADS_PER_USER_ORGANIZATION = 5
MAX_UPLOADS_PER_USER_HOUR = 20
MAX_FILENAME_LENGTH = 255
MAX_ASSET_NAME_LENGTH = 200
MAX_ASSET_DESCRIPTION_LENGTH = 2_000
MAX_JSON_DEPTH = 32
MAX_JSON_NODES = 1_000_000
MAX_CSV_COLUMNS = 500
MAX_CAPTION_CUES = 100_000


@dataclass(frozen=True)
class KindLimits:
    maximum_size_bytes: int
    declared_mime_types: frozenset[str]
    extensions: frozenset[str]


KIND_LIMITS = {
    "image": KindLimits(
        25 * MIB,
        frozenset({"image/jpeg", "image/png", "image/webp"}),
        frozenset({".jpg", ".jpeg", ".png", ".webp"}),
    ),
    "document": KindLimits(
        100 * MIB,
        frozenset({"application/pdf"}),
        frozenset({".pdf"}),
    ),
    "audio": KindLimits(
        500 * MIB,
        # Browsers disagree on the declared MIME for the same M4A container.
        # Keep the aliases at the upload boundary; ffprobe remains authoritative.
        frozenset(
            {
                "audio/mpeg",
                "audio/mp4",
                "audio/m4a",
                "audio/x-m4a",
                "audio/wav",
                "audio/ogg",
            }
        ),
        frozenset({".mp3", ".m4a", ".mp4", ".wav", ".ogg"}),
    ),
    "video": KindLimits(
        5 * GIB,
        frozenset({"video/mp4", "video/quicktime", "video/webm"}),
        frozenset({".mp4", ".mov", ".webm"}),
    ),
    "dataset": KindLimits(
        500 * MIB,
        frozenset({"text/csv", "application/json", "text/plain"}),
        frozenset({".csv", ".json", ".txt"}),
    ),
    "caption": KindLimits(
        5 * MIB,
        frozenset({"text/vtt"}),
        frozenset({".vtt"}),
    ),
}

MAX_IMAGE_PIXELS = 40_000_000
MAX_IMAGE_DIMENSION = 20_000
MAX_PDF_PAGES = 2_000
MAX_AUDIO_DURATION_MS = 12 * 60 * 60 * 1_000
MAX_VIDEO_DURATION_MS = 8 * 60 * 60 * 1_000
MAX_VIDEO_WIDTH = 4096
MAX_VIDEO_HEIGHT = 2160
