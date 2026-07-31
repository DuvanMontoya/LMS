from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import patch

from billiard.exceptions import SoftTimeLimitExceeded
from django.test import TestCase

from ..analytics import build_analytics_snapshot, process_analytics_job
from ..choices import (
    AttemptAggregation,
    AuthoringStatus,
    GradebookEntryStatus,
    GradebookSummaryStatus,
    GradingStatus,
    JobStatus,
)
from ..exceptions import AssessmentInvalid
from ..gradebooks import (
    activate_gradebook,
    add_gradebook_column,
    archive_gradebook_column,
    create_gradebook,
)
from ..grading import create_scoring_correction
from ..jobs import create_attempt_grading_job
from ..models import (
    AnalyticsRefreshJob,
    AssessmentAnalyticsSnapshot,
    AttemptGradeVersion,
    AttemptGradingJob,
)
from ..regrading import create_regrade_job, process_regrade_job
from ..services import (
    _ordered_snapshot_items,
    activate_delivery,
    add_assessment_item,
    assign_delivery,
    create_assessment_pool,
    create_assessment_revision_from_version,
    create_delivery,
    create_question,
    replace_pool_candidates,
    save_response,
    start_attempt,
    submit_attempt,
    transition_assessment_revision,
    transition_question_revision,
)
from ..tasks import grade_attempt_task
from .support import AssessmentFixtureMixin, question_definition


