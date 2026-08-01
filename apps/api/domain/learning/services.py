# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportArgumentType=false
from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime

from django.db import IntegrityError, models, transaction
from django.utils import timezone
from django.utils.text import slugify

from domain.courses.models import Course
from domain.events.services import record_domain_event
from domain.organizations.choices import MembershipStatus
from domain.organizations.models import Membership, Organization
from domain.publishing.choices import PublicationStatus
from domain.publishing.integrity import verify_release
from domain.publishing.models import CoursePublication, CourseRelease

from .access import require_learning_access
from .choices import (
    AcademicGroupMemberStatus,
    AssignmentReason,
    CohortStatus,
    EnrollmentStatus,
    LearningEventType,
    ProgressStatus,
    UnitProgressStatus,
)
from .exceptions import (
    AccessWindowInvalid,
    CohortArchived,
    CohortReleaseImmutable,
    EnrollmentAlreadyExists,
    EnrollmentCohortMismatch,
    EnrollmentConflict,
    EnrollmentReleaseUpgradeInvalid,
    EnrollmentTransitionInvalid,
    LearningPermissionDenied,
    LearningPositionInvalid,
    LearningProgressConflict,
    LearningReleaseInvalid,
    LearningUnitNotCompleted,
)
from .models import (
    AcademicGroup,
    AcademicGroupMember,
    CourseEnrollment,
    CourseProgress,
    EnrollmentReleaseAssignment,
    ExternalLearningRequirement,
    ExternalRequirementCompletion,
    LearningCohort,
    LearningEvent,
    UnitProgress,
)
from .policies import can_manage_cohorts, can_manage_enrollments
from .snapshots import (
    snapshot_node_ids,
    snapshot_unit,
    snapshot_unit_ids,
    validate_snapshot_position,
)


def _validate_window(starts_at: datetime | None, ends_at: datetime | None) -> None:
    if starts_at and ends_at and starts_at >= ends_at:
        raise AccessWindowInvalid("La fecha inicial debe ser anterior a la final.")


def _validate_release(
    *, organization: Organization, course: Course, release: CourseRelease
) -> None:
    if (
        course.organization_id != organization.id
        or release.course_id != course.id
        or release.course.organization_id != organization.id
        or not verify_release(release).valid
    ):
        raise LearningReleaseInvalid("El release no es válido para este curso.")


def _active_publication(course: Course) -> CoursePublication:
    publication = (
        CoursePublication.objects.select_for_update()
        .select_related("current_release")
        .filter(course=course)
        .first()
    )
    if publication is None or publication.status != PublicationStatus.ACTIVE:
        raise LearningReleaseInvalid("El curso no tiene publicación activa.")
    return publication


@transaction.atomic
def create_academic_group(
    *,
    actor: object,
    organization: Organization,
    name: str,
    academic_year: int,
    level: str,
    section: str = "",
    description: str = "",
    slug: str | None = None,
) -> AcademicGroup:
    if not can_manage_cohorts(actor, organization):  # type: ignore[arg-type]
        raise LearningPermissionDenied("No puede administrar grupos académicos.")
    group = AcademicGroup(
        organization=organization,
        name=name,
        slug=slugify(slug or f"{name}-{academic_year}")[:100],
        academic_year=academic_year,
        level=level,
        section=section,
        description=description,
        created_by=actor,
    )
    group.full_clean()
    group.save()
    return group


@transaction.atomic
def replace_academic_group_roster(
    *,
    actor: object,
    group: AcademicGroup,
    members: list[dict[str, object]],
) -> AcademicGroup:
    group = AcademicGroup.objects.select_for_update().get(pk=group.pk)
    if not can_manage_cohorts(actor, group.organization):  # type: ignore[arg-type]
        raise LearningPermissionDenied("No puede administrar grupos académicos.")
    requested_roles = {entry["membership_id"]: str(entry["role"]) for entry in members}
    membership_ids = list(requested_roles)
    memberships = list(
        Membership.objects.filter(
            organization=group.organization,
            status=MembershipStatus.ACTIVE,
            pk__in=membership_ids,
        )
    )
    if len(memberships) != len(set(membership_ids)):
        raise LearningPermissionDenied(
            "Una o más personas no son miembros activos de la organización."
        )
    now = timezone.now()
    existing = {
        row.membership_id: row
        for row in AcademicGroupMember.objects.select_for_update().filter(group=group)
    }
    requested = set(membership_ids)
    for membership_id, row in existing.items():
        if (
            membership_id not in requested
            and row.status == AcademicGroupMemberStatus.ACTIVE
        ):
            row.status = AcademicGroupMemberStatus.INACTIVE
            row.ended_at = now
            row.save(update_fields=["status", "ended_at"])
    for membership in memberships:
        role = requested_roles[membership.id]
        row = existing.get(membership.id)
        if row is None:
            AcademicGroupMember.objects.create(
                group=group,
                membership=membership,
                role=role,
                added_by=actor,
            )
        elif row.status != AcademicGroupMemberStatus.ACTIVE:
            row.status = AcademicGroupMemberStatus.ACTIVE
            row.ended_at = None
            row.role = role
            row.save(update_fields=["status", "ended_at", "role"])
        elif row.role != role:
            row.role = role
            row.save(update_fields=["role"])
    return group


