# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportIncompatibleVariableOverride=false
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower, Trim

from domain.courses.models import Course
from domain.organizations.models import Membership, Organization
from domain.publishing.models import CourseRelease

from .choices import (
    AcademicGroupLevel,
    AcademicGroupMemberStatus,
    AcademicGroupRole,
    AssignmentReason,
    CohortRosterMode,
    CohortStaffRole,
    CohortStatus,
    EnrollmentCohortSource,
    EnrollmentStatus,
    EnrollmentWindowMode,
    LearningEventType,
    ProgressStatus,
    RosterEventType,
    UnitProgressStatus,
)


class NoPhysicalDeleteModel(models.Model):
    class Meta:
        abstract = True

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Este historial no se elimina físicamente.")


class AcademicGroup(NoPhysicalDeleteModel):
    """Grupo institucional reutilizable entre cursos, años y cohortes."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="academic_groups"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100)
    academic_year = models.PositiveSmallIntegerField()
    level = models.CharField(max_length=32, choices=AcademicGroupLevel.choices)
    section = models.CharField(max_length=40, blank=True)
    description = models.TextField(max_length=2_000, blank=True)
    status = models.CharField(
        max_length=16, choices=CohortStatus.choices, default=CohortStatus.ACTIVE
    )
    lock_version = models.PositiveIntegerField(default=1, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="academic_groups_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("slug"), "organization", name="learning_group_org_slug_ci"
            ),
            models.CheckConstraint(
                condition=Q(slug=Lower(F("slug"))),
                name="learning_group_slug_lowercase",
            ),
            models.CheckConstraint(
                condition=Q(academic_year__gte=2000, academic_year__lte=2200),
                name="learning_group_academic_year",
            ),
            models.CheckConstraint(
                condition=Q(lock_version__gt=0),
                name="learning_group_lock_positive",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "academic_year", "status"],
                name="learn_group_org_year_ix",
            )
        ]

    def __str__(self) -> str:
        return f"{self.organization}:{self.academic_year}:{self.slug}"

    def clean(self) -> None:
        super().clean()
        self.name = self.name.strip()
        self.slug = self.slug.strip().lower()
        self.section = self.section.strip()
        self.description = self.description.strip()


class AcademicGroupMember(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        AcademicGroup, on_delete=models.PROTECT, related_name="roster"
    )
    membership = models.ForeignKey(
        Membership, on_delete=models.PROTECT, related_name="academic_groups"
    )
    role = models.CharField(max_length=16, choices=AcademicGroupRole.choices)
    status = models.CharField(
        max_length=16,
        choices=AcademicGroupMemberStatus.choices,
        default=AcademicGroupMemberStatus.ACTIVE,
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="academic_group_members_added",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group", "membership"], name="learning_group_member_unique"
            )
        ]
        indexes = [
            models.Index(
                fields=["group", "role", "status"], name="learn_group_roster_ix"
            )
        ]

    def __str__(self) -> str:
        return f"{self.group}:{self.membership}:{self.role}"

    def clean(self) -> None:
        super().clean()
        if (
            self.group_id
            and self.membership_id
            and self.group.organization_id != self.membership.organization_id
        ):
            raise ValidationError(
                {"membership": "La persona pertenece a otra organización."}
            )


class LearningCohort(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="learning_cohorts"
    )
    course = models.ForeignKey(
        Course, on_delete=models.PROTECT, related_name="learning_cohorts"
    )
    release = models.ForeignKey(
        CourseRelease, on_delete=models.PROTECT, related_name="learning_cohorts"
    )
    academic_group = models.ForeignKey(
        AcademicGroup,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="course_cohorts",
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80)
    description = models.TextField(max_length=2_000, blank=True)
    status = models.CharField(
        max_length=16, choices=CohortStatus.choices, default=CohortStatus.ACTIVE
    )
    roster_mode = models.CharField(
        max_length=16,
        choices=CohortRosterMode.choices,
        default=CohortRosterMode.MANUAL,
    )
    access_starts_at = models.DateTimeField(null=True, blank=True)
    access_ends_at = models.DateTimeField(null=True, blank=True)
    lock_version = models.PositiveIntegerField(default=1, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="learning_cohorts_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="learning_cohorts_updated",
    )
    updated_at = models.DateTimeField(auto_now=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="learning_cohorts_archived",
    )
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("slug"), "course", name="learning_cohort_course_slug_ci"
            ),
            models.CheckConstraint(
                condition=Q(slug=Lower(F("slug"))),
                name="learning_cohort_slug_lowercase",
            ),
            models.CheckConstraint(
                condition=Q(name=Trim(F("name"))) & ~Q(name=""),
                name="learning_cohort_name_trimmed",
            ),
            models.CheckConstraint(
                condition=Q(access_starts_at__isnull=True)
                | Q(access_ends_at__isnull=True)
                | Q(access_starts_at__lt=F("access_ends_at")),
                name="learning_cohort_access_window",
            ),
            models.CheckConstraint(
                condition=Q(lock_version__gt=0),
                name="learning_cohort_lock_positive",
            ),
            models.CheckConstraint(
                condition=Q(roster_mode=CohortRosterMode.MANUAL)
                | Q(academic_group__isnull=False),
                name="learning_synced_cohort_needs_group",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=CohortStatus.ACTIVE,
                        archived_by__isnull=True,
                        archived_at__isnull=True,
                    )
                    | Q(
                        status=CohortStatus.ARCHIVED,
                        archived_by__isnull=False,
                        archived_at__isnull=False,
                    )
                ),
                name="learning_cohort_archive_state",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "status"], name="learn_cohort_org_state_ix"
            ),
            models.Index(
                fields=["course", "status"], name="learn_cohort_course_state_ix"
            ),
            models.Index(fields=["release"], name="learn_cohort_release_ix"),
        ]

    def __str__(self) -> str:
        return f"{self.course}:{self.slug}"

    def clean(self) -> None:
        super().clean()
        self.name = self.name.strip()
        self.slug = self.slug.strip().lower()
        self.description = self.description.strip()
        if self.course_id and self.course.organization_id != self.organization_id:
            raise ValidationError({"course": "El curso pertenece a otra organización."})
        if (
            self.academic_group_id
            and self.academic_group.organization_id != self.organization_id
        ):
            raise ValidationError(
                {"academic_group": "El grupo pertenece a otra organización."}
            )
        if self.release_id and (
            self.release.course_id != self.course_id
            or self.release.course.organization_id != self.organization_id
        ):
            raise ValidationError({"release": "El release no pertenece al curso."})
        if self.pk and self.release_id:
            original_release_id = (
                type(self)
                .objects.filter(pk=self.pk)
                .values_list("release_id", flat=True)
                .first()
            )
            if (
                original_release_id
                and original_release_id != self.release_id
                and self.enrollments.exists()
            ):
                raise ValidationError(
                    {
                        "release": "El release es inmutable después de la primera matrícula."
                    }
                )


class CourseEnrollment(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="course_enrollments"
    )
    membership = models.ForeignKey(
        Membership, on_delete=models.PROTECT, related_name="course_enrollments"
    )
    course = models.ForeignKey(
        Course, on_delete=models.PROTECT, related_name="enrollments"
    )
    cohort = models.ForeignKey(
        LearningCohort,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="enrollments",
    )
    status = models.CharField(
        max_length=16, choices=EnrollmentStatus.choices, default=EnrollmentStatus.ACTIVE
    )
    current_release_assignment = models.ForeignKey(
        "EnrollmentReleaseAssignment",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="current_for_enrollments",
        editable=False,
    )
    access_starts_at = models.DateTimeField(null=True, blank=True)
    access_ends_at = models.DateTimeField(null=True, blank=True)
    access_provenance = models.CharField(
        max_length=32,
        choices=EnrollmentCohortSource.choices,
        default=EnrollmentCohortSource.MANUAL,
    )
    access_window_mode = models.CharField(
        max_length=16,
        choices=EnrollmentWindowMode.choices,
        default=EnrollmentWindowMode.INDIVIDUAL,
    )
    lock_version = models.PositiveIntegerField(default=1, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_enrollments_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    status_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_enrollments_status_changed",
    )
    status_changed_at = models.DateTimeField()
    suspended_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["membership", "course"],
                condition=~Q(status=EnrollmentStatus.REVOKED),
                name="learning_one_current_enrollment",
            ),
            models.CheckConstraint(
                condition=Q(lock_version__gt=0),
                name="learning_enrollment_lock_positive",
            ),
            models.CheckConstraint(
                condition=Q(access_starts_at__isnull=True)
                | Q(access_ends_at__isnull=True)
                | Q(access_starts_at__lt=F("access_ends_at")),
                name="learning_enrollment_access_window",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=EnrollmentStatus.ACTIVE,
                        suspended_at__isnull=True,
                        revoked_at__isnull=True,
                    )
                    | Q(
                        status=EnrollmentStatus.SUSPENDED,
                        suspended_at__isnull=False,
                        revoked_at__isnull=True,
                    )
                    | Q(
                        status=EnrollmentStatus.REVOKED,
                        revoked_at__isnull=False,
                    )
                ),
                name="learning_enrollment_lifecycle",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "status"], name="learn_enroll_org_state_ix"
            ),
            models.Index(
                fields=["membership", "status"], name="learn_enroll_member_state_ix"
            ),
            models.Index(
                fields=["course", "status"], name="learn_enroll_course_state_ix"
            ),
            models.Index(
                fields=["cohort", "status"], name="learn_enroll_cohort_state_ix"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.membership}:{self.course}"

    def clean(self) -> None:
        super().clean()
        if (
            self.membership_id
            and self.membership.organization_id != self.organization_id
        ):
            raise ValidationError(
                {"membership": "La membresía pertenece a otra organización."}
            )
        if self.course_id and self.course.organization_id != self.organization_id:
            raise ValidationError({"course": "El curso pertenece a otra organización."})
        if self.cohort_id and (
            self.cohort.organization_id != self.organization_id
            or self.cohort.course_id != self.course_id
        ):
            raise ValidationError({"cohort": "La cohorte no corresponde al curso."})

    @property
    def active_cohort_assignment(self) -> EnrollmentCohortAssignment | None:
        return (
            self.cohort_assignments.select_related("cohort")
            .filter(ended_at__isnull=True)
            .first()
        )

    @property
    def effective_cohort(self) -> LearningCohort | None:
        # `cohort` is the temporary v1 read mirror. Services keep it in sync
        # while assignment history is authoritative for roster mutations.
        if self.cohort_id:
            return self.cohort
        assignment = self.active_cohort_assignment
        if assignment is not None:
            return assignment.cohort
        return None

    def effective_access_window(
        self,
    ) -> tuple[datetime | None, datetime | None]:
        if self.access_window_mode == EnrollmentWindowMode.INHERIT:
            cohort = self.effective_cohort
            if cohort is not None:
                return cohort.access_starts_at, cohort.access_ends_at
        return self.access_starts_at, self.access_ends_at


class EnrollmentCohortAssignment(NoPhysicalDeleteModel):
    """Append-only membership of an enrollment in a concrete course group."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(
        CourseEnrollment, on_delete=models.PROTECT, related_name="cohort_assignments"
    )
    cohort = models.ForeignKey(
        LearningCohort,
        on_delete=models.PROTECT,
        related_name="enrollment_assignments",
    )
    source = models.CharField(max_length=32, choices=EnrollmentCohortSource.choices)
    reason = models.CharField(max_length=500)
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="enrollment_cohort_assignments_started",
    )
    started_at = models.DateTimeField()
    ended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="enrollment_cohort_assignments_ended",
    )
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment"],
                condition=Q(ended_at__isnull=True),
                name="learn_enroll_group_one_active",
            ),
            models.CheckConstraint(
                condition=(
                    Q(ended_at__isnull=True, ended_by__isnull=True)
                    | Q(ended_at__isnull=False, ended_by__isnull=False)
                ),
                name="learn_enroll_group_end_state",
            ),
            models.CheckConstraint(
                condition=Q(reason=Trim(F("reason"))) & ~Q(reason=""),
                name="learn_enroll_group_reason_trimmed",
            ),
        ]
        indexes = [
            models.Index(
                fields=["cohort", "ended_at"], name="learn_enroll_group_cohort_ix"
            ),
            models.Index(
                fields=["enrollment", "started_at"], name="learn_enroll_group_hist_ix"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.enrollment_id}:{self.cohort_id}:{self.source}"

    def clean(self) -> None:
        super().clean()
        self.reason = self.reason.strip()
        if not self.enrollment_id or not self.cohort_id:
            return
        if (
            self.enrollment.organization_id != self.cohort.organization_id
            or self.enrollment.course_id != self.cohort.course_id
        ):
            raise ValidationError(
                {"cohort": "El grupo de curso no corresponde a la matrícula."}
            )
        if self.ended_at is None:
            current = self.enrollment.current_release_assignment
            if current is None or current.release_id != self.cohort.release_id:
                raise ValidationError(
                    {"cohort": "El grupo de curso usa otro release efectivo."}
                )


class CohortStaffAssignment(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cohort = models.ForeignKey(
        LearningCohort, on_delete=models.PROTECT, related_name="staff_assignments"
    )
    membership = models.ForeignKey(
        Membership,
        on_delete=models.PROTECT,
        related_name="course_group_staff_assignments",
    )
    role = models.CharField(max_length=24, choices=CohortStaffRole.choices)
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cohort_staff_assignments_started",
    )
    started_at = models.DateTimeField()
    ended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="cohort_staff_assignments_ended",
    )
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cohort", "membership"],
                condition=Q(ended_at__isnull=True),
                name="learn_cohort_staff_one_active",
            ),
            models.CheckConstraint(
                condition=(
                    Q(ended_at__isnull=True, ended_by__isnull=True)
                    | Q(ended_at__isnull=False, ended_by__isnull=False)
                ),
                name="learn_cohort_staff_end_state",
            ),
        ]
        indexes = [
            models.Index(
                fields=["membership", "ended_at"], name="learn_cohort_staff_member_ix"
            ),
            models.Index(
                fields=["cohort", "ended_at"], name="learn_cohort_staff_cohort_ix"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.cohort_id}:{self.membership_id}:{self.role}"

    def clean(self) -> None:
        super().clean()
        if (
            self.cohort_id
            and self.membership_id
            and self.cohort.organization_id != self.membership.organization_id
        ):
            raise ValidationError(
                {"membership": "La persona pertenece a otra organización."}
            )


class RosterEvent(NoPhysicalDeleteModel):
    """Append-only evidence of roster and synchronization decisions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="learning_roster_events"
    )
    academic_group = models.ForeignKey(
        AcademicGroup,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="roster_events",
    )
    cohort = models.ForeignKey(
        LearningCohort,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="roster_events",
    )
    event_type = models.CharField(max_length=48, choices=RosterEventType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="learning_roster_events",
    )
    occurred_at = models.DateTimeField()
    details = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(academic_group__isnull=False) | Q(cohort__isnull=False),
                name="learning_roster_event_has_target",
            )
        ]
        indexes = [
            models.Index(
                fields=["organization", "occurred_at"], name="learn_roster_event_org_ix"
            ),
            models.Index(
                fields=["cohort", "occurred_at"], name="learn_roster_event_cohort_ix"
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.organization_id}:{self.event_type}:{self.occurred_at.isoformat()}"
        )

    def clean(self) -> None:
        super().clean()
        if (
            self.academic_group_id
            and self.academic_group.organization_id != self.organization_id
        ):
            raise ValidationError(
                {"academic_group": "El grupo pertenece a otra organización."}
            )
        if self.cohort_id and self.cohort.organization_id != self.organization_id:
            raise ValidationError(
                {"cohort": "El grupo de curso pertenece a otra organización."}
            )


class EnrollmentReleaseAssignment(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(
        CourseEnrollment, on_delete=models.PROTECT, related_name="release_assignments"
    )
    release = models.ForeignKey(
        CourseRelease, on_delete=models.PROTECT, related_name="enrollment_assignments"
    )
    sequence = models.PositiveIntegerField()
    reason = models.CharField(max_length=24, choices=AssignmentReason.choices)
    previous_assignment = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="next_assignment",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="release_assignments_created",
    )
    assigned_at = models.DateTimeField()
    ended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="release_assignments_ended",
    )
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "sequence"],
                name="learning_assignment_sequence_unique",
            ),
            models.UniqueConstraint(
                fields=["enrollment"],
                condition=Q(ended_at__isnull=True),
                name="learning_assignment_one_active",
            ),
            models.CheckConstraint(
                condition=Q(sequence__gt=0),
                name="learning_assignment_sequence_positive",
            ),
            models.CheckConstraint(
                condition=(
                    Q(ended_at__isnull=True, ended_by__isnull=True)
                    | Q(ended_at__isnull=False, ended_by__isnull=False)
                ),
                name="learning_assignment_end_state",
            ),
            models.CheckConstraint(
                condition=Q(previous_assignment__isnull=True)
                | ~Q(previous_assignment=F("id")),
                name="learning_assignment_not_self_previous",
            ),
        ]
        indexes = [
            models.Index(
                fields=["enrollment", "ended_at"], name="learn_assign_enroll_end_ix"
            ),
            models.Index(fields=["release"], name="learn_assign_release_ix"),
        ]

    def __str__(self) -> str:
        return f"{self.enrollment}:release-{self.release.number}"


class CourseProgress(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    release_assignment = models.OneToOneField(
        EnrollmentReleaseAssignment,
        on_delete=models.PROTECT,
        related_name="progress",
    )
    status = models.CharField(
        max_length=16,
        choices=ProgressStatus.choices,
        default=ProgressStatus.NOT_STARTED,
    )
    total_units = models.PositiveIntegerField()
    completed_units = models.PositiveIntegerField(default=0)
    total_required_activities = models.PositiveIntegerField(default=0)
    completed_required_activities = models.PositiveIntegerField(default=0)
    percent_basis_points = models.PositiveIntegerField(default=0)
    last_unit_id = models.UUIDField(null=True, blank=True)
    last_node_id = models.UUIDField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    lock_version = models.PositiveIntegerField(default=1, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(total_units__gt=0), name="learning_progress_total_positive"
            ),
            models.CheckConstraint(
                condition=Q(completed_units__gte=0)
                & Q(completed_units__lte=F("total_units")),
                name="learning_progress_completed_range",
            ),
            models.CheckConstraint(
                condition=Q(completed_required_activities__gte=0)
                & Q(completed_required_activities__lte=F("total_required_activities")),
                name="learn_progress_required_range",
            ),
            models.CheckConstraint(
                condition=Q(percent_basis_points__gte=0)
                & Q(percent_basis_points__lte=10_000),
                name="learning_progress_percent_range",
            ),
            models.CheckConstraint(
                condition=Q(lock_version__gt=0),
                name="learning_progress_lock_positive",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=ProgressStatus.NOT_STARTED,
                        completed_units=0,
                        completed_required_activities=0,
                        percent_basis_points=0,
                        started_at__isnull=True,
                        completed_at__isnull=True,
                    )
                    | Q(
                        status=ProgressStatus.IN_PROGRESS,
                        started_at__isnull=False,
                        completed_at__isnull=True,
                    )
                    | Q(
                        status=ProgressStatus.COMPLETED,
                        completed_units=F("total_units"),
                        completed_required_activities=F("total_required_activities"),
                        percent_basis_points=10_000,
                        started_at__isnull=False,
                        completed_at__isnull=False,
                    )
                ),
                name="learning_progress_lifecycle",
            ),
        ]
        indexes = [
            models.Index(fields=["status"], name="learn_progress_state_ix"),
            models.Index(
                fields=["last_activity_at"], name="learn_progress_activity_ix"
            ),
            models.Index(fields=["completed_at"], name="learn_progress_complete_ix"),
        ]

    def __str__(self) -> str:
        return f"{self.release_assignment}:{self.status}"


class ExternalLearningRequirement(NoPhysicalDeleteModel):
    """Course progress requirement registered by another bounded domain."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="external_learning_requirements",
    )
    course = models.ForeignKey(
        Course, on_delete=models.PROTECT, related_name="external_learning_requirements"
    )
    source_type = models.CharField(max_length=48)
    source_id = models.UUIDField()
    title = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="external_learning_requirements_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    deactivated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="external_learning_requirements_deactivated",
    )
    deactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("source_type", "source_id"),
                name="learn_external_requirement_source_unique",
            ),
            models.CheckConstraint(
                condition=Q(title=Trim(F("title"))) & ~Q(title=""),
                name="learn_external_requirement_title_trimmed",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        is_active=True,
                        deactivated_by__isnull=True,
                        deactivated_at__isnull=True,
                    )
                    | Q(
                        is_active=False,
                        deactivated_by__isnull=False,
                        deactivated_at__isnull=False,
                    )
                ),
                name="learn_external_requirement_lifecycle",
            ),
        ]
        indexes = [
            models.Index(
                fields=("course", "is_active"),
                name="learn_external_req_course_ix",
            )
        ]

    def __str__(self) -> str:
        return f"{self.course_id}:{self.source_type}:{self.source_id}"

    def clean(self) -> None:
        super().clean()
        self.title = self.title.strip()
        self.source_type = self.source_type.strip()
        if self.course_id and self.course.organization_id != self.organization_id:
            raise ValidationError({"course": "El curso pertenece a otra organización."})


