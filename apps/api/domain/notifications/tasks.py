# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportCallIssue=false
from __future__ import annotations

import uuid
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from config.observability.metrics import email_deliveries, safe_attributes

from .models import EmailDelivery, EmailDeliveryStatus, NotificationDeliveryEvent


@shared_task(ignore_result=True, acks_late=True, autoretry_for=(), max_retries=0)
def send_email_delivery(delivery_id: str) -> None:
    delivery_uuid = uuid.UUID(delivery_id)
    with transaction.atomic():
        delivery = (
            EmailDelivery.objects.select_for_update()
            .select_related("notification", "recipient")
            .get(pk=delivery_uuid)
        )
        if delivery.status in {EmailDeliveryStatus.SENT, EmailDeliveryStatus.DEAD}:
            return
        delivery.status = EmailDeliveryStatus.SENDING
        delivery.attempt_count += 1
        delivery.started_at = timezone.now()
        delivery.save(update_fields=("status", "attempt_count", "started_at"))
        NotificationDeliveryEvent.objects.create(
            delivery=delivery, status=delivery.status
        )
    try:
        from allauth.account.models import EmailAddress

        address = (
            EmailAddress.objects.filter(
                user=delivery.recipient, verified=True, primary=True
            )
            .values_list("email", flat=True)
            .first()
        )
        if not address:
            raise ValueError("verified_primary_email_missing")
        action_url = (
            f"{settings.FRONTEND_ORIGIN.rstrip('/')}{delivery.notification.action_url}"
            if delivery.notification.action_url
            else settings.FRONTEND_ORIGIN
        )
        context = {"notification": delivery.notification, "action_url": action_url}
        text_body = render_to_string("notifications/email.txt", context)
        html_body = render_to_string("notifications/email.html", context)
        message_id = f"<{delivery.id}@{settings.EMAIL_MESSAGE_ID_DOMAIN}>"
        message = EmailMultiAlternatives(
            subject=delivery.notification.title,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[address],
            headers={
                "Message-ID": message_id,
                "Resend-Idempotency-Key": f"notification-{delivery.id}",
            },
        )
        message.attach_alternative(html_body, "text/html")
        message.send(fail_silently=False)
    except Exception as exc:
        with transaction.atomic():
            locked = EmailDelivery.objects.select_for_update().get(pk=delivery_uuid)
            permanent = isinstance(exc, ValueError)
            locked.status = (
                EmailDeliveryStatus.DEAD
                if permanent or locked.attempt_count >= 5
                else EmailDeliveryStatus.FAILED
            )
            locked.last_error_code = (
                "recipient_unavailable" if permanent else "email_backend_failed"
            )
            locked.failed_at = timezone.now()
            locked.next_attempt_at = (
                None
                if locked.status == EmailDeliveryStatus.DEAD
                else timezone.now()
                + timedelta(seconds=min(300, 2**locked.attempt_count))
            )
            locked.save()
            NotificationDeliveryEvent.objects.create(
                delivery=locked, status=locked.status, error_code=locked.last_error_code
            )
        email_deliveries.add(1, safe_attributes({"outcome": str(locked.status)}))
        if locked.status == EmailDeliveryStatus.FAILED:
            delay = max(
                1, int((locked.next_attempt_at - timezone.now()).total_seconds())
            )
            send_email_delivery.apply_async(args=[str(locked.id)], countdown=delay)
        return
    with transaction.atomic():
        locked = EmailDelivery.objects.select_for_update().get(pk=delivery_uuid)
        locked.status = EmailDeliveryStatus.SENT
        locked.sent_at = timezone.now()
        locked.message_id = message_id
        locked.next_attempt_at = None
        locked.last_error_code = ""
        locked.save()
        NotificationDeliveryEvent.objects.create(delivery=locked, status=locked.status)
    email_deliveries.add(1, safe_attributes({"outcome": "sent"}))