def _event(
    *,
    event_type: LearningEventType,
    enrollment: CourseEnrollment,
    assignment: EnrollmentReleaseAssignment,
    actor: object,
    progress: CourseProgress | None = None,
    unit_id: uuid.UUID | None = None,
    node_id: uuid.UUID | None = None,
    external_requirement: ExternalLearningRequirement | None = None,
    occurred_at: datetime | None = None,
) -> LearningEvent:
    event = LearningEvent.objects.create(
        organization=enrollment.organization,
        enrollment=enrollment,
        release_assignment=assignment,
        course_progress=progress,
        unit_id=unit_id,
        node_id=node_id,
        external_requirement=external_requirement,
        event_type=event_type,
        actor=actor,
        occurred_at=occurred_at or timezone.now(),
    )
    domain_types = {
        LearningEventType.ENROLLMENT_CREATED: "learning.enrollment.created.v1",
        LearningEventType.ENROLLMENT_SUSPENDED: "learning.enrollment.suspended.v1",
        LearningEventType.ENROLLMENT_REACTIVATED: "learning.enrollment.reactivated.v1",
        LearningEventType.ENROLLMENT_REVOKED: "learning.enrollment.revoked.v1",
        LearningEventType.COURSE_COMPLETED: "learning.course_progress.completed.v1",
    }
    domain_type = domain_types.get(event_type)
    if domain_type:
        aggregate_id = (
            progress.id
            if event_type == LearningEventType.COURSE_COMPLETED and progress
            else enrollment.id
        )
        aggregate_type = (
            "course_progress"
            if progress and event_type == LearningEventType.COURSE_COMPLETED
            else "enrollment"
        )
        record_domain_event(
            event_type=domain_type,
            organization=enrollment.organization,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            actor=actor,
            payload={
                f"{aggregate_type}_id": str(aggregate_id),
                "membership_id": str(enrollment.membership_id),
                "course_id": str(enrollment.course_id),
                "release_id": str(assignment.release_id),
            },
        )
    return event


@transaction.atomic
def create_cohort(
    *,
    actor: object,
    organization: Organization,
    course: Course,
    release: CourseRelease,
    academic_group: AcademicGroup | None = None,
    name: str,
    slug: str | None = None,
    description: str = "",
    access_starts_at: datetime | None = None,
    access_ends_at: datetime | None = None,
) -> LearningCohort:
    if not can_manage_cohorts(actor, organization):  # type: ignore[arg-type]
        raise LearningPermissionDenied("No puede administrar cohortes.")
    _validate_window(access_starts_at, access_ends_at)
    _active_publication(course)
    _validate_release(organization=organization, course=course, release=release)
    if academic_group and academic_group.organization_id != organization.id:
        raise LearningPermissionDenied("El grupo pertenece a otra organización.")
    cohort = LearningCohort(
        organization=organization,
        course=course,
        release=release,
        academic_group=academic_group,
        name=name,
        slug=slugify(slug or name),
        description=description,
        access_starts_at=access_starts_at,
        access_ends_at=access_ends_at,
        created_by=actor,
        updated_by=actor,
    )
    cohort.full_clean()
    cohort.save()
    return cohort


@transaction.atomic
def update_cohort(
    *,
    actor: object,
    cohort: LearningCohort,
    name: str,
    description: str,
    access_starts_at: datetime | None,
    access_ends_at: datetime | None,
    release: CourseRelease | None = None,
) -> LearningCohort:
    cohort = LearningCohort.objects.select_for_update().get(pk=cohort.pk)
    if not can_manage_cohorts(actor, cohort.organization):  # type: ignore[arg-type]
        raise LearningPermissionDenied("No puede administrar cohortes.")
    if release is not None and release.id != cohort.release_id:
        raise CohortReleaseImmutable("El release de la cohorte es inmutable.")
    _validate_window(access_starts_at, access_ends_at)
    cohort.name = name
    cohort.description = description
    cohort.access_starts_at = access_starts_at
    cohort.access_ends_at = access_ends_at
    cohort.updated_by = actor
    cohort.full_clean()
    cohort.save(
        update_fields=[
            "name",
            "description",
            "access_starts_at",
            "access_ends_at",
            "updated_by",
            "updated_at",
        ]
    )
    return cohort


