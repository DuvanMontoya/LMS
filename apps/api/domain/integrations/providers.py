from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

from .models import IntegrationProvider

# urllib JSON payloads are validated at runtime before use.
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false


class ProviderFailure(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ProviderValidation:
    account_label: str
    capabilities: list[str]
    granted_scopes: list[str]


class ProviderAdapter(Protocol):
    def validate_credentials(
        self, credential: str, capabilities: list[str]
    ) -> ProviderValidation: ...
    def list_models(self, credential: str) -> list[str]: ...
    def revoke_or_disconnect(self, credential: str) -> None: ...
    def redact_error(self, error: Exception) -> str: ...


def _json_get(url: str, headers: dict[str, str]) -> dict[str, object]:
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=10) as response:  # noqa: S310 - endpoints are allowlisted below
            raw = response.read(1_000_000)
    except HTTPError as error:
        if error.code in {401, 403}:
            raise ProviderFailure("credential_invalid") from error
        if error.code == 429:
            raise ProviderFailure("provider_rate_limited") from error
        raise ProviderFailure("provider_unavailable") from error
    except URLError as error:
        raise ProviderFailure("provider_unavailable") from error
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ProviderFailure("provider_invalid_response") from error
    if not isinstance(payload, dict):
        raise ProviderFailure("provider_invalid_response")
    return payload


