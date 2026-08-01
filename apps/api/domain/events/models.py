# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from domain.organizations.models import Organization


class DeliveryStatus(models.TextChoices):
    PENDING = "pending", "Pendiente"
    PROCESSING = "processing", "Procesando"
    COMPLETED = "completed", "Completada"
    FAILED = "failed", "Fallida"
    DEAD = "dead", "Terminal"


class ReplayStatus(models.TextChoices):
    PENDING = "pending", "Pendiente"
    PROCESSING = "processing", "Procesando"
    COMPLETED = "completed", "Completada"
    FAILED = "failed", "Fallida"


class DomainEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=160)
    schema_version = models.PositiveSmallIntegerField()
    organization = models.ForeignKey(
        Organization,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="domain_events",
    )
    aggregate_type = models.CharField(max_length=80)
    aggregate_id = models.UUIDField()
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="domain_events_recorded",
    )
    correlation_id = models.UUIDField()
    causation_id = models.UUIDField(null=True, blank=True)
    payload = models.JSONField()
    occurred_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-occurred_at", "-id")
        constraints = [
            models.CheckConstraint(
                condition=Q(schema_version__gt=0), name="events_schema_version_positive"
            ),
            models.CheckConstraint(
                condition=Q(
                    event_type__regex=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){2}\.v[1-9][0-9]*$"
                ),
                name="events_type_versioned_format",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "-occurred_at"], name="events_org_occurred_ix"
            ),
            models.Index(
                fields=["event_type", "-occurred_at"], name="events_type_occurred_ix"
            ),
            models.Index(
                fields=["aggregate_type", "aggregate_id"], name="events_aggregate_ix"
            ),
            models.Index(fields=["correlation_id"], name="events_correlation_ix"),
        ]

    def __str__(self) -> str:
        return f"{self.event_type}:{self.id}"

    def save(self, *args: object, **kwargs: object) -> None:
        if not self._state.adding:
            raise ValidationError("DomainEvent es append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        raise ValidationError("DomainEvent es append-only.")


class EventConsumerDelivery(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        DomainEvent, on_delete=models.PROTECT, related_name="deliveries"
    )
    consumer_name = models.CharField(max_length=120)
    status = models.CharField(
        max_length=16, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING
    )
    attempt_count = models.PositiveSmallIntegerField(default=0)
    claimed_at = models.DateTimeField(null=True, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    last_error_code = models.CharField(max_length=80, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event", "consumer_name"],
                name="events_delivery_consumer_unique",
            )
        ]
        indexes = [
            models.Index(
                fields=["status", "next_attempt_at"], name="events_delivery_due_ix"
            ),
            models.Index(
                fields=["consumer_name", "status"], name="events_consumer_state_ix"
            ),
            models.Index(fields=["lease_expires_at"], name="events_delivery_lease_ix"),
        ]

    def __str__(self) -> str:
        return f"{self.consumer_name}:{self.event_id}"


class EventReplayRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consumer_name = models.CharField(max_length=120)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="event_replay_requests"
    )
    event_type = models.CharField(max_length=160, blank=True)
    from_event_id = models.UUIDField(null=True, blank=True)
    to_event_id = models.UUIDField(null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=ReplayStatus.choices, default=ReplayStatus.PENDING
    )
    total_events = models.PositiveIntegerField(default=0)
    processed_events = models.PositiveIntegerField(default=0)
    failed_events = models.PositiveIntegerField(default=0)
    reason = models.TextField(max_length=1000)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="event_replay_requests_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=Q(total_events__lte=100_000), name="events_replay_size_limit"
            ),
            models.CheckConstraint(
                condition=~Q(reason=""), name="events_replay_reason_required"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.consumer_name}:{self.id}"
