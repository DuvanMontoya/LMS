from django.urls import path

from . import views

BASE = "organizations/<slug:slug>/scheduling/"
EVENT = BASE + "events/<uuid:occurrence_id>/"
SESSION = BASE + "live-sessions/<uuid:session_id>/"

urlpatterns = [
    path(
        BASE + "course-activities/",
        views.LiveClassCourseActivityCreateView.as_view(),
    ),
    path(
        BASE + "course-activities/<uuid:activity_id>/binding/",
        views.LiveClassActivityBindingView.as_view(),
    ),
    path(BASE + "calendar/events/", views.CalendarEventListCreateView.as_view()),
    path(BASE + "participant-options/", views.ParticipantOptionListView.as_view()),
    path(BASE + "live-sessions/", views.LiveSessionListView.as_view()),
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
