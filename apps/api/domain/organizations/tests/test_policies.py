from __future__ import annotations

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import TestCase

from domain.organizations.capabilities import ROLE_CAPABILITIES, Capability
from domain.organizations.choices import RoleCode
from domain.organizations.policies import has_capability
from domain.organizations.services import (
    add_existing_member_with_roles,
    create_organization_with_owner,
    suspend_membership,
)


class OrganizationPolicyTests(TestCase):
    def verified_user(self, email: str, *, staff: bool = False):
        user = get_user_model().objects.create_user(
            email=email,
            password="CorrectHorseBatteryStaple42!",
            is_staff=staff,
        )
        EmailAddress.objects.create(
            user=user, email=user.email, primary=True, verified=True
        )
        return user

    def test_capability_matrix_is_complete_and_exact(self) -> None:
        self.assertEqual(set(ROLE_CAPABILITIES), set(RoleCode))
        self.assertEqual(set().union(*ROLE_CAPABILITIES.values()), set(Capability))
        for role in RoleCode:
            self.assertEqual(
                len(ROLE_CAPABILITIES[role]), len(set(ROLE_CAPABILITIES[role]))
            )

    def test_each_role_has_only_the_declared_capabilities(self) -> None:
        owner = self.verified_user("owner@example.test")
        organization = create_organization_with_owner(
            actor=owner, name="Institución", slug="institucion"
        )
        for role in RoleCode:
            user = self.verified_user(f"matrix-{role.value}@example.test")
            membership = add_existing_member_with_roles(
                actor=owner, organization=organization, user=user, roles={role}
            )
            for capability in Capability:
                self.assertEqual(
                    has_capability(user, organization, capability),
                    capability in ROLE_CAPABILITIES[role],
                    f"{role.value} / {capability.value}",
                )
            membership.refresh_from_db()

    def test_status_and_organization_scope_remove_capabilities(self) -> None:
        owner = self.verified_user("owner@example.test")
        instructor = self.verified_user("instructor@example.test")
        learner_owner = self.verified_user("learner-owner@example.test")
        first = create_organization_with_owner(
            actor=owner, name="Primera", slug="primera"
        )
        second = create_organization_with_owner(
            actor=learner_owner, name="Segunda", slug="segunda"
        )
        membership = add_existing_member_with_roles(
            actor=owner,
            organization=first,
            user=instructor,
            roles={RoleCode.INSTRUCTOR},
        )
        add_existing_member_with_roles(
            actor=learner_owner,
            organization=second,
            user=instructor,
            roles={RoleCode.LEARNER},
        )
        self.assertTrue(has_capability(instructor, first, Capability.ORGANIZATION_VIEW))
        self.assertFalse(has_capability(instructor, second, Capability.MEMBERSHIP_ADD))
        suspend_membership(actor=owner, membership=membership)
        self.assertFalse(
            has_capability(instructor, first, Capability.ORGANIZATION_VIEW)
        )

    def test_staff_is_not_a_bypass_and_superuser_is_explicit(self) -> None:
        owner = self.verified_user("owner@example.test")
        organization = create_organization_with_owner(
            actor=owner, name="Institución", slug="institucion"
        )
        staff = self.verified_user("staff@example.test", staff=True)
        superuser = self.verified_user("superuser@example.test")
        superuser.is_superuser = True
        superuser.is_staff = True
        superuser.save(update_fields=["is_superuser", "is_staff"])
        self.assertFalse(has_capability(staff, organization, Capability.MEMBERSHIP_ADD))
        self.assertTrue(
            has_capability(superuser, organization, Capability.MEMBERSHIP_ADD)
        )
