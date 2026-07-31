from django.apps import AppConfig


class ContentConfig(AppConfig):
    name = "domain.content"

    def ready(self) -> None:
        from domain.assets.usage import register_asset_usage_provider
        from domain.courses.extensions import register_outline_enricher
        from domain.courses.readiness import register_readiness_provider

        from .readiness import content_readiness_issues, enrich_content_outline
        from .usage import content_asset_usage

        register_readiness_provider("unit-content", content_readiness_issues)
        register_outline_enricher("unit-content", enrich_content_outline)
        register_asset_usage_provider("content", content_asset_usage)
