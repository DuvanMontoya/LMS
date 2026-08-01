# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportCallIssue=false
from argparse import ArgumentParser

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from domain.events.models import EventReplayRequest
from domain.events.registry import registered_consumers
from domain.events.tasks import process_event_replay
from domain.organizations.models import Organization


class Command(BaseCommand):
    help = "Crea un replay acotado y auditable para un consumidor registrado."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--organization", required=True)
        parser.add_argument("--consumer", required=True)
        parser.add_argument("--actor", required=True, help="UUID del operador")
        parser.add_argument("--reason", required=True)
        parser.add_argument("--event-type", default="")

    def handle(self, *args: object, **options: object) -> None:
        reason = str(options["reason"]).strip()
        consumer = str(options["consumer"])
        if len(reason) < 10:
            raise CommandError("Replay requiere una razón de al menos 10 caracteres.")
        if consumer not in registered_consumers():
            raise CommandError("Consumer desconocido.")
        organization = Organization.objects.filter(
            slug=str(options["organization"])
        ).first()
        actor = (
            get_user_model().objects.filter(pk=options["actor"], is_active=True).first()
        )
        if organization is None or actor is None or not actor.is_superuser:
            raise CommandError("Organización u operador de plataforma inválido.")
        replay = EventReplayRequest.objects.create(
            organization=organization,
            consumer_name=consumer,
            event_type=str(options["event_type"]),
            reason=reason,
            created_by=actor,
        )
        process_event_replay.delay(str(replay.id))
        self.stdout.write(self.style.SUCCESS(f"Replay solicitado: {replay.id}"))
