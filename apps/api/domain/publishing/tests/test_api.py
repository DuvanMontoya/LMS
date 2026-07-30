from __future__ import annotations

from django.test import TestCase
from rest_framework.test import APIClient

from domain.organizations.choices import RoleCode
from domain.publishing.services import withdraw_publication

from .support import PublishingFixtureMixin


class PublicationApiTests(PublishingFixtureMixin, TestCase):
    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_owner_history_library_reader_and_method_boundaries(self) -> None:
        owner, organization, revision, _module, unit, *_, publication, release = (
            self.published_context()
        )
        client = self.client_for(owner)
        course_base = (
            f"/api/v1/organizations/{organization.slug}/courses/{revision.course.slug}/"
        )
        library_base = f"/api/v1/organizations/{organization.slug}/library/courses/"
        state = client.get(f"{course_base}publication/")
        self.assertEqual(state.status_code, 200, state.data)
        self.assertEqual(state["Cache-Control"], "private, no-store")
        history = client.get(f"{course_base}releases/")
        self.assertEqual(history.status_code, 200, history.data)
        self.assertEqual(len(history.data), 1)
        self.assertNotIn("snapshot", history.data[0])
        detail = client.get(f"{course_base}releases/1/")
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertNotIn("snapshot", detail.data)
        verification = client.get(f"{course_base}releases/1/verify/")
        self.assertTrue(verification.data["valid"])
        library = client.get(library_base)
        self.assertEqual(library.status_code, 200, library.data)
        self.assertNotIn("snapshot_digest", library.data[0])
        reader = client.get(f"{library_base}{revision.course.slug}/units/{unit.id}/")
        self.assertEqual(reader.status_code, 200, reader.data)
        self.assertEqual(reader.data["release_number"], release.number)
        self.assertEqual(reader.data["unit"]["content"]["document"]["type"], "doc")
        self.assertEqual(client.patch(f"{course_base}releases/1/").status_code, 405)
        self.assertEqual(client.delete(f"{course_base}releases/1/").status_code, 405)

        withdrawn = withdraw_publication(
            actor=owner,
            organization=organization,
            course=revision.course,
            expected_publication_version=publication.lock_version,
            note="Retiro para prueba.",
        )
        self.assertEqual(
            client.get(f"{library_base}{revision.course.slug}/").status_code,
            404,
        )
        historical = client.get(f"{course_base}releases/1/")
        self.assertEqual(historical.status_code, 200, historical.data)
        self.assertEqual(historical["Cache-Control"], "private, no-store")
        self.assertEqual(withdrawn.current_release_id, release.id)

    def test_role_matrix_and_cross_organization_are_fail_closed(self) -> None:
        owner, organization, revision, *_ = self.approved_revision_context()
        learner = self.member(
            owner, organization, RoleCode.LEARNER, "learner-pub@example.test"
        )
        author = self.member(
            owner, organization, RoleCode.AUTHOR, "author-pub@example.test"
        )
        other_owner, other_organization, *_ = self.curriculum("-other-pub")
        course_base = (
            f"/api/v1/organizations/{organization.slug}/courses/{revision.course.slug}/"
        )
        publish_url = f"{course_base}revisions/{revision.id}/publish/"
        denied = self.client_for(author).post(
            publish_url, {"expected_publication_version": 0}, format="json"
        )
        self.assertEqual(denied.status_code, 403, denied.data)
        self.assertEqual(
            self.client_for(learner).get(f"{course_base}publication/").status_code,
            403,
        )
        hidden = self.client_for(other_owner).get(
            f"/api/v1/organizations/{other_organization.slug}/courses/"
            f"{revision.course.slug}/publication/"
        )
        self.assertEqual(hidden.status_code, 404, hidden.data)
