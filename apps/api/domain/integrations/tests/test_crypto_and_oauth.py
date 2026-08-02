from __future__ import annotations

import base64
from datetime import timedelta
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from domain.integrations.crypto import CredentialDecryptionError, decrypt, encrypt
from domain.integrations.exceptions import IntegrationConnectionUnavailable
from domain.integrations.models import OAuthAuthorizationRequest
from domain.integrations.services import begin_google_oauth, complete_google_oauth
from domain.organizations.services import create_organization_with_owner

KEY = base64.b64encode(b"k" * 32).decode("ascii")


@override_settings(
    INTEGRATIONS_MASTER_KEYS=f"test-key:{KEY}",
    INTEGRATIONS_ACTIVE_KEY_ID="test-key",
    GOOGLE_OAUTH_CLIENT_ID="client-id",
    GOOGLE_OAUTH_CLIENT_SECRET="client-secret",
    GOOGLE_OAUTH_AUTHORIZE_URL="https://accounts.google.test/authorize",
    GOOGLE_OAUTH_TOKEN_URL="https://oauth.google.test/token",
    GOOGLE_OAUTH_REDIRECT_URI="https://lms.test/api/v1/integrations/google/callback/",
)
class IntegrationSecurityTests(TestCase):
    def owner(self):
        user = get_user_model().objects.create_user(
            email="owner@example.test", password="CorrectHorseBatteryStaple42!"
        )
        EmailAddress.objects.create(
            user=user, email=user.email, primary=True, verified=True
        )
        return user

    def test_aes_gcm_binds_ciphertext_to_connection_context(self) -> None:
        encrypted = encrypt(plaintext="secret-value", aad=b"one")
        self.assertEqual(decrypt(encrypted=encrypted, aad=b"one"), "secret-value")
        with self.assertRaises(CredentialDecryptionError):
            decrypt(encrypted=encrypted, aad=b"two")

    def test_oauth_state_is_hashed_and_pkce_verifier_is_encrypted(self) -> None:
        owner = self.owner()
        organization = create_organization_with_owner(
            actor=owner, name="Institución", slug="institucion"
        )
        url = begin_google_oauth(
            actor=owner,
            organization=organization,
            capabilities=["calendar", "meet"],
        )
        request = OAuthAuthorizationRequest.objects.get()
        self.assertIn("code_challenge_method=S256", url)
        self.assertNotIn(request.state_digest, url)
        self.assertEqual(request.verifier_key_id, "test-key")
        self.assertTrue(request.verifier_ciphertext)

    def test_oauth_state_expires_and_cannot_be_reused(self) -> None:
        owner = self.owner()
        organization = create_organization_with_owner(
            actor=owner, name="Instituci\u00f3n", slug="institucion"
        )

        expired_url = begin_google_oauth(
            actor=owner, organization=organization, capabilities=["calendar"]
        )
        expired_state = expired_url.split("state=", 1)[1].split("&", 1)[0]
        expired_request = OAuthAuthorizationRequest.objects.get()
        expired_request.expires_at = timezone.now() - timedelta(seconds=1)
        expired_request.save(update_fields=("expires_at",))
        with self.assertRaises(IntegrationConnectionUnavailable):
            complete_google_oauth(state=expired_state, code="expired-code")

        reusable_url = begin_google_oauth(
            actor=owner, organization=organization, capabilities=["meet"]
        )
        reusable_state = reusable_url.split("state=", 1)[1].split("&", 1)[0]
        with patch(
            "domain.integrations.services.exchange_google_authorization_code",
            return_value={"access_token": "oauth-secret", "refresh_token": "refresh"},
        ):
            complete_google_oauth(state=reusable_state, code="approved-code")
        with self.assertRaises(IntegrationConnectionUnavailable):
            complete_google_oauth(state=reusable_state, code="replayed-code")
