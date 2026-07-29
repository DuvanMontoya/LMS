from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import close_old_connections
from django.test import TransactionTestCase

from domain.courses.exceptions import CourseRevisionConflict
from domain.courses.models import CourseModule, CourseRevision
from domain.courses.services import (
    create_module,
    replace_module_order,
    update_revision_metadata,
)
from domain.organizations.models import Organization

from .support import CourseFixtureMixin


class CourseConcurrencyTests(CourseFixtureMixin, TransactionTestCase):
    reset_sequences = True

    def test_concurrent_metadata_update_has_one_winner(self) -> None:
        owner, organization, *_, revision = self.course_revision()
        barrier = Barrier(2)

        def update(title: str) -> str:
            close_old_connections()
            try:
                actor = type(owner).objects.get(pk=owner.pk)
                scoped_organization = Organization.objects.get(pk=organization.pk)
                current = CourseRevision.objects.get(pk=revision.pk)
                barrier.wait(timeout=10)
                update_revision_metadata(
                    actor=actor,
                    organization=scoped_organization,
                    revision=current,
                    expected_version=1,
                    title=title,
                )
                return "saved"
            except CourseRevisionConflict:
                return "conflict"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(update, ("Primero", "Segundo")))
        self.assertCountEqual(results, ["saved", "conflict"])
        revision.refresh_from_db()
        self.assertEqual(revision.lock_version, 2)
        self.assertIn(revision.title, {"Primero", "Segundo"})

    def test_concurrent_reorder_keeps_a_contiguous_result(self) -> None:
        owner, organization, *_, revision = self.course_revision()
        modules = []
        for title in ("Uno", "Dos", "Tres"):
            module, revision = create_module(
                actor=owner,
                organization=organization,
                revision=revision,
                expected_version=revision.lock_version,
                title=title,
            )
            modules.append(module)
        expected_version = revision.lock_version
        barrier = Barrier(2)

        def reorder(ids: list[object]) -> str:
            close_old_connections()
            try:
                actor = type(owner).objects.get(pk=owner.pk)
                scoped_organization = Organization.objects.get(pk=organization.pk)
                current = CourseRevision.objects.get(pk=revision.pk)
                barrier.wait(timeout=10)
                replace_module_order(
                    actor=actor,
                    organization=scoped_organization,
                    revision=current,
                    expected_version=expected_version,
                    ordered_ids=ids,
                )
                return "saved"
            except CourseRevisionConflict:
                return "conflict"
            finally:
                close_old_connections()

        orders = [
            [modules[2].id, modules[1].id, modules[0].id],
            [modules[1].id, modules[0].id, modules[2].id],
        ]
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(reorder, orders))
        self.assertCountEqual(results, ["saved", "conflict"])
        self.assertEqual(
            list(
                CourseModule.objects.filter(revision=revision)
                .order_by("position")
                .values_list("position", flat=True)
            ),
            [1, 2, 3],
        )
