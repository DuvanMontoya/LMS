# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportCallIssue=false
from __future__ import annotations

import uuid

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from .models import (
    DeliveryStatus,
    DomainEvent,
    EventConsumerDelivery,
    EventReplayRequest,
    ReplayStatus,
)
from .services import process_delivery


@shared_task(ignore_result=True, acks_late=True)
def dispatch_domain_event(event_id: str) -> None:
    event_uuid = uuid.UUID(event_id)
    delivery_ids = list(
        EventConsumerDelivery.objects.filter(event_id=event_uuid)
        .filter(
            Q(status__in=(DeliveryStatus.PENDING, DeliveryStatus.FAILED))
            & (Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=timezone.now()))
            | Q(status=DeliveryStatus.PROCESSING, lease_expires_at__lte=timezone.now())
        )
        .values_list("id", flat=True)
    )
    for delivery_id in delivery_ids:
        process_delivery(delivery_id)


@shared_task(ignore_result=True, acks_late=True)
def process_event_replay(replay_id: str) -> None:
    replay = EventReplayRequest.objects.get(pk=uuid.UUID(replay_id))
    replay.status = ReplayStatus.PROCESSING
    replay.started_at = timezone.now()
    replay.save(update_fields=("status", "started_at"))
    query = DomainEvent.objects.filter(organization=replay.organization).order_by(
        "created_at", "id"
    )
    if replay.event_type:
        query = query.filter(event_type=replay.event_type)
    if replay.from_event_id:
        lower = DomainEvent.objects.filter(pk=replay.from_event_id).first()
        if lower is not None:
            query = query.filter(created_at__gte=lower.created_at)
    if replay.to_event_id:
        upper = DomainEvent.objects.filter(pk=replay.to_event_id).first()
        if upper is not None:
            query = query.filter(created_at__lte=upper.created_at)
    events = list(query[:100_001])
    if len(events) > 100_000:
        replay.status = ReplayStatus.FAILED
        replay.completed_at = timezone.now()
        replay.save(update_fields=("status", "completed_at"))
        return
    replay.total_events = len(events)
    for event in events:
        delivery, _ = EventConsumerDelivery.objects.get_or_create(
            event=event,
            consumer_name=replay.consumer_name,
            defaults={"status": DeliveryStatus.PENDING},
        )
        if delivery.status in {DeliveryStatus.FAILED, DeliveryStatus.DEAD}:
            delivery.status = DeliveryStatus.PENDING
            delivery.next_attempt_at = None
            delivery.last_error_code = ""
            delivery.save()
        dispatch_domain_event.delay(str(event.id))
        replay.processed_events += 1
    replay.status = ReplayStatus.COMPLETED
    replay.completed_at = timezone.now()
    replay.save()
