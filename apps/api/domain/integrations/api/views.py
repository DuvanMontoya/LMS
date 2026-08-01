from __future__ import annotations

from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from domain.integrations.exceptions import (
    IntegrationAccessDenied,
    IntegrationConfigurationIncomplete,
    IntegrationConnectionUnavailable,
    IntegrationDomainError,
    IntegrationRevisionConflict,
)
from domain.integrations.models import IntegrationConnection, IntegrationProvider
from domain.integrations.services import (
    begin_google_oauth,
    complete_google_oauth,
    connect_api_key,
    create_google_test_meeting,
    disconnect,
    queue_health_check,
)
from domain.organizations.capabilities import Capability
from domain.organizations.policies import has_capability
from domain.organizations.selectors import organization_visible_to

from .serializers import (
    ApiKeyConnectSerializer,
    ApiKeyRotateSerializer,
    GoogleOAuthStartResponseSerializer,
    GoogleOAuthStartSerializer,
    HealthCheckSerializer,
    IntegrationConnectionSerializer,
)

# DRF request/serializer data and reverse relations are dynamic upstream.
# The integration services enforce the domain contract below this boundary.
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportIndexIssue=false, reportOptionalSubscript=false, reportAttributeAccessIssue=false, reportCallIssue=false, reportPrivateImportUsage=false, reportArgumentType=false, reportOptionalMemberAccess=false


