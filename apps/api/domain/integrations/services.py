from __future__ import annotations

import base64
import hashlib
import json
import secrets
import uuid
from datetime import timedelta
from functools import partial
from typing import TYPE_CHECKING
from urllib.parse import urlencode

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from domain.organizations.capabilities import Capability
from domain.organizations.policies import has_capability

from .crypto import (
    CredentialConfigurationError,
    CredentialDecryptionError,
    EncryptedValue,
    connection_aad,
    decrypt,
    encrypt,
)
from .exceptions import (
    IntegrationAccessDenied,
    IntegrationConfigurationIncomplete,
    IntegrationConnectionUnavailable,
    IntegrationRevisionConflict,
)
from .models import (
    HealthCheckStatus,
    IntegrationAuthType,
    IntegrationConnection,
    IntegrationConnectionStatus,
    IntegrationCredential,
    IntegrationEvent,
    IntegrationHealthCheck,
    IntegrationProvider,
    OAuthAuthorizationRequest,
)
from .providers import (
    GoogleWorkspaceAdapter,
    ProviderFailure,
    adapter_for,
    exchange_google_authorization_code,
)

# ORM reverse relations are dynamic; policies and serialization remain explicit.
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportArgumentType=false

if TYPE_CHECKING:
    from domain.identity.models import User
    from domain.organizations.models import Organization


def _require_manage(actor: User, organization: Organization) -> None:
    if not has_capability(actor, organization, Capability.INTEGRATION_MANAGE):
        raise IntegrationAccessDenied("No tienes permiso para gestionar integraciones.")


def _aad(connection: IntegrationConnection) -> bytes:
    return connection_aad(
        organization_id=connection.organization_id,
        provider=connection.provider,
        connection_id=connection.id,
    )


def _credential_plaintext(connection: IntegrationConnection) -> str:
    try:
        credential = connection.credential
    except IntegrationCredential.DoesNotExist as error:
        raise IntegrationConnectionUnavailable(
            "La credencial no está disponible."
        ) from error
    try:
        return decrypt(
            encrypted=EncryptedValue(
                key_id=credential.key_id,
                nonce=bytes(credential.nonce),
                ciphertext=bytes(credential.ciphertext),
            ),
            aad=_aad(connection),
        )
    except (CredentialConfigurationError, CredentialDecryptionError) as error:
        raise IntegrationConfigurationIncomplete(
            "La credencial no está disponible."
        ) from error


def _record_event(
    *, connection: IntegrationConnection, actor: User | None, event_type: str
) -> None:
    IntegrationEvent.objects.create(
        connection=connection, actor=actor, event_type=event_type
    )


_GOOGLE_CAPABILITY_SCOPES = {
    "calendar": "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
    "meet": "https://www.googleapis.com/auth/meetings.space.created",
    "drive": "https://www.googleapis.com/auth/drive.metadata.readonly",
    "youtube": "https://www.googleapis.com/auth/youtube.readonly",
}


def _state_digest(state: str) -> str:
    return hashlib.sha256(state.encode("utf-8")).hexdigest()


def _new_pkce_verifier() -> str:
    return secrets.token_urlsafe(48)


def _pkce_challenge(verifier: str) -> str:
    return (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )


def _google_settings() -> tuple[str, str, str, str, str]:
    values = (
        str(settings.GOOGLE_OAUTH_CLIENT_ID),
        str(settings.GOOGLE_OAUTH_CLIENT_SECRET),
        str(settings.GOOGLE_OAUTH_AUTHORIZE_URL),
        str(settings.GOOGLE_OAUTH_TOKEN_URL),
        str(settings.GOOGLE_OAUTH_REDIRECT_URI),
    )
    if not all(values):
        raise IntegrationConfigurationIncomplete(
            "La configuración OAuth de Google está incompleta."
        )
    return values


