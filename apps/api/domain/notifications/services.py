# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportUnknownLambdaType=false, reportCallIssue=false
from __future__ import annotations

import hashlib
import hmac

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from config.observability.metrics import notifications_created, safe_attributes
from domain.events.models import DomainEvent

from .models import (
    EmailDelivery,
    Notification,
    NotificationCategory,
    NotificationPreference,
)
from .preferences import MANDATORY_IN_APP_TEMPLATES, effective_preference
from .routing import route_event


def _email_hash(email: str) -> str:
    return hmac.new(
        settings.NOTIFICATION_EMAIL_HMAC_KEY.encode(),
        email.casefold().strip().encode(),
        hashlib.sha256,
    ).hexdigest()


def route_domain_event(event: DomainEvent) -> None:
    route = route_event(event)
    if route is None:
        return
    if len(route.recipient_ids) > 10_000:
        raise ValueError("El fan-out requiere un job durable dedicado.")
    User = get_user_model()
    recipients = User.objects.filter(pk__in=route.recipient_ids, is_active=True)
    for recipient in recipients:
        preference = effective_preference(recipient, route.category)
        in_app = (
            preference.in_app_enabled
            or route.template_key in MANDATORY_IN_APP_TEMPLATES
        )
        if not in_app and not preference.email_enabled:
            continue
        with transaction.atomic():
            notification, created = Notification.objects.get_or_create(
                event=event,
                recipient=recipient,
                template_key=route.template_key,
                defaults={
                    "organization": event.organization,
                    "category": route.category,
                    "title": route.title,
                    "body": route.body,
                    "action_url": route.action_url,
                    "archived_at": None if in_app else timezone.now(),
                },
            )
            if not created:
                continue
            notifications_created.add(
                1,
                safe_attributes(
                    {"notification_category": route.category, "outcome": "created"}
                ),
            )
            if preference.email_enabled and recipient.email:
                delivery = EmailDelivery.objects.create(
                    notification=notification,
                    recipient=recipient,
                    template_key=route.template_key,
                    recipient_email_hash=_email_hash(recipient.email),
                )
                from .tasks import send_email_delivery

                transaction.on_commit(
                    lambda delivery_id=delivery.id: send_email_delivery.delay(
                        str(delivery_id)
                    )
                )


def mark_read(*, notification: Notification, read: bool) -> Notification:
    notification.read_at = timezone.now() if read else None
    notification.save(update_fields=("read_at",))
    return notification


def archive_notification(*, notification: Notification) -> Notification:
    notification.archived_at = timezone.now()
    notification.save(update_fields=("archived_at",))
    return notification


def mark_all_read(*, user: object, organization: object | None = None) -> int:
    query = Notification.objects.filter(
        recipient=user, read_at__isnull=True, archived_at__isnull=True
    )
    if organization is not None:
        query = query.filter(organization=organization)
    return query.update(read_at=timezone.now())


def replace_preferences(
    *, user: object, values: dict[str, dict[str, bool]]
) -> list[NotificationPreference]:
    unknown = set(values) - set(NotificationCategory.values)
    if unknown:
        raise ValueError("Categoría de notificación inválida.")
    output: list[NotificationPreference] = []
    with transaction.atomic():
        for category, channels in values.items():
            defaults = effective_preference(user, category)
            in_app = bool(channels.get("in_app_enabled", defaults.in_app_enabled))
            email = bool(channels.get("email_enabled", defaults.email_enabled))
            if (
                in_app == defaults.in_app_enabled
                and email == defaults.email_enabled
                and not NotificationPreference.objects.filter(
                    user=user, category=category
                ).exists()
            ):
                continue
            item, _ = NotificationPreference.objects.update_or_create(
                user=user,
                category=category,
                defaults={"in_app_enabled": in_app, "email_enabled": email},
            )
            output.append(item)
    return output
