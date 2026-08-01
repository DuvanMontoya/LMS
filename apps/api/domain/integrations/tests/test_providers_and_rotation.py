from __future__ import annotations

import base64
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings

from domain.integrations.crypto import EncryptedValue, connection_aad, decrypt
from domain.integrations.models import IntegrationProvider
from domain.integrations.providers import (
    ApiKeyModelsAdapter,
    GeminiAdapter,
    GoogleWorkspaceAdapter,
    ProviderFailure,
    exchange_google_authorization_code,
)
from domain.integrations.services import connect_api_key
from domain.organizations.services import create_organization_with_owner

OLD_KEY = base64.b64encode(b"o" * 32).decode("ascii")
NEW_KEY = base64.b64encode(b"n" * 32).decode("ascii")


class ProviderAdapterTests(TestCase):
    def test_api_key_and_gemini_adapters_normalize_models(self) -> None:
        openai = ApiKeyModelsAdapter(
            IntegrationProvider.OPENAI, "https://api.test/models"
        )
        with patch(
            "domain.integrations.providers._json_get",
            return_value={"data": [{"id": "z"}, {"id": "a"}, {"ignored": 1}]},
        ):
            validation = openai.validate_credentials("secret-1234", [])
            models = openai.list_models("secret-1234")
        self.assertEqual(validation.account_label, "••••1234")
        self.assertEqual(models, ["a", "z"])

        gemini = GeminiAdapter()
        with patch(
            "domain.integrations.providers._json_get",
            return_value={"models": [{"name": "models/gemini-2"}]},
        ):
            self.assertEqual(gemini.list_models("secret-1234"), ["gemini-2"])

    def test_google_adapter_validates_requested_scopes_and_meeting(self) -> None:
        adapter = GoogleWorkspaceAdapter()
        with patch(
            "domain.integrations.providers._json_get", return_value={}
        ) as request:
            validation = adapter.validate_credentials(
                '{"access_token":"oauth-token"}',
                ["calendar", "drive", "youtube", "meet"],
            )
        self.assertEqual(request.call_count, 3)
        self.assertEqual(
            validation.capabilities, ["calendar", "drive", "youtube", "meet"]
        )
        self.assertIn("meetings.space.created", validation.granted_scopes[-1])
        with self.assertRaises(ProviderFailure):
            adapter.validate_credentials("{}", ["calendar"])

    def test_google_exchange_rejects_payload_without_access_token(self) -> None:
        with patch(
            "domain.integrations.providers._json_post",
            return_value={"refresh_token": "x"},
        ):
            with self.assertRaises(ProviderFailure):
                exchange_google_authorization_code(
                    token_url="https://oauth.test/token",
                    client_id="id",
                    client_secret="secret",
                    redirect_uri="https://lms.test/callback",
                    code="code",
                    code_verifier="verifier",
                )


@override_settings(
    INTEGRATIONS_MASTER_KEYS=f"old:{OLD_KEY}",
    INTEGRATIONS_ACTIVE_KEY_ID="old",
)
class CredentialRotationCommandTests(TestCase):
    def test_command_reencrypts_with_active_key_without_exposing_plaintext(
        self,
    ) -> None:
        owner = get_user_model().objects.create_user(
            email="owner@example.test", password="CorrectHorseBatteryStaple42!"
        )
        EmailAddress.objects.create(
            user=owner, email=owner.email, primary=True, verified=True
        )
        organization = create_organization_with_owner(
            actor=owner, name="Institución", slug="institucion"
        )
        connection = connect_api_key(
            actor=owner,
            organization=organization,
            provider=IntegrationProvider.GEMINI,
            api_key="rotation-secret-key-1234",
        )
        credential = connection.credential
        with override_settings(
            INTEGRATIONS_MASTER_KEYS=f"old:{OLD_KEY},new:{NEW_KEY}",
            INTEGRATIONS_ACTIVE_KEY_ID="new",
        ):
            call_command("rotate_integration_credentials")
            credential.refresh_from_db()
            self.assertEqual(credential.key_id, "new")
            plaintext = decrypt(
                encrypted=EncryptedValue(
                    key_id=credential.key_id,
                    nonce=bytes(credential.nonce),
                    ciphertext=bytes(credential.ciphertext),
                ),
                aad=connection_aad(
                    organization_id=organization.id,
                    provider=connection.provider,
                    connection_id=connection.id,
                ),
            )
        self.assertEqual(plaintext, "rotation-secret-key-1234")
