from django.urls import path

from . import views

urlpatterns = [
    path(
        "organizations/<slug:slug>/integrations/",
        views.IntegrationListView.as_view(),
        name="integration-list",
    ),
    path(
        "organizations/<slug:slug>/integrations/api-key/",
        views.ApiKeyConnectView.as_view(),
        name="integration-api-key-connect",
    ),
    path(
        "organizations/<slug:slug>/integrations/<uuid:connection_id>/health-checks/",
        views.IntegrationHealthCheckView.as_view(),
        name="integration-health-check",
    ),
    path(
        "organizations/<slug:slug>/integrations/<uuid:connection_id>/disconnect/",
        views.IntegrationDisconnectView.as_view(),
        name="integration-disconnect",
    ),
    path(
        "organizations/<slug:slug>/integrations/<uuid:connection_id>/rotate-key/",
        views.ApiKeyRotateView.as_view(),
        name="integration-api-key-rotate",
    ),
    path(
        "organizations/<slug:slug>/integrations/google/authorize/",
        views.GoogleOAuthStartView.as_view(),
        name="integration-google-authorize",
    ),
    path(
        "integrations/google/callback/",
        views.GoogleOAuthCallbackView.as_view(),
        name="integration-google-callback",
    ),
    path(
        "organizations/<slug:slug>/integrations/<uuid:connection_id>/test-meeting/",
        views.GoogleTestMeetingView.as_view(),
        name="integration-google-test-meeting",
    ),
]
