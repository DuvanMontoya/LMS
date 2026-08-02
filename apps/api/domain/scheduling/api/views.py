# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportIndexIssue=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUnknownLambdaType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from domain.courses.models import Course, CourseActivity
from domain.learning.contracts import course_group_for_scheduling
from domain.learning.models import CourseGroupActivity
from domain.organizations.choices import MembershipStatus
from domain.organizations.models import Membership, Organization
from domain.organizations.policies import active_membership
from domain.organizations.selectors import organization_visible_to
from domain.scheduling.calendar_extensions import external_calendar_events
from domain.scheduling.course_activities import bind_live_class_activity
from domain.scheduling.exceptions import SchedulingDomainError
from domain.scheduling.models import AcademicEventOccurrence, LiveSession
from domain.scheduling.policies import can_create_schedule
from domain.scheduling.selectors import (
    attendance_summary,
    live_session_detail,
    live_sessions_visible_to_actor,
    occurrence_payload,
    occurrences_visible_to_actor,
    visible_occurrences_in_range,
)
from domain.scheduling.services import (
    cancel_occurrence,
    change_participant_permissions,
    create_event_series,
    end_live_session,
    expel_participant,
    join_live_session,
    reschedule_occurrence,
    start_live_session,
)
from domain.scheduling.webhooks import receive_and_process_webhook

from .serializers import (
    AttendanceSummarySerializer,
    CalendarEventSerializer,
    CalendarRangeSerializer,
    EventCancelSerializer,
    EventCreateSerializer,
    EventRescheduleSerializer,
    LiveClassActivityBindingInputSerializer,
    LiveClassActivityBindingSerializer,
    LiveConnectionSerializer,
    LiveSessionDetailSerializer,
    LiveSessionListQuerySerializer,
    OperationAcceptedSerializer,
    ParticipantOptionSerializer,
    ParticipantPermissionSerializer,
    SchedulingErrorSerializer,
    WebhookResultSerializer,
)


def _organization(request: Request, slug: str) -> Organization:
    return organization_visible_to(request.user, slug)


def _error(error: SchedulingDomainError) -> Response:
    return Response(
        {"code": error.code, "detail": str(error)}, status=error.status_code
    )


def _domain_call(operation: Callable[[], Any]) -> Response | Any:
    try:
        return operation()
    except SchedulingDomainError as error:
        return _error(error)


class LiveClassActivityBindingView(APIView):
    @extend_schema(
        operation_id="scheduling_course_activity_binding_create",
        request=LiveClassActivityBindingInputSerializer,
        responses={201: LiveClassActivityBindingSerializer},
    )
    def post(self, request: Request, slug: str, activity_id: uuid.UUID) -> Response:
        organization = _organization(request, slug)
        serializer = LiveClassActivityBindingInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        activity = get_object_or_404(
            CourseActivity.objects.select_related("module__revision__course"),
            pk=activity_id,
            module__revision__course__organization=organization,
        )
        result = _domain_call(
            lambda: bind_live_class_activity(
                actor=request.user,
                organization=organization,
                activity=activity,
                expected_revision_version=serializer.validated_data[
                    "expected_revision_version"
                ],
                minimum_attended_occurrences=serializer.validated_data[
                    "minimum_attended_occurrences"
                ],
                minimum_attendance_minutes=serializer.validated_data.get(
                    "minimum_attendance_minutes"
                ),
            )
        )
        if isinstance(result, Response):
            return result
        binding, revision_lock_version = result
        return Response(
            LiveClassActivityBindingSerializer(
                {
                    "id": binding.id,
                    "activity_id": binding.activity_id,
                    "minimum_attended_occurrences": binding.minimum_attended_occurrences,
                    "minimum_attendance_minutes": binding.minimum_attendance_minutes,
                    "revision_lock_version": revision_lock_version,
                }
            ).data,
            status=status.HTTP_201_CREATED,
        )