@transaction.atomic
def archive_cohort(*, actor: object, cohort: LearningCohort) -> LearningCohort:
    cohort = LearningCohort.objects.select_for_update().get(pk=cohort.pk)
    if not can_manage_cohorts(actor, cohort.organization):  # type: ignore[arg-type]
        raise LearningPermissionDenied("No puede administrar cohortes.")
    if cohort.status == CohortStatus.ARCHIVED:
        return cohort
    now = timezone.now()
    cohort.status = CohortStatus.ARCHIVED
    cohort.archived_by = actor
    cohort.archived_at = now
    cohort.updated_by = actor
    cohort.full_clean()
    cohort.save(
        update_fields=[
            "status",
            "archived_by",
            "archived_at",
            "updated_by",
            "updated_at",
        ]
    )
    return cohort


def _create_enrollment_rows(
    *,
    actor: object,
    organization: Organization,
    course: Course,
    membership: Membership,
    release: CourseRelease,
    cohort: LearningCohort | None,
    access_starts_at: datetime | None,
    access_ends_at: datetime | None,
) -> CourseEnrollment:
    historical = CourseEnrollment.objects.filter(
        membership=membership,
        course=course,
        status=EnrollmentStatus.REVOKED,
    ).exists()
    now = timezone.now()
    enrollment = CourseEnrollment(
        organization=organization,
        membership=membership,
        course=course,
        cohort=cohort,
        access_starts_at=access_starts_at,
        access_ends_at=access_ends_at,
        created_by=actor,
        status_changed_by=actor,
        status_changed_at=now,
    )
    enrollment.full_clean(exclude=["current_release_assignment"])
    try:
        enrollment.save()
    except IntegrityError as error:
        raise EnrollmentAlreadyExists("Ya existe una matrícula vigente.") from error
    reason = AssignmentReason.RE_ENROLLMENT if historical else AssignmentReason.INITIAL
    assignment = EnrollmentReleaseAssignment.objects.create(
        enrollment=enrollment,
        release=release,
        sequence=1,
        reason=reason,
        assigned_by=actor,
        assigned_at=now,
    )
    progress = CourseProgress.objects.create(
        release_assignment=assignment,
        total_units=release.unit_count,
        total_required_activities=ExternalLearningRequirement.objects.filter(
            course=course, is_active=True
        ).count(),
    )
    enrollment.current_release_assignment = assignment
    enrollment.save(update_fields=["current_release_assignment"])
    _event(
        event_type=LearningEventType.ENROLLMENT_CREATED,
        enrollment=enrollment,
        assignment=assignment,
        progress=progress,
        actor=actor,
        occurred_at=now,
    )
    _event(
        event_type=LearningEventType.RELEASE_ASSIGNED,
        enrollment=enrollment,
        assignment=assignment,
        progress=progress,
        actor=actor,
        occurred_at=now,
    )
    return enrollment


@transaction.atomic
def enroll_member(
    *,
    actor: object,
    organization: Organization,
    course: Course,
    membership: Membership,
    cohort: LearningCohort | None = None,
    release: CourseRelease | None = None,
    access_starts_at: datetime | None = None,
    access_ends_at: datetime | None = None,
) -> CourseEnrollment:
    if not can_manage_enrollments(actor, organization):  # type: ignore[arg-type]
        raise LearningPermissionDenied("No puede administrar matrículas.")
    membership = (
        Membership.objects.select_for_update()
        .select_related("user")
        .get(pk=membership.pk)
    )
    if (
        membership.organization_id != organization.id
        or membership.status != MembershipStatus.ACTIVE.value
        or not membership.user.is_active
    ):
        raise EnrollmentCohortMismatch(
            "La membresía no está activa en la organización."
        )
    if course.organization_id != organization.id:
        raise EnrollmentCohortMismatch("El curso pertenece a otra organización.")
    publication = _active_publication(course)
    if cohort is not None:
        cohort = (
            LearningCohort.objects.select_for_update()
            .select_related("release__course")
            .get(pk=cohort.pk)
        )
        if cohort.status != CohortStatus.ACTIVE:
            raise CohortArchived("La cohorte está archivada.")
        if (
            cohort.organization_id != organization.id
            or cohort.course_id != course.id
            or (release is not None and release.id != cohort.release_id)
        ):
            raise EnrollmentCohortMismatch("La cohorte no corresponde a la matrícula.")
        release = cohort.release
        access_starts_at = cohort.access_starts_at
        access_ends_at = cohort.access_ends_at
    else:
        release = release or publication.current_release
    _validate_window(access_starts_at, access_ends_at)
    _validate_release(organization=organization, course=course, release=release)
    if (
        CourseEnrollment.objects.filter(
            membership=membership,
            course=course,
        )
        .exclude(status=EnrollmentStatus.REVOKED)
        .exists()
    ):
        raise EnrollmentAlreadyExists("Ya existe una matrícula vigente.")
    return _create_enrollment_rows(
        actor=actor,
        organization=organization,
        course=course,
        membership=membership,
        release=release,
        cohort=cohort,
        access_starts_at=access_starts_at,
        access_ends_at=access_ends_at,
    )


