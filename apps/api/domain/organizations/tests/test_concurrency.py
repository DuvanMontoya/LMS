from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TransactionTestCase

from domain.organizations.choices import RoleCode
from domain.organizations.exceptions import LastOwnerViolation
from domain.organizations.models import Membership
from domain.organizations.services import (
    add_existing_member_with_roles,
    assign_role,
    create_organization_with_owner,
    revoke_membership,
)


class LastOwnerConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def verified_user(self, email: str):
        user = get_user_model().objects.create_user(
            email=email, password="CorrectHorseBatteryStaple42!"
        )
        EmailAddress.objects.create(
            user=user, email=user.email, primary=True, verified=True
        )
        return user

    def test_parallel_owner_revocations_leave_one_active_owner(self) -> None:
        first_owner = self.verified_user("first-owner@example.test")
        second_owner = self.verified_user("second-owner@example.test")
        organization = create_organization_with_owner(
            actor=first_owner, name="Institución", slug="institucion"
        )
        second_membership = add_existing_member_with_roles(
            actor=first_owner,
            organization=organization,
            user=second_owner,
            roles={RoleCode.LEARNER},
        )
        assign_role(
            actor=first_owner, membership=second_membership, role=RoleCode.OWNER
        )
        first_membership = Membership.objects.get(
            organization=organization, user=first_owner
        )

        def revoke(owner_id: object, membership_id: object) -> str:
            close_old_connections()
            try:
                actor = get_user_model().objects.get(pk=owner_id)
                membership = Membership.objects.get(pk=membership_id)
                revoke_membership(actor=actor, membership=membership)
                return "revoked"
            except LastOwnerViolation:
                return "protected"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(
                executor.map(
                    lambda values: revoke(*values),
                    [
                        (first_owner.pk, first_membership.pk),
                        (second_owner.pk, second_membership.pk),
                    ],
                )
            )
        self.assertCountEqual(outcomes, ["revoked", "protected"])
        self.assertEqual(
            Membership.objects.filter(
                organization=organization,
                status="active",
                role_assignments__role=RoleCode.OWNER.value,
                role_assignments__revoked_at__isnull=True,
            ).count(),
            1,
        )
