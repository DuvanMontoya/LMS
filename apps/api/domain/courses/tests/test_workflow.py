from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase

from domain.courses.choices import AuthoringStatus
from domain.courses.exceptions import (
    CourseAccessDenied,
    CourseRevisionNotEditable,
    CourseRevisionNotReady,
)
from domain.courses.services import (
    approve_revision,
    create_module,
    create_unit,
    replace_unit_learning_objectives,
    replace_unit_topics,
    request_revision_changes,
    submit_revision_for_review,
    update_revision_metadata,
)
from domain.organizations.choices import RoleCode

from .support import CourseFixtureMixin


class CourseWorkflowTests(CourseFixtureMixin, TestCase):
    @patch.dict("domain.courses.readiness._READINESS_PROVIDERS", clear=True)
    def test_readiness_and_complete_review_cycle(self) -> None:
        """Exercise the base course workflow without optional domain extensions."""
        owner, organization, _, objective, topic, revision = self.course_revision()
        author = self.member(
            owner, organization, RoleCode.AUTHOR, "author@example.test"
        )
        reviewer = self.member(
            owner, organization, RoleCode.REVIEWER, "reviewer@example.test"
        )
        with self.assertRaises(CourseRevisionNotReady):
            submit_revision_for_review(
                actor=author,
                organization=organization,
                revision=revision,
                expected_version=revision.lock_version,
            )
        module, revision = create_module(
            actor=author,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
            title="Fundamentos",
        )
        unit, revision = create_unit(
            actor=author,
            organization=organization,
            module=module,
            expected_version=revision.lock_version,
            title="Relaciones",
        )
        revision = replace_unit_topics(
            actor=author,
            organization=organization,
            unit=unit,
            expected_version=revision.lock_version,
            topics=[topic],
        )
        revision = replace_unit_learning_objectives(
            actor=author,
            organization=organization,
            unit=unit,
            expected_version=revision.lock_version,
            learning_objectives=[objective],
        )
        revision = submit_revision_for_review(
            actor=author,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
            note="Lista para revisión.",
        )
        self.assertEqual(revision.authoring_status, AuthoringStatus.IN_REVIEW)
        with self.assertRaises(CourseRevisionNotEditable):
            update_revision_metadata(
                actor=author,
                organization=organization,
                revision=revision,
                expected_version=revision.lock_version,
                title="No permitido",
            )
        with self.assertRaises(CourseAccessDenied):
            approve_revision(
                actor=reviewer,
                organization=organization,
                revision=revision,
                expected_version=revision.lock_version,
            )
        revision = request_revision_changes(
            actor=reviewer,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
            note="Aclara el resumen.",
        )
        self.assertEqual(revision.authoring_status, AuthoringStatus.CHANGES_REQUESTED)
        revision = update_revision_metadata(
            actor=author,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
            summary="Resumen aclarado para la revisión.",
        )
        revision = submit_revision_for_review(
            actor=author,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
        )
        revision = approve_revision(
            actor=owner,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
            note="Aprobada.",
        )
        self.assertEqual(revision.authoring_status, AuthoringStatus.APPROVED)
        self.assertEqual(revision.transitions.count(), 5)
        with self.assertRaises(CourseRevisionNotEditable):
            update_revision_metadata(
                actor=owner,
                organization=organization,
                revision=revision,
                expected_version=revision.lock_version,
                title="Una revisión aprobada tampoco se edita",
            )