@transaction.atomic
def begin_google_oauth(
    *,
    actor: User,
    organization: Organization,
    capabilities: list[str],
) -> str:
    _require_manage(actor, organization)
    requested = sorted(set(capabilities))
    if not requested or set(requested) - set(_GOOGLE_CAPABILITY_SCOPES):
        raise IntegrationConnectionUnavailable(
            "Las capacidades de Google no son válidas."
        )
    client_id, _, authorize_url, _, redirect_uri = _google_settings()
    connection, created = (
        IntegrationConnection.objects.select_for_update().get_or_create(
            organization=organization,
            provider=IntegrationProvider.GOOGLE_WORKSPACE,
            defaults={
                "auth_type": IntegrationAuthType.OAUTH2_USER,
                "created_by": actor,
            },
        )
    )
    if not created and connection.auth_type != IntegrationAuthType.OAUTH2_USER:
        raise IntegrationConnectionUnavailable(
            "La conexión usa otro tipo de autenticación."
        )
    verifier = _new_pkce_verifier()
    try:
        encrypted = encrypt(plaintext=verifier, aad=_aad(connection))
    except CredentialConfigurationError as error:
        raise IntegrationConfigurationIncomplete(
            "Falta la configuración de cifrado."
        ) from error
    state = secrets.token_urlsafe(32)
    OAuthAuthorizationRequest.objects.create(
        connection=connection,
        state_digest=_state_digest(state),
        verifier_key_id=encrypted.key_id,
        verifier_nonce=encrypted.nonce,
        verifier_ciphertext=encrypted.ciphertext,
        requested_capabilities=requested,
        expires_at=timezone.now() + timedelta(minutes=10),
        created_by=actor,
    )
    connection.status = IntegrationConnectionStatus.CONNECTING
    connection.capabilities = requested
    connection.last_error_code = ""
    connection.lock_version += 1
    connection.save(
        update_fields=(
            "status",
            "capabilities",
            "last_error_code",
            "lock_version",
            "updated_at",
        )
    )
    _record_event(connection=connection, actor=actor, event_type="oauth_started")
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(_GOOGLE_CAPABILITY_SCOPES[item] for item in requested),
            "state": state,
            "code_challenge": _pkce_challenge(verifier),
            "code_challenge_method": "S256",
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
        }
    )
    return f"{authorize_url}?{query}"


@transaction.atomic
def complete_google_oauth(*, state: str, code: str) -> IntegrationConnection:
    request = (
        OAuthAuthorizationRequest.objects.select_for_update()
        .select_related("connection__organization")
        .filter(state_digest=_state_digest(state))
        .first()
    )
    if (
        request is None
        or request.consumed_at is not None
        or request.expires_at <= timezone.now()
    ):
        raise IntegrationConnectionUnavailable(
            "La autorización OAuth no está disponible."
        )
    client_id, client_secret, _, token_url, redirect_uri = _google_settings()
    try:
        verifier = decrypt(
            encrypted=EncryptedValue(
                key_id=request.verifier_key_id,
                nonce=bytes(request.verifier_nonce),
                ciphertext=bytes(request.verifier_ciphertext),
            ),
            aad=_aad(request.connection),
        )
        token_payload = exchange_google_authorization_code(
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            code=code,
            code_verifier=verifier,
        )
        encrypted = encrypt(
            plaintext=json.dumps(token_payload, separators=(",", ":")),
            aad=_aad(request.connection),
        )
    except (CredentialConfigurationError, CredentialDecryptionError) as error:
        raise IntegrationConfigurationIncomplete(
            "La configuración de la conexión no está disponible."
        ) from error
    except ProviderFailure as error:
        raise IntegrationConnectionUnavailable(
            "Google rechazó la autorización."
        ) from error
    IntegrationCredential.objects.update_or_create(
        connection=request.connection,
        defaults={
            "key_id": encrypted.key_id,
            "nonce": encrypted.nonce,
            "ciphertext": encrypted.ciphertext,
            "last_four": "",
        },
    )
    request.consumed_at = timezone.now()
    request.save(update_fields=("consumed_at",))
    request.connection.status = IntegrationConnectionStatus.CONNECTING
    request.connection.last_error_code = ""
    request.connection.lock_version += 1
    request.connection.save(
        update_fields=("status", "last_error_code", "lock_version", "updated_at")
    )
    _record_event(
        connection=request.connection,
        actor=request.created_by,
        event_type="oauth_completed",
    )
    return request.connection


