# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import uuid

from celery import shared_task
from django.utils import timezone

from .models import SearchIndexJob, SearchIndexJobStatus
from .services import rebuild_search_index


@shared_task(ignore_result=True, acks_late=True)
def process_search_index_job(job_id: str) -> None:
    job = SearchIndexJob.objects.select_related("organization").get(
        pk=uuid.UUID(job_id)
    )
    if job.status == SearchIndexJobStatus.COMPLETED:
        return
    job.status = SearchIndexJobStatus.PROCESSING
    job.attempt_count += 1
    job.started_at = timezone.now()
    job.last_error_code = ""
    job.save(update_fields=("status", "attempt_count", "started_at", "last_error_code"))
    try:
        generation = rebuild_search_index(organization=job.organization)
    except Exception:
        job.status = SearchIndexJobStatus.FAILED
        job.last_error_code = "rebuild_failed"
        job.completed_at = timezone.now()
        job.save(update_fields=("status", "last_error_code", "completed_at"))
        raise
    job.status = SearchIndexJobStatus.COMPLETED
    job.generation = generation
    job.completed_at = generation.completed_at
    job.save(update_fields=("status", "generation", "completed_at"))
