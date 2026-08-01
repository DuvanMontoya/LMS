from django.urls import path

from .views import (
    EventDeliveriesView,
    EventDetailView,
    EventListView,
    ReplayCreateView,
    ReplayDetailView,
)

urlpatterns = [
    path("platform/events/", EventListView.as_view(), name="platform-events"),
    path(
        "platform/events/<uuid:event_id>/",
        EventDetailView.as_view(),
        name="platform-event-detail",
    ),
    path(
        "platform/events/<uuid:event_id>/deliveries/",
        EventDeliveriesView.as_view(),
        name="platform-event-deliveries",
    ),
    path(
        "platform/events/replays/",
        ReplayCreateView.as_view(),
        name="platform-event-replays",
    ),
    path(
        "platform/events/replays/<uuid:replay_id>/",
        ReplayDetailView.as_view(),
        name="platform-event-replay-detail",
    ),
]
