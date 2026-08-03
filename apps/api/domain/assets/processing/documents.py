from __future__ import annotations

from pathlib import Path
from zipfile import BadZipFile, ZipFile

from domain.assets.exceptions import AssetFormatInvalid
from domain.assets.limits import (
    MAX_PRESENTATION_ARCHIVE_ENTRIES,
    MAX_PRESENTATION_COMPRESSION_RATIO,
    MAX_PRESENTATION_SLIDES,
    MAX_PRESENTATION_UNCOMPRESSED_BYTES,
    MAX_SOURCE_DOCUMENT_BYTES,
    MAX_SOURCE_DOCUMENT_LINES,
)

from .common import ProcessingResult
from .pdf import process_pdf

_MARKDOWN_MIME_TYPES = frozenset({"text/markdown", "text/plain", "text/x-markdown"})
_LATEX_MIME_TYPES = frozenset({"application/x-tex", "text/x-tex"})
_PPTX_MIME_TYPE = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
)


def process_document(
    source: Path, *, declared_mime_type: str, declared_extension: str
) -> ProcessingResult:
    if declared_mime_type == "application/pdf" and declared_extension == ".pdf":
        return process_pdf(source)
    if declared_mime_type in _MARKDOWN_MIME_TYPES and declared_extension == ".md":
        return _process_utf8_source(source, declared_mime_type, ".md")
    if declared_mime_type in _LATEX_MIME_TYPES and declared_extension == ".tex":
        return _process_utf8_source(source, declared_mime_type, ".tex")
    if declared_mime_type == _PPTX_MIME_TYPE and declared_extension == ".pptx":
        return _process_pptx(source)
    raise AssetFormatInvalid("Document MIME type and extension do not match.")


def _process_utf8_source(
    source: Path, mime_type: str, extension: str
) -> ProcessingResult:
    try:
        size = source.stat().st_size
        if size <= 0 or size > MAX_SOURCE_DOCUMENT_BYTES:
            raise AssetFormatInvalid("Source document exceeds its safety limit.")
        content = source.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise AssetFormatInvalid("Source documents must use UTF-8.") from error
    except OSError as error:
        raise AssetFormatInvalid("Source document cannot be read.") from error
    if "\x00" in content:
        raise AssetFormatInvalid("Source document contains a NUL byte.")
    line_count = content.count("\n") + (1 if content else 0)
    if line_count > MAX_SOURCE_DOCUMENT_LINES:
        raise AssetFormatInvalid("Source document has too many lines.")
    return ProcessingResult(
        detected_mime_type=mime_type,
        extension=extension,
        technical_metadata={
            "file_type": "utf8_source",
            "character_count": len(content),
            "line_count": line_count,
        },
    )


def _process_pptx(source: Path) -> ProcessingResult:
    try:
        with ZipFile(source) as archive:
            entries = archive.infolist()
            if not entries or len(entries) > MAX_PRESENTATION_ARCHIVE_ENTRIES:
                raise AssetFormatInvalid("Presentation archive entry limit exceeded.")
            total_uncompressed = 0
            slide_count = 0
            names: set[str] = set()
            for entry in entries:
                name = entry.filename.replace("\\", "/")
                if not name or name.startswith("/") or ".." in name.split("/"):
                    raise AssetFormatInvalid("Presentation archive has an unsafe path.")
                if entry.flag_bits & 0x1:
                    raise AssetFormatInvalid(
                        "Encrypted presentations are not supported."
                    )
                total_uncompressed += entry.file_size
                if total_uncompressed > MAX_PRESENTATION_UNCOMPRESSED_BYTES:
                    raise AssetFormatInvalid(
                        "Presentation archive expands beyond its limit."
                    )
                if (
                    entry.compress_size > 0
                    and entry.file_size / entry.compress_size
                    > MAX_PRESENTATION_COMPRESSION_RATIO
                ):
                    raise AssetFormatInvalid(
                        "Presentation archive compression ratio is unsafe."
                    )
                names.add(name)
                if name.startswith("ppt/slides/slide") and name.endswith(".xml"):
                    slide_count += 1
            if {"[Content_Types].xml", "ppt/presentation.xml"} - names:
                raise AssetFormatInvalid("Presentation is not a valid PPTX package.")
            if not 1 <= slide_count <= MAX_PRESENTATION_SLIDES:
                raise AssetFormatInvalid("Presentation slide count exceeds the limit.")
    except AssetFormatInvalid:
        raise
    except (BadZipFile, OSError) as error:
        raise AssetFormatInvalid("Malformed PPTX file.") from error
    return ProcessingResult(
        detected_mime_type=_PPTX_MIME_TYPE,
        extension=".pptx",
        page_count=slide_count,
        technical_metadata={
            "file_type": "pptx",
            "slide_count": slide_count,
            "archive_entries": len(entries),
        },
    )
