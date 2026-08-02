from __future__ import annotations

# DRF request/serializer/pagination objects are dynamically typed by upstream.
# Domain policies and services remain in strictly checked modules.
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportIndexIssue=false, reportOptionalSubscript=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportPrivateUsage=false, reportCallIssue=false
from typing import TYPE_CHECKING, Any, cast

from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet
from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from domain.organizations.bulk import (
    confirm_bulk_invitation_preview,
    create_bulk_invitation_preview,
)
from domain.organizations.capabilities import Capability
from domain.organizations.choices import MembershipStatus, RoleCode
from domain.organizations.exceptions import (
    InitialOwnerUnavailable,
    InvalidMembershipTransition,
    InvitationAlreadyExists,
    InvitationUnavailable,
    JoinRequestAlreadyExists,
    JoinRequestUnavailable,
    LastOwnerViolation,
    ManagedAccountsDisabled,
    MemberAlreadyExists,
    MembershipNotActive,
    OrganizationAccessDenied,
    OrganizationDomainError,
    RevisionConflict,
    RoleAlreadyAssigned,
    RoleAssignmentDenied,
    RoleNotAssigned,
    VerifiedUserRequired,
)
from domain.organizations.models import (
    Membership,
    MembershipEvent,
    MembershipInvitation,
    Organization,
    OrganizationJoinRequest,
    OrganizationMemberProfile,
    OrganizationMembershipSettings,
)
from domain.organizations.policies import has_capability, is_active_platform_operator
from domain.organizations.selectors import (
    membership_visible_to,
    memberships_for_organization,
    organization_visible_to,
    organizations_visible_to,
)
from domain.organizations.services import (
    accept_session_invitation,
    activate_managed_account,
    add_existing_member_with_roles,
    begin_invitation_activation,
    begin_public_join,
    bulk_transition_memberships,
    correct_managed_account_email,
    create_managed_account,
    create_public_join_request,
    expire_due_invitations,
    invite_person,
    manually_activate_managed_account,
    provision_platform_organization,
    reactivate_membership,
    replace_membership_roles,
    resend_invitation,
    review_join_request,
    revoke_invitation,
    revoke_membership,
    revoke_user_sessions,
    send_member_password_recovery,
    suspend_membership,
    update_member_profile,
    update_membership_settings,
    update_organization_name,
)

from .serializers import (
    AccessContextSerializer,
    AccessOrganizationSerializer,
    AddMemberSerializer,
    BulkInvitationConfirmSerializer,
    BulkInvitationPreviewResponseSerializer,
    BulkInvitationPreviewSerializer,
    BulkMembershipTransitionSerializer,
    InvitationActivationResponseSerializer,
    InvitationActivationSerializer,
    InvitationCreateSerializer,
    InvitationListQuerySerializer,
    InvitationSerializer,
    JoinRequestSerializer,
    ManagedAccountCreateSerializer,
    ManagedAccountEmailCorrectionSerializer,
    ManagedActivationSerializer,
    ManagedManualActivationSerializer,
    MemberProfileSerializer,
    MemberProfileUpdateSerializer,
    MembershipEventSerializer,
    MembershipListQuerySerializer,
    MembershipSerializer,
    OrganizationMembershipSettingsSerializer,
    OrganizationMembershipSettingsUpdateSerializer,
    OrganizationSerializer,
    OrganizationUpdateSerializer,
    PlatformOrganizationProvisionSerializer,
    ReplaceRolesSerializer,
    UserSummarySerializer,
    access_organization_payload,
)

ONBOARDING_PROFILE_FIELDS = (
    "given_name",
    "middle_name",
    "family_name",
    "second_family_name",
    "preferred_name",
    "member_type",
    "institutional_id",
    "phone",
    "whatsapp",
    "date_of_birth",
    "document_type",
    "document_number",
    "gender",
    "education_stage",
    "education_institution",
    "education_level",
    "department_code",
    "municipality",
    "address",
    "socioeconomic_stratum",
    "registration_reason",
    "registration_reason_detail",
    "locale",
    "timezone_name",
)

