# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportIndexIssue=false, reportOptionalSubscript=false, reportCallIssue=false, reportOptionalMemberAccess=false
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from domain.organizations.capabilities import Capability
from domain.organizations.models import Organization
from domain.organizations.policies import has_capability, organizations_with_capability

from ..models import DomainEvent, EventReplayRequest
from ..tasks import process_event_replay
from .serializers import (
    DomainEventDetailSerializer,
    DomainEventSummarySerializer,
    EventConsumerDeliverySerializer,
    EventReplayCreateSerializer,
    EventReplaySerializer,
)


def _visible_organizations(
    request: Request, capability: Capability
) -> list[Organization]:
    return organizations_with_capability(request.user, capability)


class EventListView(APIView):
    @extend_schema(
        operation_id="platform_events_list",
        responses=DomainEventSummarySerializer(many=True),
    )
    def get(self, request: Request) -> Response:
        rows = DomainEvent.objects.filter(
            organization__in=_visible_organizations(
                request, Capability.PLATFORM_EVENTS_VIEW
            )
        ).order_by("-occurred_at")[:200]
        return Response(DomainEventSummarySerializer(rows, many=True).data)


class EventDetailView(APIView):
    @extend_schema(
        operation_id="platform_events_detail",
        responses=DomainEventDetailSerializer,
    )
    def get(self, request: Request, event_id: object) -> Response:
        event = get_object_or_404(
            DomainEvent,
            pk=event_id,
            organization__in=_visible_organizations(
                request, Capability.PLATFORM_EVENTS_VIEW
            ),
        )
        return Response(DomainEventDetailSerializer(event).data)


class EventDeliveriesView(APIView):
    @extend_schema(
        operation_id="platform_event_deliveries_list",
        responses=EventConsumerDeliverySerializer(many=True),
    )
    def get(self, request: Request, event_id: object) -> Response:
        event = get_object_or_404(
            DomainEvent,
            pk=event_id,
            organization__in=_visible_organizations(
                request, Capability.PLATFORM_EVENTS_VIEW
            ),
        )
        return Response(
            EventConsumerDeliverySerializer(event.deliveries.all(), many=True).data
        )


class ReplayCreateView(APIView):
    @extend_schema(
        operation_id="platform_event_replays_create",
        request=EventReplayCreateSerializer,
        responses={202: EventReplaySerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = EventReplayCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = get_object_or_404(
            Organization, slug=serializer.validated_data["organization_slug"]
        )
        if not has_capability(
            request.user, organization, Capability.PLATFORM_EVENTS_REPLAY
        ):
            return Response({"code": "event_not_found"}, status=404)
        replay = EventReplayRequest.objects.create(
            consumer_name=serializer.validated_data["consumer_name"],
            organization=organization,
            event_type=serializer.validated_data.get("event_type", ""),
            from_event_id=serializer.validated_data.get("from_event_id"),
            to_event_id=serializer.validated_data.get("to_event_id"),
            reason=serializer.validated_data["reason"],
            created_by=request.user,
        )
        process_event_replay.delay(str(replay.id))
        return Response(
            EventReplaySerializer(replay).data, status=status.HTTP_202_ACCEPTED
        )


class ReplayDetailView(APIView):
    @extend_schema(
        operation_id="platform_event_replays_detail",
        responses=EventReplaySerializer,
    )
    def get(self, request: Request, replay_id: object) -> Response:
        replay = get_object_or_404(
            EventReplayRequest,
            pk=replay_id,
            organization__in=_visible_organizations(
                request, Capability.PLATFORM_EVENTS_VIEW
            ),
        )
        return Response(EventReplaySerializer(replay).data)
