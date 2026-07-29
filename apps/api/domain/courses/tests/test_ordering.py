from __future__ import annotations

from django.test import TestCase

from domain.courses.choices import StructureStatus
from domain.courses.exceptions import CourseOrderInvalid, CourseRevisionConflict
from domain.courses.models import CourseModule
from domain.courses.services import (
    archive_module,
    archive_unit,
    create_module,
    create_unit,
    replace_module_order,
    replace_unit_order,
    restore_module,
    restore_unit,
)

from .support import CourseFixtureMixin


class CourseOrderingTests(CourseFixtureMixin, TestCase):
    def test_module_reorder_archive_and_restore_are_contiguous(self) -> None:
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
        revision = replace_module_order(
            actor=owner,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
            ordered_ids=[modules[2].id, modules[0].id, modules[1].id],
        )
        self.assertEqual(
            list(
                CourseModule.objects.filter(revision=revision)
                .order_by("position")
                .values_list("title", "position")
            ),
            [("Tres", 1), ("Uno", 2), ("Dos", 3)],
        )
        archived, revision = archive_module(
            actor=owner,
            organization=organization,
            module=modules[0],
            expected_version=revision.lock_version,
        )
        self.assertIsNone(archived.position)
        self.assertEqual(archived.status, StructureStatus.ARCHIVED)
        restored, revision = restore_module(
            actor=owner,
            organization=organization,
            module=archived,
            expected_version=revision.lock_version,
        )
        self.assertEqual(restored.position, 3)
        self.assertEqual(
            list(
                CourseModule.objects.filter(
                    revision=revision, status=StructureStatus.ACTIVE
                )
                .order_by("position")
                .values_list("position", flat=True)
            ),
            [1, 2, 3],
        )

    def test_unit_ordering_and_stale_version(self) -> None:
        owner, organization, *_, revision = self.course_revision()
        module, revision = create_module(
            actor=owner,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
            title="Módulo",
        )
        units = []
        for title in ("A", "B", "C"):
            unit, revision = create_unit(
                actor=owner,
                organization=organization,
                module=module,
                expected_version=revision.lock_version,
                title=title,
            )
            units.append(unit)
        stale = revision.lock_version
        revision = replace_unit_order(
            actor=owner,
            organization=organization,
            module=module,
            expected_version=stale,
            ordered_ids=[units[2].id, units[1].id, units[0].id],
        )
        with self.assertRaises(CourseRevisionConflict):
            replace_unit_order(
                actor=owner,
                organization=organization,
                module=module,
                expected_version=stale,
                ordered_ids=[unit.id for unit in units],
            )
        with self.assertRaises(CourseOrderInvalid):
            replace_unit_order(
                actor=owner,
                organization=organization,
                module=module,
                expected_version=revision.lock_version,
                ordered_ids=[units[0].id],
            )
        archived, revision = archive_unit(
            actor=owner,
            organization=organization,
            unit=units[1],
            expected_version=revision.lock_version,
        )
        self.assertIsNone(archived.position)
        restored, _ = restore_unit(
            actor=owner,
            organization=organization,
            unit=archived,
            expected_version=revision.lock_version,
        )
        self.assertEqual(restored.position, 3)