@transaction.atomic
def enroll_cohort_members(
    *,
    actor: object,
    cohort: LearningCohort,
    memberships: Iterable[Membership],
) -> list[CourseEnrollment]:
    rows = list(memberships)
    if not rows or len(rows) > 100:
        raise EnrollmentConflict("El lote debe contener entre 1 y 100 membresías.")
    cohort = (
        LearningCohort.objects.select_for_update()
        .select_related("organization", "course", "release__course")
        .get(pk=cohort.pk)
    )
    results = []
    for membership in rows:
        results.append(
            enroll_member(
                actor=actor,
                organization=cohort.organization,
                course=cohort.course,
                membership=membership,
                cohort=cohort,
            )
        )
    return results


def _locked_enrollment(enrollment: CourseEnrollment) -> CourseEnrollment:
    return (
        CourseEnrollment.objects.select_for_update(of=("self",))
        .select_related(
            "organization",
            "membership__user",
            "course",
            "cohort",
            "current_release_assignment__release__source_revision",
            "current_release_assignment__release__previous_release",
        )
        .get(pk=enrollment.pk)
    )


def _require_enrollment_version(
    enrollment: CourseEnrollment, expected_version: int
) -> None:
    if enrollment.lock_version != expected_version:
        raise EnrollmentConflict("La matrícula cambió en otra operación.")


@transaction.atomic
def suspend_enrollment(
    *, actor: object, enrollment: CourseEnrollment, expected_version: int
) -> CourseEnrollment:
    enrollment = _locked_enrollment(enrollment)
    if not can_manage_enrollments(actor, enrollment.organization):  # type: ignore[arg-type]
        raise LearningPermissionDenied("No puede suspender matrículas.")
    _require_enrollment_version(enrollment, expected_version)
    if enrollment.status != EnrollmentStatus.ACTIVE:
        raise EnrollmentTransitionInvalid(
            "Sólo una matrícula activa puede suspenderse."
        )
    now = timezone.now()
    enrollment.status = EnrollmentStatus.SUSPENDED
    enrollment.suspended_at = now
    enrollment.status_changed_by = actor
    enrollment.status_changed_at = now
    enrollment.lock_version += 1
    enrollment.full_clean()
    enrollment.save()
    assignment = enrollment.current_release_assignment
    if assignment:
        _event(
            event_type=LearningEventType.ENROLLMENT_SUSPENDED,
            enrollment=enrollment,
            assignment=assignment,
            progress=assignment.progress,
            actor=actor,
            occurred_at=now,
        )
    return enrollment


@transaction.atomic
def reactivate_enrollment(
    *, actor: object, enrollment: CourseEnrollment, expected_version: int
) -> CourseEnrollment:
    enrollment = _locked_enrollment(enrollment)
    if not can_manage_enrollments(actor, enrollment.organization):  # type: ignore[arg-type]
        raise LearningPermissionDenied("No puede reactivar matrículas.")
    _require_enrollment_version(enrollment, expected_version)
    if enrollment.status != EnrollmentStatus.SUSPENDED:
        raise EnrollmentTransitionInvalid(
            "Sólo una matrícula suspendida puede reactivarse."
        )
    if enrollment.membership.status != MembershipStatus.ACTIVE:
        raise EnrollmentTransitionInvalid("La membresía institucional no está activa.")
    publication = _active_publication(enrollment.course)
    assignment = enrollment.current_release_assignment
    if assignment is None or assignment.ended_at is not None:
        raise LearningReleaseInvalid("La asignación vigente es inválida.")
    _validate_release(
        organization=enrollment.organization,
        course=enrollment.course,
        release=assignment.release,
    )
    if publication.status != PublicationStatus.ACTIVE:
        raise LearningReleaseInvalid("La publicación no está activa.")
    now = timezone.now()
    enrollment.status = EnrollmentStatus.ACTIVE
    enrollment.suspended_at = None
    enrollment.status_changed_by = actor
    enrollment.status_changed_at = now
    enrollment.lock_version += 1
    enrollment.full_clean()
    enrollment.save()
    _event(
        event_type=LearningEventType.ENROLLMENT_REACTIVATED,
        enrollment=enrollment,
        assignment=assignment,
        progress=assignment.progress,
        actor=actor,
        occurred_at=now,
    )
    return enrollment


