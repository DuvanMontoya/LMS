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

    def test_learner_access_is_limited_to_its_academic_experience(self) -> None:
        self.assertEqual(
            ROLE_CAPABILITIES[RoleCode.LEARNER],
            {
                Capability.ORGANIZATION_VIEW,
                Capability.ASSESSMENT_ATTEMPT,
                Capability.SCHEDULING_VIEW,
                Capability.LIVE_SESSION_JOIN,
                Capability.NOTIFICATION_PREFERENCES_MANAGE_OWN,
            },
        )

    def test_assessment_capability_matrix_matches_each_institutional_role(
        self,
    ) -> None:
        expected = {
            RoleCode.AUTHOR: {
                Capability.ASSESSMENT_BANK_VIEW,
                Capability.ASSESSMENT_BANK_MANAGE,
                Capability.ASSESSMENT_BANK_VERSION,
                Capability.ASSESSMENT_QUESTION_VIEW,
                Capability.ASSESSMENT_QUESTION_MANAGE,
                Capability.ASSESSMENT_QUESTION_SUBMIT,
                Capability.ASSESSMENT_AUTHORING_VIEW,
                Capability.ASSESSMENT_AUTHORING_MANAGE,
                Capability.ASSESSMENT_AUTHORING_SUBMIT,
                Capability.ASSESSMENT_DELIVERY_VIEW,
                Capability.ASSESSMENT_RESULTS_VIEW,
                Capability.ASSESSMENT_REGRADING_VIEW,
                Capability.ASSESSMENT_GRADEBOOK_VIEW,
                Capability.ASSESSMENT_ANALYTICS_VIEW,
            },
            RoleCode.REVIEWER: {
                Capability.ASSESSMENT_BANK_VIEW,
                Capability.ASSESSMENT_QUESTION_VIEW,
                Capability.ASSESSMENT_QUESTION_REVIEW,
                Capability.ASSESSMENT_AUTHORING_VIEW,
                Capability.ASSESSMENT_AUTHORING_REVIEW,
                Capability.ASSESSMENT_DELIVERY_VIEW,
                Capability.ASSESSMENT_RESULTS_VIEW,
                Capability.ASSESSMENT_REGRADING_VIEW,
                Capability.ASSESSMENT_ANALYTICS_VIEW,
            },
            RoleCode.INSTRUCTOR: {
                Capability.ASSESSMENT_BANK_VIEW,
                Capability.ASSESSMENT_QUESTION_VIEW,
                Capability.ASSESSMENT_AUTHORING_VIEW,
                Capability.ASSESSMENT_DELIVERY_VIEW,
                Capability.ASSESSMENT_DELIVERY_MANAGE,
                Capability.ASSESSMENT_GRADING_MANAGE,
                Capability.ASSESSMENT_RESULTS_VIEW,
                Capability.ASSESSMENT_REGRADING_VIEW,
                Capability.ASSESSMENT_REGRADING_MANAGE,
                Capability.ASSESSMENT_GRADEBOOK_VIEW,
                Capability.ASSESSMENT_GRADEBOOK_MANAGE,
                Capability.ASSESSMENT_ANALYTICS_VIEW,
                Capability.ASSESSMENT_ANALYTICS_REFRESH,
            },
            RoleCode.LEARNER: {Capability.ASSESSMENT_ATTEMPT},
        }
        for role, role_expected in expected.items():
            actual = {
                capability
                for capability in ROLE_CAPABILITIES[role]
                if capability.value.startswith("assessment.")
            }
            self.assertEqual(actual, role_expected, role.value)
        for role in (RoleCode.OWNER, RoleCode.ADMINISTRATOR):
            self.assertEqual(
                {
                    capability
                    for capability in ROLE_CAPABILITIES[role]
                    if capability.value.startswith("assessment.")
                },
                {
                    capability
                    for capability in Capability
                    if capability.value.startswith("assessment.")
                    and capability != Capability.ASSESSMENT_ATTEMPT
                },
            )

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

    def test_staff_and_platform_operator_are_not_organization_role_bypasses(
        self,
    ) -> None:
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
        self.assertFalse(
            has_capability(superuser, organization, Capability.MEMBERSHIP_ADD)
        )
        self.assertFalse(
            has_capability(superuser, organization, Capability.ASSESSMENT_ATTEMPT)
        )
