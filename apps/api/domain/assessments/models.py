# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportIncompatibleVariableOverride=false
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower, Trim

from domain.assets.models import AssetVersion
from domain.catalog.models import LearningObjective
from domain.courses.choices import ActivityType
from domain.courses.models import CourseActivity
from domain.learning.models import (
    AcademicPeriod,
    CourseGroupActivity,
    EnrollmentReleaseAssignment,
    LearningCohort,
)
from domain.organizations.models import Organization
from domain.publishing.models import CourseRelease

from .choices import (
    AssignmentStatus,
    AttemptAggregation,
    AttemptEventType,
    AttemptStatus,
    AuthoringStatus,
    DeliveryStatus,
    FeedbackMode,
    GradebookColumnStatus,
    GradebookEntryStatus,
    GradebookStatus,
    GradebookSummaryStatus,
    GradeSource,
    GradingRevisionSource,
    GradingStatus,
    JobStatus,
    LifecycleStatus,
    PoolSelectionStrategy,
    QuestionType,
    RegradeAttemptStatus,
    ResponseStatus,
)


class NoPhysicalDeleteModel(models.Model):
    class Meta:
        abstract = True

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Este registro no se elimina físicamente.")


class ImmutableModel(NoPhysicalDeleteModel):
    class Meta:
        abstract = True

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise ValidationError("Este registro es inmutable.")
        super().save(*args, **kwargs)


class QuestionBank(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="question_banks"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80)
    description = models.TextField(max_length=5_000, blank=True)
    status = models.CharField(
        max_length=16,
        choices=LifecycleStatus.choices,
        default=LifecycleStatus.ACTIVE,
    )
    lock_version = models.PositiveIntegerField(default=1, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="question_banks_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="question_banks_updated",
    )
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="question_banks_archived",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("slug"),
                "organization",
                name="assess_bank_org_slug_ci_unique",
            ),
            models.CheckConstraint(
                condition=Q(slug=Lower(F("slug"))),
                name="assess_bank_slug_lowercase",
            ),
            models.CheckConstraint(
                condition=Q(name=Trim(F("name"))) & ~Q(name=""),
                name="assess_bank_name_trimmed",
            ),
            models.CheckConstraint(
                condition=Q(lock_version__gt=0),
                name="assess_bank_lock_positive",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=LifecycleStatus.ACTIVE,
                        archived_by__isnull=True,
                        archived_at__isnull=True,
                    )
                    | Q(
                        status=LifecycleStatus.ARCHIVED,
                        archived_by__isnull=False,
                        archived_at__isnull=False,
                    )
                ),
                name="assess_bank_archive_state",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "status"], name="assess_bank_org_state_ix"
            )
        ]

    def __str__(self) -> str:
        return f"{self.organization.slug}:{self.slug}"

    def clean(self) -> None:
        super().clean()
        self.name = self.name.strip()
        self.slug = self.slug.strip().lower()
        self.description = self.description.strip()


class Question(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank = models.ForeignKey(
        QuestionBank, on_delete=models.PROTECT, related_name="questions"
    )
    code = models.CharField(max_length=64)
    status = models.CharField(
        max_length=16,
        choices=LifecycleStatus.choices,
        default=LifecycleStatus.ACTIVE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="questions_created",
    )
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="questions_archived",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "bank", Lower("code"), name="assess_question_bank_code_ci_unique"
            ),
            models.CheckConstraint(
                condition=Q(code=Trim(F("code"))) & ~Q(code=""),
                name="assess_question_code_trimmed",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=LifecycleStatus.ACTIVE,
                        archived_by__isnull=True,
                        archived_at__isnull=True,
                    )
                    | Q(
                        status=LifecycleStatus.ARCHIVED,
                        archived_by__isnull=False,
                        archived_at__isnull=False,
                    )
                ),
                name="assess_question_archive_state",
            ),
        ]
        indexes = [
            models.Index(fields=["bank", "status"], name="assess_q_bank_state_ix")
        ]

    def __str__(self) -> str:
        return f"{self.bank}:{self.code}"

    @property
    def organization(self) -> Organization:
        return self.bank.organization

    def clean(self) -> None:
        super().clean()
        self.code = self.code.strip()
        if self.bank_id and self.bank.status != LifecycleStatus.ACTIVE:
            raise ValidationError({"bank": "El banco está archivado."})
        if not self._state.adding:
            original = (
                type(self)
                .objects.filter(pk=self.pk)
                .values_list("code", flat=True)
                .first()
            )
            if original is not None and original != self.code:
                raise ValidationError({"code": "El código estable es inmutable."})


class QuestionRevision(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(
        Question, on_delete=models.PROTECT, related_name="revisions"
    )
    number = models.PositiveIntegerField()
    based_on_version = models.ForeignKey(
        "QuestionVersion",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="derived_revisions",
    )
    type = models.CharField(max_length=24, choices=QuestionType.choices)
    definition = models.JSONField()
    status = models.CharField(
        max_length=24,
        choices=AuthoringStatus.choices,
        default=AuthoringStatus.DRAFT,
    )
    lock_version = models.PositiveIntegerField(default=1, editable=False)
    status_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="question_revisions_status_changed",
    )
    status_changed_at = models.DateTimeField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="question_revisions_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="question_revisions_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["question", "number"],
                name="assess_qrev_question_number_unique",
            ),
            models.UniqueConstraint(
                fields=["question"],
                condition=~Q(status=AuthoringStatus.APPROVED),
                name="assess_qrev_one_open",
            ),
            models.CheckConstraint(
                condition=Q(number__gt=0), name="assess_qrev_number_positive"
            ),
            models.CheckConstraint(
                condition=Q(lock_version__gt=0),
                name="assess_qrev_lock_positive",
            ),
        ]
        indexes = [
            models.Index(fields=["question", "status"], name="assess_qrev_q_state_ix")
        ]
        ordering = ("number",)

    def __str__(self) -> str:
        return f"{self.question}:revision-{self.number}"

    @property
    def organization(self) -> Organization:
        return self.question.organization

    def clean(self) -> None:
        super().clean()
        if self.based_on_version_id and (
            self.based_on_version.question_id != self.question_id
        ):
            raise ValidationError(
                {"based_on_version": "La versión pertenece a otra pregunta."}
            )
        if isinstance(self.definition, dict):
            definition_type = self.definition.get("type")
            if definition_type != self.type:
                raise ValidationError(
                    {"definition": "El tipo de la definición no coincide."}
                )


class QuestionRevisionTransition(ImmutableModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.ForeignKey(
        QuestionRevision, on_delete=models.PROTECT, related_name="transitions"
    )
    from_status = models.CharField(max_length=24, choices=AuthoringStatus.choices)
    to_status = models.CharField(max_length=24, choices=AuthoringStatus.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="question_revision_transitions",
    )
    note = models.TextField(max_length=2_000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(from_status=F("to_status")),
                name="assess_qtransition_changes_state",
            )
        ]
        ordering = ("created_at", "id")

    def __str__(self) -> str:
        return f"{self.revision}:{self.from_status}->{self.to_status}"


