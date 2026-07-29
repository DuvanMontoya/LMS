from __future__ import annotations

from django.test import TestCase
from rest_framework.test import APIClient

from domain.courses.choices import AuthoringStatus
from domain.courses.models import CourseRevision
from domain.organizations.choices import RoleCode

from .support import CourseFixtureMixin


class CourseApiTests(CourseFixtureMixin, TestCase):
    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_create_list_structure_conflict_and_idor(self) -> None:
        owner, organization, subject, objective, _ = self.curriculum()
        client = self.client_for(owner)
        base = f"/api/v1/organizations/{organization.slug}/courses/"
        created = client.post(
            base,
            {
                "slug": "curso-api",
                "title": "Curso API",
                "summary": "Resumen del curso.",
                "primary_subject_id": str(subject.id),
                "learning_objective_ids": [str(objective.id)],
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        revision_id = created.data["id"]
        self.assertEqual(client.get(f"{base}?search=API").data["count"], 1)
        revision_url = f"{base}curso-api/revisions/{revision_id}/"
        updated = client.patch(
            revision_url,
            {"expected_version": 1, "summary": "Resumen actualizado."},
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        conflict = client.patch(
            revision_url,
            {"expected_version": 1, "summary": "Cambio obsoleto."},
            format="json",
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.data["code"], "revision_conflict")
        modules = client.post(
            f"{revision_url}modules/",
            {"expected_version": 2, "title": "Módulo uno"},
            format="json",
        )
        self.assertEqual(modules.status_code, 201, modules.data)
        self.assertNotIn("position", {"expected_version": 2, "title": "Módulo uno"})
        other_owner, other_org, *_ = self.curriculum("-other")
        self.assertEqual(
            self.client_for(other_owner)
            .get(f"/api/v1/organizations/{other_org.slug}/courses/curso-api/")
            .status_code,
            404,
        )

    def test_role_visibility_and_no_delete_surface(self) -> None:
        owner, organization, *_, revision = self.course_revision()
        instructor = self.member(
            owner,
            organization,
            RoleCode.INSTRUCTOR,
            "instructor@example.test",
        )
        learner = self.member(
            owner, organization, RoleCode.LEARNER, "learner@example.test"
        )
        base = f"/api/v1/organizations/{organization.slug}/courses/"
        self.assertEqual(self.client_for(instructor).get(base).data["count"], 0)
        self.assertEqual(self.client_for(learner).get(base).status_code, 403)
        self.assertEqual(
            self.client_for(owner).delete(f"{base}{revision.course.slug}/").status_code,
            405,
        )

    def test_instructor_filters_cannot_infer_a_newer_draft(self) -> None:
        owner, organization, *_, revision = self.course_revision()
        revision.authoring_status = AuthoringStatus.APPROVED
        revision.title = "Título aprobado"
        revision.summary = "Resumen visible"
        revision.save(
            update_fields=["authoring_status", "title", "summary", "updated_at"]
        )
        CourseRevision.objects.create(
            course=revision.course,
            number=2,
            based_on_revision=revision,
            title="Borrador confidencial",
            summary="Secreto institucional",
            status_changed_by=owner,
            created_by=owner,
            updated_by=owner,
        )
        instructor = self.member(
            owner,
            organization,
            RoleCode.INSTRUCTOR,
            "instructor-filter@example.test",
        )
        client = self.client_for(instructor)
        base = f"/api/v1/organizations/{organization.slug}/courses/"
        self.assertEqual(client.get(f"{base}?search=confidencial").data["count"], 0)
        visible = client.get(f"{base}?search=aprobado")
        self.assertEqual(visible.data["count"], 1)
        self.assertEqual(visible.data["results"][0]["title"], "Título aprobado")
        self.assertEqual(client.get(f"{base}?authoring_status=draft").data["count"], 0)
