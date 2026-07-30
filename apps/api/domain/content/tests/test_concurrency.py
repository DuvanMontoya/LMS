from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import close_old_connections
from django.test import TransactionTestCase

from domain.content.exceptions import ContentDocumentConflict
from domain.content.models import UnitContentDocument, UnitContentVersion
from domain.content.services import save_unit_content
from domain.courses.models import CourseRevision, CourseUnit
from domain.identity.models import User
from domain.organizations.models import Organization

from .support import ContentFixtureMixin, full_document


class ContentConcurrencyTests(ContentFixtureMixin, TransactionTestCase):
    reset_sequences = True

    def _run_parallel_save(self, expected_version: int) -> list[str]:
        owner, organization, revision, _module, unit, *_ = self.context
        barrier = Barrier(2)

        def save(title: str) -> str:
            close_old_connections()
            try:
                actor = User.objects.get(pk=owner.pk)
                scoped_organization = Organization.objects.get(pk=organization.pk)
                scoped_revision = CourseRevision.objects.get(pk=revision.pk)
                scoped_unit = CourseUnit.objects.get(pk=unit.pk)
                content = full_document()
                content["content"][0]["content"][0]["text"] = title
                barrier.wait(timeout=10)
                save_unit_content(
                    actor=actor,
                    organization=scoped_organization,
                    revision=scoped_revision,
                    unit=scoped_unit,
                    expected_document_version=expected_version,
                    schema_version=1,
                    content=content,
                )
                return "saved"
            except ContentDocumentConflict:
                return "conflict"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            return list(executor.map(save, ("Versión A", "Versión B")))

    def test_concurrent_first_save_has_one_winner(self) -> None:
        self.context = self.unit_context()
        self.assertCountEqual(self._run_parallel_save(0), ["saved", "conflict"])
        self.assertEqual(UnitContentDocument.objects.count(), 1)
        self.assertEqual(UnitContentVersion.objects.count(), 1)
        self.assertEqual(
            UnitContentDocument.objects.get().current_version.number,
            1,
        )

    def test_concurrent_update_has_one_winner_and_preserves_current(self) -> None:
        self.context = self.unit_context()
        owner, organization, revision, _module, unit, *_ = self.context
        save_unit_content(
            actor=owner,
            organization=organization,
            revision=revision,
            unit=unit,
            expected_document_version=0,
            schema_version=1,
            content=full_document(),
        )
        self.assertCountEqual(self._run_parallel_save(1), ["saved", "conflict"])
        document = UnitContentDocument.objects.select_related("current_version").get()
        self.assertEqual(document.current_version.number, 2)
        self.assertEqual(UnitContentVersion.objects.count(), 2)
