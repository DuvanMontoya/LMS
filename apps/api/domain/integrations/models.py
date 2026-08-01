from __future__ import annotations

import uuid
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from domain.organizations.models import Organization

# Django-stubs cannot infer unannotated relations on this bounded context.
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false


class IntegrationProvider(models.TextChoices):
    GOOGLE_WORKSPACE = "google_workspace", "Google Workspace"
    OPENAI = "openai", "OpenAI"
    GEMINI = "gemini", "Gemini"
    DEEPSEEK = "deepseek", "DeepSeek"


class IntegrationConnectionStatus(models.TextChoices):
    DISCONNECTED = "disconnected", "Desconectada"
    CONNECTING = "connecting", "Conectando"
    CONNECTED = "connected", "Conectada"
    DEGRADED = "degraded", "Degradada"
    REVOKED = "revoked", "Revocada"


class IntegrationAuthType(models.TextChoices):
    OAUTH2_USER = "oauth2_user", "OAuth 2.0 de usuario"
    API_KEY = "api_key", "Clave API"


class HealthCheckStatus(models.TextChoices):
    QUEUED = "queued", "En cola"
    RUNNING = "running", "En ejecución"
    SUCCEEDED = "succeeded", "Exitosa"
    FAILED = "failed", "Fallida"


class IntegrationConnection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="integration_connections"
    )
    provider = models.CharField(max_length=32, choices=IntegrationProvider.choices)
    status = models.CharField(
        max_length=16,
        choices=IntegrationConnectionStatus.choices,
        default=IntegrationConnectionStatus.DISCONNECTED,
    )
    auth_type = models.CharField(max_length=16, choices=IntegrationAuthType.choices)
    account_label = models.CharField(max_length=160, blank=True)
    capabilities = models.JSONField(default=list)
    granted_scopes = models.JSONField(default=list)
    allowed_models = models.JSONField(default=list)
    last_validated_at = models.DateTimeField(null=True, blank=True)
    last_error_code = models.CharField(max_length=80, blank=True)
    lock_version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="integration_connections_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "provider"],
                name="integrations_one_connection_per_provider",
            )
        ]
        indexes = [
            models.Index(
                fields=["organization", "status"], name="integration_org_state_ix"
            )
        ]

    def __str__(self) -> str:
        return f"{self.organization.slug}:{self.provider}"


class IntegrationCredential(models.Model):
    """Opaque encrypted secret. Plaintext is never a model field."""

    connection = models.OneToOneField(
        IntegrationConnection, on_delete=models.PROTECT, related_name="credential"
    )
    key_id = models.CharField(max_length=64)
    nonce = models.BinaryField(max_length=12)
    ciphertext = models.BinaryField()
    last_four = models.CharField(max_length=4, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    rotated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"credential:{self.connection_id}"


class OAuthAuthorizationRequest(models.Model):  # noqa: DJ012
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(
        IntegrationConnection, on_delete=models.PROTECT, related_name="oauth_requests"
    )
    state_digest = models.CharField(max_length=64, unique=True)
    verifier_key_id = models.CharField(max_length=64)
    verifier_nonce = models.BinaryField(max_length=12)
    verifier_ciphertext = models.BinaryField()
    requested_capabilities = models.JSONField(default=list)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="oauth_authorization_requests_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["connection", "expires_at"], name="oauth_connection_expiry_ix"
            )
        ]

    def __str__(self) -> str:
        return f"oauth:{self.connection_id}:{self.id}"


class IntegrationHealthCheck(models.Model):  # noqa: DJ012
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(
        IntegrationConnection, on_delete=models.PROTECT, related_name="health_checks"
    )
    status = models.CharField(
        max_length=16,
        choices=HealthCheckStatus.choices,
        default=HealthCheckStatus.QUEUED,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    capabilities = models.JSONField(default=list)
    error_code = models.CharField(max_length=80, blank=True)
    task_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["connection", "-created_at"],
                name="health_connection_created_ix",
            )
        ]

    def __str__(self) -> str:
        return f"health:{self.connection_id}:{self.status}"


class IntegrationEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(
        IntegrationConnection, on_delete=models.PROTECT, related_name="events"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="integration_events",
    )
    event_type = models.CharField(max_length=64)
    details = models.JSONField(default=dict)
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["connection", "-created_at"],
                name="integration_event_created_ix",
            )
        ]

    def __str__(self) -> str:
        return f"{self.connection_id}:{self.event_type}"

    def save(self, *args: object, **kwargs: object) -> None:
        if not self._state.adding:
            raise ValidationError("IntegrationEvent es append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        raise ValidationError("IntegrationEvent es append-only.")
