from __future__ import annotations

from django.test import TestCase
from rest_framework.test import APIClient

from domain.content.models import UnitContentDocument

from .support import ContentFixtureMixin, full_document


class ContentApiTests(ContentFixtureMixin, TestCase):
    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_virtual_get_save_conflict_history_restore_and_mass_assignment(
        self,
    ) -> None:
        owner, organization, revision, _module, unit, *_ = self.unit_context()
        client = self.client_for(owner)
        base = (
            f"/api/v1/organizations/{organization.slug}/courses/"
            f"{revision.course.slug}/revisions/{revision.id}/units/{unit.id}/content/"
        )
        virtual = client.get(base)
        self.assertEqual(virtual.status_code, 200, virtual.data)
        self.assertEqual(virtual.data["document_version"], 0)
        self.assertFalse(virtual.data["is_meaningful"])
        self.assertEqual(UnitContentDocument.objects.count(), 0)

        validation = client.post(
            f"{base}validate/",
            {"schema_version": 1, "content": full_document()},
            format="json",
        )
        self.assertEqual(validation.status_code, 200, validation.data)
        self.assertEqual(UnitContentDocument.objects.count(), 0)

        saved = client.put(
            base,
            {
                "expected_document_version": 0,
                "schema_version": 1,
                "content": full_document(),
                "unit": "foreign",
                "digest": "0" * 64,
                "number": 99,
                "created_by": str(owner.id),
            },
            format="json",
        )
        self.assertEqual(saved.status_code, 200, saved.data)
        self.assertEqual(saved.data["document_version"], 1)
        self.assertNotEqual(saved.data["digest"], "0" * 64)

        conflict = client.put(
            base,
            {
                "expected_document_version": 0,
                "schema_version": 1,
                "content": full_document(),
            },
            format="json",
        )
        self.assertEqual(conflict.status_code, 409, conflict.data)
        self.assertEqual(conflict.data["current_document_version"], 1)

        versions = client.get(f"{base}versions/")
        self.assertEqual(versions.status_code, 200, versions.data)
        self.assertEqual(len(versions.data), 1)
        self.assertNotIn("content", versions.data[0])
        detail = client.get(f"{base}versions/1/")
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertIn("content", detail.data)
        restored = client.post(
            f"{base}versions/1/restore/",
            {"expected_document_version": 1},
            format="json",
        )
        self.assertEqual(restored.status_code, 200, restored.data)
        self.assertEqual(restored.data["document_version"], 2)

        self.assertEqual(client.delete(base).status_code, 405)
        self.assertEqual(client.patch(f"{base}versions/1/").status_code, 405)
