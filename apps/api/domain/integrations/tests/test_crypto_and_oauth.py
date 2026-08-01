from __future__ import annotations

import base64

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from domain.integrations.crypto import CredentialDecryptionError, decrypt, encrypt
from domain.integrations.models import OAuthAuthorizationRequest
from domain.integrations.services import begin_google_oauth
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
