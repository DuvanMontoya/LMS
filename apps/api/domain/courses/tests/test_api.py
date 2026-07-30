from __future__ import annotations

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from domain.courses.choices import AuthoringStatus
from domain.courses.models import CourseRevision
from domain.courses.services import create_module, create_unit
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

    def test_mass_assignment_and_missing_expected_version_are_rejected_or_ignored(
        self,
    ) -> None:
        owner, organization, *_, revision = self.course_revision()
        client = self.client_for(owner)
        revision_url = (
            f"/api/v1/organizations/{organization.slug}/courses/"
            f"{revision.course.slug}/revisions/{revision.id}/"
        )
        missing_version = client.patch(
            revision_url,
            {"summary": "No debe guardarse."},
            format="json",
        )
        self.assertEqual(missing_version.status_code, 400, missing_version.data)

        updated = client.patch(
            revision_url,
            {
                "expected_version": revision.lock_version,
                "summary": "Sólo este campo público debe cambiar.",
                "lock_version": 999,
                "authoring_status": AuthoringStatus.APPROVED,
                "number": 99,
                "created_by": str(owner.id),
                "organization_id": str(organization.id),
            },
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        revision.refresh_from_db()
        self.assertEqual(revision.summary, "Sólo este campo público debe cambiar.")
        self.assertEqual(revision.lock_version, 2)
        self.assertEqual(revision.authoring_status, AuthoringStatus.DRAFT)
        self.assertEqual(revision.number, 1)

        module_response = client.post(
            f"{revision_url}modules/",
            {"expected_version": revision.lock_version, "title": "Módulo seguro"},
            format="json",
        )
        self.assertEqual(module_response.status_code, 201, module_response.data)
        module_id = module_response.data["id"]
        module_patch = client.patch(
            f"{revision_url}modules/{module_id}/",
            {
                "expected_version": module_response.data["lock_version"],
                "title": "Módulo actualizado",
                "position": 99,
                "status": "archived",
                "archived_at": "2026-01-01T00:00:00Z",
            },
            format="json",
        )
        self.assertEqual(module_patch.status_code, 200, module_patch.data)
        self.assertEqual(module_patch.data["position"], 1)
        self.assertEqual(module_patch.data["status"], "active")

    def test_outline_query_count_does_not_grow_with_structure(self) -> None:
        owner, organization, *_, revision = self.course_revision()
        module, revision = create_module(
            actor=owner,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
            title="Módulo uno",
        )
        _, revision = create_unit(
            actor=owner,
            organization=organization,
            module=module,
            expected_version=revision.lock_version,
            title="Unidad uno",
        )
        outline_url = (
            f"/api/v1/organizations/{organization.slug}/courses/"
            f"{revision.course.slug}/revisions/{revision.id}/outline/"
        )
        client = self.client_for(owner)
        with CaptureQueriesContext(connection) as first_queries:
            first_response = client.get(outline_url)
        self.assertEqual(first_response.status_code, 200, first_response.data)

        for index in range(2, 5):
            module, revision = create_module(
                actor=owner,
                organization=organization,
                revision=revision,
                expected_version=revision.lock_version,
                title=f"Módulo {index}",
            )
            _, revision = create_unit(
                actor=owner,
                organization=organization,
                module=module,
                expected_version=revision.lock_version,
                title=f"Unidad {index}",
            )
        with CaptureQueriesContext(connection) as expanded_queries:
            expanded_response = client.get(outline_url)
        self.assertEqual(expanded_response.status_code, 200, expanded_response.data)
        self.assertEqual(len(expanded_queries), len(first_queries))
