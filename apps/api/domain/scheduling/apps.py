from importlib import import_module

from django.apps import AppConfig


class SchedulingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "domain.scheduling"
    label = "scheduling"

    def ready(self) -> None:
        import_module("domain.scheduling.checks")
        from domain.courses.activity_extensions import register_activity_provider
        from domain.courses.choices import ActivityType
        from domain.courses.readiness import register_readiness_provider

        from .course_activities import (
            clone_binding,
            readiness_issues,
            snapshot_binding,
        )

        register_activity_provider(
            ActivityType.LIVE_CLASS,
            snapshot=snapshot_binding,
            clone=clone_binding,
        )
        register_readiness_provider("scheduling.activities", readiness_issues)
