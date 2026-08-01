from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from opentelemetry import metrics
from opentelemetry.metrics import Observation

ALLOWED_LABELS = frozenset(
    {
        "service",
        "environment",
        "route",
        "method",
        "status_class",
        "task_name",
        "queue",
        "consumer",
        "source_type",
        "notification_category",
        "outcome",
    }
)


def safe_attributes(attributes: Mapping[str, str]) -> dict[str, str]:
    unknown = set(attributes) - ALLOWED_LABELS
    if unknown:
        raise ValueError(f"Metric labels no permitidos: {sorted(unknown)}")
    return dict(attributes)


meter = metrics.get_meter("lms.platform")
http_requests = meter.create_counter("lms_http_requests")
http_request_duration = meter.create_histogram("lms_http_request_duration", unit="s")
outbox_deliveries = meter.create_counter("lms_outbox_deliveries")
search_queries = meter.create_counter("lms_search_queries")
search_duration = meter.create_histogram("lms_search_duration", unit="s")
notifications_created = meter.create_counter("lms_notifications_created")
email_deliveries = meter.create_counter("lms_email_deliveries")
celery_tasks = meter.create_counter("lms_celery_tasks")
celery_task_duration = meter.create_histogram("lms_celery_task_duration", unit="s")


def _age(value: datetime | None) -> float:
    if value is None:
        return 0.0
    from django.utils import timezone

    return max(0.0, (timezone.now() - value).total_seconds())


def _outbox_oldest(_: Any) -> list[Observation]:
    try:
        from domain.events.models import DeliveryStatus, EventConsumerDelivery

        created = (
            EventConsumerDelivery.objects.filter(
                status__in=(DeliveryStatus.PENDING, DeliveryStatus.FAILED)
            )
            .order_by("created_at")
            .values_list("created_at", flat=True)
            .first()
        )
        return [Observation(_age(created))]
    except Exception:
        return []


def _outbox_dead(_: Any) -> list[Observation]:
    try:
        from domain.events.models import DeliveryStatus, EventConsumerDelivery

        return [
            Observation(
                EventConsumerDelivery.objects.filter(status=DeliveryStatus.DEAD).count()
            )
        ]
    except Exception:
        return []


def _search_lag(_: Any) -> list[Observation]:
    try:
        from domain.discovery.models import SearchIndexJob, SearchIndexJobStatus

        created = (
            SearchIndexJob.objects.filter(
                status__in=(
                    SearchIndexJobStatus.PENDING,
                    SearchIndexJobStatus.PROCESSING,
                )
            )
            .order_by("created_at")
            .values_list("created_at", flat=True)
            .first()
        )
        return [Observation(_age(created))]
    except Exception:
        return []


def _email_dead(_: Any) -> list[Observation]:
    try:
        from domain.notifications.models import EmailDelivery, EmailDeliveryStatus

        return [
            Observation(
                EmailDelivery.objects.filter(status=EmailDeliveryStatus.DEAD).count()
            )
        ]
    except Exception:
        return []


def _asset_processing_oldest(_: Any) -> list[Observation]:
    try:
        from domain.assets.choices import ProcessingJobStatus
        from domain.assets.models import AssetProcessingJob

        created = (
            AssetProcessingJob.objects.filter(
                status__in=(ProcessingJobStatus.QUEUED, ProcessingJobStatus.RUNNING)
            )
            .order_by("created_at")
            .values_list("created_at", flat=True)
            .first()
        )
        return [Observation(_age(created))]
    except Exception:
        return []


def _grading_job_oldest(_: Any) -> list[Observation]:
    try:
        from domain.assessments.choices import JobStatus
        from domain.assessments.models import AttemptGradingJob, RegradeJob

        active = (JobStatus.QUEUED, JobStatus.RUNNING)
        dates = [
            item
            for item in (
                AttemptGradingJob.objects.filter(status__in=active)
                .order_by("created_at")
                .values_list("created_at", flat=True)
                .first(),
                RegradeJob.objects.filter(status__in=active)
                .order_by("created_at")
                .values_list("created_at", flat=True)
                .first(),
            )
            if item is not None
        ]
        return [Observation(_age(min(dates) if dates else None))]
    except Exception:
        return []


meter.create_observable_gauge(
    "lms_outbox_oldest_pending", callbacks=[_outbox_oldest], unit="s"
)
meter.create_observable_gauge("lms_outbox_dead", callbacks=[_outbox_dead])
meter.create_observable_gauge("lms_search_index_lag", callbacks=[_search_lag], unit="s")
meter.create_observable_gauge("lms_email_dead", callbacks=[_email_dead])
meter.create_observable_gauge(
    "lms_asset_processing_oldest", callbacks=[_asset_processing_oldest], unit="s"
)
meter.create_observable_gauge(
    "lms_grading_job_oldest", callbacks=[_grading_job_oldest], unit="s"
)