class QuestionVersion(ImmutableModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(
        Question, on_delete=models.PROTECT, related_name="versions"
    )
    number = models.PositiveIntegerField()
    source_revision = models.OneToOneField(
        QuestionRevision, on_delete=models.PROTECT, related_name="version"
    )
    schema_version = models.PositiveIntegerField(default=1, editable=False)
    type = models.CharField(max_length=24, choices=QuestionType.choices, editable=False)
    public = models.JSONField(editable=False)
    grading = models.JSONField(editable=False)
    feedback = models.JSONField(editable=False)
    definition_digest = models.CharField(max_length=64, editable=False)
    public_digest = models.CharField(max_length=64, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="question_versions_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["question", "number"],
                name="assess_qversion_question_number_unique",
            ),
            models.CheckConstraint(
                condition=Q(number__gt=0), name="assess_qversion_number_positive"
            ),
            models.CheckConstraint(
                condition=Q(schema_version__gt=0),
                name="assess_qversion_schema_positive",
            ),
            models.CheckConstraint(
                condition=Q(definition_digest__regex=r"^[0-9a-f]{64}$"),
                name="assess_qversion_definition_sha256",
            ),
            models.CheckConstraint(
                condition=Q(public_digest__regex=r"^[0-9a-f]{64}$"),
                name="assess_qversion_public_sha256",
            ),
        ]
        indexes = [
            models.Index(
                fields=["question", "created_at"], name="assess_qver_q_created_ix"
            ),
            models.Index(
                fields=["definition_digest"], name="assess_qver_def_digest_ix"
            ),
        ]
        ordering = ("number",)

    def __str__(self) -> str:
        return f"{self.question}:version-{self.number}"

    def clean(self) -> None:
        super().clean()
        if self.source_revision_id and (
            self.source_revision.question_id != self.question_id
            or self.source_revision.type != self.type
        ):
            raise ValidationError(
                {"source_revision": "La revisión no corresponde a esta versión."}
            )


class AssessmentAssetReference(ImmutableModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question_version = models.ForeignKey(
        QuestionVersion,
        on_delete=models.PROTECT,
        related_name="asset_references",
    )
    asset_version = models.ForeignKey(
        AssetVersion,
        on_delete=models.PROTECT,
        related_name="assessment_references",
    )
    location = models.CharField(max_length=255, editable=False)
    reference_role = models.CharField(max_length=24, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("question_version", "location"),
                name="assess_assetref_version_location_unique",
            ),
            models.CheckConstraint(
                condition=Q(location=Trim(F("location"))) & ~Q(location=""),
                name="assess_assetref_location_trimmed",
            ),
            models.CheckConstraint(
                condition=Q(reference_role__in=("primary", "captions", "choice")),
                name="assess_assetref_role_valid",
            ),
        ]
        indexes = [
            models.Index(
                fields=("asset_version", "created_at"),
                name="assess_assetref_asset_time_ix",
            )
        ]

    def __str__(self) -> str:
        return f"{self.question_version_id}:{self.location}"


class QuestionBankVersion(ImmutableModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank = models.ForeignKey(
        QuestionBank, on_delete=models.PROTECT, related_name="versions"
    )
    number = models.PositiveIntegerField()
    previous_version = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="next_versions",
        editable=False,
    )
    snapshot = models.JSONField(editable=False)
    snapshot_digest = models.CharField(max_length=64, editable=False)
    question_count = models.PositiveIntegerField(editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="question_bank_versions_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["bank", "number"],
                name="assess_bankversion_bank_number_unique",
            ),
            models.CheckConstraint(
                condition=Q(number__gt=0),
                name="assess_bankversion_number_positive",
            ),
            models.CheckConstraint(
                condition=Q(snapshot_digest__regex=r"^[0-9a-f]{64}$"),
                name="assess_bankversion_digest_sha256",
            ),
            models.CheckConstraint(
                condition=Q(previous_version__isnull=True)
                | ~Q(previous_version=F("id")),
                name="assess_bankversion_not_self",
            ),
        ]
        ordering = ("number",)

    def __str__(self) -> str:
        return f"{self.bank}:version-{self.number}"


class Assessment(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="assessments"
    )
    slug = models.SlugField(max_length=80)
    status = models.CharField(
        max_length=16,
        choices=LifecycleStatus.choices,
        default=LifecycleStatus.ACTIVE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessments_created",
    )
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assessments_archived",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("slug"),
                "organization",
                name="assess_assessment_org_slug_ci_unique",
            ),
            models.CheckConstraint(
                condition=Q(slug=Lower(F("slug"))),
                name="assess_assessment_slug_lowercase",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=LifecycleStatus.ACTIVE,
                        archived_by__isnull=True,
                        archived_at__isnull=True,
                    )
                    | Q(
                        status=LifecycleStatus.ARCHIVED,
                        archived_by__isnull=False,
                        archived_at__isnull=False,
                    )
                ),
                name="assess_assessment_archive_state",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "status"], name="assess_a_org_state_ix"
            )
        ]

    def __str__(self) -> str:
        return f"{self.organization.slug}:{self.slug}"

    def clean(self) -> None:
        super().clean()
        self.slug = self.slug.strip().lower()


class AssessmentRevision(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(
        Assessment, on_delete=models.PROTECT, related_name="revisions"
    )
    number = models.PositiveIntegerField()
    based_on_version = models.ForeignKey(
        "AssessmentVersion",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="derived_revisions",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=5_000, blank=True)
    instructions = models.TextField(max_length=10_000, blank=True)
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True)
    attempt_limit = models.PositiveIntegerField(null=True, blank=True)
    pass_basis_points = models.PositiveIntegerField(default=6_000)
    shuffle_sections = models.BooleanField(default=False)
    shuffle_items = models.BooleanField(default=False)
    feedback_mode = models.CharField(
        max_length=24,
        choices=FeedbackMode.choices,
        default=FeedbackMode.FULL_AFTER_GRADING,
    )
    status = models.CharField(
        max_length=24,
        choices=AuthoringStatus.choices,
        default=AuthoringStatus.DRAFT,
    )
    lock_version = models.PositiveIntegerField(default=1, editable=False)
    status_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessment_revisions_status_changed",
    )
    status_changed_at = models.DateTimeField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessment_revisions_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessment_revisions_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "number"],
                name="assess_arev_assessment_number_unique",
            ),
            models.UniqueConstraint(
                fields=["assessment"],
                condition=~Q(status=AuthoringStatus.APPROVED),
                name="assess_arev_one_open",
            ),
            models.CheckConstraint(
                condition=Q(number__gt=0), name="assess_arev_number_positive"
            ),
            models.CheckConstraint(
                condition=Q(lock_version__gt=0),
                name="assess_arev_lock_positive",
            ),
            models.CheckConstraint(
                condition=Q(pass_basis_points__gte=0)
                & Q(pass_basis_points__lte=10_000),
                name="assess_arev_pass_bps_range",
            ),
            models.CheckConstraint(
                condition=Q(time_limit_minutes__isnull=True)
                | (Q(time_limit_minutes__gt=0) & Q(time_limit_minutes__lte=10_080)),
                name="assess_arev_time_range",
            ),
            models.CheckConstraint(
                condition=Q(attempt_limit__isnull=True)
                | (Q(attempt_limit__gt=0) & Q(attempt_limit__lte=20)),
                name="assess_arev_attempt_range",
            ),
        ]
        indexes = [
            models.Index(fields=["assessment", "status"], name="assess_arev_a_state_ix")
        ]
        ordering = ("number",)

    def __str__(self) -> str:
        return f"{self.assessment}:revision-{self.number}"

    @property
    def organization(self) -> Organization:
        return self.assessment.organization

    def clean(self) -> None:
        super().clean()
        self.title = self.title.strip()
        self.description = self.description.strip()
        self.instructions = self.instructions.strip()
        if self.based_on_version_id and (
            self.based_on_version.assessment_id != self.assessment_id
        ):
            raise ValidationError(
                {"based_on_version": "La versión pertenece a otra evaluación."}
            )


