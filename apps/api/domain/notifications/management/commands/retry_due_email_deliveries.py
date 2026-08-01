# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
from argparse import ArgumentParser

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from domain.notifications.models import EmailDelivery, EmailDeliveryStatus
from domain.notifications.tasks import send_email_delivery


class Command(BaseCommand):
    help = "Agenda emails fallidos cuyo backoff ya venció."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--limit", type=int, default=500)

    def handle(self, *args: object, **options: object) -> None:
        raw_limit = options.get("limit")
        limit = max(1, min(raw_limit if isinstance(raw_limit, int) else 500, 10_000))
        ids = list(
            EmailDelivery.objects.filter(status=EmailDeliveryStatus.FAILED)
            .filter(
                Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=timezone.now())
            )
            .values_list("id", flat=True)[:limit]
        )
        for delivery_id in ids:
            send_email_delivery.delay(str(delivery_id))
        self.stdout.write(self.style.SUCCESS(f"Emails agendados: {len(ids)}"))
