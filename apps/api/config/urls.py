from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("api/v1/", include("domain.identity.api.urls")),
    path("api/v1/", include("domain.organizations.api.urls")),
    path("api/v1/", include("domain.catalog.api.urls")),
    path("api/v1/", include("domain.courses.api.urls")),
    path("api/v1/", include("domain.content.api.urls")),
    path("api/v1/", include("domain.publishing.api.urls")),
    path("api/v1/", include("domain.learning.api.urls")),
    path("api/v1/", include("domain.scheduling.api.urls")),
    path("api/v1/", include("domain.assessments.api.urls")),
    path("api/v1/", include("domain.assets.api.urls")),
    path("api/v1/", include("domain.events.api.urls")),
    path("api/v1/", include("domain.discovery.api.urls")),
    path("api/v1/", include("domain.notifications.api.urls")),
    path("api/v1/", include("domain.integrations.api.urls")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="platform-schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="platform-schema"),
        name="platform-swagger-ui",
    ),
    path(
        "api/v1/redoc/",
        SpectacularRedocView.as_view(url_name="platform-schema"),
        name="platform-redoc",
    ),
    path("admin/", admin.site.urls),
    path("health/", include("config.health.urls")),
    path("accounts/", include("allauth.urls")),
    path("_allauth/", include("domain.identity.headless_urls")),
]

if settings.SETTINGS_MODULE == "config.settings.e2e":
    from config import e2e_integration_stub

    urlpatterns.extend(
        [
            path(
                "_e2e/integrations/<str:provider>/v1/models",
                e2e_integration_stub.models,
            ),
            path(
                "_e2e/integrations/<str:provider>/<str:version>/models",
                e2e_integration_stub.models,
            ),
            path(
                "_e2e/integrations/<str:provider>/models",
                e2e_integration_stub.models,
            ),
            path(
                "_e2e/integrations/google/authorize",
                e2e_integration_stub.google_authorize,
            ),
            path(
                "_e2e/integrations/google/token",
                e2e_integration_stub.google_token,
            ),
            path(
                "_e2e/integrations/google/<path:resource>",
                e2e_integration_stub.google_resource,
            ),
        ]
    )
