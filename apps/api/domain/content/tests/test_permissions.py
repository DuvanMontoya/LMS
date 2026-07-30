from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from domain.content.exceptions import ContentAccessDenied, ContentNotEditable
from domain.content.services import save_unit_content
from domain.courses.choices import AuthoringStatus
from domain.courses.models import CourseRevision
from domain.organizations.choices import RoleCode

from .support import ContentFixtureMixin, full_document


class ContentPermissionTests(ContentFixtureMixin, TestCase):
    def test_author_can_save_draft_and_changes_requested_only(self) -> None:
        owner, organization, revision, _module, unit, *_ = self.unit_context()
        author = self.member(
            owner, organization, RoleCode.AUTHOR, "author@example.test"
        )
        first = save_unit_content(
            actor=author,
            organization=organization,
            revision=revision,
            unit=unit,
            expected_document_version=0,
            schema_version=1,
            content=full_document(),
        )
        self.assertEqual(first.version.number, 1)
        for status in (
            AuthoringStatus.IN_REVIEW,
            AuthoringStatus.APPROVED,
        ):
            CourseRevision.objects.filter(pk=revision.pk).update(
                authoring_status=status
            )
            revision.refresh_from_db()
            with self.assertRaises(ContentNotEditable):
                save_unit_content(
                    actor=author,
                    organization=organization,
                    revision=revision,
                    unit=unit,
                    expected_document_version=1,
                    schema_version=1,
                    content=full_document(),
                )
        CourseRevision.objects.filter(pk=revision.pk).update(
            authoring_status=AuthoringStatus.CHANGES_REQUESTED
        )
        revision.refresh_from_db()
        changed = full_document()
        changed["content"][0]["content"][0]["text"] = "Cambio solicitado"
        second = save_unit_content(
            actor=author,
            organization=organization,
            revision=revision,
            unit=unit,
            expected_document_version=1,
            schema_version=1,
            content=changed,
        )
        self.assertEqual(second.version.number, 2)

    def test_reviewer_instructor_learner_and_staff_do_not_edit(self) -> None:
        owner, organization, revision, _module, unit, *_ = self.unit_context()
        actors = [
            self.member(
                owner, organization, RoleCode.REVIEWER, "reviewer@example.test"
            ),
            self.member(
                owner,
                organization,
                RoleCode.INSTRUCTOR,
                "instructor@example.test",
            ),
            self.member(owner, organization, RoleCode.LEARNER, "learner@example.test"),
        ]
        staff = self.user("staff@example.test")
        staff.is_staff = True
        staff.save(update_fields=["is_staff"])
        actors.append(staff)
        for actor in actors:
            with self.subTest(actor=actor.email):
                with self.assertRaises(ContentAccessDenied):
                    save_unit_content(
                        actor=actor,
                        organization=organization,
                        revision=revision,
                        unit=unit,
                        expected_document_version=0,
                        schema_version=1,
                        content=full_document(),
                    )

    def test_explicit_active_superuser_bypass_and_inactive_denial(self) -> None:
        _owner, organization, revision, _module, unit, *_ = self.unit_context()
        operator = get_user_model().objects.create_superuser(
            email="operator@example.test", password="Password123!x"
        )
        saved = save_unit_content(
            actor=operator,
            organization=organization,
            revision=revision,
            unit=unit,
            expected_document_version=0,
            schema_version=1,
            content=full_document(),
        )
        self.assertEqual(saved.version.number, 1)
        operator.is_active = False
        operator.save(update_fields=["is_active"])
        with self.assertRaises(ContentAccessDenied):
            save_unit_content(
                actor=operator,
                organization=organization,
                revision=revision,
                unit=unit,
                expected_document_version=1,
                schema_version=1,
                content=full_document(),
            )

    def test_learner_and_cross_organization_paths_are_not_found(self) -> None:
        owner, organization, revision, _module, unit, *_ = self.unit_context()
        learner = self.member(
            owner, organization, RoleCode.LEARNER, "learner-api@example.test"
        )
        client = APIClient()
        client.force_authenticate(user=learner)
        base = (
            f"/api/v1/organizations/{organization.slug}/courses/"
            f"{revision.course.slug}/revisions/{revision.id}/units/{unit.id}/content/"
        )
        self.assertEqual(client.get(base).status_code, 404)

        foreign_owner, foreign_organization, *_ = self.curriculum("-foreign")
        client.force_authenticate(user=foreign_owner)
        cross = base.replace(organization.slug, foreign_organization.slug)
        self.assertEqual(client.get(cross).status_code, 404)
