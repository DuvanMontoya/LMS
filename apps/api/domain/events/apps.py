# pyright: reportUnusedImport=false
from django.apps import AppConfig


class EventsConfig(AppConfig):
    name = "domain.events"

    def ready(self) -> None:
        from . import registry  # noqa: F401
