# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportArgumentType=false
from __future__ import annotations

import uuid
from functools import partial
from typing import Any

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from domain.events.services import record_domain_event
from domain.organizations.models import Organization

from .choices import (
    AttemptStatus,
    GradeSource,
    JobStatus,
    RegradeAttemptStatus,
)
from .exceptions import AssessmentConflict, AssessmentInvalid
from .grading import create_attempt_grade, evaluate_symbolic_responses
from .models import (
    AssessmentDelivery,
    AssessmentGradingPolicy,
    AssessmentGradingRevision,
    AssessmentVersion,
    Attempt,
    AttemptGradeVersion,
    RegradeJob,
    RegradeJobAttempt,
)
from .queues import assessment_task_options

REGRADE_JOB_ATTEMPT_LIMIT = 50_000
REGRADE_CHUNK_SIZE = 100


def _actor_id(actor: object) -> Any:
    actor_id = getattr(actor, "pk", None)
    if actor_id is None:
        raise AssessmentInvalid("Se requiere un actor autenticado.")
    return actor_id


def _eligible_attempts(
    *,
    assessment_version: AssessmentVersion,
    delivery: AssessmentDelivery | None,
):
    queryset = Attempt.objects.filter(
        assessment_version=assessment_version,
        submitted_at__isnull=False,
    ).exclude(status=AttemptStatus.IN_PROGRESS)
    if delivery is not None:
        queryset = queryset.filter(delivery_assignment__delivery=delivery)
    return queryset.order_by("submitted_at", "id")


@transaction.atomic
def create_regrade_job(
    *,
    actor: object,
    organization: Organization,
    assessment_version: AssessmentVersion,
    grading_revision: AssessmentGradingRevision,
    reason: str,
    delivery: AssessmentDelivery | None = None,
) -> RegradeJob:
    if not reason.strip():
        raise AssessmentInvalid("La recalificación exige una razón.")
    if assessment_version.assessment.organization_id != organization.id:
        raise AssessmentInvalid("La evaluación pertenece a otra organización.")
    policy = AssessmentGradingPolicy.objects.select_for_update(of=("self",)).get(
        assessment_version=assessment_version
    )
    if grading_revision.policy_id != policy.id:
        raise AssessmentInvalid("La revisión no pertenece a esta policy.")
    if delivery is not None:
        if delivery.organization_id != organization.id:
            raise AssessmentInvalid("La entrega pertenece a otra organización.")
        if delivery.assessment_version_id != assessment_version.id:
            raise AssessmentInvalid("La entrega usa otra versión de evaluación.")
    attempts = _eligible_attempts(
        assessment_version=assessment_version,
        delivery=delivery,
    )
    count = attempts.count()
    if count > REGRADE_JOB_ATTEMPT_LIMIT:
        raise AssessmentInvalid(
            "El job excede 50000 intentos; requiere particionado explícito."
        )
    active = RegradeJob.objects.select_for_update().filter(
        organization=organization,
        assessment_version=assessment_version,
        grading_revision=grading_revision,
        delivery=delivery,
        status__in=[JobStatus.QUEUED, JobStatus.RUNNING],
    )
    if active.exists():
        raise AssessmentConflict("Ya existe un job activo para este alcance.")
    task_id = uuid.uuid4()
    job = RegradeJob.objects.create(
        organization=organization,
        assessment_version=assessment_version,
        grading_revision=grading_revision,
        delivery=delivery,
        reason=reason.strip(),
        total_attempts=count,
        task_id=task_id,
        created_by_id=_actor_id(actor),
    )
    for offset in range(0, count, 1_000):
        attempt_ids = list(
            attempts.values_list("id", flat=True)[offset : offset + 1_000]
        )
        RegradeJobAttempt.objects.bulk_create(
            [
                RegradeJobAttempt(job=job, attempt_id=attempt_id)
                for attempt_id in attempt_ids
            ]
        )
    from .tasks import process_regrade_job_task

    transaction.on_commit(
        partial(
            process_regrade_job_task.apply_async,
            args=[str(job.id)],
            task_id=str(task_id),
            **assessment_task_options("regrading"),
        )
    )
    return job


