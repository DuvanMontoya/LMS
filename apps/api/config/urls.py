"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView

urlpatterns = [
    path("api/v1/", include("domain.identity.api.urls")),
    path("api/v1/", include("domain.organizations.api.urls")),
    path("api/v1/", include("domain.catalog.api.urls")),
    path("api/v1/", include("domain.courses.api.urls")),
    path("api/v1/", include("domain.content.api.urls")),
    path("api/v1/", include("domain.publishing.api.urls")),
    path("api/v1/", include("domain.learning.api.urls")),
    path("api/v1/", include("domain.assessments.api.urls")),
    path("api/v1/", include("domain.assets.api.urls")),
    path("api/v1/", include("domain.events.api.urls")),
    path("api/v1/", include("domain.discovery.api.urls")),
    path("api/v1/", include("domain.notifications.api.urls")),
    path("api/v1/", include("domain.integrations.api.urls")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="platform-schema"),
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
