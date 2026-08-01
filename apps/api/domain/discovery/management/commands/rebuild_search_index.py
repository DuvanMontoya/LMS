# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportMissingTypeArgument=false
from django.core.management.base import BaseCommand, CommandParser

from domain.organizations.models import Organization

from ...services import rebuild_search_index


class Command(BaseCommand):
    help = "Reconstruye el índice académico mediante una generación sombra."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--organization", required=True)

    def handle(self, *args: object, **options: object) -> None:
        organization = Organization.objects.get(slug=options["organization"])
        generation = rebuild_search_index(organization=organization)
        self.stdout.write(
            self.style.SUCCESS(
                f"generation={generation.number} documents={generation.document_count}"
            )
        )
