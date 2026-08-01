# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
from argparse import ArgumentParser

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from domain.events.models import DeliveryStatus, EventConsumerDelivery
from domain.events.tasks import dispatch_domain_event


class Command(BaseCommand):
    help = "Agenda eventos con deliveries vencidos, sin reejecutar completados."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--limit", type=int, default=500)

    def handle(self, *args: object, **options: object) -> None:
        raw_limit = options.get("limit")
        limit = max(1, min(raw_limit if isinstance(raw_limit, int) else 500, 10_000))
        event_ids = list(
            EventConsumerDelivery.objects.filter(
                Q(status=DeliveryStatus.PENDING)
                | Q(
                    status=DeliveryStatus.FAILED,
                    next_attempt_at__lte=timezone.now(),
                )
                | Q(
                    status=DeliveryStatus.PROCESSING,
                    lease_expires_at__lte=timezone.now(),
                )
            )
            .values_list("event_id", flat=True)
            .distinct()[:limit]
        )
        for event_id in event_ids:
            dispatch_domain_event.delay(str(event_id))
        self.stdout.write(self.style.SUCCESS(f"Eventos agendados: {len(event_ids)}"))
