from __future__ import annotations

from django.core.exceptions import ValidationError
from django.test import TestCase

from domain.content.exceptions import ContentDocumentConflict
from domain.content.models import UnitContentDocument, UnitContentVersion
from domain.content.services import restore_unit_content, save_unit_content

from .support import ContentFixtureMixin, full_document


class ContentVersioningTests(ContentFixtureMixin, TestCase):
    def test_first_save_noop_conflict_second_save_and_restore_are_append_only(
        self,
    ) -> None:
        owner, organization, revision, _module, unit, *_ = self.unit_context()
        first = save_unit_content(
            actor=owner,
            organization=organization,
            revision=revision,
            unit=unit,
            expected_document_version=0,
            schema_version=1,
            content=full_document(),
        )
        self.assertEqual(first.version.number, 1)
        self.assertFalse(first.no_op)
        self.assertEqual(UnitContentDocument.objects.count(), 1)

        noop = save_unit_content(
            actor=owner,
            organization=organization,
            revision=revision,
            unit=unit,
            expected_document_version=1,
            schema_version=1,
            content=full_document(),
        )
        self.assertTrue(noop.no_op)
        self.assertEqual(UnitContentVersion.objects.count(), 1)

        changed = full_document()
        changed["content"][0]["content"][0]["text"] = "Funciones reales"
        second = save_unit_content(
            actor=owner,
            organization=organization,
            revision=revision,
            unit=unit,
            expected_document_version=1,
            schema_version=1,
            content=changed,
        )
        self.assertEqual(second.version.number, 2)
        with self.assertRaises(ContentDocumentConflict):
            save_unit_content(
                actor=owner,
                organization=organization,
                revision=revision,
                unit=unit,
                expected_document_version=1,
                schema_version=1,
                content=full_document(),
            )
        restored = restore_unit_content(
            actor=owner,
            organization=organization,
            revision=revision,
            unit=unit,
            expected_document_version=2,
            version_number=1,
        )
        self.assertEqual(restored.version.number, 3)
        self.assertEqual(restored.version.digest, first.version.digest)
        self.assertEqual(UnitContentVersion.objects.count(), 3)

        with self.assertRaises(ValidationError):
            restored.version.save()
        with self.assertRaises(ValidationError):
            restored.version.delete()
        with self.assertRaises(ValidationError):
            restored.document.delete()