@transaction.atomic
def revoke_enrollment(
    *, actor: object, enrollment: CourseEnrollment, expected_version: int
) -> CourseEnrollment:
    enrollment = _locked_enrollment(enrollment)
    if not can_manage_enrollments(actor, enrollment.organization):  # type: ignore[arg-type]
        raise LearningPermissionDenied("No puede revocar matrículas.")
    _require_enrollment_version(enrollment, expected_version)
    if enrollment.status == EnrollmentStatus.REVOKED:
        raise EnrollmentTransitionInvalid("La revocación es terminal.")
    now = timezone.now()
    assignment = enrollment.current_release_assignment
    if assignment is None:
        raise LearningReleaseInvalid("La matrícula no tiene release asignado.")
    assignment = EnrollmentReleaseAssignment.objects.select_for_update().get(
        pk=assignment.pk
    )
    assignment.ended_at = now
    assignment.ended_by = actor
    assignment.save(update_fields=["ended_at", "ended_by"])
    enrollment.status = EnrollmentStatus.REVOKED
    enrollment.suspended_at = None
    enrollment.revoked_at = now
    enrollment.status_changed_by = actor
    enrollment.status_changed_at = now
    enrollment.lock_version += 1
    enrollment.full_clean()
    enrollment.save()
    _event(
        event_type=LearningEventType.ENROLLMENT_REVOKED,
        enrollment=enrollment,
        assignment=assignment,
        progress=assignment.progress,
        actor=actor,
        occurred_at=now,
    )
    return enrollment


@transaction.atomic
def upgrade_enrollment_release(
    *,
    actor: object,
    enrollment: CourseEnrollment,
    expected_enrollment_version: int,
    target_release: CourseRelease,
) -> CourseEnrollment:
    enrollment = _locked_enrollment(enrollment)
    if not can_manage_enrollments(actor, enrollment.organization):  # type: ignore[arg-type]
        raise LearningPermissionDenied("No puede actualizar releases.")
    _require_enrollment_version(enrollment, expected_enrollment_version)
    if enrollment.status == EnrollmentStatus.REVOKED or enrollment.cohort_id:
        raise EnrollmentReleaseUpgradeInvalid("Esta matrícula no admite upgrade.")
    _active_publication(enrollment.course)
    _validate_release(
        organization=enrollment.organization,
        course=enrollment.course,
        release=target_release,
    )
    current = enrollment.current_release_assignment
    if current is None or current.ended_at is not None:
        raise EnrollmentReleaseUpgradeInvalid("No existe una asignación activa.")
    if target_release.number <= current.release.number:
        raise EnrollmentReleaseUpgradeInvalid(
            "El release objetivo debe ser posterior al actual."
        )
    now = timezone.now()
    current = EnrollmentReleaseAssignment.objects.select_for_update().get(pk=current.pk)
    current.ended_at = now
    current.ended_by = actor
    current.save(update_fields=["ended_at", "ended_by"])
    assignment = EnrollmentReleaseAssignment.objects.create(
        enrollment=enrollment,
        release=target_release,
        sequence=current.sequence + 1,
        reason=AssignmentReason.MANUAL_UPGRADE,
        previous_assignment=current,
        assigned_by=actor,
        assigned_at=now,
    )
    progress = CourseProgress.objects.create(
        release_assignment=assignment,
        total_units=target_release.unit_count,
        total_required_activities=ExternalLearningRequirement.objects.filter(
            course=enrollment.course, is_active=True
        ).count(),
    )
    enrollment.current_release_assignment = assignment
    enrollment.lock_version += 1
    enrollment.save(update_fields=["current_release_assignment", "lock_version"])
    _event(
        event_type=LearningEventType.RELEASE_UPGRADED,
        enrollment=enrollment,
        assignment=assignment,
        progress=progress,
        actor=actor,
        occurred_at=now,
    )
    return enrollment


def _locked_student_state(
    *, actor: object, enrollment: CourseEnrollment
) -> tuple[CourseEnrollment, EnrollmentReleaseAssignment, CourseProgress]:
    enrollment = _locked_enrollment(enrollment)
    access = require_learning_access(actor=actor, enrollment=enrollment)
    progress = CourseProgress.objects.select_for_update().get(
        release_assignment=access.assignment
    )
    return enrollment, access.assignment, progress


