# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager

from django.db.models import F, Q
from django.db.models.functions import Lower, Trim
from django.utils import timezone

from domain.catalog.models import LearningObjective, Subject, Topic
from domain.organizations.models import Organization

from .choices import (
    OPEN_AUTHORING_STATUSES,
    AuthoringStatus,
    CourseStatus,
    StructureStatus,
    SubjectAlignmentType,
)

RESERVED_COURSE_SLUGS = frozenset(
    {
        "admin",
        "api",
        "auth",
        "health",
        "accounts",
        "_allauth",
        "organizaciones",
        "curriculo",
        "cursos",
        "nuevo",
        "revisiones",
        "estructura",
        "contenido",
    }
)


def _clean_plain_text(value: str, field: str, *, required: bool = False) -> str:
    cleaned = value.strip()
    if required and not cleaned:
        raise ValidationError({field: "Este campo no puede estar vacío."})
    if "<" in cleaned or ">" in cleaned:
        raise ValidationError({field: "No se permite HTML."})
    return cleaned


class Course(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="courses"
    )
    slug = models.SlugField(max_length=80)
    status = models.CharField(
        max_length=10,
        choices=CourseStatus.choices,
        default=CourseStatus.ACTIVE,
        editable=False,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="courses_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="courses_archived",
    )
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "organization",
                Lower("slug"),
                name="courses_course_org_slug_ci_unique",
            ),
            models.CheckConstraint(
                condition=Q(slug=Lower(F("slug"))),
                name="courses_course_slug_lowercase",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=CourseStatus.ACTIVE,
                        archived_at__isnull=True,
                        archived_by__isnull=True,
                    )
                    | Q(
                        status=CourseStatus.ARCHIVED,
                        archived_at__isnull=False,
                        archived_by__isnull=False,
                    )
                ),
                name="courses_course_archive_state",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "status"], name="course_org_status_ix"
            ),
            models.Index(fields=["created_at"], name="course_created_ix"),
        ]

    def __str__(self) -> str:
        return f"{self.organization.slug}:{self.slug}"

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        raise ValidationError("Los cursos se archivan; no se eliminan físicamente.")

    def clean(self) -> None:
        super().clean()
        self.slug = self.slug.strip().lower()
        if self.slug in RESERVED_COURSE_SLUGS:
            raise ValidationError({"slug": "Este slug está reservado."})
        if not self._state.adding:
            original = (
                type(self)
                .objects.filter(pk=self.pk)
                .values_list("slug", flat=True)
                .first()
            )
            if original is not None and original != self.slug:
                raise ValidationError({"slug": "El slug del curso es inmutable."})


class CourseRevision(models.Model):
    if TYPE_CHECKING:
        modules: RelatedManager[CourseModule]
        subject_alignments: RelatedManager[CourseRevisionSubject]
        learning_objectives: RelatedManager[CourseRevisionLearningObjective]
        transitions: RelatedManager[CourseRevisionTransition]
        successor_revisions: RelatedManager[CourseRevision]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(
        Course, on_delete=models.PROTECT, related_name="revisions"
    )
    number = models.PositiveIntegerField()
    based_on_revision = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="successor_revisions",
    )
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=240, blank=True)
    summary = models.TextField(max_length=1200)
    description = models.TextField(max_length=5000, blank=True)
    language_code = models.CharField(max_length=12, default="es")
    estimated_duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    authoring_status = models.CharField(
        max_length=24,
        choices=AuthoringStatus.choices,
        default=AuthoringStatus.DRAFT,
        editable=False,
    )
    lock_version = models.PositiveIntegerField(default=1, editable=False)
    status_changed_at = models.DateTimeField(default=timezone.now)
    status_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_revision_status_changes",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_revisions_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_revisions_updated",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course", "number"],
                name="courses_revision_course_number_unique",
            ),
            models.UniqueConstraint(
                fields=["course"],
                condition=Q(
                    authoring_status__in=sorted(
                        status.value for status in OPEN_AUTHORING_STATUSES
                    )
                ),
                name="courses_revision_one_open",
            ),
            models.CheckConstraint(
                condition=Q(number__gt=0),
                name="courses_revision_number_positive",
            ),
            models.CheckConstraint(
                condition=Q(lock_version__gt=0),
                name="courses_revision_lock_version_positive",
            ),
            models.CheckConstraint(
                condition=Q(estimated_duration_minutes__isnull=True)
                | Q(estimated_duration_minutes__gt=0),
                name="courses_revision_duration_positive",
            ),
            models.CheckConstraint(
                condition=Q(based_on_revision__isnull=True)
                | ~Q(based_on_revision=F("id")),
                name="courses_revision_not_self_based",
            ),
            models.CheckConstraint(
                condition=Q(title=Trim(F("title"))) & ~Q(title=""),
                name="courses_revision_title_trimmed",
            ),
        ]
        indexes = [
            models.Index(
                fields=["course", "authoring_status"], name="revision_course_state_ix"
            ),
            models.Index(fields=["updated_at"], name="revision_updated_ix"),
        ]
        ordering = ("-number",)

    def __str__(self) -> str:
        return f"{self.course}:r{self.number}"

    def clean(self) -> None:
        super().clean()
        self.title = _clean_plain_text(self.title, "title", required=True)
        self.subtitle = _clean_plain_text(self.subtitle, "subtitle")
        self.summary = _clean_plain_text(self.summary, "summary", required=True)
        self.description = _clean_plain_text(self.description, "description")
        self.language_code = self.language_code.strip().lower()
        if self.based_on_revision_id:
            base = self.based_on_revision
            if (
                base.course_id != self.course_id
                or base.number >= self.number
                or base.authoring_status != AuthoringStatus.APPROVED
            ):
                raise ValidationError(
                    {"based_on_revision": "La revisión base no es coherente."}
                )
        elif self.number != 1:
            raise ValidationError(
                {"based_on_revision": "Sólo la primera revisión puede no tener base."}
            )