class AssessmentRevisionTransition(ImmutableModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.ForeignKey(
        AssessmentRevision, on_delete=models.PROTECT, related_name="transitions"
    )
    from_status = models.CharField(max_length=24, choices=AuthoringStatus.choices)
    to_status = models.CharField(max_length=24, choices=AuthoringStatus.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessment_revision_transitions",
    )
    note = models.TextField(max_length=2_000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(from_status=F("to_status")),
                name="assess_atransition_changes_state",
            )
        ]
        ordering = ("created_at", "id")

    def __str__(self) -> str:
        return f"{self.revision}:{self.from_status}->{self.to_status}"


class AssessmentSection(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.ForeignKey(
        AssessmentRevision, on_delete=models.PROTECT, related_name="sections"
    )
    title = models.CharField(max_length=200)
    instructions = models.TextField(max_length=5_000, blank=True)
    position = models.PositiveIntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessment_sections_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessment_sections_updated",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["revision", "position"],
                name="assess_section_revision_position_unique",
                deferrable=models.Deferrable.DEFERRED,
            ),
            models.CheckConstraint(
                condition=Q(position__gt=0),
                name="assess_section_position_positive",
            ),
        ]
        ordering = ("position", "id")

    def __str__(self) -> str:
        return f"{self.revision}:section-{self.position}"

    def clean(self) -> None:
        super().clean()
        self.title = self.title.strip()
        self.instructions = self.instructions.strip()


class AssessmentItem(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    section = models.ForeignKey(
        AssessmentSection, on_delete=models.PROTECT, related_name="items"
    )
    question_version = models.ForeignKey(
        QuestionVersion, on_delete=models.PROTECT, related_name="assessment_items"
    )
    position = models.PositiveIntegerField()
    points = models.DecimalField(max_digits=12, decimal_places=3)
    required = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessment_items_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessment_items_updated",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["section", "position"],
                name="assess_item_section_position_unique",
                deferrable=models.Deferrable.DEFERRED,
            ),
            models.UniqueConstraint(
                fields=["section", "question_version"],
                name="assess_item_section_qversion_unique",
            ),
            models.CheckConstraint(
                condition=Q(position__gt=0),
                name="assess_item_position_positive",
            ),
            models.CheckConstraint(
                condition=Q(points__gt=Decimal("0")),
                name="assess_item_points_positive",
            ),
        ]
        ordering = ("position", "id")

    def __str__(self) -> str:
        return f"{self.section}:item-{self.position}"

    @property
    def revision(self) -> AssessmentRevision:
        return self.section.revision

    def clean(self) -> None:
        super().clean()
        if (
            self.section_id
            and self.question_version_id
            and self.question_version.question.organization.id
            != self.section.revision.organization.id
        ):
            raise ValidationError(
                {"question_version": "La pregunta pertenece a otra organización."}
            )


class AssessmentRevisionObjective(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.ForeignKey(
        AssessmentRevision, on_delete=models.PROTECT, related_name="objective_links"
    )
    objective = models.ForeignKey(
        LearningObjective,
        on_delete=models.PROTECT,
        related_name="assessment_revision_links",
    )
    position = models.PositiveIntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessment_revision_objectives_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["revision", "objective"],
                name="assess_arev_objective_unique",
            ),
            models.UniqueConstraint(
                fields=["revision", "position"],
                name="assess_arev_objective_position_unique",
                deferrable=models.Deferrable.DEFERRED,
            ),
            models.CheckConstraint(
                condition=Q(position__gt=0),
                name="assess_arev_objective_position_positive",
            ),
        ]
        ordering = ("position",)

    def __str__(self) -> str:
        return f"{self.revision}:{self.objective}"

    def clean(self) -> None:
        super().clean()
        if (
            self.revision_id
            and self.objective_id
            and self.objective.organization.id != self.revision.organization.id
        ):
            raise ValidationError(
                {"objective": "El objetivo pertenece a otra organización."}
            )


class AssessmentItemObjective(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(
        AssessmentItem, on_delete=models.PROTECT, related_name="objective_links"
    )
    objective = models.ForeignKey(
        LearningObjective,
        on_delete=models.PROTECT,
        related_name="assessment_item_links",
    )
    position = models.PositiveIntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessment_item_objectives_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["item", "objective"],
                name="assess_item_objective_unique",
            ),
            models.UniqueConstraint(
                fields=["item", "position"],
                name="assess_item_objective_position_unique",
                deferrable=models.Deferrable.DEFERRED,
            ),
            models.CheckConstraint(
                condition=Q(position__gt=0),
                name="assess_item_objective_position_positive",
            ),
        ]
        ordering = ("position",)

    def __str__(self) -> str:
        return f"{self.item}:{self.objective}"

    def clean(self) -> None:
        super().clean()
        if not self.item_id or not self.objective_id:
            return
        revision = self.item.revision
        if self.objective.organization.id != revision.organization.id:
            raise ValidationError(
                {"objective": "El objetivo pertenece a otra organización."}
            )
        if not revision.objective_links.filter(objective=self.objective).exists():
            raise ValidationError(
                {"objective": "El objetivo no pertenece a la evaluación."}
            )


class AssessmentVersion(ImmutableModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(
        Assessment, on_delete=models.PROTECT, related_name="versions"
    )
    number = models.PositiveIntegerField()
    source_revision = models.OneToOneField(
        AssessmentRevision, on_delete=models.PROTECT, related_name="version"
    )
    previous_version = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="next_versions",
        editable=False,
    )
    schema_version = models.PositiveIntegerField(default=1, editable=False)
    public_snapshot = models.JSONField(editable=False)
    grading_snapshot = models.JSONField(editable=False)
    snapshot_digest = models.CharField(max_length=64, editable=False)
    title = models.CharField(max_length=200, editable=False)
    description = models.TextField(max_length=5_000, blank=True, editable=False)
    section_count = models.PositiveIntegerField(editable=False)
    item_count = models.PositiveIntegerField(editable=False)
    maximum_score = models.DecimalField(max_digits=12, decimal_places=3, editable=False)
    time_limit_minutes = models.PositiveIntegerField(
        null=True, blank=True, editable=False
    )
    attempt_limit = models.PositiveIntegerField(null=True, blank=True, editable=False)
    pass_basis_points = models.PositiveIntegerField(editable=False)
    feedback_mode = models.CharField(
        max_length=24, choices=FeedbackMode.choices, editable=False
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessment_versions_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "number"],
                name="assess_aversion_assessment_number_unique",
            ),
            models.CheckConstraint(
                condition=Q(number__gt=0), name="assess_aversion_number_positive"
            ),
            models.CheckConstraint(
                condition=Q(schema_version__gt=0),
                name="assess_aversion_schema_positive",
            ),
            models.CheckConstraint(
                condition=Q(snapshot_digest__regex=r"^[0-9a-f]{64}$"),
                name="assess_aversion_digest_sha256",
            ),
            models.CheckConstraint(
                condition=Q(item_count__gt=0),
                name="assess_aversion_items_positive",
            ),
            models.CheckConstraint(
                condition=Q(maximum_score__gt=Decimal("0")),
                name="assess_aversion_score_positive",
            ),
            models.CheckConstraint(
                condition=Q(pass_basis_points__gte=0)
                & Q(pass_basis_points__lte=10_000),
                name="assess_aversion_pass_bps_range",
            ),
            models.CheckConstraint(
                condition=Q(previous_version__isnull=True)
                | ~Q(previous_version=F("id")),
                name="assess_aversion_not_self",
            ),
        ]
        indexes = [
            models.Index(
                fields=["assessment", "created_at"], name="assess_aver_a_created_ix"
            ),
            models.Index(fields=["snapshot_digest"], name="assess_aver_digest_ix"),
        ]
        ordering = ("number",)

    def __str__(self) -> str:
        return f"{self.assessment}:version-{self.number}"


