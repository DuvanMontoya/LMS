from __future__ import annotations

from django.test import SimpleTestCase

from domain.assets.processing.common import calculate_sha256


class ProcessingPrimitiveTests(SimpleTestCase):
    def test_sha256_is_full_file_authority(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            path = Path(directory) / "payload.bin"
            path.write_bytes(b"asset-payload")
            self.assertEqual(
                calculate_sha256(path),
                "992d4d0c6b721650f927ca53284e43c653936269b584f657193436a39ec3103d",
            )
