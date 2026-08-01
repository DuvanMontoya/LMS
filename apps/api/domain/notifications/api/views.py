# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportIndexIssue=false, reportOptionalSubscript=false, reportCallIssue=false, reportUnknownLambdaType=false, reportOptionalMemberAccess=false
from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from domain.organizations.capabilities import Capability
from domain.organizations.policies import has_capability, organizations_with_capability

from ..models import (
    EmailDelivery,
    EmailDeliveryStatus,
    Notification,
    NotificationPreference,
)
from ..preferences import DEFAULTS
from ..services import (
    archive_notification,
    mark_all_read,
    mark_read,
    replace_preferences,
)
from ..tasks import send_email_delivery
from .serializers import (
    CountSerializer,
    EmailDeliverySerializer,
    NotificationPageSerializer,
    NotificationSerializer,
    PreferencesResponseSerializer,
    PreferencesUpdateSerializer,
    UpdatedSerializer,
)


def _own_notification(request: Request, notification_id: object) -> Notification:
    return get_object_or_404(Notification, pk=notification_id, recipient=request.user)


class NotificationListView(APIView):
    @extend_schema(
        operation_id="notifications_list",
        parameters=[OpenApiParameter("page", OpenApiTypes.INT)],
        responses=NotificationPageSerializer,
    )
    def get(self, request: Request) -> Response:
        try:
            page = max(1, int(request.query_params.get("page", "1")))
        except ValueError:
            return Response({"code": "notification_page_invalid"}, status=400)
        page_size = 20
        queryset = Notification.objects.filter(
            recipient=request.user, archived_at__isnull=True
        ).order_by("-created_at", "-id")
        total = queryset.count()
        start = (page - 1) * page_size
        payload = {
            "results": NotificationSerializer(
                queryset[start : start + page_size], many=True
            ).data,
            "pagination": {"page": page, "page_size": page_size, "total": total},
        }
        return Response(NotificationPageSerializer(payload).data)


class NotificationUnreadCountView(APIView):
    @extend_schema(operation_id="notifications_unread_count", responses=CountSerializer)
    def get(self, request: Request) -> Response:
        count = Notification.objects.filter(
            recipient=request.user, read_at__isnull=True, archived_at__isnull=True
        ).count()
        return Response({"count": count})


class NotificationReadView(APIView):
    read = True

    @extend_schema(
        operation_id="notifications_mark_read",
        request=None,
        responses=NotificationSerializer,
    )
    def post(self, request: Request, notification_id: object) -> Response:
        return Response(
            NotificationSerializer(
                mark_read(
                    notification=_own_notification(request, notification_id),
                    read=self.read,
                )
            ).data
        )


class NotificationUnreadView(NotificationReadView):
    read = False

    @extend_schema(
        operation_id="notifications_mark_unread",
        request=None,
        responses=NotificationSerializer,
    )
    def post(self, request: Request, notification_id: object) -> Response:
        return super().post(request, notification_id)


class NotificationReadAllView(APIView):
    @extend_schema(
        operation_id="notifications_mark_all_read",
        request=None,
        responses=UpdatedSerializer,
    )
    def post(self, request: Request) -> Response:
        return Response({"updated": mark_all_read(user=request.user)})


class NotificationArchiveView(APIView):
    @extend_schema(
        operation_id="notifications_archive",
        request=None,
        responses=NotificationSerializer,
    )
    def post(self, request: Request, notification_id: object) -> Response:
        return Response(
            NotificationSerializer(
                archive_notification(
                    notification=_own_notification(request, notification_id)
                )
            ).data
        )


class NotificationPreferencesView(APIView):
    @extend_schema(
        operation_id="notification_preferences_retrieve",
        responses=PreferencesResponseSerializer,
    )
    def get(self, request: Request) -> Response:
        overrides = {
            item.category: item
            for item in NotificationPreference.objects.filter(user=request.user)
        }
        return Response(
            {
                "preferences": [
                    {
                        "category": category,
                        "in_app_enabled": overrides.get(category).in_app_enabled
                        if category in overrides
                        else default.in_app_enabled,
                        "email_enabled": overrides.get(category).email_enabled
                        if category in overrides
                        else default.email_enabled,
                    }
                    for category, default in DEFAULTS.items()
                ]
            }
        )

    @extend_schema(
        operation_id="notification_preferences_update",
        request=PreferencesUpdateSerializer,
        responses=PreferencesResponseSerializer,
    )
    def put(self, request: Request) -> Response:
        serializer = PreferencesUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = {
            item["category"]: {
                "in_app_enabled": item["in_app_enabled"],
                "email_enabled": item["email_enabled"],
            }
            for item in serializer.validated_data["preferences"]
        }
        replace_preferences(user=request.user, values=values)
        return self.get(request)


class EmailDeliveryListView(APIView):
    @extend_schema(
        operation_id="platform_email_deliveries_list",
        responses=EmailDeliverySerializer(many=True),
    )
    def get(self, request: Request) -> Response:
        organizations = organizations_with_capability(
            request.user, Capability.PLATFORM_OPERATIONS_VIEW
        )
        rows = EmailDelivery.objects.filter(
            notification__organization__in=organizations
        ).order_by("-created_at")[:200]
        return Response(EmailDeliverySerializer(rows, many=True).data)


class EmailDeliveryRetryView(APIView):
    @extend_schema(
        operation_id="platform_email_delivery_retry",
        request=None,
        responses={202: EmailDeliverySerializer},
    )
    def post(self, request: Request, delivery_id: object) -> Response:
        delivery = get_object_or_404(
            EmailDelivery.objects.select_related("notification__organization"),
            pk=delivery_id,
        )
        if not has_capability(
            request.user,
            delivery.notification.organization,
            Capability.PLATFORM_OPERATIONS_MANAGE,
        ):
            return Response({"code": "email_delivery_not_found"}, status=404)
        if delivery.status not in {
            EmailDeliveryStatus.FAILED,
            EmailDeliveryStatus.DEAD,
        }:
            return Response({"code": "email_delivery_retry_invalid"}, status=409)
        delivery.status = EmailDeliveryStatus.QUEUED
        delivery.next_attempt_at = None
        delivery.last_error_code = ""
        delivery.save()
        send_email_delivery.delay(str(delivery.id))
        return Response(
            EmailDeliverySerializer(delivery).data, status=status.HTTP_202_ACCEPTED
        )
