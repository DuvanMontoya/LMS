# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportIncompatibleVariableOverride=false
from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower, Trim
from treebeard.mp_tree import MP_Node

from domain.organizations.models import Membership, Organization

RESERVED_CATALOG_SLUGS = frozenset(
    {
        "admin",
        "api",
        "auth",
        "health",
        "accounts",
        "_allauth",
        "organizaciones",
        "curriculo",
        "catalogo",
    }
)


class CatalogStatus(models.TextChoices):
    ACTIVE = "active", "Activo"
    ARCHIVED = "archived", "Archivado"


class PrerequisiteKind(models.TextChoices):
    REQUIRED = "required", "Obligatorio"
    RECOMMENDED = "recommended", "Recomendado"


class CognitiveLevel(models.TextChoices):
    REMEMBER = "remember", "Recordar"
    UNDERSTAND = "understand", "Comprender"
    APPLY = "apply", "Aplicar"
    ANALYZE = "analyze", "Analizar"
    EVALUATE = "evaluate", "Evaluar"
    CREATE = "create", "Crear"


class CatalogEntity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(
        max_length=10,
        choices=CatalogStatus.choices,
        default=CatalogStatus.ACTIVE,
        editable=False,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_updated",
    )
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_archived",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def _normalize_slug(self) -> None:
        self.slug = self.slug.strip().lower()
        if self.slug in RESERVED_CATALOG_SLUGS:
            raise ValidationError({"slug": "Este slug está reservado."})
        if not self._state.adding:
            original = (
                type(self)
                .objects.filter(pk=self.pk)
                .values_list("slug", flat=True)
                .first()
            )
            if original is not None and original != self.slug:
                raise ValidationError({"slug": "El slug es inmutable."})


class AcademicArea(CatalogEntity):
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="academic_areas"
    )
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=80)
    description = models.TextField(max_length=2000, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "organization", Lower("slug"), name="catalog_area_org_slug_ci_unique"
            ),
            models.CheckConstraint(
                condition=Q(name=Trim(F("name"))) & ~Q(name=""),
                name="catalog_area_name_trimmed",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "status"], name="catalog_area_org_status_ix"
            )
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        self.name = self.name.strip()
        self._normalize_slug()


class Discipline(CatalogEntity):
    area = models.ForeignKey(
        AcademicArea, on_delete=models.PROTECT, related_name="disciplines"
    )
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=80)
    description = models.TextField(max_length=2000, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "area", Lower("slug"), name="catalog_discipline_area_slug_ci_unique"
            )
        ]
        indexes = [
            models.Index(
                fields=["area", "status"], name="cat_discipline_area_status_ix"
            )
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        self.name = self.name.strip()
        self._normalize_slug()

    @property
    def organization(self) -> Organization:
        return self.area.organization


class Subject(CatalogEntity):
    discipline = models.ForeignKey(
        Discipline, on_delete=models.PROTECT, related_name="subjects"
    )
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=80)
    description = models.TextField(max_length=2000, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "discipline",
                Lower("slug"),
                name="catalog_subject_discipline_slug_ci_unique",
            )
        ]
        indexes = [
            models.Index(
                fields=["discipline", "status"], name="cat_subject_discipline_ix"
            )
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        self.name = self.name.strip()
        self._normalize_slug()

    @property
    def organization(self) -> Organization:
        return self.discipline.area.organization


class Topic(MP_Node):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name="topics"
    )
    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=80)
    description = models.TextField(max_length=2000, blank=True)
    status = models.CharField(
        max_length=10,
        choices=CatalogStatus.choices,
        default=CatalogStatus.ACTIVE,
        editable=False,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="created_topics",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="updated_topics",
    )
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="archived_topics",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "subject", Lower("slug"), name="catalog_topic_subject_slug_ci_unique"
            )
        ]
        indexes = [
            models.Index(
                fields=["subject", "status"], name="cat_topic_subject_status_ix"
            )
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        super().clean()
        self.title = self.title.strip()
        self.slug = self.slug.strip().lower()
        if self.slug in RESERVED_CATALOG_SLUGS:
            raise ValidationError({"slug": "Este slug está reservado."})

    @property
    def organization(self) -> Organization:
        return self.subject.organization


class Concept(CatalogEntity):
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="concepts"
    )
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=80)
    definition = models.TextField(max_length=3000)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "organization", Lower("slug"), name="catalog_concept_org_slug_ci_unique"
            )
        ]
        indexes = [
            models.Index(
                fields=["organization", "status"], name="catalog_concept_org_status_ix"
            )
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        self.name = self.name.strip()
        self.definition = self.definition.strip()
        self._normalize_slug()


class LearningObjective(CatalogEntity):
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name="learning_objectives"
    )
    code = models.CharField(max_length=32)
    statement = models.TextField(max_length=1200)
    description = models.TextField(max_length=2000, blank=True)
    cognitive_level = models.CharField(
        max_length=16, choices=CognitiveLevel.choices, blank=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "subject",
                Lower("code"),
                name="catalog_objective_subject_code_ci_unique",
            ),
            models.CheckConstraint(
                condition=Q(code__regex=r"^[A-Z0-9_.-]+$"),
                name="catalog_objective_code_format",
            ),
        ]
        indexes = [
            models.Index(
                fields=["subject", "status"], name="cat_objective_subject_state_ix"
            )
        ]

    def __str__(self) -> str:
        return self.code

    def clean(self) -> None:
        super().clean()
        self.code = self.code.strip().upper()
        self.statement = self.statement.strip()
        if not self._state.adding:
            original = (
                type(self)
                .objects.filter(pk=self.pk)
                .values_list("code", flat=True)
                .first()
            )
            if original is not None and original != self.code:
                raise ValidationError({"code": "El código es inmutable."})

    @property
    def organization(self) -> Organization:
        return self.subject.organization


