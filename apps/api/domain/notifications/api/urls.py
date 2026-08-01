from django.urls import path

from .views import (
    EmailDeliveryListView,
    EmailDeliveryRetryView,
    NotificationArchiveView,
    NotificationListView,
    NotificationPreferencesView,
    NotificationReadAllView,
    NotificationReadView,
    NotificationUnreadCountView,
    NotificationUnreadView,
)

urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name="notifications"),
    path(
        "notifications/unread-count/",
        NotificationUnreadCountView.as_view(),
        name="notifications-unread-count",
    ),
    path(
        "notifications/<uuid:notification_id>/read/",
        NotificationReadView.as_view(),
        name="notification-read",
    ),
    path(
        "notifications/<uuid:notification_id>/unread/",
        NotificationUnreadView.as_view(),
        name="notification-unread",
    ),
    path(
        "notifications/read-all/",
        NotificationReadAllView.as_view(),
        name="notifications-read-all",
    ),
    path(
        "notifications/<uuid:notification_id>/archive/",
        NotificationArchiveView.as_view(),
        name="notification-archive",
    ),
    path(
        "notifications/preferences/",
        NotificationPreferencesView.as_view(),
        name="notification-preferences",
    ),
    path(
        "platform/email-deliveries/",
        EmailDeliveryListView.as_view(),
        name="email-deliveries",
    ),
    path(
        "platform/email-deliveries/<uuid:delivery_id>/retry/",
        EmailDeliveryRetryView.as_view(),
        name="email-delivery-retry",
    ),
]
