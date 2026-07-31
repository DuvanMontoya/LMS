from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from domain.assets.exceptions import AssetFormatInvalid
from domain.assets.limits import MAX_PDF_PAGES

from .common import ProcessingResult


def process_pdf(source: Path) -> ProcessingResult:
    try:
        with source.open("rb") as raw:
            if raw.read(5) != b"%PDF-":
                raise AssetFormatInvalid("Invalid PDF signature.")
            raw.seek(0)
            reader = PdfReader(raw, strict=True)
            if reader.is_encrypted:
                raise AssetFormatInvalid("Encrypted PDF files are not supported.")
            page_count = len(reader.pages)
            if page_count < 1 or page_count > MAX_PDF_PAGES:
                raise AssetFormatInvalid("PDF page count exceeds the limit.")
            metadata = reader.metadata
            technical = {
                "pdf_header": getattr(reader, "pdf_header", ""),
                "title": str(metadata.title or "")[:500] if metadata else "",
                "author": str(metadata.author or "")[:500] if metadata else "",
                "encrypted": False,
            }
    except AssetFormatInvalid:
        raise
    except (PdfReadError, OSError, ValueError, TypeError) as error:
        raise AssetFormatInvalid("Malformed PDF file.") from error
    return ProcessingResult(
        detected_mime_type="application/pdf",
        extension=".pdf",
        page_count=page_count,
        technical_metadata=technical,
    )
