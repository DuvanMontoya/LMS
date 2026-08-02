from __future__ import annotations

from datetime import date

from django.test import TestCase

from domain.catalog.models import CatalogStatus
from domain.catalog.services import create_learning_objective, create_subject
from domain.courses.exceptions import (
    CourseAccessDenied,
    CourseCrossOrganizationRelation,
    CourseCurriculumAlignmentInvalid,
    CourseRevisionNotReady,
)
from domain.courses.selectors import courses_visible_to_actor
from domain.courses.services import (
    assign_course_teaching_exception,
    close_course_teaching_exception,
    create_module,
    create_unit,
    replace_unit_learning_objectives,
    replace_unit_topics,
    submit_revision_for_review,
)
from domain.organizations.choices import RoleCode
from domain.organizations.models import Membership

from .support import CourseFixtureMixin


class CourseIntegrityTests(CourseFixtureMixin, TestCase):
    def test_course_exception_scopes_authoring_without_granting_group_access(
        self,
    ) -> None:
        owner, organization, *_, revision = self.course_revision()
        author = self.member(
            owner, organization, RoleCode.AUTHOR, "scoped-author@example.test"
        )
        membership = Membership.objects.get(organization=organization, user=author)
        self.assertFalse(
            courses_visible_to_actor(author, organization)
            .filter(pk=revision.course_id)
            .exists()
        )
        with self.assertRaises(CourseAccessDenied):
            create_module(
                actor=author,
                organization=organization,
                revision=revision,
                expected_version=revision.lock_version,
                title="Bypass sin responsabilidad",
            )
        exception = assign_course_teaching_exception(
            actor=owner,
            organization=organization,
            course=revision.course,
            membership=membership,
            starts_on=date.today(),
            ends_on=None,
            rationale="Excepción por experiencia específica.",
        )
        self.assertTrue(
            courses_visible_to_actor(author, organization)
            .filter(pk=revision.course_id)
            .exists()
        )
        _, revision = create_module(
            actor=author,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
            title="Módulo autorizado por excepción",
        )
        close_course_teaching_exception(
            actor=owner, exception=exception, ended_on=date.today()
        )
        self.assertFalse(
            courses_visible_to_actor(author, organization)
            .filter(pk=revision.course_id)
            .exists()
        )
        with self.assertRaises(CourseAccessDenied):
            create_module(
                actor=author,
                organization=organization,
                revision=revision,
                expected_version=revision.lock_version,
                title="Bypass tras cierre",
            )

    def test_readiness_identifies_module_and_unit_gaps(self) -> None:
        owner, organization, *_, revision = self.course_revision()
        module, revision = create_module(
            actor=owner,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
            title="Módulo sin unidad",
        )
        with self.assertRaises(CourseRevisionNotReady) as module_error:
            submit_revision_for_review(
                actor=owner,
                organization=organization,
                revision=revision,
                expected_version=revision.lock_version,
            )
        self.assertIn(
            "module_without_unit",
            {issue["code"] for issue in module_error.exception.issues},
        )

        _, revision = create_unit(
            actor=owner,
            organization=organization,
            module=module,
            expected_version=revision.lock_version,
            title="Unidad sin objetivo",
        )
        with self.assertRaises(CourseRevisionNotReady) as unit_error:
            submit_revision_for_review(
                actor=owner,
                organization=organization,
                revision=revision,
                expected_version=revision.lock_version,
            )
        self.assertIn(
            "unit_without_learning_objective",
            {issue["code"] for issue in unit_error.exception.issues},
        )

    def test_archived_catalog_references_block_review(self) -> None:
        owner, organization, _, objective, topic, revision = self.course_revision()
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
            title="Unidad",
        )
        revision = replace_unit_topics(
            actor=owner,
            organization=organization,
            unit=unit,
            expected_version=revision.lock_version,
            topics=[topic],
        )
        revision = replace_unit_learning_objectives(
            actor=owner,
            organization=organization,
            unit=unit,
            expected_version=revision.lock_version,
            learning_objectives=[objective],
        )
        type(topic).objects.filter(pk=topic.pk).update(status=CatalogStatus.ARCHIVED)
        type(objective).objects.filter(pk=objective.pk).update(
            status=CatalogStatus.ARCHIVED
        )
        with self.assertRaises(CourseRevisionNotReady) as error:
            submit_revision_for_review(
                actor=owner,
                organization=organization,
                revision=revision,
                expected_version=revision.lock_version,
            )
        codes = {issue["code"] for issue in error.exception.issues}
        self.assertIn("archived_learning_objective", codes)
        self.assertIn("archived_unit_learning_objective", codes)
        self.assertIn("archived_unit_topic", codes)

    def test_cross_organization_and_unaligned_objectives_are_rejected(self) -> None:
        owner, organization, subject, _, _, revision = self.course_revision()
        other_owner, _, _, other_objective, other_topic = self.curriculum("-other")
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
            title="Unidad",
        )
        with self.assertRaises(CourseCrossOrganizationRelation):
            replace_unit_topics(
                actor=owner,
                organization=organization,
                unit=unit,
                expected_version=revision.lock_version,
                topics=[other_topic],
            )
        with self.assertRaises(CourseCrossOrganizationRelation):
            replace_unit_learning_objectives(
                actor=owner,
                organization=organization,
                unit=unit,
                expected_version=revision.lock_version,
                learning_objectives=[other_objective],
            )

        unaligned_subject = create_subject(
            actor=owner,
            organization=organization,
            discipline=subject.discipline,
            name="Geometría",
            slug="geometria",
            description="",
        )
        unaligned_objective = create_learning_objective(
            actor=owner,
            organization=organization,
            subject=unaligned_subject,
            code="GEO-01",
            statement="Construir relaciones geométricas.",
            description="",
            cognitive_level="apply",
        )
        with self.assertRaises(CourseCurriculumAlignmentInvalid):
            replace_unit_learning_objectives(
                actor=owner,
                organization=organization,
                unit=unit,
                expected_version=revision.lock_version,
                learning_objectives=[unaligned_objective],
            )
        self.assertNotEqual(other_owner.id, owner.id)
