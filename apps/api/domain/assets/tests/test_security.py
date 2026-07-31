from __future__ import annotations

from django.test import SimpleTestCase

from domain.assets.exceptions import AssetUploadInvalid
from domain.assets.storage.keys import normalize_filename, quarantine_key
from domain.assets.uploads.services import _validate_input


class AssetInputSecurityTests(SimpleTestCase):
    def test_filename_is_display_only_and_key_is_opaque(self) -> None:
        self.assertEqual(normalize_filename("../../lesson.png"), "lesson.png")
        key = quarantine_key(
            organization_id="00000000-0000-4000-8000-000000000001",
            upload_session_id="00000000-0000-4000-8000-000000000002",
        )
        self.assertNotIn("lesson", key)
        self.assertTrue(key.startswith("uploads/"))

    def test_active_content_and_archive_formats_are_rejected(self) -> None:
        for kind, filename, mime_type in (
            ("image", "attack.svg", "image/svg+xml"),
            ("document", "attack.html", "text/html"),
            ("dataset", "archive.zip", "application/zip"),
            ("dataset", "program.exe", "application/octet-stream"),
        ):
            with self.subTest(filename=filename), self.assertRaises(AssetUploadInvalid):
                _validate_input(
                    kind=kind,
                    filename=filename,
                    declared_mime_type=mime_type,
                    size_bytes=10,
                )
