from importlib import import_module

from django.apps import AppConfig


class SchedulingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "domain.scheduling"
    label = "scheduling"

    def ready(self) -> None:
        import_module("domain.scheduling.checks")
