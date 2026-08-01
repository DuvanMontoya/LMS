from __future__ import annotations

from typing import TYPE_CHECKING

from .capabilities import Capability, capabilities_for_roles
from .choices import MembershipStatus, RoleCode

if TYPE_CHECKING:
    from domain.identity.models import User

from .models import Membership, MembershipRoleAssignment, Organization


def is_active_platform_operator(actor: User | None) -> bool:
    return bool(actor and actor.is_active and actor.is_superuser)


def active_membership(
    actor: User | None, organization: Organization
) -> Membership | None:
    if not actor or not actor.is_authenticated or not actor.is_active:
        return None
    return Membership.objects.filter(
        organization=organization, user=actor, status=MembershipStatus.ACTIVE.value
    ).first()


def active_roles(membership: Membership | None) -> set[RoleCode]:
    if membership is None or membership.status != MembershipStatus.ACTIVE.value:
        return set()
    return {
        RoleCode(assignment.role)
        for assignment in MembershipRoleAssignment.objects.filter(
            membership=membership, revoked_at__isnull=True
        )
    }


def capabilities_for_membership(membership: Membership | None) -> frozenset[Capability]:
    return capabilities_for_roles(active_roles(membership))


def has_capability(
    actor: User | None,
    organization: Organization,
    capability: Capability,
) -> bool:
    return capability in capabilities_for_membership(
        active_membership(actor, organization)
    )


def target_is_active_owner(membership: Membership) -> bool:
    return (
        membership.status == MembershipStatus.ACTIVE.value
        and RoleCode.OWNER in active_roles(membership)
    )


def target_has_owner_role(membership: Membership) -> bool:
    return MembershipRoleAssignment.objects.filter(
        membership=membership,
        role=RoleCode.OWNER.value,
        revoked_at__isnull=True,
    ).exists()


def can_manage_membership(
    actor: User | None,
    target_membership: Membership,
    capability: Capability,
) -> bool:
    organization = target_membership.organization
    if not has_capability(actor, organization, capability):
        return False
    if target_has_owner_role(target_membership):
        return has_capability(actor, organization, Capability.ROLE_ASSIGN_OWNER)
    return True


def can_assign_role(
    actor: User | None,
    target_membership: Membership,
    role: RoleCode,
) -> bool:
    capability = (
        Capability.ROLE_ASSIGN_OWNER
        if role == RoleCode.OWNER
        else Capability.ROLE_ASSIGN
    )
    return can_manage_membership(actor, target_membership, capability)
