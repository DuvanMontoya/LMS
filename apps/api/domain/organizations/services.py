from __future__ import annotations

from typing import TYPE_CHECKING

from allauth.account.models import EmailAddress
from django.db import IntegrityError, transaction
from django.utils import timezone

from .capabilities import Capability
from .choices import MembershipEventType, MembershipStatus, RoleCode
from .exceptions import (
    InvalidMembershipTransition,
    LastOwnerViolation,
    MemberAlreadyExists,
    MembershipNotActive,
    OrganizationAccessDenied,
    RoleAlreadyAssigned,
    RoleAssignmentDenied,
    RoleNotAssigned,
    VerifiedUserRequired,
)
from .models import Membership, MembershipEvent, MembershipRoleAssignment, Organization
from .policies import (
    can_assign_role,
    can_manage_membership,
    has_capability,
    target_is_active_owner,
)

if TYPE_CHECKING:
    from domain.identity.models import User


def _record_event(
    *,
    organization: Organization,
    membership: Membership,
    actor: User | None,
    event_type: MembershipEventType,
    role: RoleCode | None = None,
    previous_status: MembershipStatus | None = None,
    new_status: MembershipStatus | None = None,
) -> MembershipEvent:
    return MembershipEvent.objects.create(
        organization=organization,
        membership=membership,
        actor=actor,
        event_type=event_type,
        role=role.value if role else "",
        previous_status=previous_status.value if previous_status else "",
        new_status=new_status.value if new_status else "",
    )


def _locked_organization(organization: Organization) -> Organization:
    return Organization.objects.select_for_update().get(pk=organization.pk)


def _locked_membership(membership: Membership) -> Membership:
    return (
        Membership.objects.select_for_update()
        .select_related("organization", "user")
        .get(pk=membership.pk)
    )


def _active_owner_count(organization: Organization) -> int:
    return MembershipRoleAssignment.objects.filter(
        membership__organization=organization,
        membership__status=MembershipStatus.ACTIVE.value,
        role=RoleCode.OWNER.value,
        revoked_at__isnull=True,
    ).count()


def _ensure_not_last_owner(membership: Membership) -> None:
    if (
        target_is_active_owner(membership)
        and _active_owner_count(membership.organization) <= 1
    ):
        raise LastOwnerViolation(
            "La organización debe conservar un propietario activo."
        )


def _require_capability(
    actor: User | None, organization: Organization, capability: Capability
) -> None:
    if not has_capability(actor, organization, capability):
        raise OrganizationAccessDenied("No tienes capacidad para esta operación.")


@transaction.atomic
def create_organization_with_owner(
    *, actor: User, name: str, slug: str
) -> Organization:
    organization = Organization(name=name, slug=slug)
    organization.full_clean()
    organization.save()
    membership = Membership.objects.create(
        organization=organization,
        user=actor,
        status_changed_by=actor,
    )
    MembershipRoleAssignment.objects.create(
        membership=membership, role=RoleCode.OWNER.value, assigned_by=actor
    )
    _record_event(
        organization=organization,
        membership=membership,
        actor=actor,
        event_type=MembershipEventType.CREATED,
        new_status=MembershipStatus.ACTIVE,
    )
    _record_event(
        organization=organization,
        membership=membership,
        actor=actor,
        event_type=MembershipEventType.ROLE_ASSIGNED,
        role=RoleCode.OWNER,
    )
    return organization


@transaction.atomic
def update_organization_name(
    *, actor: User, organization: Organization, name: str
) -> Organization:
    locked = _locked_organization(organization)
    _require_capability(actor, locked, Capability.ORGANIZATION_UPDATE)
    locked.name = name
    locked.full_clean()
    locked.save(update_fields=["name", "updated_at"])
    return locked