class AdvancedAssessmentWorkflowTests(AssessmentFixtureMixin, TestCase):
    def _question_version(self, context, *, code: str):
        _, revision = create_question(
            actor=context["owner"],
            bank=context["bank"],
            code=code,
            question_type="single_choice",
            definition=question_definition("single_choice"),
        )
        revision, _ = transition_question_revision(
            actor=context["owner"],
            revision=revision,
            expected_version=revision.lock_version,
            to_status=AuthoringStatus.IN_REVIEW,
        )
        revision, version = transition_question_revision(
            actor=context["owner"],
            revision=revision,
            expected_version=revision.lock_version,
            to_status=AuthoringStatus.APPROVED,
        )
        assert version is not None
        return version

    def _submitted_symbolic_attempt(self):
        context = self.assessment_context(with_learning=True)
        definition = question_definition("mathematical_expression")
        definition["grading"]["equivalence_strategy"] = "symbolic_common_domain"
        _, revision = create_question(
            actor=context["owner"],
            bank=context["bank"],
            code="ALG-MATH-WORKER-001",
            question_type="mathematical_expression",
            definition=definition,
        )
        revision, _ = transition_question_revision(
            actor=context["owner"],
            revision=revision,
            expected_version=revision.lock_version,
            to_status=AuthoringStatus.IN_REVIEW,
        )
        revision, question_version = transition_question_revision(
            actor=context["owner"],
            revision=revision,
            expected_version=revision.lock_version,
            to_status=AuthoringStatus.APPROVED,
        )
        assert question_version is not None
        assessment_revision = create_assessment_revision_from_version(
            actor=context["owner"],
            version=context["assessment_version"],
        )
        assessment_revision, _ = add_assessment_item(
            actor=context["owner"],
            revision=assessment_revision,
            expected_version=assessment_revision.lock_version,
            section=assessment_revision.sections.get(),
            question_version=question_version,
            points=Decimal("3.000"),
            required=True,
            objectives=[context["objective"]],
        )
        assessment_revision, _ = transition_assessment_revision(
            actor=context["owner"],
            revision=assessment_revision,
            expected_version=assessment_revision.lock_version,
            to_status=AuthoringStatus.IN_REVIEW,
        )
        assessment_revision, assessment_version = transition_assessment_revision(
            actor=context["owner"],
            revision=assessment_revision,
            expected_version=assessment_revision.lock_version,
            to_status=AuthoringStatus.APPROVED,
        )
        assert assessment_version is not None
        delivery = create_delivery(
            actor=context["owner"],
            organization=context["organization"],
            assessment_version=assessment_version,
            name="Entrega matemática worker",
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
        for item in attempt.items.order_by("display_position"):
            if item.public_snapshot["type"] == "mathematical_expression":
                value = {
                    "latex": "x+1",
                    "mathjson": ["Add", "x", 1],
                }
            else:
                value = "b"
            attempt, _ = save_response(
                actor=context["learner"],
                attempt=attempt,
                attempt_item=item,
                expected_version=attempt.lock_version,
                payload={
                    "schema_version": 1,
                    "type": item.public_snapshot["type"],
                    "value": value,
                },
            )
        attempt = submit_attempt(
            actor=context["learner"],
            attempt=attempt,
            expected_version=attempt.lock_version,
        )
        return attempt

    def test_pool_snapshot_selection_and_clone_are_stable(self) -> None:
        context = self.assessment_context()
        revision = create_assessment_revision_from_version(
            actor=context["owner"],
            version=context["assessment_version"],
        )
        first = self._question_version(context, code="ALG-POOL-001")
        second = self._question_version(context, code="ALG-POOL-002")
        revision, pool = create_assessment_pool(
            actor=context["owner"],
            revision=revision,
            expected_version=revision.lock_version,
            title="Variantes",
            instructions="Selecciona una variante.",
            selection_count=1,
            points_per_item=Decimal("3.000"),
            shuffle_selected=False,
            question_versions=[first, second],
        )
        revision, _ = transition_assessment_revision(
            actor=context["owner"],
            revision=revision,
            expected_version=revision.lock_version,
            to_status=AuthoringStatus.IN_REVIEW,
        )
        revision, version = transition_assessment_revision(
            actor=context["owner"],
            revision=revision,
            expected_version=revision.lock_version,
            to_status=AuthoringStatus.APPROVED,
        )
        assert version is not None
        self.assertEqual(version.maximum_score, Decimal("5.000"))
        first_selection = _ordered_snapshot_items(version, 481516)
        repeated_selection = _ordered_snapshot_items(version, 481516)
        self.assertEqual(first_selection, repeated_selection)
        selected = [row for row in first_selection if row[4] == str(pool.id)]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0][0]["points"], "3.000")
        clone = create_assessment_revision_from_version(
            actor=context["owner"],
            version=version,
        )
        cloned_pool = clone.item_pools.get()
        self.assertEqual(cloned_pool.selection_count, 1)
        self.assertEqual(cloned_pool.candidates.count(), 2)

    def test_pool_candidates_are_append_only_and_cannot_be_reordered(self) -> None:
        context = self.assessment_context()
        revision = create_assessment_revision_from_version(
            actor=context["owner"],
            version=context["assessment_version"],
        )
        first = self._question_version(context, code="ALG-IMM-001")
        second = self._question_version(context, code="ALG-IMM-002")
        third = self._question_version(context, code="ALG-IMM-003")
        revision, pool = create_assessment_pool(
            actor=context["owner"],
            revision=revision,
            expected_version=revision.lock_version,
            title="Candidatos inmutables",
            instructions="",
            selection_count=1,
            points_per_item=Decimal("1.000"),
            shuffle_selected=False,
            question_versions=[first, second],
        )
        original_candidate_ids = list(
            pool.candidates.order_by("position").values_list("id", flat=True)
        )
        revision, pool = replace_pool_candidates(
            actor=context["owner"],
            revision=revision,
            pool=pool,
            expected_version=revision.lock_version,
            question_versions=[first, second, third],
        )
        self.assertEqual(
            list(pool.candidates.order_by("position").values_list("id", flat=True)[:2]),
            original_candidate_ids,
        )
        self.assertEqual(pool.candidates.count(), 3)
        with self.assertRaisesMessage(
            AssessmentInvalid, "Los candidatos existentes son inmutables"
        ):
            replace_pool_candidates(
                actor=context["owner"],
                revision=revision,
                pool=pool,
                expected_version=revision.lock_version,
                question_versions=[second, first, third],
            )

    def test_regrade_updates_append_only_grade_and_active_gradebook(self) -> None:
        context = self.assessment_context(with_learning=True)
        delivery = create_delivery(
            actor=context["owner"],
            organization=context["organization"],
            assessment_version=context["assessment_version"],
            name="Entrega con gradebook",
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
        gradebook = create_gradebook(
            actor=context["owner"],
            organization=context["organization"],
            course_release=context["release"],
        )
        gradebook, column = add_gradebook_column(
            actor=context["owner"],
            gradebook=gradebook,
            expected_version=gradebook.lock_version,
            delivery=delivery,
            title="Diagnóstico",
            weight_basis_points=10_000,
            required=True,
            attempt_aggregation=AttemptAggregation.HIGHEST,
        )
        gradebook = activate_gradebook(
            actor=context["owner"],
            gradebook=gradebook,
            expected_version=gradebook.lock_version,
        )
        attempt = start_attempt(actor=context["learner"], assignment=assignment)
        attempt, _ = save_response(
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
        attempt = submit_attempt(
            actor=context["learner"],
            attempt=attempt,
            expected_version=attempt.lock_version,
        )
        entry = column.entries.get()
        summary = gradebook.summaries.get()
        self.assertEqual(entry.status, GradebookEntryStatus.GRADED)
        self.assertEqual(summary.status, GradebookSummaryStatus.COMPLETE)
        self.assertEqual(summary.weighted_percent_basis_points, 10_000)
        policy = context["assessment_version"].grading_policy
        current_revision = policy.current_revision
        assert current_revision is not None
        source_id = current_revision.grading_snapshot["items"][0]["source_id"]
        correction = create_scoring_correction(
            actor=context["owner"],
            assessment_version=context["assessment_version"],
            expected_policy_version=policy.lock_version,
            reason="La opción correcta era A.",
            item_overrides={
                source_id: {
                    "grading_payload": {
                        "correct_option_ids": ["a"],
                        "option_ids": ["a", "b", "c"],
                    }
                }
            },
        )
        job = create_regrade_job(
            actor=context["owner"],
            organization=context["organization"],
            assessment_version=context["assessment_version"],
            grading_revision=correction,
            delivery=delivery,
            reason="Aplicar corrección aprobada.",
        )
        process_regrade_job(str(job.id))
        job.refresh_from_db()
        attempt.refresh_from_db()
        entry.refresh_from_db()
        summary.refresh_from_db()
        self.assertEqual(job.status, JobStatus.COMPLETED)
        self.assertEqual(AttemptGradeVersion.objects.filter(attempt=attempt).count(), 2)
        self.assertEqual(attempt.total_score, Decimal("0.000"))
        self.assertEqual(entry.percent_basis_points, 0)
        self.assertEqual(summary.weighted_percent_basis_points, 0)
        snapshot = build_analytics_snapshot(
            assessment_version=context["assessment_version"],
            grading_revision=correction,
            delivery=delivery,
            actor=context["owner"],
        )
        self.assertEqual(snapshot.sample_size, 1)
        self.assertEqual(snapshot.mean_percent_basis_points, 0)
        self.assertIsNone(snapshot.median_percent_basis_points)
        self.assertEqual(snapshot.items.get().presented_count, 1)

    def test_archiving_gradebook_column_preserves_contiguous_active_order(self) -> None:
        context = self.assessment_context(with_learning=True)
        gradebook = create_gradebook(
            actor=context["owner"],
            organization=context["organization"],
            course_release=context["release"],
        )
        columns = []
        for index in range(1, 4):
            delivery = create_delivery(
                actor=context["owner"],
                organization=context["organization"],
                assessment_version=context["assessment_version"],
                name=f"Entrega {index}",
                course_release=context["release"],
            )
            gradebook, column = add_gradebook_column(
                actor=context["owner"],
                gradebook=gradebook,
                expected_version=gradebook.lock_version,
                delivery=delivery,
                title=f"Columna {index}",
                weight_basis_points=3_000,
                required=True,
                attempt_aggregation=AttemptAggregation.HIGHEST,
            )
            columns.append(column)

        gradebook, archived = archive_gradebook_column(
            actor=context["owner"],
            gradebook=gradebook,
            column=columns[1],
            expected_version=gradebook.lock_version,
        )

        ordered = list(gradebook.columns.order_by("position"))
        self.assertEqual(
            [item.id for item in ordered], [columns[0].id, columns[2].id, archived.id]
        )
        self.assertEqual([item.position for item in ordered], [1, 2, 3])
        self.assertEqual(
            list(
                gradebook.columns.filter(status="active")
                .order_by("position")
                .values_list("position", flat=True)
            ),
            [1, 2],
        )

    def test_analytics_job_locks_only_the_job_when_delivery_is_global(self) -> None:
        context = self.assessment_context()
        revision = context["assessment_version"].grading_policy.current_revision
        assert revision is not None
        job = AnalyticsRefreshJob.objects.create(
            organization=context["organization"],
            assessment_version=context["assessment_version"],
            grading_revision=revision,
            delivery=None,
            task_id=uuid.uuid4(),
            created_by=context["owner"],
        )

        process_analytics_job(str(job.id))

        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.COMPLETED)
        self.assertTrue(
            AssessmentAnalyticsSnapshot.objects.filter(
                assessment_version=context["assessment_version"],
                grading_revision=revision,
                delivery=None,
            ).exists()
        )

    def test_grading_job_dispatch_is_after_commit_and_idempotent(self) -> None:
        attempt = self._submitted_symbolic_attempt()
        revision = attempt.assessment_version.grading_policy.current_revision
        assert revision is not None
        existing = attempt.grading_jobs.get()
        with patch(
            "domain.assessments.tasks.grade_attempt_task.apply_async"
        ) as apply_async:
            with self.captureOnCommitCallbacks(execute=True):
                duplicate = create_attempt_grading_job(
                    attempt=attempt,
                    grading_revision=revision,
                )
        self.assertEqual(duplicate.pk, existing.pk)
        apply_async.assert_not_called()
        self.assertEqual(AttemptGradingJob.objects.filter(attempt=attempt).count(), 1)

    def test_worker_timeout_is_inconclusive_and_retry_is_idempotent(self) -> None:
        attempt = self._submitted_symbolic_attempt()
        job = attempt.grading_jobs.get()
        with patch(
            "domain.assessments.tasks._symbolic_outcomes",
            side_effect=SoftTimeLimitExceeded,
        ):
            grade_attempt_task.run(str(job.id))
        job.refresh_from_db()
        attempt.refresh_from_db()
        grade = attempt.current_grade
        assert grade is not None
        math_grade = grade.item_grades.get(
            attempt_item__public_snapshot__type="mathematical_expression"
        )
        self.assertEqual(job.status, JobStatus.COMPLETED_WITH_ERRORS)
        self.assertEqual(job.last_error_code, "symbolic_timeout")
        self.assertEqual(math_grade.grading_status, GradingStatus.PENDING_MANUAL)
        self.assertIsNone(math_grade.is_correct)
        self.assertEqual(math_grade.manual_review_reason, "symbolic_inconclusive")
        grade_attempt_task.run(str(job.id))
        self.assertEqual(AttemptGradeVersion.objects.filter(attempt=attempt).count(), 1)
