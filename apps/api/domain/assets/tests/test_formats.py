from __future__ import annotations

import tempfile
from pathlib import Path
from zipfile import ZipFile

from django.test import SimpleTestCase
from PIL import Image
from pypdf import PdfWriter

from domain.assets.exceptions import AssetFormatInvalid
from domain.assets.processing.captions import process_caption
from domain.assets.processing.datasets import process_dataset
from domain.assets.processing.documents import process_document
from domain.assets.processing.images import process_image
from domain.assets.processing.pdf import process_pdf


class AssetFormatTests(SimpleTestCase):
    def test_png_pdf_vtt_csv_and_json_are_processed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "image.png"
            Image.new("RGBA", (64, 32), (10, 20, 30, 120)).save(image)
            image_result = process_image(image, root)
            self.assertEqual(image_result.detected_mime_type, "image/png")
            self.assertTrue(image_result.variants)

            pdf = root / "document.pdf"
            writer = PdfWriter()
            writer.add_blank_page(width=200, height=200)
            with pdf.open("wb") as target:
                writer.write(target)
            self.assertEqual(process_pdf(pdf).page_count, 1)

            caption = root / "captions.vtt"
            caption.write_text(
                "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nTexto seguro.\n",
                encoding="utf-8",
            )
            self.assertEqual(
                process_caption(caption, root).technical_metadata["cue_count"], 1
            )

            csv = root / "data.csv"
            csv.write_text("name,value\n'=SUM(A1:A2),2\n", encoding="utf-8")
            csv_result = process_dataset(csv, "text/csv")
            self.assertEqual(csv_result.row_count, 1)

            data = root / "data.json"
            data.write_text('{"safe": true}', encoding="utf-8")
            self.assertEqual(process_dataset(data, "application/json").row_count, 1)

            markdown = root / "guia.md"
            markdown.write_text(
                "# Guía\nContenido académico seguro.\n", encoding="utf-8"
            )
            self.assertEqual(
                process_document(
                    markdown,
                    declared_mime_type="text/markdown",
                    declared_extension=".md",
                ).technical_metadata["line_count"],
                3,
            )

            latex = root / "guia.tex"
            latex.write_text("\\section{Guía}\n", encoding="utf-8")
            self.assertEqual(
                process_document(
                    latex,
                    declared_mime_type="application/x-tex",
                    declared_extension=".tex",
                ).detected_mime_type,
                "application/x-tex",
            )

            presentation = root / "clase.pptx"
            with ZipFile(presentation, "w") as archive:
                archive.writestr("[Content_Types].xml", "<Types />")
                archive.writestr("ppt/presentation.xml", "<p:presentation />")
                archive.writestr("ppt/slides/slide1.xml", "<p:sld />")
            self.assertEqual(
                process_document(
                    presentation,
                    declared_mime_type=(
                        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    ),
                    declared_extension=".pptx",
                ).page_count,
                1,
            )

    def test_script_like_vtt_and_invalid_utf8_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            caption = root / "captions.vtt"
            caption.write_text(
                "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\n<script>\n",
                encoding="utf-8",
            )
            with self.assertRaises(AssetFormatInvalid):
                process_caption(caption, root)
            text = root / "bad.txt"
            text.write_bytes(b"\xff\xfe")
            with self.assertRaises(AssetFormatInvalid):
                process_dataset(text, "text/plain")
            markdown = root / "unsafe.md"
            markdown.write_bytes(b"\xff\x00")
            with self.assertRaises(AssetFormatInvalid):
                process_document(
                    markdown,
                    declared_mime_type="text/markdown",
                    declared_extension=".md",
                )
