from __future__ import annotations

import warnings
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from domain.assets.exceptions import AssetFormatInvalid
from domain.assets.limits import MAX_IMAGE_DIMENSION, MAX_IMAGE_PIXELS

from .common import ProcessingResult, VariantArtifact

_FORMATS = {
    "JPEG": ("image/jpeg", ".jpg"),
    "PNG": ("image/png", ".png"),
    "WEBP": ("image/webp", ".webp"),
}
_SIZES = (
    ("image_thumbnail", 320),
    ("image_medium", 1280),
    ("image_large", 2560),
)


def process_image(source: Path, workdir: Path) -> ProcessingResult:
    previous_limit = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(source) as probe:
                if probe.format not in _FORMATS:
                    raise AssetFormatInvalid("Unsupported image format.")
                if (
                    getattr(probe, "is_animated", False)
                    or getattr(probe, "n_frames", 1) != 1
                ):
                    raise AssetFormatInvalid("Animated images are not supported.")
                if (
                    probe.width > MAX_IMAGE_DIMENSION
                    or probe.height > MAX_IMAGE_DIMENSION
                ):
                    raise AssetFormatInvalid("Image dimensions exceed the limit.")
                probe.verify()
            with Image.open(source) as opened:
                opened.load()
                image = ImageOps.exif_transpose(opened)
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise AssetFormatInvalid("Image pixel count exceeds the limit.")
                image = _safe_color_mode(image)
                artifacts: list[VariantArtifact] = []
                for role, maximum in _SIZES:
                    output = image.copy()
                    output.thumbnail((maximum, maximum), Image.Resampling.LANCZOS)
                    path = workdir / f"{role}.webp"
                    output.save(
                        path,
                        format="WEBP",
                        quality=82,
                        method=6,
                        exif=b"",
                        icc_profile=None,
                    )
                    artifacts.append(
                        VariantArtifact(
                            role=role,
                            path=path,
                            mime_type="image/webp",
                            extension=".webp",
                            width=output.width,
                            height=output.height,
                        )
                    )
                fallback = image.copy()
                has_alpha = "A" in fallback.getbands()
                fallback_extension = ".png" if has_alpha else ".jpg"
                fallback_mime = "image/png" if has_alpha else "image/jpeg"
                fallback_path = workdir / f"image_web_fallback{fallback_extension}"
                if has_alpha:
                    fallback.save(fallback_path, format="PNG", optimize=True)
                else:
                    fallback.convert("RGB").save(
                        fallback_path,
                        format="JPEG",
                        quality=88,
                        optimize=True,
                        progressive=True,
                        exif=b"",
                        icc_profile=None,
                    )
                artifacts.append(
                    VariantArtifact(
                        role="image_web_fallback",
                        path=fallback_path,
                        mime_type=fallback_mime,
                        extension=fallback_extension,
                        width=fallback.width,
                        height=fallback.height,
                    )
                )
                mime_type, extension = _FORMATS[opened.format or ""]
                return ProcessingResult(
                    detected_mime_type=mime_type,
                    extension=extension,
                    width=image.width,
                    height=image.height,
                    technical_metadata={
                        "source_format": opened.format,
                        "mode": image.mode,
                        "animated": False,
                        "metadata_stripped": True,
                        "exif_orientation_applied": True,
                    },
                    variants=tuple(artifacts),
                )
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as error:
        raise AssetFormatInvalid("Invalid or unsafe image.") from error
    finally:
        Image.MAX_IMAGE_PIXELS = previous_limit


def _safe_color_mode(image: Image.Image) -> Image.Image:
    if "A" in image.getbands():
        return image.convert("RGBA")
    return image.convert("RGB")
