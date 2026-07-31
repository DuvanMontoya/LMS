from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError
from django.test import SimpleTestCase

from domain.assets.exceptions import AssetStorageError
from domain.assets.storage.boto3_gateway import (
    Boto3ObjectStorageGateway,
    build_s3_client,
)
from domain.assets.storage.gateway import MultipartPart


def _gateway() -> tuple[Boto3ObjectStorageGateway, MagicMock, MagicMock]:
    gateway = object.__new__(Boto3ObjectStorageGateway)
    internal = MagicMock()
    public = MagicMock()
    gateway._internal = internal
    gateway._public = public
    return gateway, internal, public


class Boto3GatewayExtendedTests(SimpleTestCase):
    def test_success_paths_map_s3_contracts(self) -> None:
        gateway, internal, public = _gateway()
        public.generate_presigned_post.return_value = {
            "url": "https://upload.example.test",
            "fields": {"key": "object"},
        }
        post = gateway.generate_upload_post(
            bucket="quarantine",
            key="key",
            size_bytes=10,
            expires_seconds=60,
            session_id="session",
        )
        self.assertEqual(post.fields["key"], "object")

        internal.create_multipart_upload.return_value = {"UploadId": "upload"}
        self.assertEqual(
            gateway.create_multipart_upload(
                bucket="quarantine", key="key", session_id="session"
            ),
            "upload",
        )
        public.generate_presigned_url.return_value = "https://signed.example.test"
        self.assertIn(
            "signed",
            gateway.generate_part_upload_url(
                bucket="quarantine",
                key="key",
                upload_id="upload",
                part_number=1,
                checksum_sha256="checksum",
                expires_seconds=60,
            ),
        )
        gateway.complete_multipart_upload(
            bucket="quarantine",
            key="key",
            upload_id="upload",
            parts=[MultipartPart(1, "etag", "checksum")],
        )
        gateway.abort_multipart_upload(
            bucket="quarantine", key="key", upload_id="upload"
        )

        internal.head_object.return_value = {
            "ContentLength": 3,
            "ETag": '"etag"',
            "ChecksumSHA256": "sha",
            "ContentType": "text/plain",
            "Metadata": {"upload-session": "session"},
            "VersionId": "v1",
        }
        head = gateway.head_object(bucket="private", key="key")
        self.assertEqual(head.checksum_algorithm, "SHA256")
        self.assertEqual(head.etag, "etag")

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.write_bytes(b"abc")
            target = Path(directory) / "target"

            def download(_bucket: str, _key: str, stream: object) -> None:
                stream.write(b"abc")  # type: ignore[attr-defined]

            internal.download_fileobj.side_effect = download
            gateway.download_to_path(bucket="private", key="key", path=target)
            self.assertEqual(target.read_bytes(), b"abc")
            gateway.upload_path(
                bucket="private",
                key="new",
                path=source,
                content_type="text/plain",
            )

        gateway.copy_object(
            source_bucket="quarantine",
            source_key="source",
            destination_bucket="private",
            destination_key="target",
            content_type="text/plain",
        )
        gateway.delete_object(bucket="private", key="target")
        self.assertIn(
            "signed",
            gateway.generate_download_url(
                bucket="private",
                key="target",
                expires_seconds=60,
                content_type="text/plain",
                content_disposition="attachment",
            ),
        )

    def test_errors_translate_and_missing_multipart_abort_is_idempotent(self) -> None:
        gateway, internal, public = _gateway()
        error = ClientError({"Error": {"Code": "AccessDenied"}}, "operation")
        public.generate_presigned_post.side_effect = error
        with self.assertRaises(AssetStorageError):
            gateway.generate_upload_post(
                bucket="q",
                key="k",
                size_bytes=1,
                expires_seconds=1,
                session_id="s",
            )
        internal.abort_multipart_upload.side_effect = ClientError(
            {"Error": {"Code": "NoSuchUpload"}}, "abort"
        )
        gateway.abort_multipart_upload(bucket="q", key="k", upload_id="gone")
        internal.head_object.side_effect = error
        with self.assertRaises(AssetStorageError):
            gateway.head_object(bucket="q", key="k")

    @patch("domain.assets.storage.boto3_gateway.boto3.client")
    def test_client_uses_signature_v4_and_explicit_credentials(
        self, client: MagicMock
    ) -> None:
        build_s3_client("http://127.0.0.1:4566")
        kwargs = client.call_args.kwargs
        self.assertEqual(kwargs["endpoint_url"], "http://127.0.0.1:4566")
        self.assertEqual(kwargs["config"].signature_version, "s3v4")
        self.assertEqual(kwargs["aws_access_key_id"], "test")
