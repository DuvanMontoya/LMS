from __future__ import annotations

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from domain.organizations.capabilities import Capability
from domain.organizations.choices import MembershipStatus, RoleCode
from domain.organizations.exceptions import LastOwnerViolation, RoleAssignmentDenied
from domain.organizations.models import (
    Membership,
    MembershipEvent,
    OrganizationMemberProfile,
)
from domain.organizations.policies import has_capability
from domain.organizations.services import (
    add_existing_member_with_roles,
    assign_role,
    create_organization_with_owner,
    reactivate_membership,
    revoke_membership,
    revoke_role,
    suspend_membership,
)


class OrganizationServiceTests(TestCase):
    def verified_user(self, email: str):
        user = get_user_model().objects.create_user(
            email=email, password="CorrectHorseBatteryStaple42!"
        )
        EmailAddress.objects.create(
            user=user, email=user.email, primary=True, verified=True
        )
        return user

    def create_organization(self):
        owner = self.verified_user("owner@example.test")
        organization = create_organization_with_owner(
            actor=owner, name="Institución de prueba", slug="institucion-prueba"
        )
        return owner, organization

    def test_owner_membership_and_event_are_created_atomically(self) -> None:
        owner, organization = self.create_organization()
        membership = Membership.objects.get(organization=organization, user=owner)
        self.assertEqual(membership.status, MembershipStatus.ACTIVE.value)
        self.assertTrue(
            has_capability(owner, organization, Capability.ROLE_ASSIGN_OWNER)
        )
        self.assertEqual(
            MembershipEvent.objects.filter(membership=membership).count(), 2
        )
        self.assertTrue(
            OrganizationMemberProfile.objects.filter(membership=membership).exists()
        )

    def test_slug_is_reserved_lowercase_and_immutable(self) -> None:
        owner, organization = self.create_organization()
        organization.slug = "ADMIN"
        with self.assertRaises(ValidationError):
            organization.full_clean()
        organization.refresh_from_db()
        organization.slug = "other"
        with self.assertRaises(ValidationError):
            organization.full_clean()
        self.assertTrue(owner.is_active)

    def test_membership_lifecycle_preserves_history_and_roles(self) -> None:
        owner, organization = self.create_organization()
        learner = self.verified_user("learner@example.test")
        membership = add_existing_member_with_roles(
            actor=owner,
            organization=organization,
            user=learner,
            roles={RoleCode.LEARNER},
        )
        self.assertTrue(
            has_capability(learner, organization, Capability.ORGANIZATION_VIEW)
        )
        suspend_membership(actor=owner, membership=membership)
        self.assertFalse(
            has_capability(learner, organization, Capability.ORGANIZATION_VIEW)
        )
        reactivate_membership(actor=owner, membership=membership)
        self.assertTrue(
            has_capability(learner, organization, Capability.ORGANIZATION_VIEW)
        )
        revoke_membership(actor=owner, membership=membership)
        self.assertFalse(
            has_capability(learner, organization, Capability.ORGANIZATION_VIEW)
        )
        renewed = add_existing_member_with_roles(
            actor=owner,
            organization=organization,
            user=learner,
            roles={RoleCode.LEARNER},
        )
        self.assertNotEqual(membership.pk, renewed.pk)
        self.assertEqual(
            Membership.objects.filter(organization=organization, user=learner).count(),
            2,
        )

    def test_database_rejects_incoherent_membership_timestamps(self) -> None:
        owner, organization = self.create_organization()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Membership.objects.create(
                    organization=organization,
                    user=owner,
                    status=MembershipStatus.SUSPENDED.value,
                )

    def test_last_owner_cannot_be_removed_until_a_second_owner_exists(self) -> None:
        owner, organization = self.create_organization()
        membership = Membership.objects.get(organization=organization, user=owner)
        with self.assertRaises(LastOwnerViolation):
            revoke_role(actor=owner, membership=membership, role=RoleCode.OWNER)
        second_owner = self.verified_user("second-owner@example.test")
        second_membership = add_existing_member_with_roles(
            actor=owner,
            organization=organization,
            user=second_owner,
            roles={RoleCode.LEARNER},
        )
        assign_role(actor=owner, membership=second_membership, role=RoleCode.OWNER)
        revoke_role(actor=owner, membership=membership, role=RoleCode.OWNER)
        self.assertFalse(
            has_capability(owner, organization, Capability.ORGANIZATION_VIEW)
        )

    def test_administrator_cannot_assign_or_manage_owner(self) -> None:
        owner, organization = self.create_organization()
        administrator = self.verified_user("administrator@example.test")
        membership = add_existing_member_with_roles(
            actor=owner,
            organization=organization,
            user=administrator,
            roles={RoleCode.ADMINISTRATOR},
        )
        with self.assertRaises(RoleAssignmentDenied):
            assign_role(actor=administrator, membership=membership, role=RoleCode.OWNER)
