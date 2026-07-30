from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import DatabaseError, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from domain.learning.services import enroll_member
from domain.organizations.models import Membership

from ..choices import AttemptStatus
from ..exceptions import AssessmentConflict, AssessmentInvalid, AttemptExpired
from ..models import AssessmentVersion, Attempt, AttemptEvent, QuestionVersion
from ..services import (
    activate_delivery,
    add_assessment_section,
    assessment_readiness,
    assign_delivery,
    assign_delivery_batch,
    create_assessment_revision_from_version,
    create_delivery,
    reorder_assessment_sections,
    save_response,
    start_attempt,
    submit_attempt,
    update_assessment_item,
    update_assessment_revision,
    update_assessment_section,
)
from .support import AssessmentFixtureMixin


class AuthoringWorkflowTests(AssessmentFixtureMixin, TestCase):
    def test_approval_materializes_separate_public_and_secret_snapshots(self) -> None:
        context = self.assessment_context()
        version = context["assessment_version"]
        self.assertEqual(assessment_readiness(context["assessment_revision"]), ())
        self.assertEqual(version.maximum_score, Decimal("2.000"))
        public_item = version.public_snapshot["sections"][0]["items"][0]
        self.assertNotIn("grading", public_item)
        self.assertNotIn("grading", public_item["question"])
        self.assertNotIn("correct_option_ids", str(version.public_snapshot))
        self.assertIn("correct_option_ids", str(version.grading_snapshot))

    def test_stale_expected_version_is_rejected_without_partial_write(self) -> None:
        context = self.assessment_context()
        approved = context["assessment_revision"]
        with self.assertRaises(AssessmentConflict):
            update_assessment_revision(
                actor=context["owner"],
                revision=approved,
                expected_version=approved.lock_version - 1,
                values={"title": "No debe persistir"},
            )
        approved.refresh_from_db()
        self.assertEqual(approved.title, "Diagnóstico de álgebra")

    def test_editable_composition_updates_and_reorders_with_revision_lock(self) -> None:
        context = self.assessment_context()
        revision = create_assessment_revision_from_version(
            actor=context["owner"], version=context["assessment_version"]
        )
        first = revision.sections.get()
        revision, second = add_assessment_section(
            actor=context["owner"],
            revision=revision,
            expected_version=revision.lock_version,
            title="Aplicaciones",
        )
        revision = reorder_assessment_sections(
            actor=context["owner"],
            revision=revision,
            expected_version=revision.lock_version,
            section_ids=[second.id, first.id],
        )
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((second.position, first.position), (1, 2))
        revision, second = update_assessment_section(
            actor=context["owner"],
            revision=revision,
            section=second,
            expected_version=revision.lock_version,
            title="Aplicaciones algebraicas",
            instructions="Resuelve con precisión.",
        )
        item = first.items.get()
        revision, item = update_assessment_item(
            actor=context["owner"],
            revision=revision,
            item=item,
            expected_version=revision.lock_version,
            points=Decimal("3.500"),
            required=False,
            objectives=[context["objective"]],
        )
        self.assertEqual(second.title, "Aplicaciones algebraicas")
        self.assertEqual(item.points, Decimal("3.500"))
        self.assertFalse(item.required)
        self.assertEqual(revision.lock_version, 5)