class ExternalRequirementCompletion(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requirement = models.ForeignKey(
        ExternalLearningRequirement,
        on_delete=models.PROTECT,
        related_name="completions",
    )
    course_progress = models.ForeignKey(
        CourseProgress,
        on_delete=models.PROTECT,
        related_name="external_requirement_completions",
    )
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="external_requirement_completions",
    )
    completed_at = models.DateTimeField()
    evidence = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("requirement", "course_progress"),
                name="learn_external_completion_unique",
            )
        ]
        indexes = [
            models.Index(
                fields=("course_progress", "completed_at"),
                name="learn_external_completion_ix",
            )
        ]

    def __str__(self) -> str:
        return f"{self.course_progress_id}:{self.requirement_id}"


class UnitProgress(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course_progress = models.ForeignKey(
        CourseProgress, on_delete=models.PROTECT, related_name="unit_progress"
    )
    unit_id = models.UUIDField()
    status = models.CharField(
        max_length=16,
        choices=UnitProgressStatus.choices,
        default=UnitProgressStatus.IN_PROGRESS,
    )
    first_opened_at = models.DateTimeField()
    last_opened_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    last_node_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course_progress", "unit_id"],
                name="learning_unit_progress_unique",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=UnitProgressStatus.IN_PROGRESS,
                        completed_at__isnull=True,
                    )
                    | Q(
                        status=UnitProgressStatus.COMPLETED,
                        completed_at__isnull=False,
                    )
                ),
                name="learning_unit_progress_lifecycle",
            ),
        ]
        indexes = [
            models.Index(
                fields=["course_progress", "status"],
                name="learn_unit_progress_state_ix",
            ),
            models.Index(fields=["last_opened_at"], name="learn_unit_last_open_ix"),
        ]

    def __str__(self) -> str:
        return f"{self.course_progress}:{self.unit_id}:{self.status}"


