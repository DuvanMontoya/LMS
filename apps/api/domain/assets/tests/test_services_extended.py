from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase

from domain.assets.choices import AssetKind, AssetStatus, AssetVersionStatus
from domain.assets.exceptions import AssetConflict, AssetUploadInvalid
from domain.assets.models import Asset, AssetEvent, AssetVersion
from domain.assets.services import (
    archive_asset,
    promote_asset_version,
    reprocess_asset_version,
    restore_asset,
    update_asset_metadata,
)

from .support import celery_result, owner_context


class AssetServiceExtendedTests(TestCase):
    def setUp(self) -> None:
        self.owner, self.organization = owner_context("service-extended")
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
            storage_key="organizations/source.csv",
            pipeline_name="media",
            pipeline_version="1",
            expected_asset_lock_version=1,
            created_by=self.owner,
        )

    def test_metadata_archive_restore_and_conflicts(self) -> None:
        updated = update_asset_metadata(
            actor=self.owner,
            organization=self.organization,
            asset=self.asset,
            expected_lock_version=1,
            name="  Dataset updated  ",
            description="  Description  ",
        )
        self.assertEqual(updated.name, "Dataset updated")
        self.assertEqual(updated.description, "Description")
        with self.assertRaises(AssetConflict):
            update_asset_metadata(
                actor=self.owner,
                organization=self.organization,
                asset=updated,
                expected_lock_version=1,
                name="Stale",
                description="",
            )
        with self.assertRaises(AssetUploadInvalid):
            update_asset_metadata(
                actor=self.owner,
                organization=self.organization,
                asset=updated,
                expected_lock_version=updated.lock_version,
                name=" ",
                description="",
            )

        archived = archive_asset(
            actor=self.owner,
            organization=self.organization,
            asset=updated,
            expected_lock_version=updated.lock_version,
        )
        self.assertEqual(archived.status, AssetStatus.ARCHIVED)
        same = archive_asset(
            actor=self.owner,
            organization=self.organization,
            asset=archived,
            expected_lock_version=archived.lock_version,
        )
        self.assertEqual(same.pk, archived.pk)
        restored = restore_asset(
            actor=self.owner,
            organization=self.organization,
            asset=archived,
            expected_lock_version=archived.lock_version,
        )
        self.assertEqual(restored.status, AssetStatus.ACTIVE)
        same = restore_asset(
            actor=self.owner,
            organization=self.organization,
            asset=restored,
            expected_lock_version=restored.lock_version,
        )
        self.assertEqual(same.pk, restored.pk)
        self.assertEqual(AssetEvent.objects.count(), 2)

    def test_promotion_and_reprocess_are_idempotent(self) -> None:
        promoted = promote_asset_version(
            actor=self.owner,
            organization=self.organization,
            version=self.version,
            expected_lock_version=self.asset.lock_version,
        )
        self.assertEqual(promoted.current_version_id, self.version.id)
        same = promote_asset_version(
            actor=self.owner,
            organization=self.organization,
            version=self.version,
            expected_lock_version=promoted.lock_version,
        )
        self.assertEqual(same.current_version_id, self.version.id)

        with (
            patch(
                "domain.assets.processing.tasks.process_asset_version_task.delay",
                return_value=celery_result(),
            ) as delay,
            self.captureOnCommitCallbacks(execute=True),
        ):
            first = reprocess_asset_version(
                actor=self.owner,
                organization=self.organization,
                version=self.version,
            )
        second = reprocess_asset_version(
            actor=self.owner,
            organization=self.organization,
            version=self.version,
        )
        self.assertEqual(first.pk, second.pk)
        delay.assert_called_once()

    def test_non_ready_version_cannot_be_promoted_or_reprocessed(self) -> None:
        pending = AssetVersion.objects.create(
            asset=self.asset,
            number=2,
            status=AssetVersionStatus.PENDING_UPLOAD,
            original_filename="pending.csv",
            declared_mime_type="text/csv",
            expected_asset_lock_version=self.asset.lock_version,
            created_by=self.owner,
        )
        with self.assertRaises(AssetConflict):
            promote_asset_version(
                actor=self.owner,
                organization=self.organization,
                version=pending,
                expected_lock_version=self.asset.lock_version,
            )
        with self.assertRaises(AssetConflict):
            reprocess_asset_version(
                actor=self.owner,
                organization=self.organization,
                version=pending,
            )
