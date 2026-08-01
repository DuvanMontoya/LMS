from __future__ import annotations

# drf-spectacular's decorator has incomplete third-party generic annotations.
# pyright: reportUnknownVariableType=false, reportUnnecessaryComparison=false
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from domain.organizations.choices import (
    InvitationStatus,
    InvitationType,
    MembershipStatus,
    RoleCode,
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
from domain.organizations.policies import active_roles, capabilities_for_membership


class UserSummarySerializer(serializers.Serializer[object]):
    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(read_only=True)
    display = serializers.SerializerMethodField()

    def get_display(self, user: object) -> str:
        return user.get_full_name() or user.email  # type: ignore[attr-defined]


class OrganizationSerializer(serializers.ModelSerializer[Organization]):
    class Meta:
        model = Organization
        fields = ("id", "name", "slug")
        read_only_fields = ("id", "slug")


class OrganizationUpdateSerializer(serializers.Serializer[object]):
    name = serializers.CharField(max_length=160)

    def validate_name(self, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise serializers.ValidationError("El nombre es obligatorio.")
        return normalized


class MembershipSerializer(serializers.ModelSerializer[Membership]):
    membership_id = serializers.UUIDField(source="id", read_only=True)
    user = UserSummarySerializer(read_only=True)
    roles = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = ("membership_id", "user", "status", "roles", "joined_at")

    @extend_schema_field(
        serializers.ListField(child=serializers.ChoiceField(choices=RoleCode.choices))
    )
    def get_roles(self, membership: Membership) -> list[str]:
        return sorted(role.value for role in active_roles(membership))


class AddMemberSerializer(serializers.Serializer[object]):
    email = serializers.EmailField()
    roles = serializers.ListField(
        child=serializers.ChoiceField(choices=RoleCode.choices), allow_empty=False
    )

    def validate_roles(self, roles: list[str]) -> list[str]:
        if len(set(roles)) != len(roles):
            raise serializers.ValidationError("No repitas roles.")
        return roles


class MembershipListQuerySerializer(serializers.Serializer[object]):
    q = serializers.CharField(max_length=254, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=MembershipStatus.choices, required=False)
    role = serializers.ChoiceField(choices=RoleCode.choices, required=False)
    member_type = serializers.CharField(max_length=80, required=False, allow_blank=True)
    ordering = serializers.ChoiceField(
        choices=("email", "-email", "joined_at", "-joined_at"),
        required=False,
        default="email",
    )


class BulkMembershipTransitionSerializer(serializers.Serializer[object]):
    membership_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, max_length=100
    )
    action = serializers.ChoiceField(choices=("suspend", "reactivate", "revoke"))

    def validate_membership_ids(self, values: list[object]) -> list[object]:
        if len(set(values)) != len(values):
            raise serializers.ValidationError("No repitas membresías.")
        return values


class ReplaceRolesSerializer(serializers.Serializer[object]):
    roles = serializers.ListField(
        child=serializers.ChoiceField(choices=RoleCode.choices), allow_empty=False
    )

    def validate_roles(self, roles: list[str]) -> list[str]:
        if len(set(roles)) != len(roles):
            raise serializers.ValidationError("No repitas roles.")
        return roles


class MembershipEventSerializer(serializers.ModelSerializer[MembershipEvent]):
    class Meta:
        model = MembershipEvent
        fields = (
            "id",
            "event_type",
            "role",
            "previous_status",
            "new_status",
            "created_at",
        )
        read_only_fields = fields


class OrganizationMembershipSettingsSerializer(
    serializers.ModelSerializer[OrganizationMembershipSettings]
):
    class Meta:
        model = OrganizationMembershipSettings
        fields = (
            "public_join_enabled",
            "join_requires_approval",
            "allowed_email_domains",
            "default_role",
            "invitation_expiry_hours",
            "allow_admin_managed_accounts",
            "allow_bulk_invitations",
            "updated_at",
            "lock_version",
        )
        read_only_fields = ("updated_at", "lock_version")


class OrganizationMembershipSettingsUpdateSerializer(serializers.Serializer[object]):
    expected_version = serializers.IntegerField(min_value=1)
    public_join_enabled = serializers.BooleanField()
    join_requires_approval = serializers.BooleanField()
    allowed_email_domains = serializers.ListField(
        child=serializers.CharField(max_length=253), required=False, default=list
    )
    default_role = serializers.ChoiceField(choices=RoleCode.choices)
    invitation_expiry_hours = serializers.IntegerField(min_value=1, max_value=720)
    allow_admin_managed_accounts = serializers.BooleanField()
    allow_bulk_invitations = serializers.BooleanField()

    def validate_default_role(self, value: str) -> str:
        if value == RoleCode.OWNER:
            raise serializers.ValidationError(
                "El rol predeterminado no puede ser owner."
            )
        return value


class InvitationSerializer(serializers.ModelSerializer[MembershipInvitation]):
    roles = serializers.ListField(source="invited_roles", read_only=True)

    class Meta:
        model = MembershipInvitation
        fields = (
            "id",
            "email",
            "roles",
            "invitation_type",
            "status",
            "expires_at",
            "accepted_at",
            "revoked_at",
            "given_name",
            "family_name",
            "preferred_name",
            "member_type",
            "institutional_id",
            "phone",
            "locale",
            "timezone_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class InvitationCreateSerializer(serializers.Serializer[object]):
    email = serializers.EmailField()
    roles = serializers.ListField(
        child=serializers.ChoiceField(choices=RoleCode.choices), allow_empty=False
    )
    given_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    family_name = serializers.CharField(
        max_length=150, required=False, allow_blank=True
    )
    preferred_name = serializers.CharField(
        max_length=150, required=False, allow_blank=True
    )
    member_type = serializers.CharField(max_length=80, required=False, allow_blank=True)
    institutional_id = serializers.CharField(
        max_length=120, required=False, allow_blank=True
    )
    phone = serializers.CharField(max_length=64, required=False, allow_blank=True)
    locale = serializers.CharField(max_length=16, required=False, default="es")
    timezone_name = serializers.CharField(max_length=64, required=False, default="UTC")

    def validate_roles(self, roles: list[str]) -> list[str]:
        if len(set(roles)) != len(roles) or RoleCode.OWNER.value in roles:
            raise serializers.ValidationError(
                "Los roles deben ser únicos y no incluir owner."
            )
        return roles


class InvitationListQuerySerializer(serializers.Serializer[object]):
    q = serializers.CharField(max_length=254, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=InvitationStatus.choices, required=False)
    invitation_type = serializers.ChoiceField(
        choices=InvitationType.choices, required=False
    )


class ManagedAccountEmailCorrectionSerializer(serializers.Serializer[object]):
    email = serializers.EmailField()


class ManagedAccountCreateSerializer(InvitationCreateSerializer):
    given_name = serializers.CharField(max_length=150)
    family_name = serializers.CharField(max_length=150)
    member_type = serializers.CharField(max_length=80)
    institutional_id = serializers.CharField(
        max_length=120, required=False, allow_blank=True
    )


class JoinRequestSerializer(serializers.ModelSerializer[OrganizationJoinRequest]):
    user = UserSummarySerializer(read_only=True)

    class Meta:
        model = OrganizationJoinRequest
        fields = ("id", "user", "email", "status", "reviewed_at", "created_at")
        read_only_fields = fields


class MemberProfileSerializer(serializers.ModelSerializer[OrganizationMemberProfile]):
    class Meta:
        model = OrganizationMemberProfile
        fields = (
            "member_type",
            "institutional_id",
            "preferred_name",
            "phone",
            "locale",
            "timezone",
            "administrative_notes",
            "updated_at",
        )
        read_only_fields = ("updated_at",)


class MemberProfileUpdateSerializer(serializers.Serializer[object]):
    member_type = serializers.CharField(max_length=80, required=False, allow_blank=True)
    institutional_id = serializers.CharField(
        max_length=120, required=False, allow_blank=True
    )
    preferred_name = serializers.CharField(
        max_length=150, required=False, allow_blank=True
    )
    phone = serializers.CharField(max_length=64, required=False, allow_blank=True)
    locale = serializers.CharField(max_length=16, required=False, allow_blank=True)
    timezone = serializers.CharField(max_length=64, required=False, allow_blank=True)
    administrative_notes = serializers.CharField(
        max_length=4000, required=False, allow_blank=True
    )


class InvitationActivationSerializer(serializers.Serializer[object]):
    token = serializers.CharField(write_only=True, min_length=24, max_length=512)


class InvitationActivationResponseSerializer(serializers.Serializer[object]):
    invitation_type = serializers.ChoiceField(
        choices=InvitationType.choices, read_only=True
    )


class BulkInvitationPreviewSerializer(serializers.Serializer[object]):
    file = serializers.FileField(write_only=True, allow_empty_file=False)


class BulkInvitationIssueSerializer(serializers.Serializer[object]):
    row = serializers.IntegerField(read_only=True)
    field = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)


class BulkInvitationPreviewResponseSerializer(serializers.Serializer[object]):
    preview_id = serializers.UUIDField(read_only=True)
    valid_count = serializers.IntegerField(read_only=True)
    issues = BulkInvitationIssueSerializer(many=True, read_only=True)


class BulkInvitationConfirmSerializer(serializers.Serializer[object]):
    preview_id = serializers.UUIDField()


class ManagedActivationSerializer(serializers.Serializer[object]):
    password = serializers.CharField(write_only=True, min_length=12, max_length=256)


class AccessOrganizationSerializer(serializers.Serializer[object]):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    slug = serializers.SlugField(read_only=True)
    membership_id = serializers.UUIDField(read_only=True)
    membership_status = serializers.ChoiceField(
        choices=MembershipStatus.choices, read_only=True
    )
    roles = serializers.ListField(
        child=serializers.ChoiceField(choices=RoleCode.choices), read_only=True
    )
    capabilities = serializers.ListField(child=serializers.CharField(), read_only=True)


class AccessContextSerializer(serializers.Serializer[object]):
    user = UserSummarySerializer(read_only=True)
    organizations = AccessOrganizationSerializer(many=True, read_only=True)


def access_organization_payload(membership: Membership) -> dict[str, object]:
    return {
        "id": membership.organization.id,
        "name": membership.organization.name,
        "slug": membership.organization.slug,
        "membership_id": membership.id,
        "membership_status": membership.status,
        "roles": sorted(role.value for role in active_roles(membership)),
        "capabilities": sorted(
            capability.value for capability in capabilities_for_membership(membership)
        ),
    }
