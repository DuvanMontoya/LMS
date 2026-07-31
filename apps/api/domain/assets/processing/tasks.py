# pyright: reportUnknownVariableType=false
from __future__ import annotations

import uuid

from celery import shared_task

from .jobs import process_asset_version


@shared_task(
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=32_000,
    time_limit=32_400,
)
def process_asset_version_task(_task: object, job_id: str) -> None:
    process_asset_version(uuid.UUID(job_id))
