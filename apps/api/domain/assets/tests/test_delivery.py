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

    def test_document_preview_is_inline_but_original_download_is_attachment(
        self,
    ) -> None:
        owner, organization = owner_context("document-preview")
        asset = Asset.objects.create(
            organization=organization,
            kind=AssetKind.DOCUMENT,
            name="Document",
            created_by=owner,
            updated_by=owner,
        )
        version = AssetVersion.objects.create(
            asset=asset,
            number=1,
            status=AssetVersionStatus.READY,
            original_filename="paper.pdf",
            declared_mime_type="application/pdf",
            detected_mime_type="application/pdf",
            size_bytes=10,
            sha256="c" * 64,
            storage_bucket="private",
            storage_key="originals/paper.pdf",
            expected_asset_lock_version=1,
            created_by=owner,
        )

        class RecordingGateway(FakeStorageGateway):
            dispositions: list[str]

            def __init__(self) -> None:
                super().__init__()
                self.dispositions = []

            def generate_download_url(
                self,
                *,
                bucket: str,
                key: str,
                expires_seconds: int,
                content_type: str,
                content_disposition: str,
            ) -> str:
                del bucket, key, expires_seconds, content_type
                self.dispositions.append(content_disposition)
                return "https://storage.example.test/document?signature=test"

        gateway = RecordingGateway()
        asset_access_descriptor(version=version, gateway=gateway)
        asset_access_descriptor(version=version, gateway=gateway, include_original=True)

        self.assertTrue(gateway.dispositions[0].startswith("inline;"))
        self.assertTrue(gateway.dispositions[1].startswith("attachment;"))
