from django.apps import AppConfig


class AssessmentsConfig(AppConfig):
    name = "domain.assessments"

    def ready(self) -> None:
        from domain.assets.usage import register_asset_usage_provider
        from domain.courses.activity_extensions import register_activity_provider
        from domain.courses.choices import ActivityType
        from domain.courses.readiness import register_readiness_provider
        from domain.scheduling.calendar_extensions import register_calendar_provider

        from .calendar import assessment_calendar_events
        from .course_activities import (
            clone_binding,
            readiness_issues,
            snapshot_binding,
        )
        from .usage import assessment_asset_usage

        register_activity_provider(
            ActivityType.ASSESSMENT,
            snapshot=snapshot_binding,
            clone=clone_binding,
        )
        register_readiness_provider("assessments.activities", readiness_issues)
        register_calendar_provider("assessments.windows", assessment_calendar_events)
        register_asset_usage_provider("assessments", assessment_asset_usage)