@transaction.atomic
def create_google_test_meeting(
    *, actor: User, connection: IntegrationConnection
) -> dict[str, object]:
    locked = (
        IntegrationConnection.objects.select_for_update()
        .select_related("organization")
        .get(pk=connection.pk)
    )
    _require_manage(actor, locked.organization)
    if (
        locked.provider != IntegrationProvider.GOOGLE_WORKSPACE
        or "meet" not in locked.capabilities
    ):
        raise IntegrationConnectionUnavailable(
            "La conexión no tiene capacidad de Meet."
        )
    adapter = adapter_for(locked.provider)
    if not isinstance(adapter, GoogleWorkspaceAdapter):
        raise IntegrationConnectionUnavailable(
            "El proveedor no admite reuniones de prueba."
        )
    try:
        result = adapter.create_test_meeting(_credential_plaintext(locked))
    except ProviderFailure as error:
        raise IntegrationConnectionUnavailable(
            "No fue posible crear la reunión."
        ) from error
    _record_event(connection=locked, actor=actor, event_type="meet_test_created")
    return result


@transaction.atomic
def connect_api_key(
    *,
    actor: User,
    organization: Organization,
    provider: IntegrationProvider,
    api_key: str,
    expected_version: int | None = None,
) -> IntegrationConnection:
    if provider == IntegrationProvider.GOOGLE_WORKSPACE:
        raise IntegrationConnectionUnavailable("Google Workspace requiere OAuth.")
    _require_manage(actor, organization)
    key = api_key.strip()
    if len(key) < 12:
        raise IntegrationConnectionUnavailable("La clave no es válida.")
    connection, created = (
        IntegrationConnection.objects.select_for_update().get_or_create(
            organization=organization,
            provider=provider,
            defaults={"auth_type": IntegrationAuthType.API_KEY, "created_by": actor},
        )
    )
    if (
        not created
        and expected_version is not None
        and connection.lock_version != expected_version
    ):
        raise IntegrationRevisionConflict("La conexión cambió antes de guardar.")
    if connection.auth_type != IntegrationAuthType.API_KEY:
        raise IntegrationConnectionUnavailable(
            "La conexión usa otro tipo de autenticación."
        )
    try:
        encrypted = encrypt(plaintext=key, aad=_aad(connection))
    except CredentialConfigurationError as error:
        raise IntegrationConfigurationIncomplete(
            "Falta la configuración de cifrado."
        ) from error
    IntegrationCredential.objects.update_or_create(
        connection=connection,
        defaults={
            "key_id": encrypted.key_id,
            "nonce": encrypted.nonce,
            "ciphertext": encrypted.ciphertext,
            "last_four": key[-4:],
        },
    )
    connection.status = IntegrationConnectionStatus.CONNECTING
    connection.account_label = "••••" + key[-4:]
    connection.last_error_code = ""
    connection.lock_version += 1
    connection.save(
        update_fields=(
            "status",
            "account_label",
            "last_error_code",
            "lock_version",
            "updated_at",
        )
    )
    _record_event(connection=connection, actor=actor, event_type="api_key_connected")
    return connection


@transaction.atomic
def queue_health_check(
    *, actor: User, connection: IntegrationConnection
) -> IntegrationHealthCheck:
    locked = (
        IntegrationConnection.objects.select_for_update()
        .select_related("organization")
        .get(pk=connection.pk)
    )
    _require_manage(actor, locked.organization)
    check = IntegrationHealthCheck.objects.create(
        connection=locked, task_id=uuid.uuid4()
    )
    _record_event(connection=locked, actor=actor, event_type="health_check_queued")
    from .tasks import run_integration_health_check

    transaction.on_commit(partial(run_integration_health_check.delay, str(check.id)))
    return check