class CourseRevisionTransition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.ForeignKey(
        CourseRevision, on_delete=models.PROTECT, related_name="transitions"
    )
    from_status = models.CharField(  # noqa: DJ001 -- el evento inicial no tiene origen
        max_length=24, choices=AuthoringStatus.choices, null=True, blank=True
    )
    to_status = models.CharField(max_length=24, choices=AuthoringStatus.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_revision_transitions",
    )
    note = models.TextField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["revision", "created_at"], name="transition_revision_created_ix"
            )
        ]
        ordering = ("created_at", "id")

    def __str__(self) -> str:
        return f"{self.revision}:{self.from_status or 'initial'}->{self.to_status}"

    def save(self, *args: object, **kwargs: object) -> None:
        if not self._state.adding:
            raise ValidationError("El historial de transiciones es inmutable.")
        self.note = _clean_plain_text(self.note, "note")
        if self.to_status == AuthoringStatus.CHANGES_REQUESTED and not self.note:
            raise ValidationError({"note": "La nota es obligatoria."})
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        raise ValidationError("El historial de transiciones no se elimina.")


class CourseModule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.ForeignKey(
        CourseRevision, on_delete=models.PROTECT, related_name="modules"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=3000, blank=True)
    status = models.CharField(
        max_length=10,
        choices=StructureStatus.choices,
        default=StructureStatus.ACTIVE,
        editable=False,
    )
    position = models.PositiveIntegerField(null=True, blank=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_modules_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_modules_updated",
    )
    updated_at = models.DateTimeField(auto_now=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="course_modules_archived",
    )
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["revision", "position"],
                deferrable=models.Deferrable.DEFERRED,
                name="courses_module_revision_position_unique",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=StructureStatus.ACTIVE,
                        position__isnull=False,
                        position__gt=0,
                        archived_at__isnull=True,
                        archived_by__isnull=True,
                    )
                    | Q(
                        status=StructureStatus.ARCHIVED,
                        position__isnull=True,
                        archived_at__isnull=False,
                        archived_by__isnull=False,
                    )
                ),
                name="courses_module_state_position",
            ),
        ]
        indexes = [
            models.Index(
                fields=["revision", "status", "position"],
                name="module_revision_state_pos_ix",
            )
        ]
        ordering = ("position", "created_at")

    def __str__(self) -> str:
        return f"{self.revision}:m{self.position or 'archived'}:{self.title}"

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        raise ValidationError("Los módulos se archivan; no se eliminan físicamente.")

    def clean(self) -> None:
        super().clean()
        self.title = _clean_plain_text(self.title, "title", required=True)
        self.description = _clean_plain_text(self.description, "description")


