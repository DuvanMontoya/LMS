from __future__ import annotations

from rest_framework import serializers

from domain.organizations.choices import MembershipStatus, RoleCode
from domain.organizations.models import Membership, MembershipEvent, Organization
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


class AccessOrganizationSerializer(serializers.Serializer[object]):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    slug = serializers.SlugField(read_only=True)
    membership_id = serializers.UUIDField(read_only=True)
    membership_status = serializers.ChoiceField(
        choices=MembershipStatus.choices, read_only=True
    )
    roles = serializers.ListField(child=serializers.CharField(), read_only=True)
    capabilities = serializers.ListField(child=serializers.CharField(), read_only=True)


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