def claim_regrade_job(job_id: str) -> RegradeJob | None:
    with transaction.atomic():
        job = (
            RegradeJob.objects.select_for_update()
            .select_related("grading_revision__policy")
            .get(pk=job_id)
        )
        if job.status not in {JobStatus.QUEUED, JobStatus.RUNNING}:
            return None
        job.status = JobStatus.RUNNING
        job.started_at = job.started_at or timezone.now()
        job.lock_version += 1
        job.save(update_fields=["status", "started_at", "lock_version"])
        return job


def _mark_regrade_item_failed(item_id: object, error_code: str) -> None:
    with transaction.atomic():
        item = RegradeJobAttempt.objects.select_for_update().get(pk=item_id)
        if item.status in {
            RegradeAttemptStatus.COMPLETED,
            RegradeAttemptStatus.SKIPPED,
        }:
            return
        item.status = RegradeAttemptStatus.FAILED
        item.error_code = error_code
        item.processed_at = timezone.now()
        item.save(update_fields=["status", "error_code", "processed_at"])


def process_regrade_item(item_id: object) -> None:
    with transaction.atomic():
        item = (
            RegradeJobAttempt.objects.select_for_update()
            .select_related("attempt", "job__grading_revision")
            .get(pk=item_id)
        )
        if item.status not in {
            RegradeAttemptStatus.PENDING,
            RegradeAttemptStatus.PROCESSING,
        }:
            return
        item.status = RegradeAttemptStatus.PROCESSING
        item.previous_grade = item.attempt.current_grade
        item.error_code = ""
        item.save(update_fields=["status", "previous_grade", "error_code"])
    try:
        with transaction.atomic():
            item = (
                RegradeJobAttempt.objects.select_for_update()
                .select_related("job__grading_revision", "attempt")
                .get(pk=item_id)
            )
            attempt = Attempt.objects.select_for_update().get(pk=item.attempt_id)
            if (
                attempt.submitted_at is None
                or attempt.status == AttemptStatus.IN_PROGRESS
            ):
                item.status = RegradeAttemptStatus.SKIPPED
                item.error_code = "attempt_not_submitted"
                item.processed_at = timezone.now()
                item.save(update_fields=["status", "error_code", "processed_at"])
                return
            existing = AttemptGradeVersion.objects.filter(
                attempt=attempt,
                grading_revision=item.job.grading_revision,
                source__in=[GradeSource.INITIAL, GradeSource.REGRADE],
            ).first()
            if existing is not None:
                item.status = RegradeAttemptStatus.SKIPPED
                item.new_grade = existing
                item.error_code = ""
                item.processed_at = timezone.now()
                item.save(
                    update_fields=[
                        "status",
                        "new_grade",
                        "error_code",
                        "processed_at",
                    ]
                )
                return
            grade = create_attempt_grade(
                attempt=attempt,
                grading_revision=item.job.grading_revision,
                source=GradeSource.REGRADE,
                actor=None,
                symbolic_outcomes=evaluate_symbolic_responses(
                    attempt=attempt,
                    grading_revision=item.job.grading_revision,
                ),
            )
            item.status = RegradeAttemptStatus.COMPLETED
            item.new_grade = grade
            item.error_code = ""
            item.processed_at = timezone.now()
            item.save(
                update_fields=["status", "new_grade", "error_code", "processed_at"]
            )
    except Exception:
        _mark_regrade_item_failed(item_id, "regrade_failed")


