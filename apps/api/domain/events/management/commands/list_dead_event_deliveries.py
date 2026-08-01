# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false
from argparse import ArgumentParser

from django.core.management.base import BaseCommand

from domain.events.models import DeliveryStatus, EventConsumerDelivery


class Command(BaseCommand):
    help = "Lista deliveries terminales sin exponer payloads."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args: object, **options: object) -> None:
        raw_limit = options.get("limit")
        limit = max(1, min(raw_limit if isinstance(raw_limit, int) else 100, 1_000))
        rows = EventConsumerDelivery.objects.filter(
            status=DeliveryStatus.DEAD
        ).order_by("created_at", "id")[:limit]
        for row in rows:
            self.stdout.write(
                f"{row.id} event={row.event_id} consumer={row.consumer_name} "
                f"attempts={row.attempt_count} error={row.last_error_code}"
            )
        self.stdout.write(self.style.SUCCESS(f"Deliveries terminales: {len(rows)}"))
