from django.apps import AppConfig


class PublishingConfig(AppConfig):
    name = "domain.publishing"
    label = "publishing"

    def ready(self) -> None:
        from domain.assets.usage import register_asset_usage_provider

        from .usage import published_asset_usage

        register_asset_usage_provider("publishing", published_asset_usage)
