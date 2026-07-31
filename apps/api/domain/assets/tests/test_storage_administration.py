from __future__ import annotations

from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError
from django.test import SimpleTestCase, override_settings

from domain.assets.exceptions import AssetStorageError
from domain.assets.storage import administration


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code}}, "operation")


class StorageAdministrationTests(SimpleTestCase):
    @override_settings(
        ASSET_QUARANTINE_BUCKET="same",
        ASSET_PRIVATE_BUCKET="same",
    )
    def test_configuration_rejects_shared_buckets(self) -> None:
        with self.assertRaises(AssetStorageError):
            administration.validate_storage_configuration()

    @override_settings(
        ASSET_QUARANTINE_BUCKET="q",
        ASSET_PRIVATE_BUCKET="private-assets",
    )
    def test_configuration_rejects_invalid_bucket(self) -> None:
        with self.assertRaises(AssetStorageError):
            administration.validate_storage_configuration()

    @override_settings(
        ASSET_S3_ACCESS_KEY_ID="only-key",
        ASSET_S3_SECRET_ACCESS_KEY="",
    )
    def test_configuration_rejects_partial_credentials(self) -> None:
        with self.assertRaises(AssetStorageError):
            administration.validate_storage_configuration()

    @override_settings(ASSET_S3_PUBLIC_ENDPOINT="not-a-url")
    def test_configuration_rejects_invalid_public_endpoint(self) -> None:
        with self.assertRaises(AssetStorageError):
            administration.validate_storage_configuration()

    @patch("domain.assets.storage.administration.build_s3_client")
    def test_initialize_status_and_smoke(self, build_client: MagicMock) -> None:
        client = MagicMock()
        build_client.return_value = client
        client.head_bucket.side_effect = [
            _client_error("NoSuchBucket"),
            None,
            None,
            None,
        ]
        client.get_bucket_versioning.side_effect = [
            {"Status": ""},
            {"Status": "Enabled"},
        ]
        client.get_bucket_encryption.return_value = {
            "ServerSideEncryptionConfiguration": {
                "Rules": [
                    {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
                ]
            }
        }
        client.get_public_access_block.return_value = {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            }
        }
        client.get_bucket_lifecycle_configuration.return_value = {
            "Rules": [{"ID": "rule"}]
        }
        states = administration.initialize_storage()
        self.assertEqual(states[1].versioning, "Enabled")
        self.assertTrue(states[0].blocked_public)
        self.assertEqual(client.create_bucket.call_count, 1)
        self.assertEqual(client.put_bucket_cors.call_count, 2)
        cors_origins = [
            call.kwargs["CORSConfiguration"]["CORSRules"][0]["AllowedOrigins"]
            for call in client.put_bucket_cors.call_args_list
        ]
        self.assertTrue(
            all("http://127.0.0.1:3000" in origins for origins in cors_origins)
        )
        self.assertTrue(
            all("http://localhost:3000" in origins for origins in cors_origins)
        )
        self.assertEqual(client.put_bucket_lifecycle_configuration.call_count, 2)

        client.head_object.return_value = {
            "ContentLength": 24,
            "ChecksumSHA256": "checksum",
        }
        client.generate_presigned_url.return_value = "https://signed.example.test"
        smoke = administration.storage_smoke()
        self.assertEqual(smoke["size"], 24)
        self.assertTrue(smoke["checksum_present"])
        self.assertTrue(smoke["signed_url_generated"])
        client.delete_object.assert_called()

    @override_settings(ASSET_S3_INTERNAL_ENDPOINT="https://s3.amazonaws.com")
    def test_reset_is_localstack_only(self) -> None:
        with self.assertRaises(AssetStorageError):
            administration.reset_local_storage()

    @patch("domain.assets.storage.administration.build_s3_client")
    def test_local_reset_aborts_uploads_and_deletes_versions(
        self, build_client: MagicMock
    ) -> None:
        client = MagicMock()
        build_client.return_value = client
        multipart = MagicMock()
        multipart.paginate.return_value = [
            {"Uploads": [{"Key": "pending", "UploadId": "upload-1"}]}
        ]
        versions = MagicMock()
        versions.paginate.return_value = [
            {
                "Versions": [{"Key": "one", "VersionId": "v1"}],
                "DeleteMarkers": [{"Key": "two", "VersionId": "v2"}],
            }
        ]
        client.get_paginator.side_effect = [multipart, versions, multipart, versions]
        administration.reset_local_storage()
        self.assertEqual(client.abort_multipart_upload.call_count, 2)
        self.assertEqual(client.delete_objects.call_count, 2)

    @override_settings(ASSET_S3_REGION="eu-west-1")
    def test_ensure_bucket_uses_region_and_propagates_other_errors(self) -> None:
        client = MagicMock()
        client.head_bucket.side_effect = _client_error("NotFound")
        administration._ensure_bucket(client, "regional-bucket")
        client.create_bucket.assert_called_once_with(
            Bucket="regional-bucket",
            CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
        )
        client.head_bucket.side_effect = _client_error("AccessDenied")
        with self.assertRaises(ClientError):
            administration._ensure_bucket(client, "denied-bucket")
