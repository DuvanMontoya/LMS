# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportUnknownParameterType=false, reportMissingParameterType=false
from __future__ import annotations

from billiard.exceptions import SoftTimeLimitExceeded
from celery import shared_task
from django.db import transaction
from django.utils import timezone

from config.observability.tracing import traced_domain_operation

from .choices import AttemptStatus, GradeSource, JobStatus
from .grading import create_attempt_grade, evaluate_symbolic_responses
from .math.equivalence import MathEquivalenceOutcome
from .models import Attempt, AttemptGradingJob
from .queues import assessment_queue


def _claim_grading_job(job_id: str) -> AttemptGradingJob | None:
    with transaction.atomic():
        job = (
            AttemptGradingJob.objects.select_for_update()
            .select_related("attempt", "grading_revision__policy")
            .get(pk=job_id)
        )
        if job.status in {JobStatus.COMPLETED, JobStatus.COMPLETED_WITH_ERRORS}:
            return None
        if job.status == JobStatus.FAILED:
            return None
        job.status = JobStatus.RUNNING
        job.attempts += 1
        job.started_at = job.started_at or timezone.now()
        job.last_error_code = ""
        job.save(
            update_fields=[
                "status",
                "attempts",
                "started_at",
                "last_error_code",
                "updated_at",
            ]
        )
        return job


def _symbolic_outcomes(job: AttemptGradingJob) -> dict[str, MathEquivalenceOutcome]:
    return evaluate_symbolic_responses(
        attempt=job.attempt,
        grading_revision=job.grading_revision,
    )


def _inconclusive_outcomes(job: AttemptGradingJob) -> dict[str, MathEquivalenceOutcome]:
    policies = {
        str(item["source_id"]): item
        for item in job.grading_revision.grading_snapshot["items"]
    }
    return {
        str(item.id): MathEquivalenceOutcome("inconclusive", False)
        for item in job.attempt.items.all()
        if policies[str(item.assessment_item_id)]["question_type"]
        == "mathematical_expression"
    }


def _complete_grading_job(
    job_id: str,
    *,
    status: str,
    error_code: str = "",
) -> None:
    with transaction.atomic():
        job = AttemptGradingJob.objects.select_for_update().get(pk=job_id)
        job.status = status
        job.last_error_code = error_code
        job.completed_at = timezone.now()
        job.save(
            update_fields=[
                "status",
                "last_error_code",
                "completed_at",
                "updated_at",
            ]
        )


@shared_task(
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=3,
    time_limit=5,
    max_retries=0,
)
@traced_domain_operation("assessments.grade_attempt")
def grade_attempt_task(self, job_id: str) -> None:
    del self
    job = _claim_grading_job(job_id)
    if job is None:
        return
    try:
        outcomes = _symbolic_outcomes(job)
        create_attempt_grade(
            attempt=job.attempt,
            grading_revision=job.grading_revision,
            source=GradeSource.INITIAL,
            actor=None,
            symbolic_outcomes=outcomes,
        )
        _complete_grading_job(job_id, status=JobStatus.COMPLETED)
    except SoftTimeLimitExceeded:
        create_attempt_grade(
            attempt=job.attempt,
            grading_revision=job.grading_revision,
            source=GradeSource.INITIAL,
            actor=None,
            symbolic_outcomes=_inconclusive_outcomes(job),
        )
        _complete_grading_job(
            job_id,
            status=JobStatus.COMPLETED_WITH_ERRORS,
            error_code="symbolic_timeout",
        )
    except Exception:
        with transaction.atomic():
            attempt = Attempt.objects.select_for_update().get(pk=job.attempt_id)
            if attempt.current_grade_id is None:
                attempt.status = AttemptStatus.GRADING_FAILED
                attempt.lock_version += 1
                attempt.save(update_fields=["status", "lock_version", "updated_at"])
        _complete_grading_job(
            job_id,
            status=JobStatus.FAILED,
            error_code="grading_failed",
        )
        raise


@shared_task(
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=40,
    time_limit=45,
    max_retries=0,
)
@traced_domain_operation("assessments.process_regrade")
def process_regrade_job_task(self, job_id: str) -> None:
    from .regrading import process_regrade_job_chunk

    if process_regrade_job_chunk(job_id):
        self.apply_async(args=[job_id], queue=assessment_queue("regrading"))


@shared_task(
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=0,
)
@traced_domain_operation("assessments.refresh_analytics")
def refresh_analytics_task(self, job_id: str) -> None:
    del self
    from .analytics import process_analytics_job

    process_analytics_job(job_id)