def run_health_check(*, check_id: uuid.UUID) -> IntegrationHealthCheck:
    with transaction.atomic():
        check = (
            IntegrationHealthCheck.objects.select_for_update()
            .select_related("connection__organization")
            .get(pk=check_id)
        )
        if check.status in {HealthCheckStatus.SUCCEEDED, HealthCheckStatus.FAILED}:
            return check
        check.status = HealthCheckStatus.RUNNING
        check.started_at = timezone.now()
        check.save(update_fields=("status", "started_at"))
        connection = check.connection
    try:
        credential = _credential_plaintext(connection)
        adapter = adapter_for(connection.provider)
        result = adapter.validate_credentials(credential, list(connection.capabilities))
        models = adapter.list_models(credential)
    except (IntegrationConfigurationIncomplete, ProviderFailure) as error:
        code = (
            error.code
            if isinstance(error, ProviderFailure)
            else "configuration_incomplete"
        )
        with transaction.atomic():
            check = (
                IntegrationHealthCheck.objects.select_for_update()
                .select_related("connection")
                .get(pk=check_id)
            )
            check.status = HealthCheckStatus.FAILED
            check.error_code = code
            check.completed_at = timezone.now()
            check.save(update_fields=("status", "error_code", "completed_at"))
            check.connection.status = IntegrationConnectionStatus.DEGRADED
            check.connection.last_error_code = code
            check.connection.last_validated_at = check.completed_at
            check.connection.save(
                update_fields=(
                    "status",
                    "last_error_code",
                    "last_validated_at",
                    "updated_at",
                )
            )
        return check
    with transaction.atomic():
        check = (
            IntegrationHealthCheck.objects.select_for_update()
            .select_related("connection")
            .get(pk=check_id)
        )
        check.status = HealthCheckStatus.SUCCEEDED
        check.capabilities = result.capabilities
        check.completed_at = timezone.now()
        check.save(update_fields=("status", "capabilities", "completed_at"))
        connection = check.connection
        connection.status = IntegrationConnectionStatus.CONNECTED
        connection.account_label = result.account_label
        connection.capabilities = result.capabilities
        connection.granted_scopes = result.granted_scopes
        connection.allowed_models = models
        connection.last_error_code = ""
        connection.last_validated_at = check.completed_at
        connection.save(
            update_fields=(
                "status",
                "account_label",
                "capabilities",
                "granted_scopes",
                "allowed_models",
                "last_error_code",
                "last_validated_at",
                "updated_at",
            )
        )
    return check


@transaction.atomic
def disconnect(
    *, actor: User, connection: IntegrationConnection
) -> IntegrationConnection:
    locked = (
        IntegrationConnection.objects.select_for_update()
        .select_related("organization")
        .get(pk=connection.pk)
    )
    _require_manage(actor, locked.organization)
    try:
        adapter_for(locked.provider).revoke_or_disconnect(_credential_plaintext(locked))
    except (
        IntegrationConnectionUnavailable,
        IntegrationConfigurationIncomplete,
        ProviderFailure,
    ):
        pass
    IntegrationCredential.objects.filter(connection=locked).delete()
    locked.status = IntegrationConnectionStatus.REVOKED
    locked.account_label = ""
    locked.granted_scopes = []
    locked.allowed_models = []
    locked.last_error_code = ""
    locked.lock_version += 1
    locked.save(
        update_fields=(
            "status",
            "account_label",
            "granted_scopes",
            "allowed_models",
            "last_error_code",
            "lock_version",
            "updated_at",
        )
    )
    _record_event(connection=locked, actor=actor, event_type="disconnected")
    return locked
