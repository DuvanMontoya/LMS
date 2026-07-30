from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase

from domain.content.models import UnitContentVersion
from domain.content.services import save_unit_content
from domain.courses import readiness as course_readiness
from domain.courses.exceptions import CourseRevisionNotReady
from domain.courses.readiness import (
    register_readiness_provider,
    revision_readiness_issues,
)
from domain.courses.services import submit_revision_for_review

from .support import ContentFixtureMixin, empty_document, full_document


class ContentReadinessTests(ContentFixtureMixin, TestCase):
    def test_missing_empty_and_valid_content_control_submit(self) -> None:
        owner, organization, revision, _module, unit, *_ = self.unit_context()
        missing = revision_readiness_issues(revision)
        self.assertIn("unit_content_missing", {item["code"] for item in missing})
        with self.assertRaises(CourseRevisionNotReady):
            submit_revision_for_review(
                actor=owner,
                organization=organization,
                revision=revision,
                expected_version=revision.lock_version,
            )
        save_unit_content(
            actor=owner,
            organization=organization,
            revision=revision,
            unit=unit,
            expected_document_version=0,
            schema_version=1,
            content=empty_document(),
        )
        empty = revision_readiness_issues(revision)
        self.assertIn("unit_content_empty", {item["code"] for item in empty})
        save_unit_content(
            actor=owner,
            organization=organization,
            revision=revision,
            unit=unit,
            expected_document_version=1,
            schema_version=1,
            content=full_document(),
        )
        self.assertNotIn(
            "unit_content_empty",
            {item["code"] for item in revision_readiness_issues(revision)},
        )
        submitted = submit_revision_for_review(
            actor=owner,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
        )
        self.assertEqual(submitted.authoring_status, "in_review")

    def test_duplicate_provider_name_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            register_readiness_provider("unit-content", lambda revision: [])

    def test_unsupported_schema_and_corrupt_digest_are_reported(self) -> None:
        owner, organization, revision, _module, unit, *_ = self.unit_context()
        result = save_unit_content(
            actor=owner,
            organization=organization,
            revision=revision,
            unit=unit,
            expected_document_version=0,
            schema_version=1,
            content=full_document(),
        )
        UnitContentVersion.objects.filter(pk=result.version.pk).update(
            schema_version=99
        )
        issues = revision_readiness_issues(revision)
        self.assertIn(
            "unit_content_schema_unsupported",
            {item["code"] for item in issues},
        )
        UnitContentVersion.objects.filter(pk=result.version.pk).update(
            schema_version=1, digest="0" * 64
        )
        issues = revision_readiness_issues(revision)
        self.assertIn(
            "unit_content_digest_mismatch",
            {item["code"] for item in issues},
        )

    def test_provider_order_is_deterministic(self) -> None:
        _owner, _organization, revision, *_ = self.unit_context()
        with patch.dict(course_readiness._READINESS_PROVIDERS, {}, clear=True):
            register_readiness_provider(
                "zeta",
                lambda _revision: [{"code": "z", "path": "z", "message": "último"}],
            )
            register_readiness_provider(
                "alpha",
                lambda _revision: [{"code": "a", "path": "a", "message": "primero"}],
            )
            issues = revision_readiness_issues(revision)
        self.assertEqual([item["code"] for item in issues[-2:]], ["a", "z"])
