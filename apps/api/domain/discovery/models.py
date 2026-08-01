# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import uuid

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex, OpClass
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.db.models import Q

from domain.events.models import DomainEvent
from domain.organizations.models import Organization


class GenerationStatus(models.TextChoices):
    BUILDING = "building", "Construyendo"
    ACTIVE = "active", "Activa"
    FAILED = "failed", "Fallida"
    SUPERSEDED = "superseded", "Reemplazada"


class SearchAudience(models.TextChoices):
    LEARNING = "learning", "Aprendizaje"
    AUTHORING = "authoring", "Autoría"
    INSTITUTIONAL = "institutional", "Institucional"


class SearchSourceType(models.TextChoices):
    COURSE_RELEASE = "course_release", "Release de curso"
    COURSE_UNIT = "course_unit", "Unidad de curso"
    CATALOG_SUBJECT = "catalog_subject", "Asignatura"
    CATALOG_TOPIC = "catalog_topic", "Tema"
    CATALOG_CONCEPT = "catalog_concept", "Concepto"
    LEARNING_OBJECTIVE = "learning_objective", "Objetivo"
    ASSET_VERSION = "asset_version", "Versión de asset"
    QUESTION_VERSION = "question_version", "Versión de pregunta"
    ASSESSMENT_VERSION = "assessment_version", "Versión de evaluación"


class SearchIndexJobStatus(models.TextChoices):
    PENDING = "pending", "Pendiente"
    PROCESSING = "processing", "Procesando"
    COMPLETED = "completed", "Completado"
    FAILED = "failed", "Fallido"


class SearchIndexOperation(models.TextChoices):
    UPSERT = "upsert", "Actualizar"
    DEACTIVATE = "deactivate", "Desactivar"
    REBUILD = "rebuild", "Reconstruir"


class SearchGeneration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="search_generations"
    )
    number = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=GenerationStatus.choices)
    document_count = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(max_length=80, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="search_generations_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("organization_id", "-number")
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "number"],
                name="discovery_generation_number_unique",
            ),
            models.UniqueConstraint(
                fields=["organization"],
                condition=Q(status=GenerationStatus.ACTIVE),
                name="discovery_one_active_generation",
            ),
            models.UniqueConstraint(
                fields=["organization"],
                condition=Q(status=GenerationStatus.BUILDING),
                name="discovery_one_building_generation",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.organization_id}:generation-{self.number}"


class SearchDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    generation = models.ForeignKey(
        SearchGeneration, on_delete=models.PROTECT, related_name="documents"
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="search_documents"
    )
    source_type = models.CharField(max_length=40, choices=SearchSourceType.choices)
    source_id = models.UUIDField()
    source_version_id = models.UUIDField(null=True, blank=True)
    audience = models.CharField(max_length=20, choices=SearchAudience.choices)
    language_code = models.CharField(max_length=8, default="es")
    title = models.CharField(max_length=300)
    subtitle = models.CharField(max_length=500, blank=True)
    body_plain_text = models.TextField(blank=True)
    normalized_title = models.CharField(max_length=300)
    url_path = models.CharField(max_length=1000)
    metadata = models.JSONField(default=dict)
    search_vector = SearchVectorField(null=True)
    content_digest = models.CharField(max_length=64)
    source_created_at = models.DateTimeField(null=True, blank=True)
    source_updated_at = models.DateTimeField(null=True, blank=True)
    indexed_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "generation",
                    "source_type",
                    "source_id",
                    "source_version_id",
                    "audience",
                ],
                nulls_distinct=False,
                name="discovery_document_source_unique",
            ),
            models.CheckConstraint(
                condition=Q(language_code__in=("es", "en")),
                name="discovery_language_supported",
            ),
        ]
        indexes = [
            GinIndex(fields=["search_vector"], name="discovery_search_vector_gin"),
            GinIndex(
                OpClass("normalized_title", name="gin_trgm_ops"),
                name="discovery_title_trgm_gin",
            ),
            models.Index(
                fields=["generation", "audience", "source_type"],
                name="discovery_generation_aud_ix",
            ),
            models.Index(
                fields=["organization", "source_id"], name="discovery_org_source_ix"
            ),
            models.Index(
                fields=["source_version_id"], name="discovery_source_version_ix"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.source_type}:{self.source_id}:{self.audience}"


class SearchIndexJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="search_index_jobs"
    )
    generation = models.ForeignKey(
        SearchGeneration,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="jobs",
    )
    source_type = models.CharField(max_length=40, choices=SearchSourceType.choices)
    source_id = models.UUIDField(null=True, blank=True)
    source_version_id = models.UUIDField(null=True, blank=True)
    operation = models.CharField(max_length=16, choices=SearchIndexOperation.choices)
    status = models.CharField(
        max_length=16,
        choices=SearchIndexJobStatus.choices,
        default=SearchIndexJobStatus.PENDING,
    )
    event = models.ForeignKey(
        DomainEvent,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="search_index_jobs",
    )
    attempt_count = models.PositiveSmallIntegerField(default=0)
    task_id = models.UUIDField(null=True, blank=True)
    last_error_code = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event", "operation"],
                condition=Q(event__isnull=False),
                name="discovery_event_operation_unique",
            )
        ]
        indexes = [
            models.Index(
                fields=["organization", "status", "created_at"],
                name="discovery_job_state_ix",
            )
        ]

    def __str__(self) -> str:
        return f"{self.operation}:{self.organization_id}:{self.id}"