MEMBER_PROFILE_FIELDS = (
    "first_name",
    "middle_name",
    "first_surname",
    "second_surname",
    "whatsapp",
    "date_of_birth",
    "document_type",
    "document_number",
    "gender",
    "education_stage",
    "education_institution",
    "education_level",
    "department_code",
    "municipality",
    "address",
    "socioeconomic_stratum",
    "registration_reason",
    "registration_reason_detail",
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
        InitialOwnerUnavailable: (
            status.HTTP_400_BAD_REQUEST,
            "initial_owner_unavailable",
            "La persona propietaria debe tener una cuenta activa y correo verificado.",
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
        RevisionConflict: (
            status.HTTP_409_CONFLICT,
            "revision_conflict",
            "La configuración cambió antes de guardar.",
        ),
        InvitationAlreadyExists: (
            status.HTTP_409_CONFLICT,
            "invitation_already_exists",
            "Ya existe una invitación pendiente para este correo.",
        ),
        InvitationUnavailable: (
            status.HTTP_409_CONFLICT,
            "invitation_unavailable",
            "La invitación no está disponible.",
        ),
        JoinRequestAlreadyExists: (
            status.HTTP_409_CONFLICT,
            "join_request_already_exists",
            "Ya existe una solicitud pendiente.",
        ),
        JoinRequestUnavailable: (
            status.HTTP_409_CONFLICT,
            "join_request_unavailable",
            "La solicitud no está disponible.",
        ),
        ManagedAccountsDisabled: (
            status.HTTP_409_CONFLICT,
            "managed_accounts_disabled",
            "La institución no permite cuentas administradas.",
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
        actor = _actor(request)
        memberships = (
            Membership.objects.filter(user=actor, status=MembershipStatus.ACTIVE.value)
            .select_related("organization")
            .prefetch_related("role_assignments")
            .order_by("organization__name")
        )
        payload = [
            access_organization_payload(membership) for membership in memberships
        ]
        return Response(
            {
                "user": UserSummarySerializer(actor).data,
                "organizations": AccessOrganizationSerializer(payload, many=True).data,
                "is_platform_operator": is_active_platform_operator(actor),
            }
        )


class OrganizationListView(APIView):
    @extend_schema(responses={200: OrganizationSerializer(many=True)})
    def get(self, request: Request) -> Response:
        actor = _actor(request)
        organizations = (
            Organization.objects.order_by("name")
            if is_active_platform_operator(actor)
            else organizations_visible_to(actor).order_by("name")
        )
        return Response(OrganizationSerializer(organizations, many=True).data)


class PlatformOrganizationProvisionView(APIView):
    """Restricted control-plane endpoint for institutional provisioning."""

    @extend_schema(
        request=PlatformOrganizationProvisionSerializer,
        responses={201: OrganizationSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = PlatformOrganizationProvisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            organization = provision_platform_organization(
                actor=_actor(request),
                name=serializer.validated_data["name"],
                owner_email=serializer.validated_data["owner_email"],
                administrator_emails=tuple(
                    serializer.validated_data["administrator_emails"]
                ),
            )
        except OrganizationDomainError as error:
            return _domain_error_response(error)
        return Response(
            OrganizationSerializer(organization).data,
            status=status.HTTP_201_CREATED,
        )


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

    @extend_schema(
        parameters=[MembershipListQuerySerializer],
        responses={200: MembershipSerializer(many=True)},
    )
    def get(self, request: Request, slug: str) -> Response:
        organization = self._organization(request, slug)
        if not has_capability(
            _actor(request), organization, Capability.MEMBERSHIP_VIEW
        ):
            raise PermissionDenied("permission_denied")
        filters = MembershipListQuerySerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        values = filters.validated_data
        memberships = memberships_for_organization(organization)
        if query := values.get("q"):
            memberships = memberships.filter(
                Q(user__email__icontains=query)
                | Q(user__first_name__icontains=query)
                | Q(user__last_name__icontains=query)
                | Q(institutional_profile__preferred_name__icontains=query)
            )
        if membership_status := values.get("status"):
            memberships = memberships.filter(status=membership_status)
        if role := values.get("role"):
            memberships = memberships.filter(
                role_assignments__role=role,
                role_assignments__revoked_at__isnull=True,
            ).distinct()
        if member_type := values.get("member_type"):
            memberships = memberships.filter(
                institutional_profile__member_type__icontains=member_type
            )
        ordering = values.get("ordering", "email")
        order_fields = {
            "email": "user__email",
            "-email": "-user__email",
            "joined_at": "joined_at",
            "-joined_at": "-joined_at",
        }
        memberships = memberships.order_by(order_fields[ordering])
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


class BulkMembershipTransitionView(APIView):
    @extend_schema(
        request=BulkMembershipTransitionSerializer,
        responses={200: MembershipSerializer(many=True)},
    )
    def post(self, request: Request, slug: str) -> Response:
        organization = _organization_or_404(_actor(request), slug)
        serializer = BulkMembershipTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_status = {
            "suspend": MembershipStatus.SUSPENDED,
            "reactivate": MembershipStatus.ACTIVE,
            "revoke": MembershipStatus.REVOKED,
        }[serializer.validated_data["action"]]
        try:
            memberships = bulk_transition_memberships(
                actor=_actor(request),
                organization=organization,
                membership_ids=[
                    str(membership_id)
                    for membership_id in serializer.validated_data["membership_ids"]
                ],
                target_status=target_status,
            )
        except OrganizationDomainError as error:
            return _domain_error_response(error)
        return Response(MembershipSerializer(memberships, many=True).data)


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


class MembershipSettingsView(APIView):
    @extend_schema(responses={200: OrganizationMembershipSettingsSerializer})
    def get(self, request: Request, slug: str) -> Response:
        organization = _organization_or_404(_actor(request), slug)
        if not has_capability(
            _actor(request), organization, Capability.MEMBERSHIP_SETTINGS_VIEW
        ):
            raise PermissionDenied("permission_denied")
        settings = get_object_or_404(
            OrganizationMembershipSettings, organization=organization
        )
        return Response(OrganizationMembershipSettingsSerializer(settings).data)

    @extend_schema(
        request=OrganizationMembershipSettingsUpdateSerializer,
        responses={200: OrganizationMembershipSettingsSerializer},
    )
    def put(self, request: Request, slug: str) -> Response:
        organization = _organization_or_404(_actor(request), slug)
        serializer = OrganizationMembershipSettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            membership_settings = update_membership_settings(
                actor=_actor(request),
                organization=organization,
                expected_version=serializer.validated_data["expected_version"],
                public_join_enabled=serializer.validated_data["public_join_enabled"],
                join_requires_approval=serializer.validated_data[
                    "join_requires_approval"
                ],
                allowed_email_domains=serializer.validated_data[
                    "allowed_email_domains"
                ],
                default_role=RoleCode(serializer.validated_data["default_role"]),
                invitation_expiry_hours=serializer.validated_data[
                    "invitation_expiry_hours"
                ],
                allow_admin_managed_accounts=serializer.validated_data[
                    "allow_admin_managed_accounts"
                ],
                allow_bulk_invitations=serializer.validated_data[
                    "allow_bulk_invitations"
                ],
            )
        except OrganizationDomainError as error:
            return _domain_error_response(error)
        return Response(
            OrganizationMembershipSettingsSerializer(membership_settings).data
        )


class InvitationListCreateView(APIView):
    pagination_class = MembershipPagination

    @extend_schema(responses={200: InvitationSerializer(many=True)})
    def get(self, request: Request, slug: str) -> Response:
        organization = _organization_or_404(_actor(request), slug)
        if not has_capability(
            _actor(request), organization, Capability.MEMBERSHIP_INVITATION_MANAGE
        ):
            raise PermissionDenied("permission_denied")
        expire_due_invitations(organization=organization)
        filters = InvitationListQuerySerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        values = filters.validated_data
        invitations = MembershipInvitation.objects.filter(organization=organization)
        if query := values.get("q"):
            invitations = invitations.filter(
                Q(email__icontains=query)
                | Q(given_name__icontains=query)
                | Q(family_name__icontains=query)
                | Q(preferred_name__icontains=query)
            )
        if invitation_status := values.get("status"):
            invitations = invitations.filter(status=invitation_status)
        if invitation_type := values.get("invitation_type"):
            invitations = invitations.filter(invitation_type=invitation_type)
        invitations = invitations.order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(invitations, request)
        if page is not None:
            return paginator.get_paginated_response(
                InvitationSerializer(page, many=True).data
            )
        return Response(InvitationSerializer(invitations, many=True).data)

    @extend_schema(
        request=InvitationCreateSerializer, responses={201: InvitationSerializer}
    )
    def post(self, request: Request, slug: str) -> Response:
        organization = _organization_or_404(_actor(request), slug)
        serializer = InvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = cast(dict[str, Any], serializer.validated_data)
        try:
            invitation = invite_person(
                actor=_actor(request),
                organization=organization,
                email=values["email"],
                roles={RoleCode(role) for role in values["roles"]},
                **{
                    field: values[field]
                    for field in ONBOARDING_PROFILE_FIELDS
                    if field in values
                },
            )
        except OrganizationDomainError as error:
            return _domain_error_response(error)
        return Response(
            InvitationSerializer(invitation).data, status=status.HTTP_201_CREATED
        )


class BulkInvitationPreviewView(APIView):
    @extend_schema(
        request=BulkInvitationPreviewSerializer,
        responses={200: BulkInvitationPreviewResponseSerializer},
    )
    def post(self, request: Request, slug: str) -> Response:
        organization = _organization_or_404(_actor(request), slug)
        serializer = BulkInvitationPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payload = create_bulk_invitation_preview(
                request=request._request,
                actor=_actor(request),
                organization=organization,
                upload=serializer.validated_data["file"],
            )
        except OrganizationDomainError as error:
            return _domain_error_response(error)
        return Response(payload)


class BulkInvitationConfirmView(APIView):
    @extend_schema(
        request=BulkInvitationConfirmSerializer, responses={201: OpenApiTypes.OBJECT}
    )
    def post(self, request: Request, slug: str) -> Response:
        organization = _organization_or_404(_actor(request), slug)
        serializer = BulkInvitationConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            created = confirm_bulk_invitation_preview(
                request=request._request,
                actor=_actor(request),
                organization=organization,
                preview_id=str(serializer.validated_data["preview_id"]),
            )
        except OrganizationDomainError as error:
            return _domain_error_response(error)
        return Response({"created": created}, status=status.HTTP_201_CREATED)


class ManagedAccountCreateView(APIView):
    @extend_schema(
        request=ManagedAccountCreateSerializer, responses={201: InvitationSerializer}
    )
    def post(self, request: Request, slug: str) -> Response:
        organization = _organization_or_404(_actor(request), slug)
        serializer = ManagedAccountCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = cast(dict[str, Any], serializer.validated_data)
        try:
            invitation, _ = create_managed_account(
                actor=_actor(request),
                organization=organization,
                email=values["email"],
                roles={RoleCode(role) for role in values["roles"]},
                **{
                    field: values[field]
                    for field in ONBOARDING_PROFILE_FIELDS
                    if field in values
                },
            )
        except OrganizationDomainError as error:
            return _domain_error_response(error)
        return Response(
            InvitationSerializer(invitation).data, status=status.HTTP_201_CREATED
        )


class InvitationActionView(APIView):
    action = ""

    @extend_schema(request=None, responses={200: InvitationSerializer})
    def post(self, request: Request, slug: str, invitation_id: str) -> Response:
        organization = _organization_or_404(_actor(request), slug)
        invitation = get_object_or_404(
            MembershipInvitation, pk=invitation_id, organization=organization
        )
        try:
            if self.action == "resend":
                resend_invitation(actor=_actor(request), invitation=invitation)
                invitation.refresh_from_db()
            else:
                invitation = revoke_invitation(
                    actor=_actor(request), invitation=invitation
                )
        except OrganizationDomainError as error:
            return _domain_error_response(error)
        return Response(InvitationSerializer(invitation).data)


class ResendInvitationView(InvitationActionView):
    action = "resend"


class RevokeInvitationView(InvitationActionView):
    action = "revoke"


class ManagedAccountEmailCorrectionView(APIView):
    @extend_schema(
        request=ManagedAccountEmailCorrectionSerializer,
        responses={200: InvitationSerializer},
    )
    def patch(self, request: Request, slug: str, invitation_id: str) -> Response:
        organization = _organization_or_404(_actor(request), slug)
        invitation = get_object_or_404(
            MembershipInvitation, pk=invitation_id, organization=organization
        )
        serializer = ManagedAccountEmailCorrectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = correct_managed_account_email(
                actor=_actor(request),
                invitation=invitation,
                email=serializer.validated_data["email"],
            )
        except OrganizationDomainError as error:
            return _domain_error_response(error)
        return Response(InvitationSerializer(updated).data)


class ManagedAccountManualActivationView(APIView):
    @extend_schema(
        request=ManagedManualActivationSerializer,
        responses={201: MembershipSerializer},
    )
    def post(self, request: Request, slug: str, invitation_id: str) -> Response:
        organization = _organization_or_404(_actor(request), slug)
        invitation = get_object_or_404(
            MembershipInvitation, pk=invitation_id, organization=organization
        )
        serializer = ManagedManualActivationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            membership = manually_activate_managed_account(
                actor=_actor(request),
                invitation=invitation,
                temporary_password=serializer.validated_data["temporary_password"],
                confirm_identity=serializer.validated_data["confirm_identity"],
            )
        except OrganizationDomainError as error:
            return _domain_error_response(error)
        return Response(
            MembershipSerializer(membership).data, status=status.HTTP_201_CREATED
        )


class InvitationActivationView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=InvitationActivationSerializer,
        responses={200: InvitationActivationResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = InvitationActivationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            invitation = begin_invitation_activation(
                request=request._request, token=serializer.validated_data["token"]
            )
        except OrganizationDomainError as error:
            return _domain_error_response(error)
        return Response({"invitation_type": invitation.invitation_type})


class AcceptInvitationView(APIView):
    @extend_schema(request=None, responses={201: MembershipSerializer})
    def post(self, request: Request) -> Response:
        try:
            membership = accept_session_invitation(
                request=request._request, user=_actor(request)
            )
        except OrganizationDomainError as error:
            return _domain_error_response(error)
        if membership is None:
            return Response(
                {
                    "code": "invitation_unavailable",
                    "detail": "No hay invitación activa.",
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            MembershipSerializer(membership).data, status=status.HTTP_201_CREATED
        )


class ManagedAccountActivationView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=ManagedActivationSerializer, responses={201: MembershipSerializer}
    )
    def post(self, request: Request) -> Response:
        serializer = ManagedActivationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            membership = activate_managed_account(
                request=request._request, password=serializer.validated_data["password"]
            )
        except OrganizationDomainError as error:
            return _domain_error_response(error)
        return Response(
            MembershipSerializer(membership).data, status=status.HTTP_201_CREATED
        )


class PublicJoinView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=None, responses={202: None, 201: JoinRequestSerializer})
    def post(self, request: Request, slug: str) -> Response:
        organization = get_object_or_404(Organization, slug=slug)
        try:
            begin_public_join(request=request._request, organization=organization)
            if not request.user.is_authenticated:
                return Response(status=status.HTTP_202_ACCEPTED)
            created = create_public_join_request(
                user=_actor(request), organization=organization
            )
        except OrganizationDomainError as error:
            return _domain_error_response(error)
        if isinstance(created, Membership):
            return Response(
                MembershipSerializer(created).data, status=status.HTTP_201_CREATED
            )
        return Response(
            JoinRequestSerializer(created).data, status=status.HTTP_201_CREATED
        )


class JoinRequestListView(APIView):
    pagination_class = MembershipPagination

    @extend_schema(responses={200: JoinRequestSerializer(many=True)})
    def get(self, request: Request, slug: str) -> Response:
        organization = _organization_or_404(_actor(request), slug)
        if not has_capability(
            _actor(request), organization, Capability.MEMBERSHIP_JOIN_REQUEST_MANAGE
        ):
            raise PermissionDenied("permission_denied")
        records = OrganizationJoinRequest.objects.filter(
            organization=organization
        ).order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(records, request)
        if page is not None:
            return paginator.get_paginated_response(
                JoinRequestSerializer(page, many=True).data
            )
        return Response(JoinRequestSerializer(records, many=True).data)


class JoinRequestReviewView(APIView):
    @extend_schema(request=None, responses={200: JoinRequestSerializer})
    def post(
        self, request: Request, slug: str, join_request_id: str, action: str
    ) -> Response:
        if action not in {"approve", "reject"}:
            raise Http404
        organization = _organization_or_404(_actor(request), slug)
        join_request = get_object_or_404(
            OrganizationJoinRequest, pk=join_request_id, organization=organization
        )
        try:
            updated = review_join_request(
                actor=_actor(request),
                join_request=join_request,
                approve=action == "approve",
            )
        except OrganizationDomainError as error:
            return _domain_error_response(error)
        return Response(JoinRequestSerializer(updated).data)


class MemberProfileView(APIView):
    @extend_schema(responses={200: MemberProfileSerializer})
    def get(self, request: Request, slug: str, membership_id: str) -> Response:
        organization = _organization_or_404(_actor(request), slug)
        membership = _membership_or_404(_actor(request), organization, membership_id)
        if membership.user_id != _actor(request).pk and not has_capability(
            _actor(request), organization, Capability.MEMBERSHIP_VIEW
        ):
            raise PermissionDenied("permission_denied")
        profile = get_object_or_404(OrganizationMemberProfile, membership=membership)
        payload = MemberProfileSerializer(profile).data
        if not has_capability(
            _actor(request), organization, Capability.MEMBERSHIP_PROFILE_MANAGE
        ):
            payload.pop("administrative_notes", None)
        return Response(payload)

    @extend_schema(
        request=MemberProfileUpdateSerializer, responses={200: MemberProfileSerializer}
    )
    def patch(self, request: Request, slug: str, membership_id: str) -> Response:
        organization = _organization_or_404(_actor(request), slug)
        membership = _membership_or_404(_actor(request), organization, membership_id)
        serializer = MemberProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        current = get_object_or_404(OrganizationMemberProfile, membership=membership)
        values = cast(dict[str, Any], serializer.validated_data)
        try:
            profile = update_member_profile(
                actor=_actor(request),
                membership=membership,
                member_type=values.get("member_type", current.member_type),
                institutional_id=values.get(
                    "institutional_id", current.institutional_id
                ),
                preferred_name=values.get("preferred_name", current.preferred_name),
                phone=values.get("phone", current.phone),
                locale=values.get("locale", current.locale),
                timezone_name=values.get("timezone", current.timezone),
                administrative_notes=values.get("administrative_notes"),
                profile_values={
                    field: values[field]
                    for field in MEMBER_PROFILE_FIELDS
                    if field in values
                },
            )
        except OrganizationDomainError as error:
            return _domain_error_response(error)
        payload = MemberProfileSerializer(profile).data
        if not has_capability(
            _actor(request), organization, Capability.MEMBERSHIP_PROFILE_MANAGE
        ):
            payload.pop("administrative_notes", None)
        return Response(payload)


class RevokeMemberSessionsView(APIView):
    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
    def post(self, request: Request, slug: str, membership_id: str) -> Response:
        organization = _organization_or_404(_actor(request), slug)
        membership = _membership_or_404(_actor(request), organization, membership_id)
        try:
            deleted = revoke_user_sessions(actor=_actor(request), membership=membership)
        except OrganizationDomainError as error:
            return _domain_error_response(error)
        return Response({"revoked_sessions": deleted})


class SendMemberPasswordRecoveryView(APIView):
    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
    def post(self, request: Request, slug: str, membership_id: str) -> Response:
        organization = _organization_or_404(_actor(request), slug)
        membership = _membership_or_404(_actor(request), organization, membership_id)
        try:
            send_member_password_recovery(actor=_actor(request), membership=membership)
        except OrganizationDomainError as error:
            return _domain_error_response(error)
        return Response({"sent": True})