class CalendarEventListCreateView(APIView):
    @extend_schema(
        operation_id="scheduling_calendar_events_list",
        parameters=[
            OpenApiParameter("start", str, required=True),
            OpenApiParameter("end", str, required=True),
            OpenApiParameter("timeZone", str, required=True),
            OpenApiParameter("course", uuid.UUID, required=False),
        ],
        responses={
            200: CalendarEventSerializer(many=True),
            400: SchedulingErrorSerializer,
        },
    )
    def get(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        serializer = CalendarRangeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            occurrences = visible_occurrences_in_range(
                actor=request.user,
                organization=organization,
                starts_at=data["start"],
                ends_at=data["end"],
                timezone_name=data["timeZone"],
            )
        except (ValueError, SchedulingDomainError) as error:
            return Response(
                {"code": "calendar_range_invalid", "detail": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if course_id := data.get("course"):
            occurrences = occurrences.filter(series__course_id=course_id)
        payload = [occurrence_payload(item, request.user) for item in occurrences]
        payload.extend(
            external_calendar_events(
                actor=request.user,
                organization=organization,
                starts_at=data["start"],
                ends_at=data["end"],
                course_id=data.get("course"),
            )
        )
        payload.sort(key=lambda item: (item["start"], str(item["id"])))
        return Response(CalendarEventSerializer(payload, many=True).data)

    @extend_schema(
        operation_id="scheduling_calendar_events_create",
        request=EventCreateSerializer,
        responses={
            201: CalendarEventSerializer(many=True),
            400: SchedulingErrorSerializer,
        },
    )
    def post(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        serializer = EventCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        course_slug = data.get("course_slug")
        course = (
            get_object_or_404(
                Course.objects.select_related("organization"),
                organization=organization,
                slug=course_slug,
            )
            if course_slug
            else None
        )
        course_group = (
            course_group_for_scheduling(
                organization=organization, course_group_id=data["course_group_id"]
            )
            if data.get("course_group_id")
            else None
        )
        if data.get("course_group_id") and course_group is None:
            return Response(
                {
                    "code": "course_group_invalid",
                    "detail": "El grupo de curso no está disponible.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        course_group_activity = None
        if data.get("course_group_activity_id"):
            if course_group is None:
                return Response(
                    {
                        "code": "course_group_activity_invalid",
                        "detail": "La actividad exige un grupo de curso.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            course_group_activity = get_object_or_404(
                CourseGroupActivity,
                pk=data["course_group_activity_id"],
                course_group=course_group,
                course_release=course_group.release,
                activity_type="live_class",
                migration_review_required=False,
            )
        participant_ids = data.get("participant_membership_ids", [])
        participants = list(
            Membership.objects.select_related("organization", "user").filter(
                organization=organization, pk__in=participant_ids
            )
        )
        if len(participants) != len(set(participant_ids)):
            return Response(
                {
                    "code": "participant_invalid",
                    "detail": "Uno o más participantes no pertenecen a la organización.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        host = (
            get_object_or_404(
                Membership.objects.select_related("organization", "user"),
                organization=organization,
                pk=data["host_membership_id"],
            )
            if data.get("host_membership_id")
            else active_membership(request.user, organization)
        )
        if host is None:
            return Response(
                {"code": "host_required", "detail": "Falta el profesor."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = _domain_call(
            lambda: create_event_series(
                actor=request.user,
                organization=organization,
                course=course,
                course_group=course_group,
                course_group_activity=course_group_activity,
                host_membership=host,
                participant_memberships=participants,
                title=data["title"],
                description=data.get("description", ""),
                event_type=data["event_type"],
                timezone_name=data["timezone_name"],
                first_starts_at=data["starts_at"],
                duration_minutes=data["duration_minutes"],
                recurrence_rule=data.get("rrule", ""),
                counts_toward_progress=data.get("counts_toward_progress", False),
                contributes_to_activity_progress=data.get(
                    "contributes_to_activity_progress"
                ),
                attendance_threshold_minutes=data.get("attendance_threshold_minutes"),
            )
        )
        if isinstance(result, Response):
            return result
        occurrences = result.occurrences.select_related(
            "series__course", "series__host_membership__user", "live_session"
        )
        payload = [occurrence_payload(item, request.user) for item in occurrences]
        return Response(
            CalendarEventSerializer(payload, many=True).data,
            status=status.HTTP_201_CREATED,
        )


class ParticipantOptionListView(APIView):
    @extend_schema(
        operation_id="scheduling_participant_options_list",
        responses={200: ParticipantOptionSerializer(many=True)},
    )
    def get(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        if not can_create_schedule(request.user, organization):
            return Response(
                {"code": "permission_denied", "detail": "Acceso denegado."},
                status=status.HTTP_403_FORBIDDEN,
            )
        memberships = (
            Membership.objects.filter(
                organization=organization, status=MembershipStatus.ACTIVE
            )
            .select_related("user")
            .order_by("user__email")[:500]
        )
        payload = [
            {
                "membership_id": membership.id,
                "display": membership.user.get_full_name() or membership.user.email,
            }
            for membership in memberships
        ]
        return Response(ParticipantOptionSerializer(payload, many=True).data)


class CalendarEventDetailView(APIView):
    @extend_schema(
        operation_id="scheduling_calendar_event_retrieve",
        responses={200: CalendarEventSerializer, 404: SchedulingErrorSerializer},
    )
    def get(self, request: Request, slug: str, occurrence_id: uuid.UUID) -> Response:
        organization = _organization(request, slug)
        occurrence = get_object_or_404(
            occurrences_visible_to_actor(actor=request.user, organization=organization),
            pk=occurrence_id,
        )
        return Response(
            CalendarEventSerializer(occurrence_payload(occurrence, request.user)).data
        )

    @extend_schema(
        operation_id="scheduling_calendar_event_reschedule",
        request=EventRescheduleSerializer,
        responses={200: CalendarEventSerializer, 409: SchedulingErrorSerializer},
    )
    def patch(self, request: Request, slug: str, occurrence_id: uuid.UUID) -> Response:
        organization = _organization(request, slug)
        get_object_or_404(
            AcademicEventOccurrence,
            pk=occurrence_id,
            series__organization=organization,
        )
        serializer = EventRescheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _domain_call(
            lambda: reschedule_occurrence(
                actor=request.user,
                occurrence_id=occurrence_id,
                **serializer.validated_data,
            )
        )
        if isinstance(result, Response):
            return result
        return Response(
            CalendarEventSerializer(occurrence_payload(result, request.user)).data
        )


class CalendarEventCancelView(APIView):
    @extend_schema(
        operation_id="scheduling_calendar_event_cancel",
        request=EventCancelSerializer,
        responses={200: CalendarEventSerializer, 409: SchedulingErrorSerializer},
    )
    def post(self, request: Request, slug: str, occurrence_id: uuid.UUID) -> Response:
        organization = _organization(request, slug)
        get_object_or_404(
            AcademicEventOccurrence,
            pk=occurrence_id,
            series__organization=organization,
        )
        serializer = EventCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _domain_call(
            lambda: cancel_occurrence(
                actor=request.user,
                occurrence_id=occurrence_id,
                **serializer.validated_data,
            )
        )
        if isinstance(result, Response):
            return result
        return Response(
            CalendarEventSerializer(occurrence_payload(result, request.user)).data
        )


class LiveSessionDetailView(APIView):
    @extend_schema(
        operation_id="scheduling_live_session_retrieve",
        responses={200: LiveSessionDetailSerializer, 404: SchedulingErrorSerializer},
    )
    def get(self, request: Request, slug: str, session_id: uuid.UUID) -> Response:
        organization = _organization(request, slug)
        try:
            payload = live_session_detail(
                actor=request.user, organization=organization, session_id=session_id
            )
        except LiveSession.DoesNotExist:
            return Response(
                {"code": "not_found", "detail": "Clase no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(LiveSessionDetailSerializer(payload).data)


class LiveSessionListView(APIView):
    @extend_schema(
        operation_id="scheduling_live_sessions_list",
        parameters=[LiveSessionListQuerySerializer],
        responses={200: LiveSessionDetailSerializer(many=True)},
    )
    def get(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        serializer = LiveSessionListQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        payload = live_sessions_visible_to_actor(
            actor=request.user,
            organization=organization,
            course_slug=serializer.validated_data.get("course_slug", ""),
            scope=serializer.validated_data["scope"],
        )
        return Response(LiveSessionDetailSerializer(payload, many=True).data)


class LiveSessionStartView(APIView):
    @extend_schema(
        operation_id="scheduling_live_session_start",
        request=None,
        responses={200: LiveConnectionSerializer, 409: SchedulingErrorSerializer},
    )
    def post(self, request: Request, slug: str, session_id: uuid.UUID) -> Response:
        organization = _organization(request, slug)
        get_object_or_404(
            LiveSession, pk=session_id, occurrence__series__organization=organization
        )
        result = _domain_call(
            lambda: start_live_session(actor=request.user, session_id=session_id)
        )
        return result if isinstance(result, Response) else Response(result)


class LiveSessionJoinView(APIView):
    @extend_schema(
        operation_id="scheduling_live_session_join",
        request=None,
        responses={200: LiveConnectionSerializer, 409: SchedulingErrorSerializer},
    )
    def post(self, request: Request, slug: str, session_id: uuid.UUID) -> Response:
        organization = _organization(request, slug)
        get_object_or_404(
            LiveSession, pk=session_id, occurrence__series__organization=organization
        )
        result = _domain_call(
            lambda: join_live_session(actor=request.user, session_id=session_id)
        )
        return result if isinstance(result, Response) else Response(result)


class LiveSessionEndView(APIView):
    @extend_schema(
        operation_id="scheduling_live_session_end",
        request=None,
        responses={200: OperationAcceptedSerializer, 409: SchedulingErrorSerializer},
    )
    def post(self, request: Request, slug: str, session_id: uuid.UUID) -> Response:
        organization = _organization(request, slug)
        get_object_or_404(
            LiveSession, pk=session_id, occurrence__series__organization=organization
        )
        result = _domain_call(
            lambda: end_live_session(actor=request.user, session_id=session_id)
        )
        return (
            result
            if isinstance(result, Response)
            else Response({"status": result.status})
        )


class LiveParticipantPermissionView(APIView):
    @extend_schema(
        operation_id="scheduling_live_participant_permissions",
        request=ParticipantPermissionSerializer,
        responses={200: OperationAcceptedSerializer, 403: SchedulingErrorSerializer},
    )
    def post(
        self, request: Request, slug: str, session_id: uuid.UUID, identity: str
    ) -> Response:
        organization = _organization(request, slug)
        get_object_or_404(
            LiveSession, pk=session_id, occurrence__series__organization=organization
        )
        serializer = ParticipantPermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _domain_call(
            lambda: change_participant_permissions(
                actor=request.user,
                session_id=session_id,
                identity=identity,
                **serializer.validated_data,
            )
        )
        return (
            result if isinstance(result, Response) else Response({"status": "updated"})
        )


class LiveParticipantRemoveView(APIView):
    @extend_schema(
        operation_id="scheduling_live_participant_remove",
        responses={200: OperationAcceptedSerializer, 403: SchedulingErrorSerializer},
    )
    def delete(
        self, request: Request, slug: str, session_id: uuid.UUID, identity: str
    ) -> Response:
        organization = _organization(request, slug)
        get_object_or_404(
            LiveSession, pk=session_id, occurrence__series__organization=organization
        )
        result = _domain_call(
            lambda: expel_participant(
                actor=request.user, session_id=session_id, identity=identity
            )
        )
        return (
            result if isinstance(result, Response) else Response({"status": "removed"})
        )


class LiveAttendanceView(APIView):
    @extend_schema(
        operation_id="scheduling_live_attendance_list",
        responses={200: AttendanceSummarySerializer(many=True)},
    )
    def get(self, request: Request, slug: str, session_id: uuid.UUID) -> Response:
        organization = _organization(request, slug)
        detail = live_session_detail(
            actor=request.user, organization=organization, session_id=session_id
        )
        if not detail["canModerate"]:
            return Response(
                {"code": "permission_denied", "detail": "Acceso denegado."},
                status=status.HTTP_403_FORBIDDEN,
            )
        session = get_object_or_404(LiveSession, pk=session_id)
        return Response(
            AttendanceSummarySerializer(attendance_summary(session), many=True).data
        )


@method_decorator(csrf_exempt, name="dispatch")
class LiveKitWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        operation_id="scheduling_livekit_webhook",
        exclude=True,
        responses={200: WebhookResultSerializer, 401: SchedulingErrorSerializer},
    )
    def post(self, request: Request) -> Response:
        content_type = request.content_type.split(";", 1)[0].lower()
        if content_type != "application/webhook+json":
            return Response(
                {"code": "unsupported_media_type", "detail": "Content-Type inválido."},
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )
        authorization = request.headers.get("Authorization", "")
        result = _domain_call(
            lambda: receive_and_process_webhook(
                body=request.body, authorization=authorization
            )
        )
        if isinstance(result, Response):
            return result
        _event, created = result
        return Response({"status": "processed", "duplicate": not created})
