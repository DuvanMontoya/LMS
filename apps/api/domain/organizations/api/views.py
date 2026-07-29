from __future__ import annotations

# DRF request/serializer/pagination objects are dynamically typed by upstream.
# Domain policies and services remain in strictly checked modules.
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportIndexIssue=false, reportOptionalSubscript=false, reportAttributeAccessIssue=false
from typing import TYPE_CHECKING, cast

from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from domain.organizations.capabilities import Capability
from domain.organizations.choices import MembershipStatus, RoleCode
from domain.organizations.exceptions import (
    InvalidMembershipTransition,
    LastOwnerViolation,
    MemberAlreadyExists,
    MembershipNotActive,
    OrganizationAccessDenied,
    OrganizationDomainError,
    RoleAlreadyAssigned,
    RoleAssignmentDenied,
    RoleNotAssigned,
    VerifiedUserRequired,
)
from domain.organizations.models import Membership, MembershipEvent, Organization
from domain.organizations.policies import has_capability
from domain.organizations.selectors import (
    membership_visible_to,
    memberships_for_organization,
    organization_visible_to,
    organizations_visible_to,
)
from domain.organizations.services import (
    add_existing_member_with_roles,
    reactivate_membership,
    replace_membership_roles,
    revoke_membership,
    suspend_membership,
    update_organization_name,
)

from .serializers import (
    AccessContextSerializer,
    AccessOrganizationSerializer,
    AddMemberSerializer,
    MembershipEventSerializer,
    MembershipSerializer,
    OrganizationSerializer,
    OrganizationUpdateSerializer,
    ReplaceRolesSerializer,
    UserSummarySerializer,
    access_organization_payload,
)

if TYPE_CHECKING:
    from domain.identity.models import User


class MembershipPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


def _actor(request: Request) -> User:
    return request.user  # type: ignore[return-value]


def _domain_error_response(error: OrganizationDomainError) -> Response:
    errors: dict[type[OrganizationDomainError], tuple[int, str, str]] = {
        OrganizationAccessDenied: (
            status.HTTP_403_FORBIDDEN,
            "permission_denied",
            "No tienes permiso para esta operación.",
        ),
        MemberAlreadyExists: (
            status.HTTP_400_BAD_REQUEST,
            "member_could_not_be_added",
            "No fue posible agregar a la persona indicada.",
        ),
        VerifiedUserRequired: (
            status.HTTP_400_BAD_REQUEST,
            "member_could_not_be_added",
            "No fue posible agregar a la persona indicada.",
        ),
        InvalidMembershipTransition: (
            status.HTTP_409_CONFLICT,
            "membership_transition_invalid",
            "La transición de membresía no es válida.",
        ),
        LastOwnerViolation: (
            status.HTTP_409_CONFLICT,
            "last_owner_required",
            "La organización debe conservar al menos un propietario activo.",
        ),
        RoleAssignmentDenied: (
            status.HTTP_403_FORBIDDEN,
            "role_assignment_denied",
            "No puedes modificar este rol.",
        ),
        RoleAlreadyAssigned: (
            status.HTTP_409_CONFLICT,
            "role_already_assigned",
            "El rol ya está asignado.",
        ),
        RoleNotAssigned: (
            status.HTTP_409_CONFLICT,
            "role_not_assigned",
            "El rol no está asignado.",
        ),
        MembershipNotActive: (
            status.HTTP_409_CONFLICT,
            "membership_transition_invalid",
            "La membresía no permite esta operación.",
        ),
    }
    code, stable_code, message = errors[type(error)]
    return Response({"code": stable_code, "detail": message}, status=code)


def _organization_or_404(actor: User, slug: str) -> Organization:
    return organization_visible_to(actor, slug)


def _membership_or_404(
    actor: User, organization: Organization, membership_id: str
) -> Membership:
    return membership_visible_to(actor, organization, membership_id)


class AccessContextView(APIView):
    @extend_schema(responses={200: AccessContextSerializer})
    def get(self, request: Request) -> Response:
        memberships = (
            Membership.objects.filter(
                user=_actor(request), status=MembershipStatus.ACTIVE.value
            )
            .select_related("organization")
            .prefetch_related("role_assignments")
            .order_by("organization__name")
        )
        payload = [
            access_organization_payload(membership) for membership in memberships
        ]
        return Response(
            {
                "user": UserSummarySerializer(_actor(request)).data,
                "organizations": AccessOrganizationSerializer(payload, many=True).data,
            }
        )


class OrganizationListView(APIView):
    @extend_schema(responses={200: OrganizationSerializer(many=True)})
    def get(self, request: Request) -> Response:
        organizations = organizations_visible_to(_actor(request)).order_by("name")
        return Response(OrganizationSerializer(organizations, many=True).data)


