from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from domain.organizations.choices import MembershipStatus, RoleCode
from domain.organizations.models import (
    Membership,
    MembershipRoleAssignment,
    Organization,
)
from domain.organizations.services import create_organization_with_owner


class BootstrapLocalAccessTests(TestCase):
    @override_settings(DEBUG=True)
    def test_creates_verified_idempotent_local_access(self) -> None:
        owner = get_user_model().objects.create_user(
            email="owner@example.test",
            password="OwnerPassword42!",
        )
        EmailAddress.objects.create(
            user=owner,
            email=owner.email,
            primary=True,
            verified=True,
        )
        organization = create_organization_with_owner(
            actor=owner,
            name="Academia local",
            slug="academia-local",
        )

        with patch.dict(
            "os.environ",
            {"LMS_LOCAL_ACCESS_PASSWORD": "LocalPassword42!"},
        ):
            call_command(
                "bootstrap_local_access",
                email="person@example.test",
                organization_slug=organization.slug,
                role=RoleCode.ADMINISTRATOR.value,
                stdout=StringIO(),
            )
            initial_password_hash = (
                get_user_model().objects.get(email="person@example.test").password
            )
            call_command(
                "bootstrap_local_access",
                email="person@example.test",
                organization_slug=organization.slug,
                role=RoleCode.ADMINISTRATOR.value,
                stdout=StringIO(),
            )

        user = get_user_model().objects.get(email="person@example.test")
        membership = Membership.objects.get(organization=organization, user=user)
        self.assertTrue(user.check_password("LocalPassword42!"))
        self.assertEqual(user.password, initial_password_hash)
        self.assertTrue(
            EmailAddress.objects.filter(
                user=user,
                email=user.email,
                primary=True,
                verified=True,
            ).exists()
        )
        self.assertEqual(membership.status, MembershipStatus.ACTIVE.value)
        self.assertEqual(
            MembershipRoleAssignment.objects.filter(
                membership=membership,
                role=RoleCode.ADMINISTRATOR.value,
                revoked_at__isnull=True,
            ).count(),
            1,
        )

    @override_settings(DEBUG=True)
    def test_creates_personal_organization_and_can_make_access_exclusive(
        self,
    ) -> None:
        legacy_owner = get_user_model().objects.create_user(
            email="legacy-owner@example.test",
            password="OwnerPassword42!",
        )
        EmailAddress.objects.create(
            user=legacy_owner,
            email=legacy_owner.email,
            primary=True,
            verified=True,
        )
        legacy = create_organization_with_owner(
            actor=legacy_owner,
            name="Contexto heredado",
            slug="contexto-heredado",
        )

        with patch.dict(
            "os.environ",
            {"LMS_LOCAL_ACCESS_PASSWORD": "LocalPassword42!"},
        ):
            call_command(
                "bootstrap_local_access",
                email="person@example.test",
                organization_slug=legacy.slug,
                role=RoleCode.ADMINISTRATOR.value,
                stdout=StringIO(),
            )
            call_command(
                "bootstrap_local_access",
                email="person@example.test",
                organization_slug="espacio-personal",
                organization_name="Espacio académico personal",
                exclusive=True,
                stdout=StringIO(),
            )

        user = get_user_model().objects.get(email="person@example.test")
        personal = Organization.objects.get(slug="espacio-personal")
        personal_membership = Membership.objects.get(
            organization=personal,
            user=user,
        )
        legacy_membership = Membership.objects.get(
            organization=legacy,
            user=user,
        )
        self.assertEqual(
            personal_membership.status,
            MembershipStatus.ACTIVE.value,
        )
        self.assertTrue(
            MembershipRoleAssignment.objects.filter(
                membership=personal_membership,
                role=RoleCode.OWNER.value,
                revoked_at__isnull=True,
            ).exists()
        )
        self.assertEqual(
            legacy_membership.status,
            MembershipStatus.REVOKED.value,
        )

    @override_settings(DEBUG=False)
    def test_rejects_non_development_settings_before_database_access(self) -> None:
        with self.assertRaisesMessage(
            CommandError,
            "El acceso local sólo se permite con DEBUG=True.",
        ):
            call_command(
                "bootstrap_local_access",
                email="person@example.test",
                organization_slug="academia-local",
                stdout=StringIO(),
            )
