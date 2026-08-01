from django.urls import path

from .views import PublicRegistrationSettingsView, RegistrationSettingsView

urlpatterns = [
    path(
        "platform/registration-settings/public/",
        PublicRegistrationSettingsView.as_view(),
        name="registration-settings-public",
    ),
    path(
        "platform/registration-settings/",
        RegistrationSettingsView.as_view(),
        name="registration-settings",
    ),
]
