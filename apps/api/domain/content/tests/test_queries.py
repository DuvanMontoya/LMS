from __future__ import annotations

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from domain.content.services import save_unit_content
from domain.courses.readiness import revision_readiness_issues
from domain.courses.selectors import course_outline
from domain.courses.services import confirm_completion_policy

from .support import ContentFixtureMixin, full_document


class ContentQueryShapeTests(ContentFixtureMixin, TestCase):
    def test_version_list_defers_document_json_and_actor_is_joined(self) -> None:
        owner, organization, revision, _module, unit, *_ = self.unit_context()
        save_unit_content(
            actor=owner,
            organization=organization,
            revision=revision,
            unit=unit,
            expected_document_version=0,
            schema_version=1,
            content=full_document(),
        )
        client = APIClient()
        client.force_authenticate(user=owner)
        base = (
            f"/api/v1/organizations/{organization.slug}/courses/"
            f"{revision.course.slug}/revisions/{revision.id}/units/{unit.id}/content/"
        )
        with CaptureQueriesContext(connection) as captured:
            response = client.get(f"{base}versions/")
        self.assertEqual(response.status_code, 200, response.data)
        version_selects = [
            query["sql"]
            for query in captured.captured_queries
            if "content_unitcontentversion" in query["sql"]
            and query["sql"].lstrip().upper().startswith("SELECT")
        ]
        self.assertTrue(version_selects)
        select_clause = version_selects[-1].split(" FROM ", 1)[0]
        self.assertNotIn('"content"', select_clause)
        self.assertNotIn('"plain_text"', select_clause)

    def test_outline_and_readiness_use_bounded_eager_queries(self) -> None:
        owner, organization, revision, _module, unit, *_ = self.unit_context()
        save_unit_content(
            actor=owner,
            organization=organization,
            revision=revision,
            unit=unit,
            expected_document_version=0,
            schema_version=1,
            content=full_document(),
        )
        _, revision = confirm_completion_policy(
            actor=owner,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
            require_required_activities=True,
            minimum_grade_basis_points=None,
            minimum_attendance_basis_points=None,
        )
        with CaptureQueriesContext(connection) as outline_queries:
            outline = course_outline(owner, revision.course, str(revision.id))
            list(outline.modules.all())
        with CaptureQueriesContext(connection) as readiness_queries:
            issues = revision_readiness_issues(revision)
        self.assertIsNotNone(outline)
        self.assertEqual(issues, [])
        self.assertLessEqual(
            sum(
                "content_unitcontentversion" in query["sql"]
                for query in outline_queries.captured_queries
            ),
            1,
        )
        self.assertLess(len(readiness_queries), 15)
