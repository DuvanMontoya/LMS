from __future__ import annotations

from django.test import TestCase

from domain.assets.choices import AssetKind, AssetVersionStatus
from domain.assets.exceptions import AssetConflict
from domain.assets.models import Asset, AssetVersion
from domain.assets.services import promote_asset_version

from .support import owner_context


class AssetOptimisticConcurrencyTests(TestCase):
    def test_stale_promotion_is_rejected(self) -> None:
        owner, organization = owner_context("concurrency")
        asset = Asset.objects.create(
            organization=organization,
            kind=AssetKind.DOCUMENT,
            name="Document",
            created_by=owner,
            updated_by=owner,
        )
        versions = [
            AssetVersion.objects.create(
                asset=asset,
                number=number,
                status=AssetVersionStatus.READY,
                original_filename=f"v{number}.pdf",
                declared_mime_type="application/pdf",
                detected_mime_type="application/pdf",
                size_bytes=10,
                sha256=str(number) * 64,
                storage_bucket="private",
                storage_key=f"originals/{number}",
                expected_asset_lock_version=1,
                created_by=owner,
            )
            for number in (1, 2)
        ]
        promote_asset_version(
            actor=owner,
            organization=organization,
            version=versions[0],
            expected_lock_version=1,
        )
        with self.assertRaises(AssetConflict):
            promote_asset_version(
                actor=owner,
                organization=organization,
                version=versions[1],
                expected_lock_version=1,
            )