class AssessmentActivityBinding(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity = models.OneToOneField(
        CourseActivity,
        on_delete=models.PROTECT,
        related_name="assessment_binding",
    )
    assessment_version = models.ForeignKey(
        AssessmentVersion,
        on_delete=models.PROTECT,
        related_name="course_activity_bindings",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessment_activity_bindings_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.activity_id}:{self.assessment_version_id}"

    def clean(self) -> None:
        super().clean()
        if self.activity.activity_type != ActivityType.ASSESSMENT:
            raise ValidationError({"activity": "La actividad no es una evaluación."})
        if (
            self.activity.module.revision.course.organization_id
            != self.assessment_version.assessment.organization_id
        ):
            raise ValidationError(
                {"assessment_version": "La evaluación pertenece a otra organización."}
            )


class AssessmentDelivery(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="assessment_deliveries"
    )
    assessment_version = models.ForeignKey(
        AssessmentVersion, on_delete=models.PROTECT, related_name="deliveries"
    )
    course_release = models.ForeignKey(
        CourseRelease,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assessment_deliveries",
    )
    course_group_activity = models.ForeignKey(
        CourseGroupActivity,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assessment_deliveries",
    )
    migration_review_required = models.BooleanField(default=False)
    unit_id = models.UUIDField(null=True, blank=True)
    name = models.CharField(max_length=200)
    status = models.CharField(
        max_length=16, choices=DeliveryStatus.choices, default=DeliveryStatus.DRAFT
    )
    opens_at = models.DateTimeField(null=True, blank=True)
    closes_at = models.DateTimeField(null=True, blank=True)
    lock_version = models.PositiveIntegerField(default=1, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessment_deliveries_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessment_deliveries_updated",
    )
    withdrawn_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assessment_deliveries_withdrawn",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    withdrawal_note = models.TextField(max_length=2_000, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course_group_activity"],
                condition=Q(course_group_activity__isnull=False)
                & ~Q(status=DeliveryStatus.WITHDRAWN),
                name="assess_delivery_one_current_activity",
            ),
            models.CheckConstraint(
                condition=Q(lock_version__gt=0),
                name="assess_delivery_lock_positive",
            ),
            models.CheckConstraint(
                condition=Q(opens_at__isnull=True)
                | Q(closes_at__isnull=True)
                | Q(opens_at__lt=F("closes_at")),
                name="assess_delivery_window",
            ),
            models.CheckConstraint(
                condition=Q(unit_id__isnull=True) | Q(course_release__isnull=False),
                name="assess_delivery_unit_requires_release",
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(status=DeliveryStatus.WITHDRAWN)
                    & Q(
                        withdrawn_by__isnull=True,
                        withdrawn_at__isnull=True,
                        withdrawal_note="",
                    )
                    | (
                        Q(
                            status=DeliveryStatus.WITHDRAWN,
                            withdrawn_by__isnull=False,
                            withdrawn_at__isnull=False,
                        )
                        & ~Q(withdrawal_note="")
                    )
                ),
                name="assess_delivery_withdraw_state",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "status"], name="assess_del_org_state_ix"
            ),
            models.Index(
                fields=["course_release", "status"], name="assess_del_rel_state_ix"
            ),
            models.Index(
                fields=["course_group_activity", "status"],
                name="assess_del_activity_state_ix",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.organization.slug}:{self.name}"

    def clean(self) -> None:
        super().clean()
        self.name = self.name.strip()
        self.withdrawal_note = self.withdrawal_note.strip()
        if (
            self.assessment_version_id
            and self.assessment_version.assessment.organization_id
            != self.organization_id
        ):
            raise ValidationError(
                {"assessment_version": "La versión pertenece a otra organización."}
            )
        if (
            self.course_release_id
            and self.course_release.course.organization_id != self.organization_id
        ):
            raise ValidationError(
                {"course_release": "El release pertenece a otra organización."}
            )
        if self.course_group_activity_id:
            activity = self.course_group_activity
            if (
                activity.course_release_id != self.course_release_id
                or activity.course_group.organization_id != self.organization_id
                or activity.activity_type != "assessment"
            ):
                raise ValidationError(
                    {
                        "course_group_activity": (
                            "La actividad no corresponde a la evaluación y release."
                        )
                    }
                )
            binding_version_id = activity.binding_snapshot.get("assessment_version_id")
            if binding_version_id != str(self.assessment_version_id):
                raise ValidationError(
                    {
                        "assessment_version": (
                            "La versión no coincide con el binding del release."
                        )
                    }
                )
        elif (
            self._state.adding
            and (self.course_release_id or self.unit_id)
            and not self.migration_review_required
        ):
            raise ValidationError(
                {
                    "course_group_activity": (
                        "Una entrega curricular nueva exige actividad de grupo."
                    )
                }
            )


class DeliveryAssignment(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    delivery = models.ForeignKey(
        AssessmentDelivery, on_delete=models.PROTECT, related_name="assignments"
    )
    release_assignment = models.ForeignKey(
        EnrollmentReleaseAssignment,
        on_delete=models.PROTECT,
        related_name="assessment_assignments",
    )
    cohort = models.ForeignKey(
        LearningCohort,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assessment_assignments",
    )
    status = models.CharField(
        max_length=16,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.ACTIVE,
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessment_assignments_created",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assessment_assignments_revoked",
    )
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["delivery", "release_assignment"],
                condition=Q(status=AssignmentStatus.ACTIVE),
                name="assess_assignment_one_active",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=AssignmentStatus.ACTIVE,
                        revoked_by__isnull=True,
                        revoked_at__isnull=True,
                    )
                    | Q(
                        status=AssignmentStatus.REVOKED,
                        revoked_by__isnull=False,
                        revoked_at__isnull=False,
                    )
                ),
                name="assess_assignment_revoke_state",
            ),
        ]
        indexes = [
            models.Index(
                fields=["release_assignment", "status"],
                name="assess_assign_release_state_ix",
            )
        ]

    def __str__(self) -> str:
        return f"{self.delivery}:{self.release_assignment}"

    def clean(self) -> None:
        super().clean()
        if not self.delivery_id or not self.release_assignment_id:
            return
        enrollment = self.release_assignment.enrollment
        if enrollment.organization_id != self.delivery.organization_id:
            raise ValidationError(
                {"release_assignment": "La asignación pertenece a otra organización."}
            )
        if (
            self.delivery.course_release_id
            and self.release_assignment.release_id != self.delivery.course_release_id
        ):
            raise ValidationError(
                {"release_assignment": "La asignación usa otro release."}
            )
        effective_cohort = enrollment.effective_cohort
        if self.cohort_id and (
            effective_cohort is None or effective_cohort.id != self.cohort_id
        ):
            raise ValidationError(
                {"cohort": "La matrícula no pertenece al grupo de curso efectivo."}
            )


