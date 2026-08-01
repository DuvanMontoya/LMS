# pyright: reportUnknownArgumentType=false
from domain.events.registry import EVENT_TYPES, ConsumerDefinition, register_consumer

from .services import route_domain_event

NOTIFICATION_EVENTS = frozenset(
    item
    for item in EVENT_TYPES
    if item.startswith(
        (
            "learning.enrollment.",
            "assessments.attempt.",
            "assessments.regrade.",
            "assessments.question_revision.changes_requested.",
            "assessments.assessment_revision.changes_requested.",
            "assets.asset_version.",
            "courses.revision.changes_requested.",
            "publishing.course_release.published.",
            "publishing.course_publication.withdrawn.",
        )
    )
)


def register_consumers() -> None:
    register_consumer(
        ConsumerDefinition(
            name="notifications.domain_event_router.v1",
            event_types=NOTIFICATION_EVENTS,
            handler=route_domain_event,
        )
    )
