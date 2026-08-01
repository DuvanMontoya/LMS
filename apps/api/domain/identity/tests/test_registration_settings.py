import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from domain.identity.models import PlatformRegistrationSettings


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