class Attempt(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    delivery_assignment = models.ForeignKey(
        DeliveryAssignment, on_delete=models.PROTECT, related_name="attempts"
    )
    assessment_version = models.ForeignKey(
        AssessmentVersion, on_delete=models.PROTECT, related_name="attempts"
    )
    attempt_number = models.PositiveIntegerField()
    status = models.CharField(
        max_length=24, choices=AttemptStatus.choices, default=AttemptStatus.IN_PROGRESS
    )
    seed = models.PositiveBigIntegerField(editable=False)
    started_at = models.DateTimeField()
    expires_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    lock_version = models.PositiveIntegerField(default=1, editable=False)
    auto_score = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal("0.000")
    )
    manual_score = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal("0.000")
    )
    total_score = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal("0.000")
    )
    maximum_score = models.DecimalField(max_digits=12, decimal_places=3)
    basis_points = models.PositiveIntegerField(null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)
    current_grade = models.OneToOneField(
        "AttemptGradeVersion",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="current_for_attempt",
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["delivery_assignment", "attempt_number"],
                name="assess_attempt_assignment_number_unique",
            ),
            models.UniqueConstraint(
                fields=["delivery_assignment"],
                condition=Q(status=AttemptStatus.IN_PROGRESS),
                name="assess_attempt_one_in_progress",
            ),
            models.CheckConstraint(
                condition=Q(attempt_number__gt=0),
                name="assess_attempt_number_positive",
            ),
            models.CheckConstraint(
                condition=Q(lock_version__gt=0),
                name="assess_attempt_lock_positive",
            ),
            models.CheckConstraint(
                condition=Q(maximum_score__gt=Decimal("0")),
                name="assess_attempt_maximum_positive",
            ),
            models.CheckConstraint(
                condition=Q(auto_score__gte=Decimal("0"))
                & Q(manual_score__gte=Decimal("0"))
                & Q(total_score__gte=Decimal("0"))
                & Q(total_score__lte=F("maximum_score")),
                name="assess_attempt_scores_range",
            ),
            models.CheckConstraint(
                condition=Q(basis_points__isnull=True)
                | (Q(basis_points__gte=0) & Q(basis_points__lte=10_000)),
                name="assess_attempt_bps_range",
            ),
        ]
        indexes = [
            models.Index(
                fields=["delivery_assignment", "status"],
                name="assess_att_assign_state_ix",
            ),
            models.Index(
                fields=["assessment_version", "status"],
                name="assess_att_ver_state_ix",
            ),
        ]
        ordering = ("attempt_number",)

    def __str__(self) -> str:
        return f"{self.delivery_assignment}:attempt-{self.attempt_number}"

    @property
    def organization(self) -> Organization:
        return self.delivery_assignment.delivery.organization


class AttemptItem(ImmutableModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(Attempt, on_delete=models.PROTECT, related_name="items")
    assessment_item_id = models.UUIDField(editable=False)
    pool = models.ForeignKey(
        "AssessmentItemPool",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="attempt_items",
        editable=False,
    )
    candidate_position = models.PositiveIntegerField(
        null=True, blank=True, editable=False
    )
    question_version = models.ForeignKey(
        QuestionVersion, on_delete=models.PROTECT, related_name="attempt_items"
    )
    section_position = models.PositiveIntegerField(editable=False)
    item_position = models.PositiveIntegerField(editable=False)
    display_position = models.PositiveIntegerField(editable=False)
    points = models.DecimalField(max_digits=12, decimal_places=3, editable=False)
    required = models.BooleanField(editable=False)
    public_snapshot = models.JSONField(editable=False)
    grading_snapshot = models.JSONField(editable=False)
    feedback_snapshot = models.JSONField(editable=False)
    snapshot_digest = models.CharField(max_length=64, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "assessment_item_id"],
                name="assess_attemptitem_source_unique",
            ),
            models.UniqueConstraint(
                fields=["attempt", "display_position"],
                name="assess_attemptitem_display_unique",
            ),
            models.CheckConstraint(
                condition=Q(points__gt=Decimal("0")),
                name="assess_attemptitem_points_positive",
            ),
            models.CheckConstraint(
                condition=Q(snapshot_digest__regex=r"^[0-9a-f]{64}$"),
                name="assess_attemptitem_digest_sha256",
            ),
            models.CheckConstraint(
                condition=(
                    Q(pool__isnull=True, candidate_position__isnull=True)
                    | Q(pool__isnull=False, candidate_position__gt=0)
                ),
                name="assess_attitem_pool_candidate_state",
            ),
        ]
        ordering = ("display_position",)

    def __str__(self) -> str:
        return f"{self.attempt}:item-{self.display_position}"


class Response(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt_item = models.OneToOneField(
        AttemptItem, on_delete=models.PROTECT, related_name="response"
    )
    response = models.JSONField()
    status = models.CharField(
        max_length=24,
        choices=ResponseStatus.choices,
        default=ResponseStatus.SAVED,
    )
    score = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal("0.000")
    )
    grading_version = models.PositiveIntegerField(default=1)
    saved_at = models.DateTimeField()
    graded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(score__gte=Decimal("0")),
                name="assess_response_score_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(grading_version__gt=0),
                name="assess_response_grading_version_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.attempt_item}:{self.status}"


class ManualGradeDecision(ImmutableModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    response = models.ForeignKey(
        Response, on_delete=models.PROTECT, related_name="manual_decisions"
    )
    sequence = models.PositiveIntegerField()
    score = models.DecimalField(max_digits=12, decimal_places=3)
    feedback = models.TextField(max_length=10_000, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="manual_grade_decisions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["response", "sequence"],
                name="assess_manual_response_sequence_unique",
            ),
            models.CheckConstraint(
                condition=Q(sequence__gt=0),
                name="assess_manual_sequence_positive",
            ),
            models.CheckConstraint(
                condition=Q(score__gte=Decimal("0")),
                name="assess_manual_score_nonnegative",
            ),
        ]
        ordering = ("sequence",)

    def __str__(self) -> str:
        return f"{self.response}:decision-{self.sequence}"


class AttemptEvent(ImmutableModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(
        Attempt, on_delete=models.PROTECT, related_name="events"
    )
    event_type = models.CharField(max_length=32, choices=AttemptEventType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assessment_attempt_events",
    )
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["attempt", "created_at"], name="assess_evt_att_created_ix"
            )
        ]
        ordering = ("created_at", "id")

    def __str__(self) -> str:
        return f"{self.attempt}:{self.event_type}"


class AssessmentItemPool(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.ForeignKey(
        AssessmentRevision, on_delete=models.PROTECT, related_name="item_pools"
    )
    title = models.CharField(max_length=200)
    instructions = models.TextField(max_length=5_000, blank=True)
    position = models.PositiveIntegerField()
    selection_count = models.PositiveIntegerField()
    points_per_item = models.DecimalField(max_digits=12, decimal_places=3)
    selection_strategy = models.CharField(
        max_length=32,
        choices=PoolSelectionStrategy.choices,
        default=PoolSelectionStrategy.RANDOM_WITHOUT_REPLACEMENT,
    )
    shuffle_selected = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessment_item_pools_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessment_item_pools_updated",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["revision", "position"],
                name="assess_pool_revision_position_unique",
                deferrable=models.Deferrable.DEFERRED,
            ),
            models.CheckConstraint(
                condition=Q(position__gt=0),
                name="assess_pool_position_positive",
            ),
            models.CheckConstraint(
                condition=Q(selection_count__gt=0),
                name="assess_pool_selection_positive",
            ),
            models.CheckConstraint(
                condition=Q(points_per_item__gt=Decimal("0")),
                name="assess_pool_points_positive",
            ),
        ]
        ordering = ("position", "id")

    def __str__(self) -> str:
        return f"{self.revision}:pool-{self.position}"

    def clean(self) -> None:
        super().clean()
        self.title = self.title.strip()
        self.instructions = self.instructions.strip()


class AssessmentPoolCandidate(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pool = models.ForeignKey(
        AssessmentItemPool, on_delete=models.PROTECT, related_name="candidates"
    )
    question_version = models.ForeignKey(
        QuestionVersion, on_delete=models.PROTECT, related_name="pool_candidates"
    )
    position = models.PositiveIntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessment_pool_candidates_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["pool", "question_version"],
                name="assess_pool_candidate_version_unique",
            ),
            models.UniqueConstraint(
                fields=["pool", "position"],
                name="assess_pool_candidate_position_unique",
                deferrable=models.Deferrable.DEFERRED,
            ),
            models.CheckConstraint(
                condition=Q(position__gt=0),
                name="assess_pool_candidate_position_positive",
            ),
        ]
        ordering = ("position", "id")

    def __str__(self) -> str:
        return f"{self.pool}:candidate-{self.position}"

    def clean(self) -> None:
        super().clean()
        if (
            self.pool_id
            and self.question_version_id
            and self.question_version.question.organization.id
            != self.pool.revision.organization.id
        ):
            raise ValidationError(
                {"question_version": "La pregunta pertenece a otra organización."}
            )