class CourseUnit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.ForeignKey(
        CourseModule, on_delete=models.PROTECT, related_name="units"
    )
    title = models.CharField(max_length=200)
    summary = models.TextField(max_length=1200, blank=True)
    estimated_duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=StructureStatus.choices,
        default=StructureStatus.ACTIVE,
        editable=False,
    )
    position = models.PositiveIntegerField(null=True, blank=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_units_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_units_updated",
    )
    updated_at = models.DateTimeField(auto_now=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="course_units_archived",
    )
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["module", "position"],
                deferrable=models.Deferrable.DEFERRED,
                name="courses_unit_module_position_unique",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=StructureStatus.ACTIVE,
                        position__isnull=False,
                        position__gt=0,
                        archived_at__isnull=True,
                        archived_by__isnull=True,
                    )
                    | Q(
                        status=StructureStatus.ARCHIVED,
                        position__isnull=True,
                        archived_at__isnull=False,
                        archived_by__isnull=False,
                    )
                ),
                name="courses_unit_state_position",
            ),
            models.CheckConstraint(
                condition=Q(estimated_duration_minutes__isnull=True)
                | Q(estimated_duration_minutes__gt=0),
                name="courses_unit_duration_positive",
            ),
        ]
        indexes = [
            models.Index(
                fields=["module", "status", "position"],
                name="unit_module_state_pos_ix",
            )
        ]
        ordering = ("position", "created_at")

    def __str__(self) -> str:
        return f"{self.module}:u{self.position or 'archived'}:{self.title}"

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        raise ValidationError("Las unidades se archivan; no se eliminan físicamente.")

    def clean(self) -> None:
        super().clean()
        self.title = _clean_plain_text(self.title, "title", required=True)
        self.summary = _clean_plain_text(self.summary, "summary")


class CourseRevisionSubject(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.ForeignKey(
        CourseRevision, on_delete=models.PROTECT, related_name="subject_alignments"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name="course_revision_alignments"
    )
    alignment_type = models.CharField(
        max_length=12, choices=SubjectAlignmentType.choices
    )
    position = models.PositiveIntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_subject_alignments_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["revision", "subject"],
                name="courses_revision_subject_unique",
            ),
            models.UniqueConstraint(
                fields=["revision", "position"],
                name="courses_revision_subject_position_unique",
            ),
            models.UniqueConstraint(
                fields=["revision"],
                condition=Q(alignment_type=SubjectAlignmentType.PRIMARY),
                name="courses_revision_one_primary_subject",
            ),
            models.CheckConstraint(
                condition=Q(position__gt=0),
                name="courses_revision_subject_position_positive",
            ),
        ]
        ordering = ("position",)

    def __str__(self) -> str:
        return f"{self.revision}:{self.subject}:{self.alignment_type}"


class CourseRevisionLearningObjective(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.ForeignKey(
        CourseRevision, on_delete=models.PROTECT, related_name="objective_alignments"
    )
    learning_objective = models.ForeignKey(
        LearningObjective,
        on_delete=models.PROTECT,
        related_name="course_revision_alignments",
    )
    position = models.PositiveIntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_objective_alignments_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["revision", "learning_objective"],
                name="courses_revision_objective_unique",
            ),
            models.UniqueConstraint(
                fields=["revision", "position"],
                name="courses_revision_objective_position_unique",
            ),
            models.CheckConstraint(
                condition=Q(position__gt=0),
                name="courses_revision_objective_position_positive",
            ),
        ]
        ordering = ("position",)

    def __str__(self) -> str:
        return f"{self.revision}:{self.learning_objective}"


class CourseUnitTopic(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey(
        CourseUnit, on_delete=models.PROTECT, related_name="topic_alignments"
    )
    topic = models.ForeignKey(
        Topic, on_delete=models.PROTECT, related_name="course_unit_alignments"
    )
    position = models.PositiveIntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_unit_topic_alignments_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["unit", "topic"], name="courses_unit_topic_unique"
            ),
            models.UniqueConstraint(
                fields=["unit", "position"], name="courses_unit_topic_position_unique"
            ),
            models.CheckConstraint(
                condition=Q(position__gt=0),
                name="courses_unit_topic_position_positive",
            ),
        ]
        ordering = ("position",)

    def __str__(self) -> str:
        return f"{self.unit}:{self.topic}"


class CourseUnitLearningObjective(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey(
        CourseUnit, on_delete=models.PROTECT, related_name="objective_alignments"
    )
    learning_objective = models.ForeignKey(
        LearningObjective,
        on_delete=models.PROTECT,
        related_name="course_unit_alignments",
    )
    position = models.PositiveIntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_unit_objective_alignments_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["unit", "learning_objective"],
                name="courses_unit_objective_unique",
            ),
            models.UniqueConstraint(
                fields=["unit", "position"],
                name="courses_unit_objective_position_unique",
            ),
            models.CheckConstraint(
                condition=Q(position__gt=0),
                name="courses_unit_objective_position_positive",
            ),
        ]
        ordering = ("position",)

    def __str__(self) -> str:
        return f"{self.unit}:{self.learning_objective}"
