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
from domain.organizations.models import Membership, Organization

from .choices import (
    OPEN_AUTHORING_STATUSES,
    ActivityCompletionMethod,
    ActivityType,
    AuthoringStatus,
    AvailabilityRuleType,
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


class CourseActivity(models.Model):
    """Ordered curricular identity shared by lesson, live and assessment types."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.ForeignKey(
        CourseModule, on_delete=models.PROTECT, related_name="activities"
    )
    activity_type = models.CharField(max_length=24, choices=ActivityType.choices)
    lesson_unit = models.OneToOneField(
        CourseUnit,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="activity",
    )
    title = models.CharField(max_length=200)
    summary = models.TextField(max_length=1200, blank=True)
    estimated_duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    required = models.BooleanField(default=True)
    completion_method = models.CharField(
        max_length=24, choices=ActivityCompletionMethod.choices
    )
    minimum_attendance_basis_points = models.PositiveIntegerField(null=True, blank=True)
    minimum_grade_basis_points = models.PositiveIntegerField(null=True, blank=True)
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
        related_name="course_activities_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_activities_updated",
    )
    updated_at = models.DateTimeField(auto_now=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="course_activities_archived",
    )
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["module", "position"],
                deferrable=models.Deferrable.DEFERRED,
                name="courses_activity_module_position_unique",
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
                name="courses_activity_state_position",
            ),
            models.CheckConstraint(
                condition=Q(estimated_duration_minutes__isnull=True)
                | Q(estimated_duration_minutes__gt=0),
                name="courses_activity_duration_positive",
            ),
            models.CheckConstraint(
                condition=Q(minimum_attendance_basis_points__isnull=True)
                | (
                    Q(minimum_attendance_basis_points__gte=1)
                    & Q(minimum_attendance_basis_points__lte=10_000)
                ),
                name="courses_activity_attendance_range",
            ),
            models.CheckConstraint(
                condition=Q(minimum_grade_basis_points__isnull=True)
                | Q(minimum_grade_basis_points__lte=10_000),
                name="courses_activity_grade_range",
            ),
        ]
        indexes = [
            models.Index(
                fields=["module", "status", "position"],
                name="activity_module_state_pos_ix",
            ),
            models.Index(
                fields=["activity_type", "status"], name="activity_type_state_ix"
            ),
        ]
        ordering = ("position", "created_at")

    def __str__(self) -> str:
        return f"{self.module}:a{self.position or 'archived'}:{self.title}"

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        raise ValidationError(
            "Las actividades se archivan; no se eliminan físicamente."
        )

    def clean(self) -> None:
        super().clean()
        self.title = _clean_plain_text(self.title, "title", required=True)
        self.summary = _clean_plain_text(self.summary, "summary")
        if self.activity_type == ActivityType.LESSON:
            if self.lesson_unit_id is None:
                raise ValidationError({"lesson_unit": "La lección exige una unidad."})
            if self.lesson_unit.module_id != self.module_id:
                raise ValidationError(
                    {"lesson_unit": "La unidad pertenece a otro módulo."}
                )
            allowed_methods = {
                ActivityCompletionMethod.VIEW,
                ActivityCompletionMethod.MANUAL,
            }
        else:
            if self.lesson_unit_id is not None:
                raise ValidationError(
                    {"lesson_unit": "Sólo una lección puede vincular una unidad."}
                )
            allowed_methods = (
                {ActivityCompletionMethod.ATTENDANCE}
                if self.activity_type == ActivityType.LIVE_CLASS
                else {
                    ActivityCompletionMethod.SUBMISSION,
                    ActivityCompletionMethod.GRADE,
                    ActivityCompletionMethod.PASS,
                }
            )
        if self.completion_method not in allowed_methods:
            raise ValidationError(
                {"completion_method": "La política no corresponde al tipo."}
            )
        if (self.completion_method == ActivityCompletionMethod.ATTENDANCE) != (
            self.minimum_attendance_basis_points is not None
        ):
            raise ValidationError(
                {
                    "minimum_attendance_basis_points": (
                        "La asistencia exige un umbral y sólo aplica a ese método."
                    )
                }
            )
        if (self.completion_method == ActivityCompletionMethod.PASS) != (
            self.minimum_grade_basis_points is not None
        ):
            raise ValidationError(
                {
                    "minimum_grade_basis_points": (
                        "La aprobación exige un umbral y sólo aplica a ese método."
                    )
                }
            )


class CourseActivityLearningObjective(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity = models.ForeignKey(
        CourseActivity, on_delete=models.PROTECT, related_name="objective_alignments"
    )
    learning_objective = models.ForeignKey(
        LearningObjective,
        on_delete=models.PROTECT,
        related_name="course_activity_alignments",
    )
    position = models.PositiveIntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_activity_objective_alignments_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["activity", "learning_objective"],
                name="courses_activity_objective_unique",
            ),
            models.UniqueConstraint(
                fields=["activity", "position"],
                name="courses_activity_objective_position_unique",
            ),
            models.CheckConstraint(
                condition=Q(position__gt=0),
                name="courses_activity_objective_position_positive",
            ),
        ]
        ordering = ("position",)

    def __str__(self) -> str:
        return f"{self.activity_id}:{self.learning_objective_id}"


class CourseActivityAvailabilityRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity = models.ForeignKey(
        CourseActivity, on_delete=models.PROTECT, related_name="availability_rules"
    )
    rule_type = models.CharField(max_length=32, choices=AvailabilityRuleType.choices)
    prerequisite_activity = models.ForeignKey(
        CourseActivity,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="dependent_availability_rules",
    )
    learning_objective = models.ForeignKey(
        LearningObjective,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="course_availability_rules",
    )
    threshold_basis_points = models.PositiveIntegerField(null=True, blank=True)
    available_at = models.DateTimeField(null=True, blank=True)
    position = models.PositiveIntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_activity_availability_rules_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["activity", "position"],
                name="courses_activity_rule_position_unique",
            ),
            models.CheckConstraint(
                condition=Q(position__gt=0),
                name="courses_activity_rule_position_positive",
            ),
            models.CheckConstraint(
                condition=Q(threshold_basis_points__isnull=True)
                | Q(threshold_basis_points__lte=10_000),
                name="courses_activity_rule_threshold_range",
            ),
        ]
        ordering = ("position", "id")

    def __str__(self) -> str:
        return f"{self.activity_id}:{self.position}:{self.rule_type}"

    def clean(self) -> None:
        super().clean()
        activity_rules = {
            AvailabilityRuleType.ACTIVITY_COMPLETED,
            AvailabilityRuleType.ACTIVITY_PASSED,
            AvailabilityRuleType.MINIMUM_GRADE,
        }
        if self.rule_type in activity_rules:
            if self.prerequisite_activity_id is None:
                raise ValidationError(
                    {"prerequisite_activity": "La regla exige otra actividad."}
                )
            if (
                self.prerequisite_activity_id == self.activity_id
                or self.prerequisite_activity.module.revision_id
                != self.activity.module.revision_id
            ):
                raise ValidationError(
                    {"prerequisite_activity": "La actividad requerida no es válida."}
                )
        elif self.prerequisite_activity_id is not None:
            raise ValidationError(
                {"prerequisite_activity": "Esta regla no usa otra actividad."}
            )
        if (self.rule_type == AvailabilityRuleType.OBJECTIVE_MASTERED) != (
            self.learning_objective_id is not None
        ):
            raise ValidationError(
                {"learning_objective": "La regla de dominio exige un objetivo."}
            )
        date_rule = self.rule_type in {
            AvailabilityRuleType.AVAILABLE_FROM,
            AvailabilityRuleType.AVAILABLE_UNTIL,
        }
        if date_rule != (self.available_at is not None):
            raise ValidationError({"available_at": "La regla de fecha exige fecha."})
        if (self.rule_type == AvailabilityRuleType.MINIMUM_GRADE) != (
            self.threshold_basis_points is not None
        ):
            raise ValidationError(
                {"threshold_basis_points": "La regla de nota exige umbral."}
            )


class CourseCompletionPolicy(models.Model):
    revision = models.OneToOneField(
        CourseRevision, on_delete=models.PROTECT, related_name="completion_policy"
    )
    require_required_activities = models.BooleanField(default=True)
    minimum_grade_basis_points = models.PositiveIntegerField(null=True, blank=True)
    minimum_attendance_basis_points = models.PositiveIntegerField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="course_completion_policies_confirmed",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    lock_version = models.PositiveIntegerField(default=1)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_completion_policies_updated",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(lock_version__gt=0),
                name="courses_completion_policy_lock_positive",
            ),
            models.CheckConstraint(
                condition=Q(minimum_grade_basis_points__isnull=True)
                | Q(minimum_grade_basis_points__lte=10_000),
                name="courses_completion_policy_grade_range",
            ),
            models.CheckConstraint(
                condition=Q(minimum_attendance_basis_points__isnull=True)
                | Q(minimum_attendance_basis_points__lte=10_000),
                name="courses_completion_policy_attendance_range",
            ),
            models.CheckConstraint(
                condition=(
                    Q(confirmed_at__isnull=True, confirmed_by__isnull=True)
                    | Q(confirmed_at__isnull=False, confirmed_by__isnull=False)
                ),
                name="courses_completion_policy_confirmation",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.revision_id}:v{self.lock_version}"


class CourseGradeCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.ForeignKey(
        CourseRevision, on_delete=models.PROTECT, related_name="grade_categories"
    )
    code = models.SlugField(max_length=64)
    title = models.CharField(max_length=120)
    position = models.PositiveIntegerField()
    weight_basis_points = models.PositiveIntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_grade_categories_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["revision", "code"], name="courses_grade_category_code_unique"
            ),
            models.UniqueConstraint(
                fields=["revision", "position"],
                name="courses_grade_category_position_unique",
            ),
            models.CheckConstraint(
                condition=Q(position__gt=0),
                name="courses_grade_category_position_positive",
            ),
            models.CheckConstraint(
                condition=Q(weight_basis_points__gte=1)
                & Q(weight_basis_points__lte=10_000),
                name="courses_grade_category_weight_range",
            ),
        ]
        ordering = ("position", "id")

    def __str__(self) -> str:
        return f"{self.revision_id}:{self.code}"


class CourseGradedActivity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        CourseGradeCategory, on_delete=models.PROTECT, related_name="graded_activities"
    )
    activity = models.OneToOneField(
        CourseActivity, on_delete=models.PROTECT, related_name="grade_item"
    )
    weight_basis_points = models.PositiveIntegerField()
    required = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_graded_activities_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(weight_basis_points__gte=1)
                & Q(weight_basis_points__lte=10_000),
                name="courses_graded_activity_weight_range",
            )
        ]

    def __str__(self) -> str:
        return f"{self.category_id}:{self.activity_id}"

    def clean(self) -> None:
        super().clean()
        if self.activity.module.revision_id != self.category.revision_id:
            raise ValidationError(
                {"activity": "La actividad pertenece a otra revisión."}
            )
        if self.activity.activity_type != ActivityType.ASSESSMENT:
            raise ValidationError(
                {"activity": "Sólo una evaluación puede ser calificable."}
            )


class CourseTeachingException(models.Model):
    """Excepción académica por curso; no sustituye el staff operativo del grupo."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(
        Course, on_delete=models.PROTECT, related_name="teaching_exceptions"
    )
    membership = models.ForeignKey(
        Membership,
        on_delete=models.PROTECT,
        related_name="course_teaching_exceptions",
    )
    starts_on = models.DateField()
    ends_on = models.DateField(null=True, blank=True)
    rationale = models.TextField(max_length=1000)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_teaching_exceptions_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    ended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="course_teaching_exceptions_ended",
    )
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course", "membership"],
                condition=Q(ended_at__isnull=True),
                name="courses_course_teacher_active_unique",
            ),
            models.CheckConstraint(
                condition=Q(ends_on__isnull=True) | Q(starts_on__lte=F("ends_on")),
                name="courses_course_teacher_date_window",
            ),
            models.CheckConstraint(
                condition=(
                    Q(ended_at__isnull=True, ended_by__isnull=True)
                    | Q(ended_at__isnull=False, ended_by__isnull=False)
                ),
                name="courses_course_teacher_end_state",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.course_id}:{self.membership_id}"

    def clean(self) -> None:
        super().clean()
        self.rationale = self.rationale.strip()
        if self.course.organization_id != self.membership.organization_id:
            raise ValidationError(
                {"membership": "La persona pertenece a otra organización."}
            )
        if not self.rationale:
            raise ValidationError({"rationale": "La excepción exige motivo."})

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        raise ValidationError("La excepción académica no se elimina físicamente.")