class AttemptWorkflowTests(AssessmentFixtureMixin, TestCase):
    def test_batch_assignment_is_all_or_nothing(self) -> None:
        context = self.assessment_context(with_learning=True)
        owner = context["owner"]
        organization = context["organization"]
        enrollment = context["enrollment"]
        second_user = get_user_model().objects.create_user(
            email="assessment-batch-invalid@example.test",
            password="AssessmentBatchPassword!42",
        )
        second_membership = Membership.objects.create(
            organization=organization,
            user=second_user,
            status_changed_by=owner,
            status_changed_at=timezone.now(),
        )
        second_enrollment = enroll_member(
            actor=owner,
            organization=organization,
            course=enrollment.course,
            membership=second_membership,
            release=context["release"],
        )
        Membership.objects.filter(pk=second_membership.pk).update(
            status="suspended",
            status_changed_by=owner,
            status_changed_at=timezone.now(),
            suspended_at=timezone.now(),
        )
        delivery = create_delivery(
            actor=owner,
            organization=organization,
            assessment_version=context["assessment_version"],
            name="Lote atómico",
            course_release=context["release"],
        )
        delivery = activate_delivery(
            actor=owner,
            delivery=delivery,
            expected_version=delivery.lock_version,
        )
        with self.assertRaises(AssessmentInvalid):
            assign_delivery_batch(
                actor=owner,
                delivery=delivery,
                release_assignments=[
                    enrollment.current_release_assignment,
                    second_enrollment.current_release_assignment,
                ],
            )
        self.assertFalse(delivery.assignments.exists())

    def test_learner_attempt_is_release_pinned_and_deterministically_graded(
        self,
    ) -> None:
        context = self.assessment_context(with_learning=True)
        owner = context["owner"]
        learner = context["learner"]
        enrollment = context["enrollment"]
        delivery = create_delivery(
            actor=owner,
            organization=context["organization"],
            assessment_version=context["assessment_version"],
            name="Diagnóstico asignado",
            course_release=context["release"],
        )
        delivery = activate_delivery(
            actor=owner,
            delivery=delivery,
            expected_version=delivery.lock_version,
        )
        assignment = assign_delivery(
            actor=owner,
            delivery=delivery,
            release_assignment=enrollment.current_release_assignment,
        )
        attempt = start_attempt(actor=learner, assignment=assignment)
        item = attempt.items.get()
        attempt, _ = save_response(
            actor=learner,
            attempt=attempt,
            attempt_item=item,
            expected_version=attempt.lock_version,
            payload={
                "schema_version": 1,
                "type": "single_choice",
                "value": "b",
            },
        )
        attempt = submit_attempt(
            actor=learner,
            attempt=attempt,
            expected_version=attempt.lock_version,
        )
        self.assertEqual(attempt.status, AttemptStatus.GRADED)
        self.assertEqual(attempt.total_score, Decimal("2.000"))
        self.assertEqual(attempt.basis_points, 10000)
        self.assertTrue(attempt.passed)
        self.assertEqual(attempt.assessment_version, context["assessment_version"])
        self.assertNotIn("grading", item.public_snapshot)

    def test_expired_attempt_rejects_save_but_allows_final_submit(self) -> None:
        context = self.assessment_context(with_learning=True)
        delivery = create_delivery(
            actor=context["owner"],
            organization=context["organization"],
            assessment_version=context["assessment_version"],
            name="Entrega temporizada",
            course_release=context["release"],
        )
        delivery = activate_delivery(
            actor=context["owner"],
            delivery=delivery,
            expected_version=delivery.lock_version,
        )
        assignment = assign_delivery(
            actor=context["owner"],
            delivery=delivery,
            release_assignment=context["enrollment"].current_release_assignment,
        )
        attempt = start_attempt(actor=context["learner"], assignment=assignment)
        Attempt.objects.filter(pk=attempt.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        attempt.refresh_from_db()
        with self.assertRaises(AttemptExpired):
            save_response(
                actor=context["learner"],
                attempt=attempt,
                attempt_item=attempt.items.get(),
                expected_version=attempt.lock_version,
                payload={
                    "schema_version": 1,
                    "type": "single_choice",
                    "value": "b",
                },
            )
        submitted = submit_attempt(
            actor=context["learner"],
            attempt=attempt,
            expected_version=attempt.lock_version,
        )
        self.assertEqual(submitted.status, AttemptStatus.GRADED)
        self.assertEqual(submitted.total_score, Decimal("0.000"))


class DatabaseImmutabilityTests(AssessmentFixtureMixin, TransactionTestCase):
    reset_sequences = True

    def test_versions_and_events_reject_database_update_and_delete(self) -> None:
        context = self.assessment_context()
        with self.assertRaises(DatabaseError), transaction.atomic():
            QuestionVersion.objects.filter(pk=context["question_version"].pk).update(
                public={}
            )
        with self.assertRaises(DatabaseError), transaction.atomic():
            AssessmentVersion.objects.filter(
                pk=context["assessment_version"].pk
            ).delete()

    def test_attempt_events_are_append_only_at_database_level(self) -> None:
        context = self.assessment_context(with_learning=True)
        delivery = create_delivery(
            actor=context["owner"],
            organization=context["organization"],
            assessment_version=context["assessment_version"],
            name="Entrega",
            course_release=context["release"],
        )
        delivery = activate_delivery(
            actor=context["owner"],
            delivery=delivery,
            expected_version=delivery.lock_version,
        )
        assignment = assign_delivery(
            actor=context["owner"],
            delivery=delivery,
            release_assignment=context["enrollment"].current_release_assignment,
        )
        start_attempt(actor=context["learner"], assignment=assignment)
        with self.assertRaises(DatabaseError), transaction.atomic():
            AttemptEvent.objects.all().update(payload={"tampered": True})
