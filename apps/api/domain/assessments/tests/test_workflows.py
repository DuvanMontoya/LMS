from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import DatabaseError, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from domain.catalog.services import assign_subject_teaching_responsibility
from domain.courses.choices import ActivityCompletionMethod, ActivityType
from domain.courses.services import (
    GradeCategoryInput,
    GradedActivityInput,
    approve_revision,
    confirm_completion_policy,
    create_activity,
    replace_activity_learning_objectives,
    replace_grading_scheme,
    submit_revision_for_review,
)
from domain.learning.choices import AcademicPeriodType, ActivityProgressStatus
from domain.learning.models import ActivityProgress
from domain.learning.selectors import progress_payload
from domain.learning.services import (
    create_academic_period,
    create_cohort,
    enroll_member,
)
from domain.organizations.choices import RoleCode
from domain.organizations.models import Membership
from domain.publishing.services import (
    create_draft_from_release,
    publish_approved_revision,
)

from ..api.serializers import LearnerDeliverySerializer
from ..choices import AttemptStatus
from ..course_activities import bind_assessment_activity
from ..exceptions import AssessmentConflict, AssessmentInvalid, AttemptExpired
from ..models import (
    AssessmentDelivery,
    AssessmentVersion,
    Attempt,
    AttemptEvent,
    QuestionVersion,
)
from ..services import (
    activate_delivery,
    add_assessment_section,
    assessment_readiness,
    assign_delivery,
    assign_delivery_batch,
    create_assessment_revision_from_version,
    create_delivery,
    materialize_course_group_assessments,
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
    def test_mixed_release_assessment_updates_progress_and_calendar(self) -> None:
        context = self.assessment_context(with_learning=True)
        owner = context["owner"]
        organization = context["organization"]
        release = context["release"]
        publication = release.course.publication
        draft = create_draft_from_release(
            actor=owner,
            organization=organization,
            course=release.course,
            release_number=release.number,
            expected_publication_version=publication.lock_version,
        )
        module = draft.modules.get(position=1)
        activity, draft = create_activity(
            actor=owner,
            organization=organization,
            module=module,
            expected_version=draft.lock_version,
            activity_type=ActivityType.ASSESSMENT,
            title="Parcial de cierre",
            completion_method=ActivityCompletionMethod.PASS,
            minimum_grade_basis_points=6000,
        )
        draft = replace_activity_learning_objectives(
            actor=owner,
            organization=organization,
            activity=activity,
            expected_version=draft.lock_version,
            learning_objectives=[context["objective"]],
        )
        _binding, next_lock = bind_assessment_activity(
            actor=owner,
            organization=organization,
            activity=activity,
            assessment_version=context["assessment_version"],
            expected_revision_version=draft.lock_version,
        )
        draft.refresh_from_db()
        self.assertEqual(draft.lock_version, next_lock)
        _categories, draft = replace_grading_scheme(
            actor=owner,
            organization=organization,
            revision=draft,
            expected_version=draft.lock_version,
            categories=[
                GradeCategoryInput(
                    code="parciales",
                    title="Parciales",
                    weight_basis_points=10000,
                    activities=[
                        GradedActivityInput(
                            activity=activity,
                            weight_basis_points=10000,
                            required=True,
                        )
                    ],
                )
            ],
        )
        _, draft = confirm_completion_policy(
            actor=owner,
            organization=organization,
            revision=draft,
            expected_version=draft.lock_version,
            require_required_activities=True,
            minimum_grade_basis_points=6000,
            minimum_attendance_basis_points=None,
        )
        draft = submit_revision_for_review(
            actor=owner,
            organization=organization,
            revision=draft,
            expected_version=draft.lock_version,
        )
        reviewer = self.member(
            owner,
            organization,
            RoleCode.REVIEWER,
            "mixed-release-reviewer@example.test",
        )
        assign_subject_teaching_responsibility(
            actor=owner,
            organization=organization,
            subject=draft.subject_alignments.get(position=1).subject,
            membership=Membership.objects.get(organization=organization, user=reviewer),
            starts_on=date(2020, 1, 1),
            ends_on=None,
            rationale="Revisión académica explícita del flujo mixto.",
        )
        draft = approve_revision(
            actor=reviewer,
            organization=organization,
            revision=draft,
            expected_version=draft.lock_version,
        )
        result = publish_approved_revision(
            actor=owner,
            organization=organization,
            course=release.course,
            revision=draft,
            expected_publication_version=publication.lock_version,
        )
        period = create_academic_period(
            actor=owner,
            organization=organization,
            name="Periodo integrado",
            slug="periodo-integrado",
            period_type=AcademicPeriodType.TERM,
            starts_on=timezone.localdate(),
            ends_on=timezone.localdate() + timedelta(days=120),
        )
        cohort = create_cohort(
            actor=owner,
            organization=organization,
            course=release.course,
            release=result.release,
            academic_period=period,
            name="Grupo integrado",
            slug="grupo-integrado",
        )
        learner = self.member(
            owner,
            organization,
            RoleCode.LEARNER,
            "mixed-release-learner@example.test",
        )
        membership = Membership.objects.get(organization=organization, user=learner)
        enrollment = enroll_member(
            actor=owner,
            organization=organization,
            course=release.course,
            membership=membership,
            cohort=cohort,
            expected_cohort_version=cohort.lock_version,
        )
        group_activity = cohort.activity_instances.get(
            source_activity_id=activity.id,
            activity_type=ActivityType.ASSESSMENT,
        )
        now = timezone.now()
        materialized = materialize_course_group_assessments(
            actor=owner,
            organization=organization,
            course_group=cohort,
        )
        repeated = materialize_course_group_assessments(
            actor=owner,
            organization=organization,
            course_group=cohort,
        )
        self.assertEqual(
            materialized,
            {
                "created_delivery_count": 1,
                "already_materialized_count": 0,
                "created_assignment_count": 1,
                "already_assigned_count": 0,
            },
        )
        self.assertEqual(repeated["created_delivery_count"], 0)
        self.assertEqual(repeated["already_materialized_count"], 1)
        self.assertEqual(repeated["created_assignment_count"], 0)
        self.assertEqual(repeated["already_assigned_count"], 1)
        delivery = AssessmentDelivery.objects.get(course_group_activity=group_activity)
        delivery.opens_at = now - timedelta(minutes=1)
        delivery.closes_at = now + timedelta(hours=1)
        delivery.save(update_fields=("opens_at", "closes_at", "updated_at"))
        assignment = delivery.assignments.get(
            release_assignment=enrollment.current_release_assignment
        )
        learner_payload = LearnerDeliverySerializer(assignment).data
        version = context["assessment_version"]
        self.assertEqual(learner_payload["description"], version.description)
        self.assertEqual(learner_payload["item_count"], version.item_count)
        self.assertEqual(
            learner_payload["time_limit_minutes"], version.time_limit_minutes
        )
        self.assertEqual(
            learner_payload["pass_basis_points"], version.pass_basis_points
        )
        self.assertNotIn("public_snapshot", learner_payload)
        self.assertNotIn("grading_snapshot", learner_payload)
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
        activity_progress = ActivityProgress.objects.get(
            course_progress=enrollment.current_release_assignment.progress,
            group_activity=group_activity,
        )
        self.assertEqual(activity_progress.status, ActivityProgressStatus.PASSED)
        self.assertEqual(activity_progress.evidence["grade_basis_points"], 10000)
        progress = progress_payload(enrollment.current_release_assignment.progress)
        self.assertEqual(progress["grade"]["basis_points"], 10000)
        self.assertFalse(progress["is_complete"])
        self.assertEqual(progress["blockers"][0]["code"], "required_activities_pending")

        client = APIClient()
        client.force_authenticate(user=learner)
        calendar = client.get(
            f"/api/v1/organizations/{organization.slug}/scheduling/calendar/events/",
            {
                "start": (now - timedelta(hours=1)).isoformat(),
                "end": (now + timedelta(hours=2)).isoformat(),
                "timeZone": "America/Bogota",
                "course": str(release.course_id),
            },
        )
        self.assertEqual(calendar.status_code, 200, calendar.data)
        assessment_events = [
            row
            for row in calendar.data
            if row["extendedProps"]["eventType"].startswith("assessment_")
        ]
        self.assertEqual(len(assessment_events), 2)
        self.assertIn(str(assignment.id), assessment_events[0]["extendedProps"]["href"])
        serialized_calendar = str(assessment_events).lower()
        self.assertNotIn("grading", serialized_calendar)
        self.assertNotIn("token", serialized_calendar)

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
            migration_review_required=True,
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
            migration_review_required=True,
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
            migration_review_required=True,
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

    def test_start_finalizes_stale_attempt_before_opening_the_next_one(self) -> None:
        context = self.assessment_context(with_learning=True)
        delivery = create_delivery(
            actor=context["owner"],
            organization=context["organization"],
            assessment_version=context["assessment_version"],
            name="Entrega con recuperación de expiración",
            course_release=context["release"],
            migration_review_required=True,
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
        first = start_attempt(actor=context["learner"], assignment=assignment)
        Attempt.objects.filter(pk=first.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )

        second = start_attempt(actor=context["learner"], assignment=assignment)

        first.refresh_from_db()
        self.assertEqual(first.status, AttemptStatus.GRADED)
        self.assertEqual(second.attempt_number, 2)
        self.assertEqual(second.status, AttemptStatus.IN_PROGRESS)


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
            migration_review_required=True,
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