def _recalculate_progress(progress: CourseProgress, now: datetime) -> None:
    completed = UnitProgress.objects.filter(
        course_progress=progress,
        status=UnitProgressStatus.COMPLETED,
    ).count()
    progress.completed_units = completed
    completed_requirements = ExternalRequirementCompletion.objects.filter(
        course_progress=progress,
        requirement__is_active=True,
    ).count()
    total_requirements = ExternalLearningRequirement.objects.filter(
        course=progress.release_assignment.enrollment.course,
        is_active=True,
    ).count()
    progress.completed_required_activities = completed_requirements
    progress.total_required_activities = total_requirements
    completed_total = completed + completed_requirements
    required_total = progress.total_units + total_requirements
    progress.percent_basis_points = (
        10_000
        if completed_total == required_total
        else completed_total * 10_000 // required_total
    )
    if completed_total == required_total:
        progress.status = ProgressStatus.COMPLETED
        progress.completed_at = progress.completed_at or now
    elif completed_total == 0 and progress.started_at is None:
        progress.status = ProgressStatus.NOT_STARTED
        progress.completed_at = None
    else:
        progress.status = ProgressStatus.IN_PROGRESS
        progress.completed_at = None
    progress.last_activity_at = now


@transaction.atomic
def register_external_requirement(
    *,
    actor: object,
    organization: Organization,
    course: Course,
    source_type: str,
    source_id: uuid.UUID,
    title: str,
) -> ExternalLearningRequirement:
    """Register one active course requirement without importing its source domain."""
    requirement, created = ExternalLearningRequirement.objects.get_or_create(
        source_type=source_type,
        source_id=source_id,
        defaults={
            "organization": organization,
            "course": course,
            "title": title,
            "created_by": actor,
        },
    )
    if not created:
        if requirement.course_id != course.id or not requirement.is_active:
            raise LearningProgressConflict(
                "El requisito externo ya existe con otro estado."
            )
        return requirement
    requirement.full_clean()
    requirement.save()
    now = timezone.now()
    progresses = CourseProgress.objects.select_for_update().filter(
        release_assignment__enrollment__course=course,
        release_assignment__enrollment__current_release_assignment=models.F(
            "release_assignment"
        ),
    )
    for progress in progresses:
        was_completed = progress.status == ProgressStatus.COMPLETED
        _recalculate_progress(progress, now)
        progress.lock_version += 1
        progress.full_clean()
        progress.save()
        if was_completed and progress.status != ProgressStatus.COMPLETED:
            enrollment = progress.release_assignment.enrollment
            _event(
                event_type=LearningEventType.COURSE_REOPENED,
                enrollment=enrollment,
                assignment=progress.release_assignment,
                progress=progress,
                external_requirement=requirement,
                actor=actor,
                occurred_at=now,
            )
    return requirement


@transaction.atomic
def deactivate_external_requirement(
    *, actor: object, source_type: str, source_id: uuid.UUID
) -> None:
    requirement = (
        ExternalLearningRequirement.objects.select_for_update()
        .filter(source_type=source_type, source_id=source_id, is_active=True)
        .first()
    )
    if requirement is None:
        return
    now = timezone.now()
    requirement.is_active = False
    requirement.deactivated_by = actor
    requirement.deactivated_at = now
    requirement.full_clean()
    requirement.save(update_fields=("is_active", "deactivated_by", "deactivated_at"))
    progresses = CourseProgress.objects.select_for_update().filter(
        release_assignment__enrollment__course=requirement.course,
        release_assignment__enrollment__current_release_assignment=models.F(
            "release_assignment"
        ),
    )
    for progress in progresses:
        _recalculate_progress(progress, now)
        progress.lock_version += 1
        progress.full_clean()
        progress.save()


