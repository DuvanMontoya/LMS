from __future__ import annotations

# DRF's BasePermission stubs currently model the default method as Literal[True].
# This adapter remains deliberately thin; domain policies stay strictly typed.
# pyright: reportIncompatibleMethodOverride=false, reportUnknownParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from domain.organizations.capabilities import Capability
from domain.organizations.models import Organization
from domain.organizations.policies import has_capability


class HasOrganizationCapability(BasePermission):
    """Thin DRF adapter; services repeat authorization before writes."""

    capability: Capability

    def has_object_permission(
        self, request: Request, view: APIView, obj: Organization
    ) -> bool:
        return has_capability(request.user, obj, self.capability)
