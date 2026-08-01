from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from domain.identity.models import PlatformRegistrationSettings
from domain.identity.services import (
    RegistrationSettingsConflict,
    RegistrationSettingsDenied,
    update_platform_registration_settings,
)

from .serializers import (
    PublicRegistrationSettingsSerializer,
    RegistrationSettingsSerializer,
    RegistrationSettingsUpdateSerializer,
)

# DRF request and serializer values are dynamic at the transport boundary.
# The domain service remains explicit and typed below that boundary.
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportIndexIssue=false, reportOptionalSubscript=false, reportAttributeAccessIssue=false, reportCallIssue=false


class PublicRegistrationSettingsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: PublicRegistrationSettingsSerializer})
    def get(self, request: Request) -> Response:
        return Response(
            PublicRegistrationSettingsSerializer(
                PlatformRegistrationSettings.current(), context={"request": request}
            ).data
        )


class RegistrationSettingsView(APIView):
    @extend_schema(responses={200: RegistrationSettingsSerializer})
    def get(self, request: Request) -> Response:
        if not (
            request.user.is_superuser
            or request.user.has_perm("identity.manage_platform_registration")
        ):
            return Response(
                {"code": "permission_denied"}, status=status.HTTP_403_FORBIDDEN
            )
        return Response(
            RegistrationSettingsSerializer(PlatformRegistrationSettings.current()).data
        )

    @extend_schema(
        request=RegistrationSettingsUpdateSerializer,
        responses={200: RegistrationSettingsSerializer},
    )
    def put(self, request: Request) -> Response:
        serializer = RegistrationSettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            registration = update_platform_registration_settings(
                actor=request.user, **serializer.validated_data
            )
        except RegistrationSettingsConflict:
            return Response(
                {"code": "revision_conflict"}, status=status.HTTP_409_CONFLICT
            )
        except RegistrationSettingsDenied:
            return Response(
                {"code": "permission_denied"}, status=status.HTTP_403_FORBIDDEN
            )
        return Response(RegistrationSettingsSerializer(registration).data)
