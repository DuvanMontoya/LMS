from __future__ import annotations

import base64
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from domain.integrations.models import (
    HealthCheckStatus,
    IntegrationConnectionStatus,
    IntegrationCredential,
    IntegrationHealthCheck,
    IntegrationProvider,
)
from domain.integrations.providers import ProviderFailure, ProviderValidation
from domain.integrations.services import (
    begin_google_oauth,
    complete_google_oauth,
    connect_api_key,
    create_google_test_meeting,
    disconnect,
    run_health_check,
)
from domain.organizations.services import create_organization_with_owner

KEY = base64.b64encode(b"z" * 32).decode("ascii")


class SuccessfulAdapter:
    def validate_credentials(
        self, credential: str, capabilities: list[str]
    ) -> ProviderValidation:
        return ProviderValidation(
            account_label="Cuenta válida",
            capabilities=capabilities,
            granted_scopes=["validated"],
        )

    def list_models(self, credential: str) -> list[str]:
        return ["model-a", "model-b"]

    def revoke_or_disconnect(self, credential: str) -> None:
        return None


class FailingAdapter(SuccessfulAdapter):
    def validate_credentials(
        self, credential: str, capabilities: list[str]
    ) -> ProviderValidation:
        raise ProviderFailure("credential_invalid")


@override_settings(
    INTEGRATIONS_MASTER_KEYS=f"test-key:{KEY}",
    INTEGRATIONS_ACTIVE_KEY_ID="test-key",
    GOOGLE_OAUTH_CLIENT_ID="client-id",
    GOOGLE_OAUTH_CLIENT_SECRET="client-secret",
    GOOGLE_OAUTH_AUTHORIZE_URL="https://accounts.google.test/authorize",
    GOOGLE_OAUTH_TOKEN_URL="https://oauth.google.test/token",
    GOOGLE_OAUTH_REDIRECT_URI="https://lms.test/api/v1/integrations/google/callback/",
)
class IntegrationServiceAndApiTests(TestCase):
    def setUp(self) -> None:
        self.owner = get_user_model().objects.create_user(
            email="owner@example.test", password="CorrectHorseBatteryStaple42!"
        )
        EmailAddress.objects.create(
            user=self.owner, email=self.owner.email, primary=True, verified=True
        )
        self.organization = create_organization_with_owner(
            actor=self.owner, name="Institución", slug="institucion"
        )

    def test_api_key_connection_health_rotation_and_disconnect(self) -> None:
        connection = connect_api_key(
            actor=self.owner,
            organization=self.organization,
            provider=IntegrationProvider.OPENAI,
            api_key="first-secret-key-1234",
        )
        self.assertEqual(connection.status, IntegrationConnectionStatus.CONNECTING)
        self.assertEqual(connection.credential.last_four, "1234")
        check = IntegrationHealthCheck.objects.create(connection=connection)
        with patch(
            "domain.integrations.services.adapter_for", return_value=SuccessfulAdapter()
        ):
            completed = run_health_check(check_id=check.id)
        self.assertEqual(completed.status, HealthCheckStatus.SUCCEEDED)
        connection.refresh_from_db()
        self.assertEqual(connection.status, IntegrationConnectionStatus.CONNECTED)
        self.assertEqual(connection.allowed_models, ["model-a", "model-b"])

        with patch(
            "domain.integrations.services.adapter_for", return_value=SuccessfulAdapter()
        ):
            disconnected = disconnect(actor=self.owner, connection=connection)
        self.assertEqual(disconnected.status, IntegrationConnectionStatus.REVOKED)
        self.assertFalse(
            IntegrationCredential.objects.filter(connection=connection).exists()
        )

    def test_failed_health_check_redacts_provider_failure_code(self) -> None:
        connection = connect_api_key(
            actor=self.owner,
            organization=self.organization,
            provider=IntegrationProvider.DEEPSEEK,
            api_key="failure-secret-key-1234",
        )
        check = IntegrationHealthCheck.objects.create(connection=connection)
        with patch(
            "domain.integrations.services.adapter_for", return_value=FailingAdapter()
        ):
            completed = run_health_check(check_id=check.id)
        self.assertEqual(completed.status, HealthCheckStatus.FAILED)
        self.assertEqual(completed.error_code, "credential_invalid")
        connection.refresh_from_db()
        self.assertEqual(connection.status, IntegrationConnectionStatus.DEGRADED)

    def test_google_completion_and_test_meeting_keep_tokens_server_side(self) -> None:
        authorization_url = begin_google_oauth(
            actor=self.owner,
            organization=self.organization,
            capabilities=["meet"],
        )
        state = parse_qs(urlparse(authorization_url).query)["state"][0]
        with patch(
            "domain.integrations.services.exchange_google_authorization_code",
            return_value={"access_token": "oauth-secret", "refresh_token": "refresh"},
        ):
            connection = complete_google_oauth(state=state, code="approved-code")
        self.assertTrue(
            IntegrationCredential.objects.filter(connection=connection).exists()
        )
        with patch(
            "domain.integrations.providers.GoogleWorkspaceAdapter.create_test_meeting",
            return_value={"name": "spaces/test", "meetingCode": "abc-defg-hij"},
        ):
            result = create_google_test_meeting(actor=self.owner, connection=connection)
        self.assertEqual(result["meetingCode"], "abc-defg-hij")

    def test_integration_api_exposes_no_api_key_and_honors_revision(self) -> None:
        self.client.force_login(self.owner)
        base = f"/api/v1/organizations/{self.organization.slug}/integrations"
        with (
            self.captureOnCommitCallbacks(execute=True),
            patch("domain.integrations.tasks.run_integration_health_check.delay") as delay,
        ):
            created = self.client.post(
                f"{base}/api-key/",
                {"provider": "openai", "api_key": "api-secret-key-1234"},
                content_type="application/json",
            )
        self.assertEqual(created.status_code, 200)
        self.assertNotIn("api_key", created.json())
        connection_id = created.json()["id"]
        delay.assert_called_once()
        self.assertEqual(
            self.client.get(f"{base}/{connection_id}/health-checks/").json()[0]["status"],
            HealthCheckStatus.QUEUED,
        )
        self.assertEqual(self.client.get(f"{base}/").status_code, 200)
        self.assertEqual(
            self.client.get(f"{base}/{connection_id}/health-checks/").status_code,
            200,
        )
        with (
            self.captureOnCommitCallbacks(execute=True),
            patch("domain.integrations.tasks.run_integration_health_check.delay"),
        ):
            queued = self.client.post(f"{base}/{connection_id}/health-checks/")
        self.assertEqual(queued.status_code, 202)

        stale = self.client.post(
            f"{base}/{connection_id}/rotate-key/",
            {"api_key": "replacement-key-1234", "expected_version": 1},
            content_type="application/json",
        )
        self.assertEqual(stale.status_code, 409)
        connection = connect_api_key(
            actor=self.owner,
            organization=self.organization,
            provider=IntegrationProvider.OPENAI,
            api_key="replacement-key-1234",
            expected_version=2,
        )
        self.assertEqual(connection.credential.last_four, "1234")
        with patch(
            "domain.integrations.services.adapter_for", return_value=SuccessfulAdapter()
        ):
            self.assertEqual(
                self.client.post(f"{base}/{connection_id}/disconnect/").status_code,
                200,
            )

    def test_google_authorize_api_returns_pkce_url(self) -> None:
        self.client.force_login(self.owner)
        response = self.client.post(
            f"/api/v1/organizations/{self.organization.slug}/integrations/google/authorize/",
            {"capabilities": ["calendar"]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("code_challenge=", response.json()["authorization_url"])