class OrganizationDetailView(APIView):
    @extend_schema(responses={200: OrganizationSerializer})
    def get(self, request: Request, slug: str) -> Response:
        return Response(
            OrganizationSerializer(_organization_or_404(_actor(request), slug)).data
        )

    @extend_schema(
        request=OrganizationUpdateSerializer, responses={200: OrganizationSerializer}
    )
    def patch(self, request: Request, slug: str) -> Response:
        organization = _organization_or_404(_actor(request), slug)
        serializer = OrganizationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = update_organization_name(
                actor=_actor(request),
                organization=organization,
                name=serializer.validated_data["name"],
            )
        except OrganizationDomainError as error:
            return _domain_error_response(error)
        return Response(OrganizationSerializer(updated).data)


class MembershipListCreateView(APIView):
    pagination_class = MembershipPagination

    def _organization(self, request: Request, slug: str) -> Organization:
        return _organization_or_404(_actor(request), slug)

    @extend_schema(responses={200: MembershipSerializer(many=True)})
    def get(self, request: Request, slug: str) -> Response:
        organization = self._organization(request, slug)
        if not has_capability(
            _actor(request), organization, Capability.MEMBERSHIP_VIEW
        ):
            raise PermissionDenied("permission_denied")
        memberships = memberships_for_organization(organization).order_by("user__email")
        email = request.query_params.get("email")
        if email:
            memberships = memberships.filter(user__email__icontains=email)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(memberships, request)
        if page is not None:
            return paginator.get_paginated_response(
                MembershipSerializer(page, many=True).data
            )
        return Response(MembershipSerializer(memberships, many=True).data)

    @extend_schema(request=AddMemberSerializer, responses={201: MembershipSerializer})
    def post(self, request: Request, slug: str) -> Response:
        organization = self._organization(request, slug)
        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = cast(
            "User | None",
            get_user_model()
            .objects.filter(email__iexact=serializer.validated_data["email"])
            .first(),
        )
        if user is None:
            return _domain_error_response(
                VerifiedUserRequired("La persona indicada no está disponible.")
            )
        try:
            membership = add_existing_member_with_roles(
                actor=_actor(request),
                organization=organization,
                user=user,
                roles={RoleCode(role) for role in serializer.validated_data["roles"]},
            )
        except OrganizationDomainError as error:
            return _domain_error_response(error)
        return Response(
            MembershipSerializer(membership).data, status=status.HTTP_201_CREATED
        )


class MembershipDetailView(APIView):
    @extend_schema(responses={200: MembershipSerializer})
    def get(self, request: Request, slug: str, membership_id: str) -> Response:
        organization = _organization_or_404(_actor(request), slug)
        membership = _membership_or_404(_actor(request), organization, membership_id)
        if membership.user.pk != _actor(request).pk and not has_capability(
            _actor(request), organization, Capability.MEMBERSHIP_VIEW
        ):
            raise PermissionDenied("permission_denied")
        return Response(MembershipSerializer(membership).data)


class MembershipActionView(APIView):
    action = ""

    @extend_schema(request=None, responses={200: MembershipSerializer})
    def post(self, request: Request, slug: str, membership_id: str) -> Response:
        organization = _organization_or_404(_actor(request), slug)
        membership = _membership_or_404(_actor(request), organization, membership_id)
        service = {
            "suspend": suspend_membership,
            "reactivate": reactivate_membership,
            "revoke": revoke_membership,
        }[self.action]
        try:
            updated = service(actor=_actor(request), membership=membership)
        except OrganizationDomainError as error:
            return _domain_error_response(error)
        return Response(MembershipSerializer(updated).data)


class SuspendMembershipView(MembershipActionView):
    action = "suspend"


class ReactivateMembershipView(MembershipActionView):
    action = "reactivate"


class RevokeMembershipView(MembershipActionView):
    action = "revoke"


class ReplaceRolesView(APIView):
    @extend_schema(
        request=ReplaceRolesSerializer, responses={200: MembershipSerializer}
    )
    def put(self, request: Request, slug: str, membership_id: str) -> Response:
        organization = _organization_or_404(_actor(request), slug)
        membership = _membership_or_404(_actor(request), organization, membership_id)
        serializer = ReplaceRolesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = replace_membership_roles(
                actor=_actor(request),
                membership=membership,
                roles={RoleCode(role) for role in serializer.validated_data["roles"]},
            )
        except OrganizationDomainError as error:
            return _domain_error_response(error)
        return Response(MembershipSerializer(updated).data)


class MembershipEventsView(APIView):
    pagination_class = MembershipPagination

    @extend_schema(responses={200: MembershipEventSerializer(many=True)})
    def get(self, request: Request, slug: str, membership_id: str) -> Response:
        organization = _organization_or_404(_actor(request), slug)
        membership = _membership_or_404(_actor(request), organization, membership_id)
        if not has_capability(
            _actor(request), organization, Capability.MEMBERSHIP_EVENT_VIEW
        ):
            raise PermissionDenied("permission_denied")
        events: QuerySet[MembershipEvent] = MembershipEvent.objects.filter(
            membership=membership
        ).order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(events, request)
        if page is not None:
            return paginator.get_paginated_response(
                MembershipEventSerializer(page, many=True).data
            )
        return Response(MembershipEventSerializer(events, many=True).data)
