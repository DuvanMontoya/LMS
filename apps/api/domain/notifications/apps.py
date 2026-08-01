from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    name = "domain.notifications"

    def ready(self) -> None:
        from .consumers import register_consumers

        register_consumers()
