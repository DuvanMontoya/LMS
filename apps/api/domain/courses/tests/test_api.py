from __future__ import annotations

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from domain.catalog.services import assign_subject_teaching_responsibility
from domain.courses.choices import AuthoringStatus
from domain.courses.models import CourseRevision
from domain.courses.services import create_module, create_unit
from domain.organizations.choices import RoleCode
from domain.organizations.models import Membership

from .support import CourseFixtureMixin


class CourseApiTests(CourseFixtureMixin, TestCase):
    def test_patch_unit_saves_information_and_alignment_once(self) -> None:
        owner, organization, _subject, objective, topic, revision = (
            self.course_revision()
        )
        module, revision = create_module(
            actor=owner,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
            title="Módulo",
        )
        unit, revision = create_unit(
            actor=owner,
            organization=organization,
            module=module,
            expected_version=revision.lock_version,
            title="Lección",
        )
        response = self.client_for(owner).patch(
            f"/api/v1/organizations/{organization.slug}/courses/"
            f"{revision.course.slug}/revisions/{revision.id}/units/{unit.id}/",
            {
                "expected_version": revision.lock_version,
                "title": "Lección integralmente configurada",
                "summary": "Un único contrato de escritura.",
                "estimated_duration_minutes": 40,
                "topic_ids": [str(topic.id)],
                "learning_objective_ids": [str(objective.id)],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["lock_version"], revision.lock_version + 1)
        unit.refresh_from_db()
        self.assertEqual(unit.title, "Lección integralmente configurada")
        self.assertEqual(unit.topic_alignments.get().topic_id, topic.id)
        self.assertEqual(
            unit.objective_alignments.get().learning_objective_id, objective.id
        )

    def test_author_creates_courses_only_for_assigned_subjects(self) -> None:
        owner, organization, subject, objective, _topic = self.curriculum()
        author = self.member(
            owner, organization, RoleCode.AUTHOR, "responsible-author@example.test"
        )
        client = self.client_for(author)
        base = f"/api/v1/organizations/{organization.slug}/courses/"
        payload = {
            "slug": "curso-responsable",
            "title": "Curso responsable",
            "summary": "Curso limitado por responsabilidad académica.",
            "primary_subject_id": str(subject.id),
            "learning_objective_ids": [str(objective.id)],
        }
        denied = client.post(base, payload, format="json")
        self.assertEqual(denied.status_code, 403, denied.data)
        membership = Membership.objects.get(organization=organization, user=author)
        assign_subject_teaching_responsibility(
            actor=owner,
            organization=organization,
            subject=subject,
            membership=membership,
            starts_on=timezone.localdate(),
            ends_on=None,
            rationale="Autor responsable de la asignatura.",
        )
        created = client.post(base, payload, format="json")
        self.assertEqual(created.status_code, 201, created.data)

    def test_course_teaching_exceptions_are_administered_and_self_scoped(self) -> None:
        owner, organization, *_, revision = self.course_revision()
        instructor = self.member(
            owner, organization, RoleCode.INSTRUCTOR, "exception@example.test"
        )
        other = self.member(
            owner, organization, RoleCode.INSTRUCTOR, "other-exception@example.test"
        )
        membership = Membership.objects.get(organization=organization, user=instructor)
        base = f"/api/v1/organizations/{organization.slug}/courses/teaching-exceptions/"
        payload = {
            "course_id": str(revision.course_id),
            "membership_id": str(membership.id),
            "starts_on": timezone.localdate().isoformat(),
            "rationale": "Cobertura temporal y explícita de este curso.",
        }
        created = self.client_for(owner).post(base, payload, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(
            self.client_for(instructor).get(base).data[0]["id"], created.data["id"]
        )
        self.assertEqual(self.client_for(other).get(base).data, [])
        self.assertEqual(
            self.client_for(instructor).post(base, payload, format="json").status_code,
            403,
        )
        close_url = f"{base}{created.data['id']}/close/"
        self.assertEqual(
            self.client_for(instructor)
            .post(
                close_url,
                {"ended_on": timezone.localdate().isoformat()},
                format="json",
            )
            .status_code,
            403,
        )
        closed = self.client_for(owner).post(
            close_url,
            {"ended_on": timezone.localdate().isoformat()},
            format="json",
        )
        self.assertEqual(closed.status_code, 200, closed.data)
        self.assertIsNotNone(closed.data["ended_at"])

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
        owner, organization, subject, _objective, _topic, revision = (
            self.course_revision()
        )
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
        unassigned_instructor = self.member(
            owner,
            organization,
            RoleCode.INSTRUCTOR,
            "unassigned-instructor@example.test",
        )
        membership = Membership.objects.get(organization=organization, user=instructor)
        assign_subject_teaching_responsibility(
            actor=owner,
            organization=organization,
            subject=subject,
            membership=membership,
            starts_on=timezone.localdate(),
            ends_on=None,
            rationale="Responsabilidad docente vigente.",
        )
        client = self.client_for(instructor)
        base = f"/api/v1/organizations/{organization.slug}/courses/"
        self.assertEqual(
            self.client_for(unassigned_instructor).get(base).data["count"], 0
        )
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

    def test_unified_activity_authoring_order_rules_and_completion_policy(self) -> None:
        owner, organization, _subject, objective, _topic, revision = (
            self.course_revision()
        )
        client = self.client_for(owner)
        revision_url = (
            f"/api/v1/organizations/{organization.slug}/courses/"
            f"{revision.course.slug}/revisions/{revision.id}/"
        )
        module = client.post(
            f"{revision_url}modules/",
            {"expected_version": revision.lock_version, "title": "Secuencia mixta"},
            format="json",
        )
        self.assertEqual(module.status_code, 201, module.data)
        unit = client.post(
            f"{revision_url}modules/{module.data['id']}/units/",
            {
                "expected_version": module.data["lock_version"],
                "title": "Lección inicial",
            },
            format="json",
        )
        self.assertEqual(unit.status_code, 201, unit.data)
        activity_base = f"{revision_url}modules/{module.data['id']}/activities/"
        live = client.post(
            activity_base,
            {
                "expected_version": unit.data["lock_version"],
                "activity_type": "live_class",
                "title": "Encuentro sincrónico",
                "completion_method": "attendance",
                "minimum_attendance_basis_points": 7500,
                "required": True,
            },
            format="json",
        )
        self.assertEqual(live.status_code, 201, live.data)
        objectives = client.put(
            f"{revision_url}activities/{live.data['id']}/learning-objectives/",
            {
                "expected_version": live.data["lock_version"],
                "learning_objective_ids": [str(objective.id)],
            },
            format="json",
        )
        self.assertEqual(objectives.status_code, 200, objectives.data)
        rules = client.put(
            f"{revision_url}activities/{live.data['id']}/availability-rules/",
            {
                "expected_version": objectives.data["lock_version"],
                "rules": [
                    {
                        "rule_type": "activity_completed",
                        "prerequisite_activity_id": unit.data["id"],
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(rules.status_code, 200, rules.data)
        ordered = client.put(
            f"{activity_base}order/",
            {
                "expected_version": rules.data["lock_version"],
                "ordered_ids": [live.data["id"], unit.data["id"]],
            },
            format="json",
        )
        self.assertEqual(ordered.status_code, 200, ordered.data)
        policy = client.put(
            f"{revision_url}completion-policy/",
            {
                "expected_version": ordered.data["lock_version"],
                "require_required_activities": True,
                "minimum_grade_basis_points": 6000,
                "minimum_attendance_basis_points": 7500,
            },
            format="json",
        )
        self.assertEqual(policy.status_code, 200, policy.data)
        self.assertIsNotNone(policy.data["confirmed_at"])
        outline = client.get(f"{revision_url}outline/")
        self.assertEqual(outline.status_code, 200, outline.data)
        activities = outline.data["modules"][0]["activities"]
        self.assertEqual(
            [item["activity_type"] for item in activities],
            ["live_class", "lesson"],
        )
        self.assertEqual(
            activities[0]["availability_rules"][0]["prerequisite_activity_id"],
            unit.data["id"],
        )
        self.assertIn("units", outline.data["modules"][0])

    def test_non_lesson_activity_moves_between_modules_without_losing_identity(
        self,
    ) -> None:
        owner, organization, _subject, _objective, _topic, revision = (
            self.course_revision()
        )
        client = self.client_for(owner)
        revision_url = (
            f"/api/v1/organizations/{organization.slug}/courses/"
            f"{revision.course.slug}/revisions/{revision.id}/"
        )
        first_module = client.post(
            f"{revision_url}modules/",
            {"expected_version": revision.lock_version, "title": "Semana uno"},
            format="json",
        )
        self.assertEqual(first_module.status_code, 201, first_module.data)
        second_module = client.post(
            f"{revision_url}modules/",
            {
                "expected_version": first_module.data["lock_version"],
                "title": "Semana dos",
            },
            format="json",
        )
        self.assertEqual(second_module.status_code, 201, second_module.data)
        unit = client.post(
            f"{revision_url}modules/{first_module.data['id']}/units/",
            {
                "expected_version": second_module.data["lock_version"],
                "title": "Lección estable",
            },
            format="json",
        )
        self.assertEqual(unit.status_code, 201, unit.data)
        activity = client.post(
            f"{revision_url}modules/{first_module.data['id']}/activities/",
            {
                "expected_version": unit.data["lock_version"],
                "activity_type": "live_class",
                "title": "Clase que cambia de semana",
                "completion_method": "attendance",
                "minimum_attendance_basis_points": 7500,
            },
            format="json",
        )
        self.assertEqual(activity.status_code, 201, activity.data)

        moved = client.post(
            f"{revision_url}activities/{activity.data['id']}/move/",
            {
                "expected_version": activity.data["lock_version"],
                "target_module_id": second_module.data["id"],
            },
            format="json",
        )
        self.assertEqual(moved.status_code, 200, moved.data)
        self.assertEqual(moved.data["id"], activity.data["id"])
        self.assertEqual(moved.data["module_id"], second_module.data["id"])
        self.assertEqual(moved.data["position"], 1)

        lesson_move = client.post(
            f"{revision_url}activities/{unit.data['id']}/move/",
            {
                "expected_version": moved.data["lock_version"],
                "target_module_id": second_module.data["id"],
            },
            format="json",
        )
        self.assertEqual(lesson_move.status_code, 400, lesson_move.data)

        outline = client.get(f"{revision_url}outline/")
        self.assertEqual(outline.status_code, 200, outline.data)
        self.assertEqual(
            [item["title"] for item in outline.data["modules"][0]["activities"]],
            ["Lección estable"],
        )
        self.assertEqual(
            [item["title"] for item in outline.data["modules"][1]["activities"]],
            ["Clase que cambia de semana"],
        )

    def test_grading_scheme_weights_assessment_activities_and_rejects_bad_totals(
        self,
    ) -> None:
        owner, organization, _subject, _objective, _topic, revision = (
            self.course_revision()
        )
        client = self.client_for(owner)
        revision_url = (
            f"/api/v1/organizations/{organization.slug}/courses/"
            f"{revision.course.slug}/revisions/{revision.id}/"
        )
        module = client.post(
            f"{revision_url}modules/",
            {"expected_version": revision.lock_version, "title": "Evaluaciones"},
            format="json",
        )
        assessment = client.post(
            f"{revision_url}modules/{module.data['id']}/activities/",
            {
                "expected_version": module.data["lock_version"],
                "activity_type": "assessment",
                "title": "Parcial",
                "completion_method": "pass",
                "minimum_grade_basis_points": 6000,
            },
            format="json",
        )
        self.assertEqual(assessment.status_code, 201, assessment.data)
        url = f"{revision_url}grading-scheme/"
        invalid = client.put(
            url,
            {
                "expected_version": assessment.data["lock_version"],
                "categories": [
                    {
                        "code": "parciales",
                        "title": "Parciales",
                        "weight_basis_points": 9000,
                        "activities": [
                            {
                                "activity_id": assessment.data["id"],
                                "weight_basis_points": 10000,
                                "required": True,
                            }
                        ],
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)
        created = client.put(
            url,
            {
                "expected_version": assessment.data["lock_version"],
                "categories": [
                    {
                        "code": "parciales",
                        "title": "Parciales",
                        "weight_basis_points": 10000,
                        "activities": [
                            {
                                "activity_id": assessment.data["id"],
                                "weight_basis_points": 10000,
                                "required": True,
                            }
                        ],
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(created.status_code, 200, created.data)
        self.assertEqual(created.data["categories"][0]["code"], "parciales")
        self.assertEqual(
            created.data["categories"][0]["activities"][0]["activity_id"],
            assessment.data["id"],
        )
