import json
from urllib.parse import parse_qs, urlparse

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase

from domain.identity.models import PlatformRegistrationSettings
from domain.organizations.choices import OrganizationStatus
from domain.organizations.models import Membership
from domain.organizations.services import provision_platform_organization


class RegistrationSettingsApiTests(TestCase):
    def setUp(self) -> None:
        self.superuser = get_user_model().objects.create_superuser(
            email="root@example.test", password="CorrectHorseBatteryStaple42!"
        )

    def test_public_settings_and_superuser_versioned_update(self) -> None:
        public = self.client.get("/api/v1/platform/registration-settings/public/")
        self.assertEqual(public.status_code, 200)
        self.assertEqual(public.json()["signup_mode"], "open")

        self.client.force_login(self.superuser)
        current = self.client.get("/api/v1/platform/registration-settings/")
        self.assertEqual(current.status_code, 200)
        response = self.client.put(
            "/api/v1/platform/registration-settings/",
            {
                "expected_version": current.json()["lock_version"],
                "signup_mode": "invite_only",
                "default_locale": "es-CO",
                "default_timezone": "America/Bogota",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["signup_mode"], "invite_only")
        self.assertFalse(response.json()["public_signup_enabled"])
        self.assertEqual(
            PlatformRegistrationSettings.current().updated_by, self.superuser
        )

        conflict = self.client.put(
            "/api/v1/platform/registration-settings/",
            {
                "expected_version": 1,
                "signup_mode": "open",
                "default_locale": "es",
                "default_timezone": "UTC",
            },
            content_type="application/json",
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "revision_conflict")

    def test_non_superuser_cannot_read_or_update_private_settings(self) -> None:
        user = get_user_model().objects.create_user(
            email="member@example.test", password="CorrectHorseBatteryStaple42!"
        )
        self.client.force_login(user)
        self.assertEqual(
            self.client.get("/api/v1/platform/registration-settings/").status_code,
            403,
        )
        self.assertEqual(
            self.client.put(
                "/api/v1/platform/registration-settings/",
                {
                    "expected_version": 1,
                    "signup_mode": "open",
                    "default_locale": "es",
                    "default_timezone": "UTC",
                },
                content_type="application/json",
            ).status_code,
            403,
        )

    def test_closed_registration_rejects_direct_allauth_signup(self) -> None:
        registration = PlatformRegistrationSettings.current()
        registration.signup_mode = PlatformRegistrationSettings.SignupMode.CLOSED
        registration.public_signup_enabled = False
        registration.full_clean()
        registration.save(
            update_fields=("signup_mode", "public_signup_enabled", "updated_at")
        )

        response = self.client.post(
            "/_allauth/browser/v1/auth/signup",
            data=json.dumps(
                {
                    "email": "blocked@example.test",
                    "password": "CorrectHorseBatteryStaple42!",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            get_user_model().objects.filter(email="blocked@example.test").exists()
        )

    def test_closed_registration_allows_only_the_email_bound_to_invitation_session(
        self,
    ) -> None:
        registration = PlatformRegistrationSettings.current()
        registration.signup_mode = PlatformRegistrationSettings.SignupMode.CLOSED
        registration.public_signup_enabled = False
        registration.full_clean()
        registration.save(
            update_fields=("signup_mode", "public_signup_enabled", "updated_at")
        )
        with self.captureOnCommitCallbacks(execute=True):
            organization = provision_platform_organization(
                actor=self.superuser,
                name="Academia invitada",
                owner_email="invited-owner@example.test",
            )
        activation_url = next(
            part for part in mail.outbox[-1].body.split() if "?token=" in part
        )
        token = parse_qs(urlparse(activation_url).query)["token"][0]

        activated = self.client.post(
            "/api/v1/public/invitations/activate/",
            {"token": token},
            content_type="application/json",
        )
        self.assertEqual(activated.status_code, 200)
        context = self.client.get("/api/v1/public/invitations/signup-context/")
        self.assertEqual(context.status_code, 200)
        self.assertEqual(context.json()["email"], "invited-owner@example.test")
        self.assertEqual(context.json()["organization_name"], "Academia invitada")

        rejected = self.client.post(
            "/_allauth/browser/v1/auth/signup",
            data=json.dumps(
                {
                    "email": "attacker@example.test",
                    "password": "CorrectHorseBatteryStaple42!",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(rejected.status_code, 403)
        self.assertFalse(
            get_user_model().objects.filter(email="attacker@example.test").exists()
        )

        accepted = self.client.post(
            "/_allauth/browser/v1/auth/signup",
            data=json.dumps(
                {
                    "email": "INVITED-OWNER@example.test",
                    "password": "CorrectHorseBatteryStaple42!",
                }
            ),
            content_type="application/json",
        )
        self.assertIn(accepted.status_code, {200, 401})
        invited_owner = get_user_model().objects.get(email="invited-owner@example.test")
        self.assertFalse(
            Membership.objects.filter(
                organization=organization, user=invited_owner
            ).exists()
        )
        organization.refresh_from_db()
        self.assertEqual(organization.status, OrganizationStatus.PENDING_ACTIVATION)

    def test_verified_invited_owner_activates_pending_institution_once(self) -> None:
        registration = PlatformRegistrationSettings.current()
        registration.signup_mode = PlatformRegistrationSettings.SignupMode.CLOSED
        registration.public_signup_enabled = False
        registration.full_clean()
        registration.save(
            update_fields=("signup_mode", "public_signup_enabled", "updated_at")
        )
        with self.captureOnCommitCallbacks(execute=True):
            organization = provision_platform_organization(
                actor=self.superuser,
                name="Academia verificable",
                owner_email="owner-to-verify@example.test",
            )
        activation_url = next(
            part for part in mail.outbox[-1].body.split() if "?token=" in part
        )
        token = parse_qs(urlparse(activation_url).query)["token"][0]
        self.assertEqual(
            self.client.post(
                "/api/v1/public/invitations/activate/",
                {"token": token},
                content_type="application/json",
            ).status_code,
            200,
        )
        self.client.post(
            "/_allauth/browser/v1/auth/signup",
            data=json.dumps(
                {
                    "email": "owner-to-verify@example.test",
                    "password": "CorrectHorseBatteryStaple42!",
                }
            ),
            content_type="application/json",
        )
        user = get_user_model().objects.get(email="owner-to-verify@example.test")
        email_address = EmailAddress.objects.get(user=user)
        self.assertFalse(email_address.verified)
        organization.refresh_from_db()
        self.assertEqual(organization.status, OrganizationStatus.PENDING_ACTIVATION)

        email_address.verified = True
        email_address.save(update_fields=("verified",))
        self.client.force_login(user)
        accepted = self.client.post("/api/v1/public/invitations/accept/")
        self.assertEqual(accepted.status_code, 201)
        organization.refresh_from_db()
        self.assertEqual(organization.status, OrganizationStatus.ACTIVE)