class AssessmentGradingPolicy(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment_version = models.OneToOneField(
        AssessmentVersion,
        on_delete=models.PROTECT,
        related_name="grading_policy",
    )
    current_revision = models.OneToOneField(
        "AssessmentGradingRevision",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="current_for_policy",
    )
    lock_version = models.PositiveIntegerField(default=1, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(lock_version__gt=0),
                name="assess_gpolicy_lock_positive",
            )
        ]

    def __str__(self) -> str:
        return f"{self.assessment_version}:grading-policy"


class AssessmentGradingRevision(ImmutableModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(
        AssessmentGradingPolicy,
        on_delete=models.PROTECT,
        related_name="revisions",
    )
    number = models.PositiveIntegerField()
    previous_revision = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="next_revision",
    )
    source = models.CharField(max_length=16, choices=GradingRevisionSource.choices)
    reason = models.TextField(max_length=2_000, blank=True)
    grading_snapshot = models.JSONField(editable=False)
    snapshot_digest = models.CharField(max_length=64, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assessment_grading_revisions_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["policy", "number"],
                name="assess_grevision_policy_number_unique",
            ),
            models.CheckConstraint(
                condition=Q(number__gt=0),
                name="assess_grevision_number_positive",
            ),
            models.CheckConstraint(
                condition=Q(snapshot_digest__regex=r"^[0-9a-f]{64}$"),
                name="assess_grevision_digest_sha256",
            ),
            models.CheckConstraint(
                condition=(
                    Q(source=GradingRevisionSource.ORIGINAL, reason="")
                    | (Q(source=GradingRevisionSource.CORRECTION) & ~Q(reason=""))
                ),
                name="assess_grevision_reason_state",
            ),
            models.CheckConstraint(
                condition=Q(previous_revision__isnull=True)
                | ~Q(previous_revision=F("id")),
                name="assess_grevision_not_self",
            ),
        ]
        ordering = ("number",)

    def __str__(self) -> str:
        return f"{self.policy}:revision-{self.number}"


class AttemptGradeVersion(ImmutableModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(
        Attempt, on_delete=models.PROTECT, related_name="grade_versions"
    )
    number = models.PositiveIntegerField()
    previous_grade = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="next_grade",
    )
    grading_revision = models.ForeignKey(
        AssessmentGradingRevision,
        on_delete=models.PROTECT,
        related_name="attempt_grades",
    )
    source = models.CharField(max_length=16, choices=GradeSource.choices)
    scoring_engine_version = models.PositiveIntegerField(editable=False)
    automatic_score = models.DecimalField(
        max_digits=12, decimal_places=3, editable=False
    )
    manual_score = models.DecimalField(max_digits=12, decimal_places=3, editable=False)
    final_score = models.DecimalField(max_digits=12, decimal_places=3, editable=False)
    maximum_score = models.DecimalField(max_digits=12, decimal_places=3, editable=False)
    percent_basis_points = models.PositiveIntegerField(
        null=True, blank=True, editable=False
    )
    passed = models.BooleanField(null=True, blank=True, editable=False)
    grading_status = models.CharField(
        max_length=24, choices=GradingStatus.choices, editable=False
    )
    digest = models.CharField(max_length=64, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assessment_grade_versions_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "number"],
                name="assess_grade_attempt_number_unique",
            ),
            models.UniqueConstraint(
                fields=["attempt", "grading_revision"],
                condition=Q(source__in=[GradeSource.INITIAL, GradeSource.REGRADE]),
                name="assess_grade_attempt_revision_auto_unique",
            ),
            models.CheckConstraint(
                condition=Q(number__gt=0),
                name="assess_grade_number_positive",
            ),
            models.CheckConstraint(
                condition=Q(scoring_engine_version__gt=0),
                name="assess_grade_engine_positive",
            ),
            models.CheckConstraint(
                condition=(
                    Q(automatic_score__gte=Decimal("0"))
                    & Q(manual_score__gte=Decimal("0"))
                    & Q(final_score__gte=Decimal("0"))
                    & Q(final_score__lte=F("maximum_score"))
                    & Q(maximum_score__gt=Decimal("0"))
                ),
                name="assess_grade_scores_range",
            ),
            models.CheckConstraint(
                condition=Q(percent_basis_points__isnull=True)
                | (
                    Q(percent_basis_points__gte=0) & Q(percent_basis_points__lte=10_000)
                ),
                name="assess_grade_percent_range",
            ),
            models.CheckConstraint(
                condition=Q(digest__regex=r"^[0-9a-f]{64}$"),
                name="assess_grade_digest_sha256",
            ),
            models.CheckConstraint(
                condition=Q(previous_grade__isnull=True) | ~Q(previous_grade=F("id")),
                name="assess_grade_not_self",
            ),
        ]
        ordering = ("number",)

    def __str__(self) -> str:
        return f"{self.attempt}:grade-{self.number}"


class AttemptItemGradeVersion(ImmutableModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt_grade = models.ForeignKey(
        AttemptGradeVersion, on_delete=models.PROTECT, related_name="item_grades"
    )
    attempt_item = models.ForeignKey(
        AttemptItem, on_delete=models.PROTECT, related_name="grade_versions"
    )
    response = models.ForeignKey(
        Response,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="item_grade_versions",
    )
    credit_basis_points = models.PositiveIntegerField(editable=False)
    score = models.DecimalField(max_digits=12, decimal_places=3, editable=False)
    maximum_score = models.DecimalField(max_digits=12, decimal_places=3, editable=False)
    grading_status = models.CharField(
        max_length=24, choices=GradingStatus.choices, editable=False
    )
    is_correct = models.BooleanField(null=True, blank=True, editable=False)
    feedback_key = models.CharField(max_length=64, blank=True, editable=False)
    manual_review_reason = models.CharField(max_length=64, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt_grade", "attempt_item"],
                name="assess_itemgrade_grade_item_unique",
            ),
            models.CheckConstraint(
                condition=Q(credit_basis_points__gte=0)
                & Q(credit_basis_points__lte=10_000),
                name="assess_itemgrade_credit_range",
            ),
            models.CheckConstraint(
                condition=Q(score__gte=Decimal("0"))
                & Q(score__lte=F("maximum_score"))
                & Q(maximum_score__gt=Decimal("0")),
                name="assess_itemgrade_score_range",
            ),
        ]
        ordering = ("attempt_item__display_position",)

    def __str__(self) -> str:
        return f"{self.attempt_grade}:{self.attempt_item_id}"


class AttemptGradingJob(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(
        Attempt, on_delete=models.PROTECT, related_name="grading_jobs"
    )
    grading_revision = models.ForeignKey(
        AssessmentGradingRevision,
        on_delete=models.PROTECT,
        related_name="grading_jobs",
    )
    status = models.CharField(
        max_length=24, choices=JobStatus.choices, default=JobStatus.QUEUED
    )
    task_id = models.UUIDField(unique=True, editable=False)
    attempts = models.PositiveIntegerField(default=0)
    last_error_code = models.CharField(max_length=64, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "grading_revision"],
                condition=Q(status__in=[JobStatus.QUEUED, JobStatus.RUNNING]),
                name="assess_gjob_one_active",
            )
        ]
        indexes = [
            models.Index(fields=["status", "created_at"], name="assess_gjob_state_ix")
        ]

    def __str__(self) -> str:
        return f"{self.attempt}:grading-job-{self.id}"