def _recalculate_job(job_id: object, *, complete: bool) -> RegradeJob:
    with transaction.atomic():
        job = RegradeJob.objects.select_for_update().get(pk=job_id)
        counts = {
            row["status"]: row["count"]
            for row in job.attempt_items.values("status").annotate(count=Count("id"))
        }
        completed = counts.get(RegradeAttemptStatus.COMPLETED, 0)
        skipped = counts.get(RegradeAttemptStatus.SKIPPED, 0)
        failed = counts.get(RegradeAttemptStatus.FAILED, 0)
        job.processed_attempts = completed + skipped + failed
        job.succeeded_attempts = completed
        job.failed_attempts = failed
        if complete:
            job.status = (
                JobStatus.COMPLETED_WITH_ERRORS if failed else JobStatus.COMPLETED
            )
            job.completed_at = timezone.now()
        job.lock_version += 1
        job.save(
            update_fields=[
                "processed_attempts",
                "succeeded_attempts",
                "failed_attempts",
                "status",
                "completed_at",
                "lock_version",
            ]
        )
        if complete:
            record_domain_event(
                event_type="assessments.regrade.completed.v1",
                organization=job.organization,
                aggregate_type="regrade",
                aggregate_id=job.id,
                actor=job.created_by,
                payload={"regrade_id": str(job.id)},
            )
        return job


def process_regrade_job_chunk(job_id: str) -> bool:
    job = claim_regrade_job(job_id)
    if job is None:
        return False
    item_ids = list(
        RegradeJobAttempt.objects.filter(
            job_id=job_id,
            status__in=[
                RegradeAttemptStatus.PENDING,
                RegradeAttemptStatus.PROCESSING,
            ],
        )
        .order_by("id")
        .values_list("id", flat=True)[:REGRADE_CHUNK_SIZE]
    )
    for item_id in item_ids:
        process_regrade_item(item_id)
    remaining = RegradeJobAttempt.objects.filter(
        job_id=job_id,
        status__in=[
            RegradeAttemptStatus.PENDING,
            RegradeAttemptStatus.PROCESSING,
        ],
    ).exists()
    _recalculate_job(job.id, complete=not remaining)
    return remaining


def process_regrade_job(job_id: str) -> None:
    while process_regrade_job_chunk(job_id):
        continue


@transaction.atomic
def retry_failed_regrade_job(
    *,
    actor: object,
    job: RegradeJob,
    expected_version: int,
) -> RegradeJob:
    del actor
    locked = RegradeJob.objects.select_for_update().get(pk=job.pk)
    if locked.lock_version != expected_version:
        raise AssessmentConflict("El job cambió durante la operación.")
    if locked.status not in {JobStatus.FAILED, JobStatus.COMPLETED_WITH_ERRORS}:
        raise AssessmentConflict("Sólo se pueden reintentar items fallidos.")
    failed = locked.attempt_items.select_for_update().filter(
        status=RegradeAttemptStatus.FAILED
    )
    if not failed.exists():
        raise AssessmentConflict("El job no tiene items fallidos.")
    failed.update(
        status=RegradeAttemptStatus.PENDING,
        error_code="",
        processed_at=None,
    )
    completed_count = locked.attempt_items.filter(
        status=RegradeAttemptStatus.COMPLETED
    ).count()
    skipped_count = locked.attempt_items.filter(
        status=RegradeAttemptStatus.SKIPPED
    ).count()
    task_id = uuid.uuid4()
    locked.status = JobStatus.QUEUED
    locked.task_id = task_id
    locked.processed_attempts = completed_count + skipped_count
    locked.succeeded_attempts = completed_count
    locked.failed_attempts = 0
    locked.started_at = None
    locked.completed_at = None
    locked.lock_version += 1
    locked.save(
        update_fields=[
            "status",
            "task_id",
            "processed_attempts",
            "succeeded_attempts",
            "failed_attempts",
            "started_at",
            "completed_at",
            "lock_version",
        ]
    )
    from .tasks import process_regrade_job_task

    transaction.on_commit(
        partial(
            process_regrade_job_task.apply_async,
            args=[str(locked.id)],
            task_id=str(task_id),
            **assessment_task_options("regrading"),
        )
    )
    return locked
