from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Prefetch, QuerySet
from django.shortcuts import get_object_or_404

from .choices import MembershipStatus
from .models import Membership, MembershipRoleAssignment, Organization

if TYPE_CHECKING:
    from domain.identity.models import User


def organizations_visible_to(actor: User) -> QuerySet[Organization]:
    return Organization.objects.filter(
        memberships__user=actor, memberships__status=MembershipStatus.ACTIVE.value
    ).distinct()


def organization_visible_to(actor: User, slug: str) -> Organization:
    if actor.is_active and actor.is_superuser:
        return get_object_or_404(Organization, slug=slug)
    return get_object_or_404(organizations_visible_to(actor), slug=slug)


def memberships_for_organization(organization: Organization) -> QuerySet[Membership]:
    return (
        Membership.objects.filter(organization=organization)
        .select_related("user", "status_changed_by")
        .prefetch_related(
            Prefetch(
                "role_assignments",
                queryset=MembershipRoleAssignment.objects.filter(
                    revoked_at__isnull=True
                ),
            )
        )
    )


def membership_visible_to(
    actor: User, organization: Organization, membership_id: str
) -> Membership:
    return get_object_or_404(
        memberships_for_organization(organization), pk=membership_id
    )
