from __future__ import annotations

from django.test import TestCase
from rest_framework.test import APIClient

from .support import ContentFixtureMixin, full_document


class ContentApiSecurityTests(ContentFixtureMixin, TestCase):
    def test_session_put_requires_csrf_and_rejects_malicious_content(self) -> None:
        owner, organization, revision, _module, unit, *_ = self.unit_context()
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(owner)
        base = (
            f"/api/v1/organizations/{organization.slug}/courses/"
            f"{revision.course.slug}/revisions/{revision.id}/units/{unit.id}/content/"
        )
        body = {
            "expected_document_version": 0,
            "schema_version": 1,
            "content": full_document(),
        }
        self.assertEqual(client.put(base, body, format="json").status_code, 403)

        authenticated = APIClient()
        authenticated.force_authenticate(user=owner)
        malicious = full_document()
        malicious["content"][3]["attrs"]["latex"] = r"\href{javascript:alert(1)}{x}"
        response = authenticated.put(
            base,
            {**body, "content": malicious},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(response.data["code"], "content_unsafe_math")

    def test_required_expected_version_and_payload_size_are_enforced(self) -> None:
        owner, organization, revision, _module, unit, *_ = self.unit_context()
        client = APIClient()
        client.force_authenticate(user=owner)
        base = (
            f"/api/v1/organizations/{organization.slug}/courses/"
            f"{revision.course.slug}/revisions/{revision.id}/units/{unit.id}/content/"
        )
        missing = client.put(
            base,
            {"schema_version": 1, "content": full_document()},
            format="json",
        )
        self.assertEqual(missing.status_code, 400, missing.data)
        too_large = client.put(
            base,
            {
                "expected_document_version": 0,
                "schema_version": 1,
                "content": {"type": "doc", "padding": "x" * (1024 * 1024)},
            },
            format="json",
        )
        self.assertEqual(too_large.status_code, 413, too_large.data)
