# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from domain.events.models import DomainEvent
from domain.organizations.models import Organization


class NotificationCategory(models.TextChoices):
    LEARNING = "learning", "Aprendizaje"
    ASSESSMENT = "assessment", "Evaluación"
    AUTHORING = "authoring", "Autoría"
    ASSET = "asset", "Recurso"
    PUBLICATION = "publication", "Publicación"
    SYSTEM = "system", "Sistema"


class EmailDeliveryStatus(models.TextChoices):
    QUEUED = "queued", "En cola"
    SENDING = "sending", "Enviando"
    SENT = "sent", "Enviado"
    FAILED = "failed", "Fallido"
    DEAD = "dead", "Terminal"


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="notifications"
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    event = models.ForeignKey(
        DomainEvent, on_delete=models.PROTECT, related_name="notifications"
    )
    category = models.CharField(max_length=20, choices=NotificationCategory.choices)
    template_key = models.CharField(max_length=100)
    title = models.CharField(max_length=200)
    body = models.TextField(max_length=2000)
    action_url = models.CharField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=["event", "recipient", "template_key"],
                name="notifications_event_recipient_template_unique",
            ),
            models.CheckConstraint(
                condition=Q(action_url="") | Q(action_url__startswith="/"),
                name="notifications_action_url_relative",
            ),
        ]
        indexes = [
            models.Index(
                fields=["recipient", "read_at", "-created_at"],
                name="notif_recipient_unread_ix",
            ),
            models.Index(
                fields=["recipient", "category", "-created_at"],
                name="notifications_recipient_cat_ix",
            ),
            models.Index(fields=["event"], name="notifications_event_ix"),
        ]

    def __str__(self) -> str:
        return f"{self.template_key}:{self.recipient_id}"

    def save(self, *args: object, **kwargs: object) -> None:
        if not self._state.adding:
            current = type(self).objects.get(pk=self.pk)
            immutable_fields = (
                "organization_id",
                "recipient_id",
                "event_id",
                "category",
                "template_key",
                "title",
                "body",
                "action_url",
                "created_at",
            )
            if any(
                getattr(current, field) != getattr(self, field)
                for field in immutable_fields
            ):
                raise ValidationError("Sólo lectura y archivo pueden cambiar.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        raise ValidationError("Notification no admite eliminación física.")


class NotificationPreference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="notification_preferences",
    )
    category = models.CharField(max_length=20, choices=NotificationCategory.choices)
    in_app_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "category"], name="notifications_preference_unique"
            )
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.category}"


class EmailDelivery(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.OneToOneField(
        Notification, on_delete=models.PROTECT, related_name="email_delivery"
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="email_deliveries",
    )
    template_key = models.CharField(max_length=100)
    status = models.CharField(
        max_length=16,
        choices=EmailDeliveryStatus.choices,
        default=EmailDeliveryStatus.QUEUED,
    )
    attempt_count = models.PositiveSmallIntegerField(default=0)
    task_id = models.UUIDField(null=True, blank=True)
    message_id = models.CharField(max_length=255, blank=True)
    recipient_email_hash = models.CharField(max_length=64)
    last_error_code = models.CharField(max_length=80, blank=True)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["status", "next_attempt_at"], name="notifications_email_due_ix"
            ),
            models.Index(fields=["recipient"], name="notif_email_recipient_ix"),
        ]

    def __str__(self) -> str:
        return f"{self.status}:{self.notification_id}"


class NotificationDeliveryEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    delivery = models.ForeignKey(
        EmailDelivery, on_delete=models.PROTECT, related_name="events"
    )
    status = models.CharField(max_length=16, choices=EmailDeliveryStatus.choices)
    error_code = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")

    def __str__(self) -> str:
        return f"{self.delivery_id}:{self.status}"

    def save(self, *args: object, **kwargs: object) -> None:
        if not self._state.adding:
            raise ValidationError("NotificationDeliveryEvent es append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        raise ValidationError("NotificationDeliveryEvent es append-only.")
