from __future__ import annotations

from django.test import TestCase
from rest_framework.test import APIClient

from domain.assets.api.serializers import UploadInitializeSerializer
from domain.assets.choices import AssetKind
from domain.assets.models import Asset

from .support import owner_context


class AssetApiTests(TestCase):
    def test_new_upload_defaults_optional_asset_id_to_none(self) -> None:
        serializer = UploadInitializeSerializer(
            data={
                "kind": "dataset",
                "name": "New dataset",
                "filename": "data.txt",
                "declared_mime_type": "text/plain",
                "size_bytes": 12,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data["asset_id"])

    def test_library_is_scoped_has_no_delete_and_ignores_mass_assignment(self) -> None:
        owner, organization = owner_context("api")
        foreign_owner, foreign = owner_context("api-foreign")
        asset = Asset.objects.create(
            organization=organization,
            kind=AssetKind.IMAGE,
            name="Visible",
            created_by=owner,
            updated_by=owner,
        )
        foreign_asset = Asset.objects.create(
            organization=foreign,
            kind=AssetKind.IMAGE,
            name="Foreign",
            created_by=foreign_owner,
            updated_by=foreign_owner,
        )
        client = APIClient()
        client.force_authenticate(owner)
        root = f"/api/v1/organizations/{organization.slug}/assets/"
        response = client.get(root)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [str(asset.id)])
        self.assertEqual(client.get(f"{root}{foreign_asset.id}/").status_code, 404)
        self.assertEqual(client.delete(f"{root}{asset.id}/").status_code, 405)
        patched = client.patch(
            f"{root}{asset.id}/",
            {
                "expected_lock_version": asset.lock_version,
                "name": "Updated",
                "description": "",
                "organization": str(foreign.id),
                "status": "archived",
                "storage_key": "attacker-controlled",
            },
            format="json",
        )
        self.assertEqual(patched.status_code, 200, patched.data)
        asset.refresh_from_db()
        self.assertEqual(asset.organization_id, organization.id)
        self.assertEqual(asset.status, "active")