class LearningEvent(NoPhysicalDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="learning_events"
    )
    enrollment = models.ForeignKey(
        CourseEnrollment, on_delete=models.PROTECT, related_name="events"
    )
    release_assignment = models.ForeignKey(
        EnrollmentReleaseAssignment,
        on_delete=models.PROTECT,
        related_name="events",
    )
    course_progress = models.ForeignKey(
        CourseProgress,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="events",
    )
    unit_id = models.UUIDField(null=True, blank=True)
    node_id = models.UUIDField(null=True, blank=True)
    external_requirement = models.ForeignKey(
        ExternalLearningRequirement,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="events",
    )
    event_type = models.CharField(max_length=32, choices=LearningEventType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="learning_events",
    )
    occurred_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(
                fields=["enrollment", "occurred_at"], name="learn_event_enroll_time_ix"
            ),
            models.Index(
                fields=["course_progress", "occurred_at"],
                name="learn_event_progress_time_ix",
            ),
            models.Index(
                fields=["event_type", "occurred_at"], name="learn_event_type_time_ix"
            ),
        ]
        ordering = ("occurred_at", "id")

    def __str__(self) -> str:
        return f"{self.enrollment}:{self.event_type}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise ValidationError("Los eventos de aprendizaje son inmutables.")
        super().save(*args, **kwargs)
