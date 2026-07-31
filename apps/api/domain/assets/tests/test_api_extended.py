from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from domain.assets.choices import AssetKind, AssetVersionStatus
from domain.assets.models import Asset, AssetVersion

from .support import FakeStorageGateway, celery_result, owner_context


class AssetApiExtendedTests(TestCase):
    def setUp(self) -> None:
        self.owner, self.organization = owner_context("api-extended")
        self.asset = Asset.objects.create(
            organization=self.organization,
            kind=AssetKind.DATASET,
            name="Dataset",
            created_by=self.owner,
            updated_by=self.owner,
        )
        self.version = AssetVersion.objects.create(
            asset=self.asset,
            number=1,
            status=AssetVersionStatus.READY,
            original_filename="data.csv",
            declared_mime_type="text/csv",
            detected_mime_type="text/csv",
            extension=".csv",
            size_bytes=12,
            sha256="a" * 64,
            storage_bucket="private",
            storage_key="organizations/data.csv",
            pipeline_name="media",
            pipeline_version="1",
            expected_asset_lock_version=1,
            created_by=self.owner,
        )
        self.asset.current_version = self.version
        self.asset.save(update_fields=["current_version"])
        self.client = APIClient()
        self.client.force_authenticate(self.owner)
        self.root = (
            f"/api/v1/organizations/{self.organization.slug}/assets/{self.asset.id}/"
        )
        self.version_root = f"{self.root}versions/{self.version.id}/"

    def test_read_state_version_and_usage_endpoints(self) -> None:
        responses = (
            self.client.get(self.root),
            self.client.get(f"{self.root}versions/"),
            self.client.get(self.version_root),
            self.client.get(f"{self.root}usage/"),
        )
        self.assertTrue(all(response.status_code == 200 for response in responses))

        archive = self.client.post(
            f"{self.root}archive/",
            {"expected_lock_version": self.asset.lock_version},
            format="json",
        )
        self.assertEqual(archive.status_code, 200)
        restore = self.client.post(
            f"{self.root}restore/",
            {"expected_lock_version": archive.data["lock_version"]},
            format="json",
        )
        self.assertEqual(restore.status_code, 200)

    def test_promote_reprocess_job_and_signed_access(self) -> None:
        second = AssetVersion.objects.create(
            asset=self.asset,
            number=2,
            status=AssetVersionStatus.READY,
            original_filename="data-v2.csv",
            declared_mime_type="text/csv",
            detected_mime_type="text/csv",
            extension=".csv",
            size_bytes=12,
            sha256="b" * 64,
            storage_bucket="private",
            storage_key="organizations/data-v2.csv",
            pipeline_name="media",
            pipeline_version="1",
            expected_asset_lock_version=self.asset.lock_version,
            created_by=self.owner,
        )
        promote = self.client.post(
            f"{self.root}versions/{second.id}/promote/",
            {"expected_lock_version": self.asset.lock_version},
            format="json",
        )
        self.assertEqual(promote.status_code, 200, promote.data)
        with (
            patch(
                "domain.assets.processing.tasks.process_asset_version_task.delay",
                return_value=celery_result(),
            ),
            self.captureOnCommitCallbacks(execute=True),
        ):
            reprocess = self.client.post(
                f"{self.root}versions/{second.id}/reprocess/",
                format="json",
            )
        self.assertEqual(reprocess.status_code, 202, reprocess.data)
        job = self.client.get(
            f"/api/v1/organizations/{self.organization.slug}/processing-jobs/"
            f"{reprocess.data['id']}/"
        )
        self.assertEqual(job.status_code, 200)

        gateway = FakeStorageGateway()
        with patch(
            "domain.assets.delivery.services.storage_gateway",
            return_value=gateway,
        ):
            access = self.client.post(
                f"{self.root}versions/{second.id}/access/", format="json"
            )
            original = self.client.post(
                f"{self.root}versions/{second.id}/original-download/",
                format="json",
            )
        self.assertEqual(access.status_code, 200, access.data)
        self.assertEqual(original.status_code, 200, original.data)
        self.assertNotIn("storage_key", access.data)

    def test_foreign_session_job_and_version_are_hidden(self) -> None:
        foreign_owner, foreign = owner_context("api-extended-foreign")
        foreign_asset = Asset.objects.create(
            organization=foreign,
            kind=AssetKind.DATASET,
            name="Foreign",
            created_by=foreign_owner,
            updated_by=foreign_owner,
        )
        foreign_version = AssetVersion.objects.create(
            asset=foreign_asset,
            number=1,
            status=AssetVersionStatus.READY,
            original_filename="foreign.csv",
            declared_mime_type="text/csv",
            detected_mime_type="text/csv",
            extension=".csv",
            size_bytes=1,
            sha256="c" * 64,
            storage_bucket="private",
            storage_key="foreign",
            expected_asset_lock_version=1,
            created_by=foreign_owner,
        )
        response = self.client.get(f"{self.root}versions/{foreign_version.id}/")
        self.assertEqual(response.status_code, 404)
        response = self.client.get(
            f"/api/v1/organizations/{self.organization.slug}/uploads/"
            f"{foreign_version.id}/"
        )
        self.assertEqual(response.status_code, 404)
        response = self.client.get(
            f"/api/v1/organizations/{self.organization.slug}/processing-jobs/"
            f"{foreign_version.id}/"
        )
        self.assertEqual(response.status_code, 404)