class RegradeJob(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="assessment_regrade_jobs"
    )
    assessment_version = models.ForeignKey(
        AssessmentVersion, on_delete=models.PROTECT, related_name="regrade_jobs"
    )
    grading_revision = models.ForeignKey(
        AssessmentGradingRevision,
        on_delete=models.PROTECT,
        related_name="regrade_jobs",
    )
    delivery = models.ForeignKey(
        AssessmentDelivery,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="regrade_jobs",
    )
    status = models.CharField(
        max_length=24, choices=JobStatus.choices, default=JobStatus.QUEUED
    )
    reason = models.TextField(max_length=2_000)
    total_attempts = models.PositiveIntegerField(default=0)
    processed_attempts = models.PositiveIntegerField(default=0)
    succeeded_attempts = models.PositiveIntegerField(default=0)
    failed_attempts = models.PositiveIntegerField(default=0)
    lock_version = models.PositiveIntegerField(default=1, editable=False)
    task_id = models.UUIDField(unique=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessment_regrade_jobs_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "organization",
                    "assessment_version",
                    "grading_revision",
                    "delivery",
                ],
                condition=Q(
                    status__in=[JobStatus.QUEUED, JobStatus.RUNNING],
                    delivery__isnull=False,
                ),
                name="assess_regrade_delivery_active",
            ),
            models.UniqueConstraint(
                fields=["organization", "assessment_version", "grading_revision"],
                condition=Q(
                    status__in=[JobStatus.QUEUED, JobStatus.RUNNING],
                    delivery__isnull=True,
                ),
                name="assess_regrade_global_active",
            ),
            models.CheckConstraint(
                condition=~Q(reason=""),
                name="assess_regrade_reason_required",
            ),
            models.CheckConstraint(
                condition=Q(lock_version__gt=0),
                name="assess_regrade_lock_positive",
            ),
            models.CheckConstraint(
                condition=(
                    Q(processed_attempts__lte=F("total_attempts"))
                    & Q(succeeded_attempts__lte=F("processed_attempts"))
                    & Q(failed_attempts__lte=F("processed_attempts"))
                ),
                name="assess_regrade_counts_valid",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "status"], name="assess_regrade_org_state_ix"
            )
        ]

    def __str__(self) -> str:
        return f"{self.assessment_version}:regrade-{self.id}"


class RegradeJobAttempt(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(
        RegradeJob, on_delete=models.PROTECT, related_name="attempt_items"
    )
    attempt = models.ForeignKey(
        Attempt, on_delete=models.PROTECT, related_name="regrade_job_items"
    )
    status = models.CharField(
        max_length=16,
        choices=RegradeAttemptStatus.choices,
        default=RegradeAttemptStatus.PENDING,
    )
    previous_grade = models.ForeignKey(
        AttemptGradeVersion,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="regrade_items_as_previous",
    )
    new_grade = models.ForeignKey(
        AttemptGradeVersion,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="regrade_items_as_new",
    )
    error_code = models.CharField(max_length=64, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["job", "attempt"],
                name="assess_regrade_item_unique",
            )
        ]
        indexes = [
            models.Index(fields=["job", "status"], name="assess_regrade_item_state_ix")
        ]

    def __str__(self) -> str:
        return f"{self.job}:{self.attempt}"


class CourseGradebook(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="course_gradebooks"
    )
    course_release = models.ForeignKey(
        CourseRelease, on_delete=models.PROTECT, related_name="gradebooks"
    )
    course_group = models.ForeignKey(
        LearningCohort,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="gradebooks",
    )
    academic_period = models.ForeignKey(
        AcademicPeriod,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="gradebooks",
    )
    migration_review_required = models.BooleanField(default=False)
    status = models.CharField(
        max_length=16,
        choices=GradebookStatus.choices,
        default=GradebookStatus.DRAFT,
    )
    lock_version = models.PositiveIntegerField(default=1, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_gradebooks_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_gradebooks_updated",
    )
    updated_at = models.DateTimeField(auto_now=True)
    activated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="course_gradebooks_activated",
    )
    activated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course_group", "course_release", "academic_period"],
                condition=Q(course_group__isnull=False),
                name="assess_gradebook_execution_unique",
            ),
            models.CheckConstraint(
                condition=Q(lock_version__gt=0),
                name="assess_gradebook_lock_positive",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=GradebookStatus.DRAFT,
                        activated_by__isnull=True,
                        activated_at__isnull=True,
                    )
                    | Q(
                        status=GradebookStatus.ACTIVE,
                        activated_by__isnull=False,
                        activated_at__isnull=False,
                    )
                ),
                name="assess_gradebook_activation_state",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.course_release}:gradebook"

    def clean(self) -> None:
        super().clean()
        if self.course_release.course.organization_id != self.organization_id:
            raise ValidationError(
                {"course_release": "El release pertenece a otra organización."}
            )
        if self.course_group_id:
            if (
                self.course_group.organization_id != self.organization_id
                or self.course_group.release_id != self.course_release_id
                or self.course_group.academic_period_id != self.academic_period_id
            ):
                raise ValidationError(
                    {"course_group": "El gradebook usa otra ejecución académica."}
                )


class GradebookColumn(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gradebook = models.ForeignKey(
        CourseGradebook, on_delete=models.PROTECT, related_name="columns"
    )
    delivery = models.ForeignKey(
        AssessmentDelivery,
        on_delete=models.PROTECT,
        related_name="gradebook_columns",
    )
    title = models.CharField(max_length=200)
    position = models.PositiveIntegerField()
    weight_basis_points = models.PositiveIntegerField()
    required = models.BooleanField(default=True)
    attempt_aggregation = models.CharField(
        max_length=16,
        choices=AttemptAggregation.choices,
        default=AttemptAggregation.HIGHEST,
    )
    status = models.CharField(
        max_length=16,
        choices=GradebookColumnStatus.choices,
        default=GradebookColumnStatus.ACTIVE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="gradebook_columns_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="gradebook_columns_updated",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["gradebook", "position"],
                name="assess_gcolumn_position_unique",
                deferrable=models.Deferrable.DEFERRED,
            ),
            models.UniqueConstraint(
                fields=["gradebook", "delivery"],
                name="assess_gcolumn_delivery_unique",
            ),
            models.CheckConstraint(
                condition=Q(position__gt=0),
                name="assess_gcolumn_position_positive",
            ),
            models.CheckConstraint(
                condition=Q(weight_basis_points__gte=1)
                & Q(weight_basis_points__lte=10_000),
                name="assess_gcolumn_weight_range",
            ),
        ]
        ordering = ("position", "id")

    def __str__(self) -> str:
        return f"{self.gradebook}:column-{self.position}"

    def clean(self) -> None:
        super().clean()
        self.title = self.title.strip()
        if self.gradebook_id and self.delivery_id:
            if self.delivery.organization_id != self.gradebook.organization_id:
                raise ValidationError(
                    {"delivery": "La entrega pertenece a otra organización."}
                )
            if self.delivery.course_release_id != self.gradebook.course_release_id:
                raise ValidationError(
                    {"delivery": "La entrega pertenece a otro release."}
                )