@transaction.atomic
def complete_external_requirement(
    *,
    actor: object,
    source_type: str,
    source_id: uuid.UUID,
    completed_at: datetime,
    evidence: dict[str, object],
) -> bool:
    requirement = (
        ExternalLearningRequirement.objects.select_related("organization", "course")
        .filter(source_type=source_type, source_id=source_id, is_active=True)
        .first()
    )
    if requirement is None:
        return False
    from .contracts import effective_course_enrollment

    enrollment = effective_course_enrollment(
        actor=actor,
        organization=requirement.organization,
        course=requirement.course,
        at=completed_at,
    )
    if enrollment is None or enrollment.current_release_assignment_id is None:
        return False
    progress = CourseProgress.objects.select_for_update().get(
        release_assignment=enrollment.current_release_assignment
    )
    _completion, created = ExternalRequirementCompletion.objects.get_or_create(
        requirement=requirement,
        course_progress=progress,
        defaults={
            "completed_by": actor,
            "completed_at": completed_at,
            "evidence": evidence,
        },
    )
    if not created:
        return False
    was_completed = progress.status == ProgressStatus.COMPLETED
    started = progress.started_at is None
    now = completed_at
    progress.started_at = progress.started_at or now
    _recalculate_progress(progress, now)
    progress.lock_version += 1
    progress.full_clean()
    progress.save()
    if started:
        _event(
            event_type=LearningEventType.COURSE_STARTED,
            enrollment=enrollment,
            assignment=enrollment.current_release_assignment,
            progress=progress,
            external_requirement=requirement,
            actor=actor,
            occurred_at=now,
        )
    _event(
        event_type=LearningEventType.REQUIREMENT_COMPLETED,
        enrollment=enrollment,
        assignment=enrollment.current_release_assignment,
        progress=progress,
        external_requirement=requirement,
        actor=actor,
        occurred_at=now,
    )
    if progress.status == ProgressStatus.COMPLETED and not was_completed:
        _event(
            event_type=LearningEventType.COURSE_COMPLETED,
            enrollment=enrollment,
            assignment=enrollment.current_release_assignment,
            progress=progress,
            external_requirement=requirement,
            actor=actor,
            occurred_at=now,
        )
    return True


@transaction.atomic
def open_unit(
    *, actor: object, enrollment: CourseEnrollment, unit_id: uuid.UUID
) -> CourseProgress:
    enrollment, assignment, progress = _locked_student_state(
        actor=actor, enrollment=enrollment
    )
    snapshot_unit(assignment.release, unit_id)
    now = timezone.now()
    unit_progress, created = UnitProgress.objects.get_or_create(
        course_progress=progress,
        unit_id=unit_id,
        defaults={
            "first_opened_at": now,
            "last_opened_at": now,
        },
    )
    if not created:
        unit_progress.last_opened_at = now
        unit_progress.save(update_fields=["last_opened_at", "updated_at"])
    started = progress.started_at is None
    if started:
        progress.started_at = now
        progress.status = ProgressStatus.IN_PROGRESS
        progress.lock_version += 1
    progress.last_unit_id = unit_id
    progress.last_activity_at = now
    progress.save()
    if created:
        _event(
            event_type=LearningEventType.UNIT_OPENED,
            enrollment=enrollment,
            assignment=assignment,
            progress=progress,
            unit_id=unit_id,
            actor=actor,
            occurred_at=now,
        )
    if started:
        _event(
            event_type=LearningEventType.COURSE_STARTED,
            enrollment=enrollment,
            assignment=assignment,
            progress=progress,
            unit_id=unit_id,
            actor=actor,
            occurred_at=now,
        )
    return progress


@transaction.atomic
def update_learning_position(
    *,
    actor: object,
    enrollment: CourseEnrollment,
    unit_id: uuid.UUID,
    node_id: uuid.UUID,
) -> CourseProgress:
    enrollment, assignment, progress = _locked_student_state(
        actor=actor, enrollment=enrollment
    )
    validate_snapshot_position(assignment.release, unit_id, node_id)
    unit_progress = (
        UnitProgress.objects.select_for_update()
        .filter(course_progress=progress, unit_id=unit_id)
        .first()
    )
    if unit_progress is None:
        raise LearningPositionInvalid("Abra la unidad antes de guardar la posición.")
    now = timezone.now()
    unit_progress.last_node_id = node_id
    unit_progress.last_opened_at = now
    unit_progress.save(update_fields=["last_node_id", "last_opened_at", "updated_at"])
    progress.last_unit_id = unit_id
    progress.last_node_id = node_id
    progress.last_activity_at = now
    progress.save(
        update_fields=[
            "last_unit_id",
            "last_node_id",
            "last_activity_at",
            "updated_at",
        ]
    )
    return progress


def _require_progress_version(progress: CourseProgress, expected_version: int) -> None:
    if progress.lock_version != expected_version:
        raise LearningProgressConflict("El progreso cambió en otra operación.")


