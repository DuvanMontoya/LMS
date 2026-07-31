# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportArgumentType=false
from __future__ import annotations

import uuid
from functools import partial

from django.db import transaction

from .choices import JobStatus
from .models import (
    AssessmentGradingRevision,
    Attempt,
    AttemptGradingJob,
)
from .queues import assessment_task_options


@transaction.atomic
def create_attempt_grading_job(
    *,
    attempt: Attempt,
    grading_revision: AssessmentGradingRevision,
) -> AttemptGradingJob:
    existing = (
        AttemptGradingJob.objects.select_for_update()
        .filter(
            attempt=attempt,
            grading_revision=grading_revision,
            status__in=[JobStatus.QUEUED, JobStatus.RUNNING],
        )
        .first()
    )
    if existing is not None:
        return existing
    task_id = uuid.uuid4()
    job = AttemptGradingJob.objects.create(
        attempt=attempt,
        grading_revision=grading_revision,
        task_id=task_id,
    )
    from .tasks import grade_attempt_task

    transaction.on_commit(
        partial(
            grade_attempt_task.apply_async,
            args=[str(job.id)],
            task_id=str(task_id),
            **assessment_task_options("grading"),
        )
    )
    return job