class GradebookEntry(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    column = models.ForeignKey(
        GradebookColumn, on_delete=models.PROTECT, related_name="entries"
    )
    release_assignment = models.ForeignKey(
        EnrollmentReleaseAssignment,
        on_delete=models.PROTECT,
        related_name="gradebook_entries",
    )
    attempt = models.ForeignKey(
        Attempt,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="gradebook_entries",
    )
    attempt_grade = models.ForeignKey(
        AttemptGradeVersion,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="gradebook_entries",
    )
    status = models.CharField(
        max_length=16,
        choices=GradebookEntryStatus.choices,
        default=GradebookEntryStatus.MISSING,
    )
    score = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0"))
    maximum_score = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal("0")
    )
    percent_basis_points = models.PositiveIntegerField(null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["column", "release_assignment"],
                name="assess_gentry_column_assignment_unique",
            ),
            models.CheckConstraint(
                condition=Q(score__gte=Decimal("0"))
                & Q(maximum_score__gte=Decimal("0"))
                & Q(score__lte=F("maximum_score")),
                name="assess_gentry_score_range",
            ),
            models.CheckConstraint(
                condition=Q(percent_basis_points__isnull=True)
                | (
                    Q(percent_basis_points__gte=0) & Q(percent_basis_points__lte=10_000)
                ),
                name="assess_gentry_percent_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.column}:{self.release_assignment}"


class GradebookSummary(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gradebook = models.ForeignKey(
        CourseGradebook, on_delete=models.PROTECT, related_name="summaries"
    )
    release_assignment = models.ForeignKey(
        EnrollmentReleaseAssignment,
        on_delete=models.PROTECT,
        related_name="gradebook_summaries",
    )
    status = models.CharField(
        max_length=16,
        choices=GradebookSummaryStatus.choices,
        default=GradebookSummaryStatus.INCOMPLETE,
    )
    completed_columns = models.PositiveIntegerField(default=0)
    total_columns = models.PositiveIntegerField(default=0)
    weighted_percent_basis_points = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["gradebook", "release_assignment"],
                name="assess_gsummary_book_assignment_unique",
            ),
            models.CheckConstraint(
                condition=Q(completed_columns__lte=F("total_columns")),
                name="assess_gsummary_columns_valid",
            ),
            models.CheckConstraint(
                condition=Q(weighted_percent_basis_points__gte=0)
                & Q(weighted_percent_basis_points__lte=10_000),
                name="assess_gsummary_percent_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.gradebook}:{self.release_assignment}"


class AssessmentAnalyticsSnapshot(ImmutableModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment_version = models.ForeignKey(
        AssessmentVersion,
        on_delete=models.PROTECT,
        related_name="analytics_snapshots",
    )
    grading_revision = models.ForeignKey(
        AssessmentGradingRevision,
        on_delete=models.PROTECT,
        related_name="analytics_snapshots",
    )
    delivery = models.ForeignKey(
        AssessmentDelivery,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="analytics_snapshots",
    )
    sample_size = models.PositiveIntegerField()
    mean_percent_basis_points = models.PositiveIntegerField(null=True, blank=True)
    median_percent_basis_points = models.PositiveIntegerField(null=True, blank=True)
    p25_percent_basis_points = models.PositiveIntegerField(null=True, blank=True)
    p75_percent_basis_points = models.PositiveIntegerField(null=True, blank=True)
    pass_rate_basis_points = models.PositiveIntegerField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assessment_analytics_snapshots_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    (
                        Q(mean_percent_basis_points__isnull=True)
                        | Q(
                            mean_percent_basis_points__gte=0,
                            mean_percent_basis_points__lte=10_000,
                        )
                    )
                    & (
                        Q(median_percent_basis_points__isnull=True)
                        | Q(
                            median_percent_basis_points__gte=0,
                            median_percent_basis_points__lte=10_000,
                        )
                    )
                    & (
                        Q(p25_percent_basis_points__isnull=True)
                        | Q(
                            p25_percent_basis_points__gte=0,
                            p25_percent_basis_points__lte=10_000,
                        )
                    )
                    & (
                        Q(p75_percent_basis_points__isnull=True)
                        | Q(
                            p75_percent_basis_points__gte=0,
                            p75_percent_basis_points__lte=10_000,
                        )
                    )
                    & (
                        Q(pass_rate_basis_points__isnull=True)
                        | Q(
                            pass_rate_basis_points__gte=0,
                            pass_rate_basis_points__lte=10_000,
                        )
                    )
                ),
                name="assess_analytics_percent_ranges",
            )
        ]
        indexes = [
            models.Index(
                fields=["assessment_version", "created_at"],
                name="assess_analytics_version_ix",
            )
        ]

    def __str__(self) -> str:
        return f"{self.assessment_version}:analytics-{self.id}"


class ItemAnalyticsSnapshot(ImmutableModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment_snapshot = models.ForeignKey(
        AssessmentAnalyticsSnapshot,
        on_delete=models.PROTECT,
        related_name="items",
    )
    assessment_item_id = models.UUIDField(editable=False)
    question_version = models.ForeignKey(
        QuestionVersion,
        on_delete=models.PROTECT,
        related_name="item_analytics_snapshots",
    )
    question_type = models.CharField(
        max_length=24, choices=QuestionType.choices, editable=False
    )
    presented_count = models.PositiveIntegerField()
    answered_count = models.PositiveIntegerField()
    omitted_count = models.PositiveIntegerField()
    mean_credit_basis_points = models.PositiveIntegerField()
    difficulty_basis_points = models.PositiveIntegerField()
    discrimination = models.DecimalField(
        max_digits=8, decimal_places=6, null=True, blank=True
    )
    discrimination_sample_size = models.PositiveIntegerField()
    discrimination_suppressed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["assessment_snapshot", "assessment_item_id"],
                name="assess_itemanalytics_snapshot_item_unique",
            ),
            models.CheckConstraint(
                condition=Q(answered_count__lte=F("presented_count"))
                & Q(omitted_count__lte=F("presented_count"))
                & Q(answered_count=F("presented_count") - F("omitted_count")),
                name="assess_itemanalytics_counts_valid",
            ),
            models.CheckConstraint(
                condition=Q(mean_credit_basis_points__gte=0)
                & Q(mean_credit_basis_points__lte=10_000)
                & Q(difficulty_basis_points__gte=0)
                & Q(difficulty_basis_points__lte=10_000),
                name="assess_itemanalytics_bps_range",
            ),
            models.CheckConstraint(
                condition=(
                    Q(discrimination_suppressed=True, discrimination__isnull=True)
                    | Q(discrimination_suppressed=False, discrimination__isnull=False)
                ),
                name="assess_itemanalytics_discrimination_state",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.assessment_snapshot}:{self.assessment_item_id}"


class OptionAnalyticsSnapshot(ImmutableModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item_analytics = models.ForeignKey(
        ItemAnalyticsSnapshot,
        on_delete=models.PROTECT,
        related_name="options",
    )
    option_id = models.CharField(max_length=64, editable=False)
    selected_count = models.PositiveIntegerField()
    selected_rate_basis_points = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["item_analytics", "option_id"],
                name="assess_optionanalytics_item_option_unique",
            ),
            models.CheckConstraint(
                condition=Q(selected_rate_basis_points__gte=0)
                & Q(selected_rate_basis_points__lte=10_000),
                name="assess_optionanalytics_rate_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.item_analytics}:{self.option_id}"


class AnalyticsRefreshJob(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="assessment_analytics_jobs",
    )
    assessment_version = models.ForeignKey(
        AssessmentVersion,
        on_delete=models.PROTECT,
        related_name="analytics_jobs",
    )
    grading_revision = models.ForeignKey(
        AssessmentGradingRevision,
        on_delete=models.PROTECT,
        related_name="analytics_jobs",
    )
    delivery = models.ForeignKey(
        AssessmentDelivery,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="analytics_jobs",
    )
    status = models.CharField(
        max_length=24, choices=JobStatus.choices, default=JobStatus.QUEUED
    )
    task_id = models.UUIDField(unique=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assessment_analytics_jobs_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=64, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="assess_analytics_job_state_ix",
            )
        ]

    def __str__(self) -> str:
        return f"{self.assessment_version}:analytics-job-{self.id}"
