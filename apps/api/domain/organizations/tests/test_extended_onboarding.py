from datetime import date

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import TestCase

from domain.organizations.choices import MemberType, RoleCode
from domain.organizations.services import (
    create_managed_account,
    create_organization_with_owner,
    manually_activate_managed_account,
)


class ExtendedOnboardingTests(TestCase):
    def test_manual_activation_creates_verified_member_with_profile(self) -> None:
        owner = get_user_model().objects.create_user(
            email="owner-extended@example.test", password="OwnerPassword!42"
        )
        EmailAddress.objects.create(
            user=owner, email=owner.email, primary=True, verified=True
        )
        organization = create_organization_with_owner(
            actor=owner, name="Institución extendida", slug="institucion-extendida"
        )
        organization.membership_settings.allow_admin_managed_accounts = True
        organization.membership_settings.save(
            update_fields=("allow_admin_managed_accounts", "updated_at")
        )
        invitation, _ = create_managed_account(
            actor=owner,
            organization=organization,
            email="learner-extended@example.test",
            roles={RoleCode.LEARNER},
            given_name="Ana",
            family_name="Díaz",
            member_type=MemberType.LEARNER,
            date_of_birth=date(2010, 5, 3),
            whatsapp="+57 3001234567",
        )

        membership = manually_activate_managed_account(
            actor=owner,
            invitation=invitation,
            temporary_password="TemporaryPassword!42",
            confirm_identity=True,
        )

        membership.user.refresh_from_db()
        self.assertTrue(membership.user.is_active)
        self.assertTrue(EmailAddress.objects.get(user=membership.user).verified)
        self.assertEqual(membership.institutional_profile.first_name, "Ana")
        self.assertEqual(membership.institutional_profile.whatsapp, "+57 3001234567")
        self.assertGreaterEqual(membership.institutional_profile.age or 0, 15)
