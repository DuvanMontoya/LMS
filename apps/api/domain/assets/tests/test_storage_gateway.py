from __future__ import annotations

from django.test import SimpleTestCase

from domain.assets.storage.presigning import content_disposition


class StorageContractTests(SimpleTestCase):
    def test_content_disposition_sanitizes_control_characters(self) -> None:
        value = content_disposition(filename='bad"\r\nname.pdf', inline=False)
        self.assertTrue(value.startswith("attachment;"))
        self.assertNotIn("\r", value)
        self.assertNotIn("\n", value)
        self.assertIn("filename*=UTF-8''", value)