def _error(error: IntegrationDomainError) -> Response:
    mapping = {
        IntegrationAccessDenied: (
            status.HTTP_403_FORBIDDEN,
            "permission_denied",
            "No tienes permiso para administrar esta integración.",
        ),
        IntegrationRevisionConflict: (
            status.HTTP_409_CONFLICT,
            "revision_conflict",
            "La conexión cambió antes de guardar. Actualiza la página e inténtalo de nuevo.",
        ),
        IntegrationConfigurationIncomplete: (
            status.HTTP_409_CONFLICT,
            "configuration_incomplete",
            "Google Workspace requiere GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET y GOOGLE_OAUTH_REDIRECT_URI configurados en el servidor.",
        ),
        IntegrationConnectionUnavailable: (
            status.HTTP_400_BAD_REQUEST,
            "connection_unavailable",
            "La conexión no está disponible para esta operación.",
        ),
    }
    mapped = mapping.get(type(error))
    if mapped is None:
        return Response(
            {
                "code": "connection_unavailable",
                "detail": "No fue posible completar la operación.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    http_status, code, detail = mapped
    return Response(
        {"code": code, "detail": detail},
        status=http_status,
    )


def _organization(request: Request, slug: str):
    return organization_visible_to(request.user, slug)


def _connection(
    request: Request, slug: str, connection_id: str
) -> IntegrationConnection:
    organization = _organization(request, slug)
    return get_object_or_404(
        IntegrationConnection.objects.select_related("organization"),
        pk=connection_id,
        organization=organization,
    )


class IntegrationListView(APIView):
    @extend_schema(responses={200: IntegrationConnectionSerializer(many=True)})
    def get(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        if not has_capability(request.user, organization, Capability.INTEGRATION_VIEW):
            raise PermissionDenied("permission_denied")
        connections = IntegrationConnection.objects.filter(
            organization=organization
        ).order_by("provider")
        return Response(IntegrationConnectionSerializer(connections, many=True).data)


class ApiKeyConnectView(APIView):
    @extend_schema(
        request=ApiKeyConnectSerializer,
        responses={200: IntegrationConnectionSerializer},
    )
    def post(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        serializer = ApiKeyConnectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            connection = connect_api_key(
                actor=request.user,
                organization=organization,
                provider=IntegrationProvider(serializer.validated_data["provider"]),
                api_key=serializer.validated_data["api_key"],
                expected_version=serializer.validated_data.get("expected_version"),
            )
            queue_health_check(actor=request.user, connection=connection)
        except IntegrationDomainError as error:
            return _error(error)
        return Response(IntegrationConnectionSerializer(connection).data)


class IntegrationHealthCheckView(APIView):
    @extend_schema(responses={200: HealthCheckSerializer(many=True)})
    def get(self, request: Request, slug: str, connection_id: str) -> Response:
        connection = _connection(request, slug, connection_id)
        if not has_capability(
            request.user, connection.organization, Capability.INTEGRATION_VIEW
        ):
            raise PermissionDenied("permission_denied")
        checks = connection.health_checks.order_by("-created_at")[:25]
        return Response(HealthCheckSerializer(checks, many=True).data)

    @extend_schema(request=None, responses={202: HealthCheckSerializer})
    def post(self, request: Request, slug: str, connection_id: str) -> Response:
        try:
            check = queue_health_check(
                actor=request.user, connection=_connection(request, slug, connection_id)
            )
        except IntegrationDomainError as error:
            return _error(error)
        return Response(
            HealthCheckSerializer(check).data, status=status.HTTP_202_ACCEPTED
        )


class IntegrationDisconnectView(APIView):
    @extend_schema(request=None, responses={200: IntegrationConnectionSerializer})
    def post(self, request: Request, slug: str, connection_id: str) -> Response:
        try:
            connection = disconnect(
                actor=request.user, connection=_connection(request, slug, connection_id)
            )
        except IntegrationDomainError as error:
            return _error(error)
        return Response(IntegrationConnectionSerializer(connection).data)


class ApiKeyRotateView(APIView):
    @extend_schema(
        request=ApiKeyRotateSerializer, responses={200: IntegrationConnectionSerializer}
    )
    def post(self, request: Request, slug: str, connection_id: str) -> Response:
        connection = _connection(request, slug, connection_id)
        serializer = ApiKeyRotateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = connect_api_key(
                actor=request.user,
                organization=connection.organization,
                provider=IntegrationProvider(connection.provider),
                api_key=serializer.validated_data["api_key"],
                expected_version=serializer.validated_data["expected_version"],
            )
        except IntegrationDomainError as error:
            return _error(error)
        return Response(IntegrationConnectionSerializer(updated).data)


class GoogleOAuthStartView(APIView):
    @extend_schema(
        request=GoogleOAuthStartSerializer,
        responses={200: GoogleOAuthStartResponseSerializer},
    )
    def post(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        serializer = GoogleOAuthStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            authorization_url = begin_google_oauth(
                actor=request.user,
                organization=organization,
                capabilities=serializer.validated_data["capabilities"],
            )
        except IntegrationDomainError as error:
            return _error(error)
        return Response({"authorization_url": authorization_url})


class GoogleOAuthCallbackView(APIView):
    permission_classes = []

    @extend_schema(exclude=True)
    def get(self, request: Request):
        state = request.query_params.get("state", "")
        code = request.query_params.get("code", "")
        if not state or not code:
            return redirect(f"{settings.FRONTEND_ORIGIN}/organizaciones?oauth=failed")
        try:
            connection = complete_google_oauth(state=state, code=code)
        except IntegrationDomainError:
            return redirect(f"{settings.FRONTEND_ORIGIN}/organizaciones?oauth=failed")
        queue_health_check(actor=connection.created_by, connection=connection)
        return redirect(
            f"{settings.FRONTEND_ORIGIN}/organizaciones/"
            f"{connection.organization.slug}/configuracion/integraciones?oauth=complete"
        )


class GoogleTestMeetingView(APIView):
    @extend_schema(request=None, responses={201: OpenApiTypes.OBJECT})
    def post(self, request: Request, slug: str, connection_id: str) -> Response:
        try:
            result = create_google_test_meeting(
                actor=request.user, connection=_connection(request, slug, connection_id)
            )
        except IntegrationDomainError as error:
            return _error(error)
        return Response(result, status=status.HTTP_201_CREATED)
