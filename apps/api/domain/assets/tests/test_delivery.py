from __future__ import annotations

from django.test import TestCase

from domain.assets.choices import AssetKind, AssetVersionStatus, VariantRole
from domain.assets.delivery.services import asset_access_descriptor
from domain.assets.models import Asset, AssetVariant, AssetVersion

from .support import FakeStorageGateway, owner_context


class AssetDeliveryTests(TestCase):
    def test_image_descriptor_prefers_variants_and_never_quarantine(self) -> None:
        owner, organization = owner_context("delivery")
        asset = Asset.objects.create(
            organization=organization,
            kind=AssetKind.IMAGE,
            name="Image",
            created_by=owner,
            updated_by=owner,
        )
        version = AssetVersion.objects.create(
            asset=asset,
            number=1,
            status=AssetVersionStatus.READY,
            original_filename="image.png",
            declared_mime_type="image/png",
            detected_mime_type="image/png",
            size_bytes=10,
            sha256="a" * 64,
            storage_bucket="private",
            storage_key="originals/test",
            expected_asset_lock_version=1,
            created_by=owner,
        )
        AssetVariant.objects.create(
            asset_version=version,
            role=VariantRole.IMAGE_MEDIUM,
            pipeline_name="media",
            pipeline_version="1",
            mime_type="image/webp",
            extension=".webp",
            storage_bucket="private",
            storage_key="variants/test",
            size_bytes=5,
            sha256="b" * 64,
        )
        descriptor = asset_access_descriptor(
            version=version, gateway=FakeStorageGateway()
        )
        self.assertIsNone(descriptor.source)
        self.assertEqual(len(descriptor.variants), 1)
        self.assertNotIn("quarantine", descriptor.variants[0].url)