@transaction.atomic
def complete_unit(
    *,
    actor: object,
    enrollment: CourseEnrollment,
    unit_id: uuid.UUID,
    expected_progress_version: int,
) -> tuple[CourseProgress, bool]:
    enrollment, assignment, progress = _locked_student_state(
        actor=actor, enrollment=enrollment
    )
    _require_progress_version(progress, expected_progress_version)
    snapshot_unit(assignment.release, unit_id)
    now = timezone.now()
    unit_progress = (
        UnitProgress.objects.select_for_update()
        .filter(course_progress=progress, unit_id=unit_id)
        .first()
    )
    if unit_progress and unit_progress.status == UnitProgressStatus.COMPLETED:
        return progress, True
    started = progress.started_at is None
    if unit_progress is None:
        unit_progress = UnitProgress.objects.create(
            course_progress=progress,
            unit_id=unit_id,
            status=UnitProgressStatus.COMPLETED,
            first_opened_at=now,
            last_opened_at=now,
            completed_at=now,
        )
        _event(
            event_type=LearningEventType.UNIT_OPENED,
            enrollment=enrollment,
            assignment=assignment,
            progress=progress,
            unit_id=unit_id,
            actor=actor,
            occurred_at=now,
        )
    else:
        unit_progress.status = UnitProgressStatus.COMPLETED
        unit_progress.completed_at = now
        unit_progress.last_opened_at = now
        unit_progress.save()
    was_completed = progress.status == ProgressStatus.COMPLETED
    progress.started_at = progress.started_at or now
    progress.last_unit_id = unit_id
    _recalculate_progress(progress, now)
    progress.lock_version += 1
    progress.full_clean()
    progress.save()
    if started:
        _event(
            event_type=LearningEventType.COURSE_STARTED,
            enrollment=enrollment,
            assignment=assignment,
            progress=progress,
            unit_id=unit_id,
            actor=actor,
            occurred_at=now,
        )
    _event(
        event_type=LearningEventType.UNIT_COMPLETED,
        enrollment=enrollment,
        assignment=assignment,
        progress=progress,
        unit_id=unit_id,
        actor=actor,
        occurred_at=now,
    )
    if progress.status == ProgressStatus.COMPLETED and not was_completed:
        _event(
            event_type=LearningEventType.COURSE_COMPLETED,
            enrollment=enrollment,
            assignment=assignment,
            progress=progress,
            unit_id=unit_id,
            actor=actor,
            occurred_at=now,
        )
    return progress, False


@transaction.atomic
def reopen_unit(
    *,
    actor: object,
    enrollment: CourseEnrollment,
    unit_id: uuid.UUID,
    expected_progress_version: int,
) -> CourseProgress:
    enrollment, assignment, progress = _locked_student_state(
        actor=actor, enrollment=enrollment
    )
    _require_progress_version(progress, expected_progress_version)
    snapshot_unit(assignment.release, unit_id)
    unit_progress = (
        UnitProgress.objects.select_for_update()
        .filter(
            course_progress=progress,
            unit_id=unit_id,
            status=UnitProgressStatus.COMPLETED,
        )
        .first()
    )
    if unit_progress is None:
        raise LearningUnitNotCompleted("La unidad no está completada.")
    now = timezone.now()
    course_was_completed = progress.status == ProgressStatus.COMPLETED
    unit_progress.status = UnitProgressStatus.IN_PROGRESS
    unit_progress.completed_at = None
    unit_progress.save()
    progress.last_unit_id = unit_id
    _recalculate_progress(progress, now)
    progress.lock_version += 1
    progress.full_clean()
    progress.save()
    _event(
        event_type=LearningEventType.UNIT_REOPENED,
        enrollment=enrollment,
        assignment=assignment,
        progress=progress,
        unit_id=unit_id,
        actor=actor,
        occurred_at=now,
    )
    if course_was_completed:
        _event(
            event_type=LearningEventType.COURSE_REOPENED,
            enrollment=enrollment,
            assignment=assignment,
            progress=progress,
            unit_id=unit_id,
            actor=actor,
            occurred_at=now,
        )
    return progress


def resolve_resume_target(
    progress: CourseProgress,
) -> tuple[uuid.UUID, uuid.UUID | None]:
    release = progress.release_assignment.release
    unit_ids = snapshot_unit_ids(release)
    if progress.last_unit_id in unit_ids:
        node_id = progress.last_node_id
        if node_id and node_id not in snapshot_node_ids(release, progress.last_unit_id):
            node_id = None
        return progress.last_unit_id, node_id
    in_progress = (
        UnitProgress.objects.filter(
            course_progress=progress,
            status=UnitProgressStatus.IN_PROGRESS,
            unit_id__in=unit_ids,
        )
        .order_by("first_opened_at")
        .first()
    )
    if in_progress:
        return in_progress.unit_id, in_progress.last_node_id
    completed = set(
        UnitProgress.objects.filter(
            course_progress=progress,
            status=UnitProgressStatus.COMPLETED,
        ).values_list("unit_id", flat=True)
    )
    return next(
        (unit_id for unit_id in unit_ids if unit_id not in completed), unit_ids[0]
    ), None
