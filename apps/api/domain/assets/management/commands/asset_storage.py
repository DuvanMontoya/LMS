from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError, CommandParser

from domain.assets.exceptions import AssetDomainError
from domain.assets.storage.administration import (
    initialize_storage,
    reset_local_storage,
    storage_smoke,
    storage_status,
    validate_storage_configuration,
)


class Command(BaseCommand):
    help = "Validate, initialize and inspect private academic asset storage."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "action",
            choices=["validate", "init", "status", "smoke", "reset-local"],
        )

    def handle(self, *args: object, **options: object) -> None:
        action = str(options["action"])
        try:
            if action == "validate":
                validate_storage_configuration()
                payload: object = {"valid": True}
            elif action == "init":
                payload = [state.__dict__ for state in initialize_storage()]
            elif action == "status":
                payload = [state.__dict__ for state in storage_status()]
            elif action == "smoke":
                payload = storage_smoke()
            else:
                reset_local_storage()
                payload = {"reset": True}
        except AssetDomainError as error:
            raise CommandError(str(error)) from error
        self.stdout.write(json.dumps(payload, sort_keys=True))
