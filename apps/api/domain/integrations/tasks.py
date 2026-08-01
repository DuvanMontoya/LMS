from __future__ import annotations

import uuid

from celery import shared_task

from .services import run_health_check

# Celery's decorator has no complete strict type contract.
# pyright: reportUnknownVariableType=false


@shared_task(name="domain.integrations.tasks.run_integration_health_check")
def run_integration_health_check(check_id: str) -> None:
    run_health_check(check_id=uuid.UUID(check_id))
