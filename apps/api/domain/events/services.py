# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportCallIssue=false, reportArgumentType=false
from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import timedelta
from functools import partial
from typing import Any

from django.db import connection, transaction
from django.utils import timezone

from config.observability.context import bind_context, current_context, reset_context
from config.observability.metrics import outbox_deliveries, safe_attributes
from config.observability.tracing import domain_span

from .models import DeliveryStatus, DomainEvent, EventConsumerDelivery
from .registry import consumer_names_for_event, event_definition


def _context_uuid(name: str) -> uuid.UUID | None:
    value = current_context().get(name)
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def record_domain_event(
    *,
    event_type: str,
    organization: object | None,
    aggregate_type: str,
    aggregate_id: uuid.UUID,
    payload: Mapping[str, Any],
    actor: object | None = None,
    correlation_id: uuid.UUID | None = None,
    causation_id: uuid.UUID | None = None,
) -> DomainEvent:
    if not connection.in_atomic_block:
        raise RuntimeError("record_domain_event requiere una transacción activa.")
    definition = event_definition(event_type)
    definition.validator(payload)
    if organization is None and not definition.allow_global:
        raise ValueError("El evento requiere organización.")
    correlation = correlation_id or _context_uuid("correlation_id") or uuid.uuid4()
    causation = causation_id or _context_uuid("causation_id")
    event = DomainEvent.objects.create(
        event_type=event_type,
        schema_version=definition.schema_version,
        organization=organization,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        actor=actor,
        correlation_id=correlation,
        causation_id=causation,
        payload=dict(payload),
        occurred_at=timezone.now(),
    )
    names = consumer_names_for_event(event_type)
    EventConsumerDelivery.objects.bulk_create(
        [EventConsumerDelivery(event=event, consumer_name=name) for name in names]
    )
    from .tasks import dispatch_domain_event

    transaction.on_commit(partial(dispatch_domain_event.delay, str(event.id)))
    return event


def process_delivery(delivery_id: uuid.UUID) -> DeliveryStatus:
    from .registry import consumer_definition

    now = timezone.now()
    with transaction.atomic():
        delivery = (
            EventConsumerDelivery.objects.select_for_update()
            .select_related("event")
            .get(pk=delivery_id)
        )
        if delivery.status in {DeliveryStatus.COMPLETED, DeliveryStatus.DEAD}:
            return DeliveryStatus(delivery.status)
        if (
            delivery.status == DeliveryStatus.PROCESSING
            and delivery.lease_expires_at
            and delivery.lease_expires_at > now
        ):
            return DeliveryStatus.PROCESSING
        delivery.status = DeliveryStatus.PROCESSING
        delivery.attempt_count += 1
        delivery.claimed_at = now
        delivery.lease_expires_at = now + timedelta(minutes=5)
        delivery.save(
            update_fields=(
                "status",
                "attempt_count",
                "claimed_at",
                "lease_expires_at",
                "updated_at",
            )
        )
    tokens = bind_context(
        correlation_id=delivery.event.correlation_id,
        causation_id=delivery.event.causation_id,
        event_id=delivery.event_id,
    )
    try:
        with domain_span(
            "domain.event.consume",
            {
                "event.type": delivery.event.event_type,
                "event.consumer": delivery.consumer_name,
            },
        ):
            consumer_definition(delivery.consumer_name).handler(delivery.event)
    except Exception:
        with transaction.atomic():
            locked = EventConsumerDelivery.objects.select_for_update().get(
                pk=delivery_id
            )
            locked.status = (
                DeliveryStatus.DEAD
                if locked.attempt_count >= 5
                else DeliveryStatus.FAILED
            )
            locked.last_error_code = "consumer_failed"
            locked.lease_expires_at = None
            locked.next_attempt_at = (
                None
                if locked.status == DeliveryStatus.DEAD
                else timezone.now()
                + timedelta(seconds=min(300, 2**locked.attempt_count))
            )
            locked.save()
            if locked.status == DeliveryStatus.FAILED:
                from .tasks import dispatch_domain_event

                delay = max(
                    1,
                    int((locked.next_attempt_at - timezone.now()).total_seconds()),
                )
                transaction.on_commit(
                    partial(
                        dispatch_domain_event.apply_async,
                        args=[str(delivery.event_id)],
                        countdown=delay,
                    )
                )
        outbox_deliveries.add(
            1,
            safe_attributes(
                {"consumer": delivery.consumer_name, "outcome": str(locked.status)}
            ),
        )
        return DeliveryStatus(locked.status)
    finally:
        reset_context(tokens)
    with transaction.atomic():
        locked = EventConsumerDelivery.objects.select_for_update().get(pk=delivery_id)
        locked.status = DeliveryStatus.COMPLETED
        locked.processed_at = timezone.now()
        locked.lease_expires_at = None
        locked.next_attempt_at = None
        locked.last_error_code = ""
        locked.save()
    outbox_deliveries.add(
        1,
        safe_attributes({"consumer": delivery.consumer_name, "outcome": "completed"}),
    )
    return DeliveryStatus.COMPLETED
