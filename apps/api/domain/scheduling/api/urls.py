from django.urls import path

from . import views

BASE = "organizations/<slug:slug>/scheduling/"
EVENT = BASE + "events/<uuid:occurrence_id>/"
SESSION = BASE + "live-sessions/<uuid:session_id>/"

urlpatterns = [
    path(BASE + "calendar/events/", views.CalendarEventListCreateView.as_view()),
    path(EVENT, views.CalendarEventDetailView.as_view()),
    path(EVENT + "cancel/", views.CalendarEventCancelView.as_view()),
    path(SESSION, views.LiveSessionDetailView.as_view()),
    path(SESSION + "start/", views.LiveSessionStartView.as_view()),
    path(SESSION + "join/", views.LiveSessionJoinView.as_view()),
    path(SESSION + "end/", views.LiveSessionEndView.as_view()),
    path(SESSION + "attendance/", views.LiveAttendanceView.as_view()),
    path(
        SESSION + "participants/<path:identity>/permissions/",
        views.LiveParticipantPermissionView.as_view(),
    ),
    path(
        SESSION + "participants/<path:identity>/",
        views.LiveParticipantRemoveView.as_view(),
    ),
    path("livekit/webhook/", views.LiveKitWebhookView.as_view()),
]
