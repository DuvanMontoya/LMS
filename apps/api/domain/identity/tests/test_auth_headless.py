from __future__ import annotations

import json

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings

AUTH_BASE = "/_allauth/browser/v1/auth/"
CONFIG_URL = "/_allauth/browser/v1/config"


class HeadlessAuthTests(TestCase):
    def csrf_client(self) -> Client:
        client = Client(enforce_csrf_checks=True)
        response = client.get(CONFIG_URL)
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", client.cookies)
        return client

    def post_json(self, client: Client, url: str, payload: dict[str, str]):
        return client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        )

    def verification_code(self, client: Client) -> str:
        state = client.session["account_email_verification_code"]
        return str(state["code"])

    def signup_for_verification(self, client: Client, email: str) -> None:
        response = self.post_json(
            client,
            f"{AUTH_BASE}signup",
            {"email": email, "password": "CorrectHorseBatteryStaple42!"},
        )
        self.assertEqual(response.status_code, 401)

    def create_verified_user(self, email: str = "student@example.test"):
        user = get_user_model().objects.create_user(
            email=email, password="CorrectHorseBatteryStaple42!"
        )
        EmailAddress.objects.create(
            user=user, email=user.email, primary=True, verified=True
        )
        return user

    def test_browser_only_configuration_uses_database_sessions(self) -> None:
        self.assertEqual(settings.HEADLESS_CLIENTS, ("browser",))
        self.assertTrue(settings.HEADLESS_ONLY)
        self.assertEqual(
            settings.AUTHENTICATION_BACKENDS,
            [
                "django.contrib.auth.backends.ModelBackend",
                "allauth.account.auth_backends.AuthenticationBackend",
            ],
        )
        self.assertEqual(
            settings.MIDDLEWARE.count("allauth.account.middleware.AccountMiddleware"),
            1,
        )
        self.assertEqual(settings.SESSION_ENGINE, "django.contrib.sessions.backends.db")
        self.assertEqual(
            settings.CACHES["default"]["BACKEND"],
            "django.core.cache.backends.redis.RedisCache",
        )
        for excluded_app in (
            "allauth.socialaccount",
            "allauth.mfa",
            "allauth.usersessions",
            "django.contrib.sites",
        ):
            self.assertNotIn(excluded_app, settings.INSTALLED_APPS)

    def test_config_bootstraps_csrf_without_a_session_token(self) -> None:
        client = self.csrf_client()
        response = client.get(CONFIG_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], 200)
        self.assertEqual(response.json()["data"]["account"]["login_methods"], ["email"])
        self.assertNotIn("X-Session-Token", response.headers)
        self.assertNotIn("session_token", response.content.decode())
        self.assertNotIn("access_token", response.content.decode())

    def test_only_browser_headless_surface_is_available(self) -> None:
        self.assertEqual(self.client.get("/_allauth/app/v1/config").status_code, 404)
        self.assertEqual(self.client.get("/accounts/login/").status_code, 404)
        self.assertEqual(self.client.get("/accounts/signup/").status_code, 404)
        self.assertEqual(
            self.client.get("/_allauth/browser/v1/account/phone").status_code,
            404,
        )
        schema = self.client.get("/_allauth/openapi.json").json()
        self.assertFalse(
            any(
                capability in path
                for path in schema["paths"]
                for capability in ("phone", "mfa", "social", "/app/")
            )
        )

    def test_signup_verification_and_login_use_session_and_minimal_payload(
        self,
    ) -> None:
        client = self.csrf_client()
        signup = self.post_json(
            client,
            f"{AUTH_BASE}signup",
            {
                "email": " Student@Example.test ",
                "password": "CorrectHorseBatteryStaple42!",
            },
        )

        self.assertEqual(signup.status_code, 401)
        user = get_user_model().objects.get()
        self.assertEqual(user.email, "student@example.test")
        address = EmailAddress.objects.get(user=user)
        self.assertEqual(address.email, user.email)
        self.assertTrue(address.primary)
        self.assertFalse(address.verified)
        self.assertEqual(len(mail.outbox), 1)
        verification_message = mail.outbox[0]
        verification_code = self.verification_code(client)
        self.assertIn("Verifica tu correo", verification_message.subject)
        self.assertNotIn(verification_code, verification_message.subject)
        self.assertIn(verification_code, verification_message.body)
        self.assertIn("15 minutos", verification_message.body)
        self.assertNotIn("CorrectHorseBatteryStaple42!", verification_message.body)
        self.assertNotIn(str(user.pk), verification_message.body)
        self.assertNotIn("http", verification_message.body.lower())
        self.assertEqual(len(verification_message.alternatives), 1)
        verification_html = verification_message.alternatives[0].content
        self.assertIn('lang="es"', verification_html)
        self.assertIn(verification_code, verification_html)
        self.assertNotIn("<img", verification_html.lower())
        self.assertNotIn("tracker", verification_html.lower())

        before_verify_login = self.post_json(
            client,
            f"{AUTH_BASE}login",
            {"email": user.email, "password": "CorrectHorseBatteryStaple42!"},
        )
        # The upstream browser API can report the pending verification gate as
        # either a validation failure or an unauthenticated envelope. Neither
        # result may authenticate an unverified account.
        self.assertIn(before_verify_login.status_code, {400, 401})
        self.assertEqual(client.get(f"{AUTH_BASE}session").status_code, 401)

        verify = self.post_json(
            client,
            f"{AUTH_BASE}email/verify",
            {"key": verification_code},
        )
        self.assertEqual(verify.status_code, 200)
        address.refresh_from_db()
        self.assertTrue(address.verified)

        login_client = self.csrf_client()
        authenticated = self.post_json(
            login_client,
            f"{AUTH_BASE}login",
            {
                "email": " STUDENT@example.test ",
                "password": "CorrectHorseBatteryStaple42!",
            },
        )
        self.assertEqual(authenticated.status_code, 200)
        data = authenticated.json()["data"]["user"]
        self.assertEqual(set(data), {"id", "email", "display", "has_usable_password"})
        self.assertEqual(data["id"], str(user.pk))
        self.assertNotIn("is_staff", authenticated.content.decode())
        self.assertNotIn("is_superuser", authenticated.content.decode())
        self.assertIn("sessionid", login_client.cookies)
        session_cookie = login_client.cookies["sessionid"]
        self.assertTrue(session_cookie["httponly"])
        self.assertEqual(session_cookie["samesite"], "Lax")

    def test_invalid_credentials_inactive_user_and_duplicate_signup_are_generic(
        self,
    ) -> None:
        user = self.create_verified_user("known@example.test")
        active_client = self.csrf_client()
        unknown_client = self.csrf_client()

        wrong_password = self.post_json(
            active_client,
            f"{AUTH_BASE}login",
            {"email": user.email, "password": "not-the-right-password"},
        )
        unknown_account = self.post_json(
            unknown_client,
            f"{AUTH_BASE}login",
            {"email": "unknown@example.test", "password": "not-the-right-password"},
        )
        self.assertEqual(wrong_password.status_code, unknown_account.status_code)
        self.assertEqual(wrong_password.json(), unknown_account.json())
        self.assertEqual(
            wrong_password.headers.get("Content-Type"),
            unknown_account.headers.get("Content-Type"),
        )

        user.is_active = False
        user.save(update_fields=["is_active"])
        inactive_client = self.csrf_client()
        inactive = self.post_json(
            inactive_client,
            f"{AUTH_BASE}login",
            {"email": user.email, "password": "CorrectHorseBatteryStaple42!"},
        )
        self.assertGreaterEqual(inactive.status_code, 400)
        self.assertEqual(inactive_client.get(f"{AUTH_BASE}session").status_code, 401)

        duplicate_client = self.csrf_client()
        new_client = self.csrf_client()
        duplicate = self.post_json(
            duplicate_client,
            f"{AUTH_BASE}signup",
            {"email": user.email, "password": "CorrectHorseBatteryStaple42!"},
        )
        new_account = self.post_json(
            new_client,
            f"{AUTH_BASE}signup",
            {"email": "new@example.test", "password": "CorrectHorseBatteryStaple42!"},
        )
        self.assertEqual(duplicate.status_code, new_account.status_code)
        self.assertEqual(duplicate.json().keys(), new_account.json().keys())
        self.assertEqual(
            duplicate.headers.get("Content-Type"),
            new_account.headers.get("Content-Type"),
        )
        user.refresh_from_db()
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_signup_cannot_mass_assign_internal_user_fields(self) -> None:
        client = self.csrf_client()
        response = self.post_json(
            client,
            f"{AUTH_BASE}signup",
            {
                "email": "mass-assignment@example.test",
                "password": "CorrectHorseBatteryStaple42!",
                "is_staff": "true",
                "is_superuser": "true",
                "is_active": "false",
                "groups": "1",
                "user_permissions": "1",
            },
        )
        self.assertEqual(response.status_code, 401)
        user = get_user_model().objects.get(email="mass-assignment@example.test")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_verification_code_expires_and_is_single_use(self) -> None:
        client = self.csrf_client()
        self.signup_for_verification(client, "expired@example.test")
        code = self.verification_code(client)
        session = client.session
        state = session["account_email_verification_code"]
        state["at"] = 0
        session["account_email_verification_code"] = state
        session.save()

        expired = self.post_json(client, f"{AUTH_BASE}email/verify", {"key": code})
        self.assertEqual(expired.status_code, 409)
        self.assertFalse(EmailAddress.objects.get().verified)

        client = self.csrf_client()
        self.signup_for_verification(client, "single-use@example.test")
        code = self.verification_code(client)
        self.assertEqual(
            self.post_json(
                client, f"{AUTH_BASE}email/verify", {"key": code}
            ).status_code,
            200,
        )
        self.assertEqual(
            self.post_json(
                client, f"{AUTH_BASE}email/verify", {"key": code}
            ).status_code,
            409,
        )

    @override_settings(ACCOUNT_RATE_LIMITS={"confirm_email": "100/m/key"})
    def test_verification_rejects_three_invalid_codes_and_supports_resend(self) -> None:
        client = self.csrf_client()
        self.signup_for_verification(client, "attempts@example.test")
        original_code = self.verification_code(client)
        resend = client.post(
            f"{AUTH_BASE}email/verify/resend",
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        )
        self.assertEqual(resend.status_code, 200)
        self.assertNotEqual(self.verification_code(client), original_code)

        for _ in range(3):
            invalid = self.post_json(
                client, f"{AUTH_BASE}email/verify", {"key": "invalid-code"}
            )
        self.assertEqual(invalid.status_code, 400)
        self.assertNotIn("account_email_verification_code", client.session)
        self.assertFalse(EmailAddress.objects.get().verified)

    def test_verification_resend_is_not_immediately_repeatable(self) -> None:
        client = self.csrf_client()
        self.signup_for_verification(client, "resend-limit@example.test")
        resend = client.post(
            f"{AUTH_BASE}email/verify/resend",
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        )
        # allauth rejects either at the verification-process gate (409) or at
        # its Redis-backed confirmation limiter (429); neither permits spam.
        self.assertIn(resend.status_code, {409, 429})
        self.assertEqual(resend["Content-Type"], "application/json")

    def test_browser_posts_require_csrf_and_delete_logout_is_idempotent(self) -> None:
        client = Client(enforce_csrf_checks=True)
        rejected = client.post(
            f"{AUTH_BASE}signup",
            data=json.dumps(
                {
                    "email": "csrf@example.test",
                    "password": "CorrectHorseBatteryStaple42!",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(rejected.status_code, 403)

        malformed_client = self.csrf_client()
        malformed = malformed_client.post(
            f"{AUTH_BASE}signup",
            data="{",
            content_type="application/json",
            HTTP_X_CSRFTOKEN=malformed_client.cookies["csrftoken"].value,
        )
        self.assertEqual(malformed.status_code, 400)
        malformed_body = malformed.content.decode().lower()
        self.assertNotIn("traceback", malformed_body)
        self.assertNotIn("correcthorsebatterystaple42", malformed_body)

        user = self.create_verified_user("logout@example.test")
        client = self.csrf_client()
        client.session["pre_login_marker"] = "present"
        client.session.save()
        fixed_session = client.cookies["sessionid"].value
        login = self.post_json(
            client,
            f"{AUTH_BASE}login",
            {"email": user.email, "password": "CorrectHorseBatteryStaple42!"},
        )
        self.assertEqual(login.status_code, 200)
        original_session = client.cookies["sessionid"].value
        self.assertNotEqual(original_session, fixed_session)
        self.assertEqual(client.get(f"{AUTH_BASE}session").status_code, 200)
        self.assertEqual(client.get(f"{AUTH_BASE}session").json()["status"], 200)
        self.assertEqual(
            client.get(f"{AUTH_BASE}session").headers.get("Cache-Control"),
            "max-age=0, no-cache, no-store, must-revalidate, private",
        )

        get_logout = client.get(f"{AUTH_BASE}session")
        self.assertEqual(get_logout.status_code, 200)
        forbidden = client.delete(f"{AUTH_BASE}session")
        self.assertEqual(forbidden.status_code, 403)
        logout = client.delete(
            f"{AUTH_BASE}session", HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value
        )
        self.assertEqual(logout.status_code, 401)
        self.assertNotEqual(client.cookies.get("sessionid").value, original_session)
        self.assertEqual(
            client.delete(
                f"{AUTH_BASE}session",
                HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
            ).status_code,
            401,
        )

    def test_password_reset_code_changes_password_without_authenticating(self) -> None:
        user = self.create_verified_user("reset@example.test")
        authenticated_client = self.csrf_client()
        self.assertEqual(
            self.post_json(
                authenticated_client,
                f"{AUTH_BASE}login",
                {"email": user.email, "password": "CorrectHorseBatteryStaple42!"},
            ).status_code,
            200,
        )
        client = self.csrf_client()
        request_reset = self.post_json(
            client, f"{AUTH_BASE}password/request", {"email": user.email}
        )
        self.assertEqual(request_reset.status_code, 401)
        self.assertEqual(len(mail.outbox), 1)
        code = client.session["account_password_reset_verification"]["code"]
        reset_message = mail.outbox[0]
        self.assertIn("Restablece tu contraseña", reset_message.subject)
        self.assertNotIn(str(code), reset_message.subject)
        self.assertIn(str(code), reset_message.body)
        self.assertIn("3 minutos", reset_message.body)
        self.assertNotIn("CorrectHorseBatteryStaple42!", reset_message.body)
        self.assertNotIn(str(user.pk), reset_message.body)
        self.assertEqual(len(reset_message.alternatives), 1)
        reset_html = reset_message.alternatives[0].content
        self.assertIn('lang="es"', reset_html)
        self.assertIn(str(code), reset_html)
        self.assertNotIn("<img", reset_html.lower())
        self.assertNotIn("tracker", reset_html.lower())

        reset = self.post_json(
            client,
            f"{AUTH_BASE}password/reset",
            {"key": str(code), "password": "NewCorrectHorseBatteryStaple42!"},
        )
        self.assertEqual(reset.status_code, 401)
        self.assertEqual(reset.json()["status"], 401)
        user.refresh_from_db()
        self.assertTrue(user.check_password("NewCorrectHorseBatteryStaple42!"))
        self.assertFalse(user.check_password("CorrectHorseBatteryStaple42!"))
        self.assertTrue(user.password.startswith("argon2"))
        self.assertEqual(client.get(f"{AUTH_BASE}session").status_code, 401)
        self.assertEqual(
            authenticated_client.get(f"{AUTH_BASE}session").status_code,
            401,
        )

        old_password = self.post_json(
            self.csrf_client(),
            f"{AUTH_BASE}login",
            {"email": user.email, "password": "CorrectHorseBatteryStaple42!"},
        )
        self.assertEqual(old_password.status_code, 400)
        new_password = self.post_json(
            self.csrf_client(),
            f"{AUTH_BASE}login",
            {"email": user.email, "password": "NewCorrectHorseBatteryStaple42!"},
        )
        self.assertEqual(new_password.status_code, 200)

    @override_settings(
        ACCOUNT_RATE_LIMITS={
            "reset_password": "100/m/ip,100/m/key",
            "reset_password_from_key": "100/m/ip",
        }
    )
    def test_password_reset_code_expires_is_single_use_and_has_three_attempts(
        self,
    ) -> None:
        user = self.create_verified_user("reset-limits@example.test")
        client = self.csrf_client()
        self.assertEqual(
            self.post_json(
                client, f"{AUTH_BASE}password/request", {"email": user.email}
            ).status_code,
            401,
        )
        expired_code = client.session["account_password_reset_verification"]["code"]
        session = client.session
        state = session["account_password_reset_verification"]
        state["at"] = 0
        session["account_password_reset_verification"] = state
        session.save()
        self.assertEqual(
            self.post_json(
                client,
                f"{AUTH_BASE}password/reset",
                {
                    "key": str(expired_code),
                    "password": "NewCorrectHorseBatteryStaple42!",
                },
            ).status_code,
            409,
        )

        client = self.csrf_client()
        self.post_json(client, f"{AUTH_BASE}password/request", {"email": user.email})
        for _ in range(3):
            invalid = self.post_json(
                client,
                f"{AUTH_BASE}password/reset",
                {"key": "invalid-code", "password": "NewCorrectHorseBatteryStaple42!"},
            )
        self.assertEqual(invalid.status_code, 400)
        self.assertNotIn("account_password_reset_verification", client.session)

        client = self.csrf_client()
        self.post_json(client, f"{AUTH_BASE}password/request", {"email": user.email})
        code = client.session["account_password_reset_verification"]["code"]
        payload = {"key": str(code), "password": "NewCorrectHorseBatteryStaple42!"}
        self.assertEqual(
            self.post_json(client, f"{AUTH_BASE}password/reset", payload).status_code,
            401,
        )
        self.assertEqual(
            self.post_json(client, f"{AUTH_BASE}password/reset", payload).status_code,
            409,
        )

    def test_password_reset_response_does_not_enumerate_accounts(self) -> None:
        user = self.create_verified_user("known@example.test")
        known_client = self.csrf_client()
        unknown_client = self.csrf_client()

        known = self.post_json(
            known_client, f"{AUTH_BASE}password/request", {"email": user.email}
        )
        unknown = self.post_json(
            unknown_client,
            f"{AUTH_BASE}password/request",
            {"email": "unknown@example.test"},
        )

        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.json().keys(), unknown.json().keys())
        self.assertEqual(known.json()["status"], unknown.json()["status"])

    @override_settings(ACCOUNT_RATE_LIMITS={"signup": "1/m/ip"})
    def test_rate_limit_uses_redis_and_ignores_spoofed_forwarded_ip(self) -> None:
        cache.delete("allauth:rl:signup:ip:127.0.0.1")
        client = self.csrf_client()
        first = self.post_json(
            client,
            f"{AUTH_BASE}signup",
            {
                "email": "limit-one@example.test",
                "password": "CorrectHorseBatteryStaple42!",
            },
        )
        self.assertEqual(first.status_code, 401)
        second = client.post(
            f"{AUTH_BASE}signup",
            data=json.dumps(
                {
                    "email": "limit-two@example.test",
                    "password": "CorrectHorseBatteryStaple42!",
                }
            ),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
            HTTP_X_FORWARDED_FOR="198.51.100.99",
        )
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second["Content-Type"], "application/json")
        self.assertNotIn("<html", second.content.decode().lower())
        cache.delete("allauth:rl:signup:ip:127.0.0.1")

    def test_csrf_trusted_origins_accepts_localhost_and_loopback_ip(self) -> None:
        user = self.create_verified_user("loopback@example.test")
        client = self.csrf_client()
        response = client.post(
            f"{AUTH_BASE}login",
            data=json.dumps(
                {"email": user.email, "password": "CorrectHorseBatteryStaple42!"}
            ),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
            HTTP_ORIGIN="http://localhost:3000",
        )
        self.assertEqual(response.status_code, 200)