class TopicConcept(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.ForeignKey(
        Topic, on_delete=models.PROTECT, related_name="concept_links"
    )
    concept = models.ForeignKey(
        Concept, on_delete=models.PROTECT, related_name="topic_links"
    )
    position = models.PositiveIntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "topic", "concept", name="catalog_topic_concept_unique"
            ),
            models.UniqueConstraint(
                "topic", "position", name="catalog_topic_concept_position_unique"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.topic}:{self.concept}"


class LearningObjectiveConcept(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learning_objective = models.ForeignKey(
        LearningObjective, on_delete=models.PROTECT, related_name="concept_links"
    )
    concept = models.ForeignKey(
        Concept, on_delete=models.PROTECT, related_name="objective_links"
    )
    position = models.PositiveIntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "learning_objective", "concept", name="catalog_objective_concept_unique"
            ),
            models.UniqueConstraint(
                "learning_objective",
                "position",
                name="catalog_objective_concept_position_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.learning_objective}:{self.concept}"


class SubjectPrerequisite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name="prerequisite_links"
    )
    prerequisite = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name="dependent_links"
    )
    kind = models.CharField(max_length=16, choices=PrerequisiteKind.choices)
    rationale = models.TextField(max_length=1000, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "subject", "prerequisite", name="catalog_subject_prerequisite_unique"
            ),
            models.CheckConstraint(
                condition=~Q(subject=F("prerequisite")),
                name="catalog_subject_prerequisite_not_self",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.subject} <- {self.prerequisite}"


class ConceptPrerequisite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    concept = models.ForeignKey(
        Concept, on_delete=models.PROTECT, related_name="prerequisite_links"
    )
    prerequisite = models.ForeignKey(
        Concept, on_delete=models.PROTECT, related_name="dependent_links"
    )
    kind = models.CharField(max_length=16, choices=PrerequisiteKind.choices)
    rationale = models.TextField(max_length=1000, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "concept", "prerequisite", name="catalog_concept_prerequisite_unique"
            ),
            models.CheckConstraint(
                condition=~Q(concept=F("prerequisite")),
                name="catalog_concept_prerequisite_not_self",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.concept} <- {self.prerequisite}"


class SubjectTeachingResponsibility(models.Model):
    """Fecha el alcance académico; nunca concede acceso a datos de estudiantes."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name="teaching_responsibilities"
    )
    membership = models.ForeignKey(
        Membership,
        on_delete=models.PROTECT,
        related_name="subject_teaching_responsibilities",
    )
    starts_on = models.DateField()
    ends_on = models.DateField(null=True, blank=True)
    rationale = models.TextField(max_length=1000)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="subject_teaching_responsibilities_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    ended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="subject_teaching_responsibilities_ended",
    )
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["subject", "membership"],
                condition=Q(ended_at__isnull=True),
                name="catalog_subject_teacher_active_unique",
            ),
            models.CheckConstraint(
                condition=Q(ends_on__isnull=True) | Q(starts_on__lte=F("ends_on")),
                name="catalog_subject_teacher_date_window",
            ),
            models.CheckConstraint(
                condition=(
                    Q(ended_at__isnull=True, ended_by__isnull=True)
                    | Q(ended_at__isnull=False, ended_by__isnull=False)
                ),
                name="catalog_subject_teacher_end_state",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.subject_id}:{self.membership_id}"

    def clean(self) -> None:
        super().clean()
        self.rationale = self.rationale.strip()
        if self.subject.organization.id != self.membership.organization_id:
            raise ValidationError(
                {"membership": "La persona pertenece a otra organización."}
            )
        if not self.rationale:
            raise ValidationError({"rationale": "La responsabilidad exige motivo."})

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        raise ValidationError("La responsabilidad académica no se elimina físicamente.")