@transaction.atomic
def add_existing_member(
    *,
    actor: User,
    organization: Organization,
    user: User,
) -> Membership:
    locked_organization = _locked_organization(organization)
    _require_capability(actor, locked_organization, Capability.MEMBERSHIP_ADD)
    if (
        not user.is_active
        or not EmailAddress.objects.filter(user=user, verified=True).exists()
    ):
        raise VerifiedUserRequired(
            "Solo se pueden agregar usuarios activos con correo verificado."
        )
    if (
        Membership.objects.filter(organization=locked_organization, user=user)
        .exclude(status=MembershipStatus.REVOKED.value)
        .exists()
    ):
        raise MemberAlreadyExists("La persona ya tiene una membresía vigente.")
    membership = Membership.objects.create(
        organization=locked_organization,
        user=user,
        status_changed_by=actor,
    )
    _record_event(
        organization=locked_organization,
        membership=membership,
        actor=actor,
        event_type=MembershipEventType.CREATED,
        new_status=MembershipStatus.ACTIVE,
    )
    return membership


@transaction.atomic
def add_existing_member_with_roles(
    *, actor: User, organization: Organization, user: User, roles: set[RoleCode]
) -> Membership:
    membership = add_existing_member(actor=actor, organization=organization, user=user)
    replace_membership_roles(actor=actor, membership=membership, roles=roles)
    return membership


def _transition_membership(
    *,
    actor: User,
    membership: Membership,
    target_status: MembershipStatus,
) -> Membership:
    locked_organization = _locked_organization(membership.organization)
    locked_membership = _locked_membership(membership)
    capability_by_target = {
        MembershipStatus.SUSPENDED: Capability.MEMBERSHIP_SUSPEND,
        MembershipStatus.ACTIVE: Capability.MEMBERSHIP_REACTIVATE,
        MembershipStatus.REVOKED: Capability.MEMBERSHIP_REVOKE,
    }
    capability = capability_by_target[target_status]
    if not can_manage_membership(actor, locked_membership, capability):
        raise OrganizationAccessDenied("No puedes gestionar esta membresía.")
    valid = {
        MembershipStatus.ACTIVE: {MembershipStatus.SUSPENDED, MembershipStatus.REVOKED},
        MembershipStatus.SUSPENDED: {MembershipStatus.ACTIVE, MembershipStatus.REVOKED},
    }
    if target_status not in valid.get(
        MembershipStatus(locked_membership.status), set()
    ):
        raise InvalidMembershipTransition("La transición de membresía no es válida.")
    if target_status in {MembershipStatus.SUSPENDED, MembershipStatus.REVOKED}:
        _ensure_not_last_owner(locked_membership)
    previous_status = MembershipStatus(locked_membership.status)
    now = timezone.now()
    locked_membership.status = target_status.value
    locked_membership.status_changed_at = now
    locked_membership.status_changed_by = actor
    locked_membership.suspended_at = (
        now if target_status == MembershipStatus.SUSPENDED else None
    )
    if target_status == MembershipStatus.REVOKED:
        locked_membership.revoked_at = now
    locked_membership.save(
        update_fields=[
            "status",
            "status_changed_at",
            "status_changed_by",
            "suspended_at",
            "revoked_at",
        ]
    )
    event_type = {
        MembershipStatus.SUSPENDED: MembershipEventType.SUSPENDED,
        MembershipStatus.ACTIVE: MembershipEventType.REACTIVATED,
        MembershipStatus.REVOKED: MembershipEventType.REVOKED,
    }[target_status]
    _record_event(
        organization=locked_organization,
        membership=locked_membership,
        actor=actor,
        event_type=event_type,
        previous_status=previous_status,
        new_status=target_status,
    )
    if target_status == MembershipStatus.REVOKED:
        for assignment in MembershipRoleAssignment.objects.select_for_update().filter(
            membership=locked_membership, revoked_at__isnull=True
        ):
            assignment.revoked_at = now
            assignment.revoked_by = actor
            assignment.save(update_fields=["revoked_at", "revoked_by"])
            _record_event(
                organization=locked_organization,
                membership=locked_membership,
                actor=actor,
                event_type=MembershipEventType.ROLE_REVOKED,
                role=RoleCode(assignment.role),
            )
    return locked_membership


