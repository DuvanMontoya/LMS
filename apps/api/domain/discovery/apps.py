from django.apps import AppConfig


class DiscoveryConfig(AppConfig):
    name = "domain.discovery"

    def ready(self) -> None:
        from .consumers import register_consumers

        register_consumers()