def _json_post(
    url: str, *, headers: dict[str, str], body: dict[str, str]
) -> dict[str, object]:
    request = Request(
        url,
        data=urlencode(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:  # noqa: S310 - configuration or allowlisted Google endpoint
            raw = response.read(1_000_000)
    except HTTPError as error:
        if error.code in {400, 401, 403}:
            raise ProviderFailure("credential_invalid") from error
        if error.code == 429:
            raise ProviderFailure("provider_rate_limited") from error
        raise ProviderFailure("provider_unavailable") from error
    except URLError as error:
        raise ProviderFailure("provider_unavailable") from error
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ProviderFailure("provider_invalid_response") from error
    if not isinstance(payload, dict):
        raise ProviderFailure("provider_invalid_response")
    return payload


def exchange_google_authorization_code(
    *,
    token_url: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code: str,
    code_verifier: str,
) -> dict[str, object]:
    payload = _json_post(
        token_url,
        headers={"Accept": "application/json"},
        body={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
        },
    )
    if not isinstance(payload.get("access_token"), str):
        raise ProviderFailure("provider_invalid_response")
    return payload


class ApiKeyModelsAdapter:
    def __init__(self, provider: IntegrationProvider, models_url: str) -> None:
        self.provider = provider
        self.models_url = models_url

    def _headers(self, credential: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {credential}", "Accept": "application/json"}

    def validate_credentials(
        self, credential: str, capabilities: list[str]
    ) -> ProviderValidation:
        self.list_models(credential)
        return ProviderValidation(
            account_label="••••" + credential[-4:], capabilities=[], granted_scopes=[]
        )

    def list_models(self, credential: str) -> list[str]:
        payload = _json_get(self.models_url, self._headers(credential))
        data = payload.get("data")
        if not isinstance(data, list):
            raise ProviderFailure("provider_invalid_response")
        return sorted(
            str(item["id"])
            for item in data
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        )

    def revoke_or_disconnect(self, credential: str) -> None:
        return None

    def redact_error(self, error: Exception) -> str:
        return (
            error.code if isinstance(error, ProviderFailure) else "provider_unavailable"
        )


class GeminiAdapter(ApiKeyModelsAdapter):
    def __init__(self) -> None:
        super().__init__(
            IntegrationProvider.GEMINI,
            _provider_url(
                "INTEGRATIONS_GEMINI_MODELS_URL",
                "https://generativelanguage.googleapis.com/v1beta/models",
            ),
        )

    def _headers(self, credential: str) -> dict[str, str]:
        return {"x-goog-api-key": credential, "Accept": "application/json"}

    def list_models(self, credential: str) -> list[str]:
        payload = _json_get(self.models_url, self._headers(credential))
        data = payload.get("models")
        if not isinstance(data, list):
            raise ProviderFailure("provider_invalid_response")
        return sorted(
            str(item["name"]).removeprefix("models/")
            for item in data
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        )


class GoogleWorkspaceAdapter:
    def _url(self, path: str, official_url: str) -> str:
        base_url = str(getattr(settings, "INTEGRATIONS_GOOGLE_API_BASE_URL", ""))
        return f"{base_url.rstrip('/')}{path}" if base_url else official_url

    @staticmethod
    def _access_token(credential: str) -> str:
        try:
            payload = json.loads(credential)
        except json.JSONDecodeError:
            payload = {"access_token": credential}
        token = payload.get("access_token") if isinstance(payload, dict) else None
        if not isinstance(token, str) or not token:
            raise ProviderFailure("credential_invalid")
        return token

    def validate_credentials(
        self, credential: str, capabilities: list[str]
    ) -> ProviderValidation:
        token = self._access_token(credential)
        scopes: list[str] = []
        if "calendar" in capabilities:
            _json_get(
                self._url(
                    "/calendar/v3/users/me/calendarList?maxResults=1",
                    "https://www.googleapis.com/calendar/v3/users/me/calendarList?maxResults=1",
                ),
                {"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
            scopes.append(
                "https://www.googleapis.com/auth/calendar.calendarlist.readonly"
            )
        if "drive" in capabilities:
            _json_get(
                self._url(
                    "/drive/v3/files?pageSize=1&fields=files(id)",
                    "https://www.googleapis.com/drive/v3/files?pageSize=1&fields=files(id)",
                ),
                {"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
            scopes.append("https://www.googleapis.com/auth/drive.metadata.readonly")
        if "youtube" in capabilities:
            _json_get(
                self._url(
                    "/youtube/v3/channels?part=id&mine=true",
                    "https://www.googleapis.com/youtube/v3/channels?part=id&mine=true",
                ),
                {"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
            scopes.append("https://www.googleapis.com/auth/youtube.readonly")
        if "meet" in capabilities:
            scopes.append("https://www.googleapis.com/auth/meetings.space.created")
        return ProviderValidation(
            account_label="Cuenta OAuth autorizada",
            capabilities=capabilities,
            granted_scopes=scopes,
        )

    def list_models(self, credential: str) -> list[str]:
        return []

    def revoke_or_disconnect(self, credential: str) -> None:
        return None

    def create_test_meeting(self, credential: str) -> dict[str, object]:
        token = self._access_token(credential)
        request = Request(
            self._url("/meet/v2/spaces", "https://meet.googleapis.com/v2/spaces"),
            data=b"{}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:  # noqa: S310 - official endpoint
                raw = response.read(1_000_000)
        except HTTPError as error:
            if error.code in {401, 403}:
                raise ProviderFailure("credential_invalid") from error
            raise ProviderFailure("provider_unavailable") from error
        except URLError as error:
            raise ProviderFailure("provider_unavailable") from error
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ProviderFailure("provider_invalid_response") from error
        if not isinstance(payload, dict) or not isinstance(payload.get("name"), str):
            raise ProviderFailure("provider_invalid_response")
        return {
            key: value
            for key, value in payload.items()
            if key in {"name", "meetingUri", "meetingCode"} and isinstance(value, str)
        }

    def redact_error(self, error: Exception) -> str:
        return (
            error.code if isinstance(error, ProviderFailure) else "provider_unavailable"
        )


def adapter_for(provider: str) -> ProviderAdapter:
    mapping: dict[str, ProviderAdapter] = {
        IntegrationProvider.OPENAI: ApiKeyModelsAdapter(
            IntegrationProvider.OPENAI,
            _provider_url(
                "INTEGRATIONS_OPENAI_MODELS_URL", "https://api.openai.com/v1/models"
            ),
        ),
        IntegrationProvider.GEMINI: GeminiAdapter(),
        IntegrationProvider.DEEPSEEK: ApiKeyModelsAdapter(
            IntegrationProvider.DEEPSEEK,
            _provider_url(
                "INTEGRATIONS_DEEPSEEK_MODELS_URL", "https://api.deepseek.com/models"
            ),
        ),
        IntegrationProvider.GOOGLE_WORKSPACE: GoogleWorkspaceAdapter(),
    }
    return mapping[provider]


def _provider_url(setting_name: str, official_url: str) -> str:
    """Keep production endpoints official while allowing an isolated E2E peer."""

    configured = str(getattr(settings, setting_name, ""))
    return configured or official_url