@transaction.atomic
def suspend_membership(*, actor: User, membership: Membership) -> Membership:
    return _transition_membership(
        actor=actor, membership=membership, target_status=MembershipStatus.SUSPENDED
    )


@transaction.atomic
def reactivate_membership(*, actor: User, membership: Membership) -> Membership:
    return _transition_membership(
        actor=actor, membership=membership, target_status=MembershipStatus.ACTIVE
    )


@transaction.atomic
def revoke_membership(*, actor: User, membership: Membership) -> Membership:
    return _transition_membership(
        actor=actor, membership=membership, target_status=MembershipStatus.REVOKED
    )


@transaction.atomic
def assign_role(
    *, actor: User, membership: Membership, role: RoleCode
) -> MembershipRoleAssignment:
    _locked_organization(membership.organization)
    locked_membership = _locked_membership(membership)
    if locked_membership.status == MembershipStatus.REVOKED.value:
        raise MembershipNotActive("No se asignan roles a membresías revocadas.")
    if not can_assign_role(actor, locked_membership, role):
        raise RoleAssignmentDenied("No puedes asignar este rol.")
    if MembershipRoleAssignment.objects.filter(
        membership=locked_membership, role=role.value, revoked_at__isnull=True
    ).exists():
        raise RoleAlreadyAssigned("El rol ya está asignado.")
    try:
        assignment = MembershipRoleAssignment.objects.create(
            membership=locked_membership, role=role.value, assigned_by=actor
        )
    except IntegrityError as error:
        raise RoleAlreadyAssigned("El rol ya está asignado.") from error
    _record_event(
        organization=locked_membership.organization,
        membership=locked_membership,
        actor=actor,
        event_type=MembershipEventType.ROLE_ASSIGNED,
        role=role,
    )
    return assignment


@transaction.atomic
def replace_membership_roles(
    *, actor: User, membership: Membership, roles: set[RoleCode]
) -> Membership:
    _locked_organization(membership.organization)
    locked_membership = _locked_membership(membership)
    if locked_membership.status == MembershipStatus.ACTIVE.value and not roles:
        raise RoleAssignmentDenied(
            "Una membresía activa debe conservar al menos un rol."
        )
    active_assignments = {
        RoleCode(assignment.role): assignment
        for assignment in MembershipRoleAssignment.objects.select_for_update().filter(
            membership=locked_membership, revoked_at__isnull=True
        )
    }
    for role in sorted(active_assignments.keys() - roles, key=str):
        revoke_role(actor=actor, membership=locked_membership, role=role)
    for role in sorted(roles - active_assignments.keys(), key=str):
        assign_role(actor=actor, membership=locked_membership, role=role)
    return locked_membership


@transaction.atomic
def revoke_role(
    *, actor: User, membership: Membership, role: RoleCode
) -> MembershipRoleAssignment:
    _locked_organization(membership.organization)
    locked_membership = _locked_membership(membership)
    if not can_assign_role(actor, locked_membership, role):
        raise RoleAssignmentDenied("No puedes revocar este rol.")
    assignment = (
        MembershipRoleAssignment.objects.select_for_update()
        .filter(membership=locked_membership, role=role.value, revoked_at__isnull=True)
        .first()
    )
    if assignment is None:
        raise RoleNotAssigned("El rol no está asignado.")
    if role == RoleCode.OWNER:
        _ensure_not_last_owner(locked_membership)
    assignment.revoked_at = timezone.now()
    assignment.revoked_by = actor
    assignment.save(update_fields=["revoked_at", "revoked_by"])
    _record_event(
        organization=locked_membership.organization,
        membership=locked_membership,
        actor=actor,
        event_type=MembershipEventType.ROLE_REVOKED,
        role=role,
    )
    return assignment
