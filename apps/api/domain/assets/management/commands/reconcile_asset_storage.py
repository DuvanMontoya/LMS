from __future__ import annotations

import json

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandParser


class Command(BaseCommand):
    help = "Report asset storage drift; safe repairs must be requested explicitly."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--repair", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        if options["repair"]:
            # The only repair enabled in this phase is expiring sessions whose
            # server-side deadline has elapsed. No object deletion or promotion.
            call_command("expire_stale_upload_sessions", stdout=self.stdout)
        self.stdout.write(
            json.dumps(
                {
                    "mode": "safe-repair" if options["repair"] else "report-only",
                    "destructive_garbage_collection": False,
                    "next": "Run verify_asset_storage for object-level evidence.",
                },
                sort_keys=True,
            )
        )
