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
from domain.organizations.choices import MembershipStatus, RoleCode
from domain.organizations.models import Membership, Organization
from domain.organizations.policies import active_roles
from domain.publishing.choices import PublicationStatus
from domain.publishing.integrity import verify_release
from domain.publishing.models import CoursePublication, CourseRelease
from domain.publishing.snapshots import release_outline

from .access import require_learning_access
from .choices import (
    AcademicGroupMemberStatus,
    AcademicGroupRole,
    ActivityProgressSource,
    ActivityProgressStatus,
    AssignmentReason,
    CohortRosterMode,
    CohortStatus,
    EnrollmentCohortSource,
    EnrollmentStatus,
    EnrollmentWindowMode,
    LearningEventType,
    ProgressStatus,
    RosterEventType,
    UnitProgressStatus,
)
from .exceptions import (
    AcademicPeriodRequired,
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
    AcademicPeriod,
    ActivityProgress,
    ActivityProgressEvent,
    CohortStaffAssignment,
    CourseEnrollment,
    CourseGroupActivity,
    CourseProgress,
    EnrollmentCohortAssignment,
    EnrollmentReleaseAssignment,
    ExternalLearningRequirement,
    ExternalRequirementCompletion,
    LearningCohort,
    LearningEvent,
    RosterEvent,
    UnitProgress,
)
from .policies import (
    can_manage_cohorts,
    can_manage_course_group,
    can_manage_enrollment,
    can_manage_enrollments,
)
from .snapshots import (
    snapshot_node_ids,
    snapshot_unit,
    snapshot_unit_ids,
    validate_snapshot_position,
)


def _validate_window(starts_at: datetime | None, ends_at: datetime | None) -> None:
    if starts_at and ends_at and starts_at >= ends_at:
        raise AccessWindowInvalid("La fecha inicial debe ser anterior a la final.")


def _require_version(current: int, expected: int, noun: str) -> None:
    if current != expected:
        raise EnrollmentConflict(f"{noun} cambió en otra operación.")


def _roster_event(
    *,
    actor: object,
    organization: Organization,
    event_type: RosterEventType,
    academic_group: AcademicGroup | None = None,
    cohort: LearningCohort | None = None,
    expected_cohort_version: int | None = None,
    details: dict[str, object] | None = None,
) -> RosterEvent:
    return RosterEvent.objects.create(
        organization=organization,
        academic_group=academic_group,
        cohort=cohort,
        event_type=event_type,
        actor=actor,
        occurred_at=timezone.now(),
        details=details or {},
    )


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
def create_academic_period(
    *,
    actor: object,
    organization: Organization,
    name: str,
    slug: str,
    period_type: str,
    starts_on: object,
    ends_on: object,
    parent: AcademicPeriod | None = None,
) -> AcademicPeriod:
    if not can_manage_cohorts(actor, organization):  # type: ignore[arg-type]
        raise LearningPermissionDenied("No puede administrar periodos académicos.")
    if parent is not None and parent.organization_id != organization.id:
        raise LearningPermissionDenied(
            "El periodo padre pertenece a otra organización."
        )
    period = AcademicPeriod(
        organization=organization,
        parent=parent,
        name=name,
        slug=slugify(slug),
        period_type=period_type,
        starts_on=starts_on,
        ends_on=ends_on,
        created_by=actor,
        updated_by=actor,
    )
    period.full_clean()
    period.save()
    return period


def _materialize_course_group_activities(cohort: LearningCohort) -> None:
    outline = release_outline(cohort.release.snapshot)
    rows: list[CourseGroupActivity] = []
    for module in outline:
        for activity in module["activities"]:
            rows.append(
                CourseGroupActivity(
                    course_group=cohort,
                    academic_period=cohort.academic_period,
                    course_release=cohort.release,
                    source_activity_id=activity["id"],
                    source_module_id=module["id"],
                    activity_type=activity["type"],
                    module_title=module["title"],
                    title=activity["title"],
                    summary=activity["summary"],
                    module_position=module["position"],
                    position=activity["position"],
                    required=activity["required"],
                    completion_policy=activity["completion_policy"],
                    availability_rules=activity["availability_rules"],
                    binding_snapshot=activity["binding"],
                    release_snapshot_digest=cohort.release.snapshot_digest,
                    migration_review_required=cohort.migration_review_required,
                )
            )
    for row in rows:
        row.full_clean()
    CourseGroupActivity.objects.bulk_create(rows)


def _initialize_activity_progress(
    *, progress: CourseProgress, cohort: LearningCohort, actor: object, now: datetime
) -> None:
    previous_by_source_id = {
        row.group_activity.source_activity_id: row
        for row in ActivityProgress.objects.filter(course_progress=progress)
        .select_related("group_activity")
        .order_by("state_changed_at", "id")
    }
    existing_activity_ids = set(
        ActivityProgress.objects.filter(
            course_progress=progress,
            group_activity__course_group=cohort,
        ).values_list("group_activity_id", flat=True)
    )
    for group_activity in cohort.activity_instances.exclude(
        id__in=existing_activity_ids
    ):
        previous = previous_by_source_id.get(group_activity.source_activity_id)
        status = (
            previous.status
            if previous is not None
            else (
                ActivityProgressStatus.LOCKED
                if group_activity.availability_rules
                else ActivityProgressStatus.AVAILABLE
            )
        )
        evidence = {
            **(previous.evidence if previous is not None else {}),
            "initialized_from_release": cohort.release.snapshot_digest,
            **(
                {"continued_from_activity_progress_id": str(previous.id)}
                if previous is not None
                else {}
            ),
        }
        activity_progress = ActivityProgress.objects.create(
            course_progress=progress,
            group_activity=group_activity,
            status=status,
            evidence=evidence,
            source=(
                previous.source
                if previous is not None
                else ActivityProgressSource.MANUAL
            ),
            policy_version=(previous.policy_version if previous is not None else 1),
            started_at=(previous.started_at if previous is not None else None),
            completed_at=(previous.completed_at if previous is not None else None),
            state_changed_at=now,
            state_changed_by=actor,
        )
        ActivityProgressEvent.objects.create(
            activity_progress=activity_progress,
            previous_status="",
            new_status=status,
            source=activity_progress.source,
            policy_version=activity_progress.policy_version,
            evidence={
                "initialized": True,
                **(
                    {"continued_from_activity_progress_id": str(previous.id)}
                    if previous is not None
                    else {}
                ),
            },
            actor=actor,
            occurred_at=now,
        )
    _refresh_activity_availability(
        progress=progress, actor=actor, now=now, cohort=cohort
    )


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
    expected_group_version: int,
) -> AcademicGroup:
    group = AcademicGroup.objects.select_for_update().get(pk=group.pk)
    if not can_manage_cohorts(actor, group.organization):  # type: ignore[arg-type]
        raise LearningPermissionDenied("No puede administrar grupos académicos.")
    _require_version(group.lock_version, expected_group_version, "El grupo académico")
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
    group.lock_version += 1
    group.save(update_fields=["lock_version", "updated_at"])
    _roster_event(
        actor=actor,
        organization=group.organization,
        academic_group=group,
        event_type=RosterEventType.ACADEMIC_GROUP_ROSTER_REPLACED,
        details={"member_count": len(members), "group_version": group.lock_version},
    )
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
    academic_period: AcademicPeriod | None = None,
    migration_review_required: bool = False,
    academic_group: AcademicGroup | None = None,
    name: str,
    slug: str | None = None,
    description: str = "",
    access_starts_at: datetime | None = None,
    access_ends_at: datetime | None = None,
    roster_mode: str | None = None,
    staff: Iterable[dict[str, object]] = (),
) -> LearningCohort:
    if not can_manage_cohorts(actor, organization):  # type: ignore[arg-type]
        raise LearningPermissionDenied("No puede administrar cohortes.")
    _validate_window(access_starts_at, access_ends_at)
    _active_publication(course)
    _validate_release(organization=organization, course=course, release=release)
    if academic_group and academic_group.organization_id != organization.id:
        raise LearningPermissionDenied("El grupo pertenece a otra organización.")
    if academic_period is None and not migration_review_required:
        raise AcademicPeriodRequired(
            "Todo grupo de curso nuevo exige un periodo académico."
        )
    if academic_period is not None and migration_review_required:
        raise AcademicPeriodRequired(
            "La revisión de migración sólo aplica a grupos heredados sin periodo."
        )
    if academic_period and academic_period.organization_id != organization.id:
        raise LearningPermissionDenied("El periodo pertenece a otra organización.")
    resolved_roster_mode = roster_mode or (
        CohortRosterMode.SYNCED if academic_group else CohortRosterMode.MANUAL
    )
    cohort = LearningCohort(
        organization=organization,
        course=course,
        release=release,
        academic_period=academic_period,
        migration_review_required=migration_review_required,
        academic_group=academic_group,
        name=name,
        slug=slugify(slug or name),
        description=description,
        roster_mode=resolved_roster_mode,
        access_starts_at=access_starts_at,
        access_ends_at=access_ends_at,
        created_by=actor,
        updated_by=actor,
    )
    cohort.full_clean()
    cohort.save()
    _materialize_course_group_activities(cohort)
    replace_cohort_staff(
        actor=actor,
        cohort=cohort,
        staff=list(staff),
        expected_cohort_version=cohort.lock_version,
        emit_event=False,
    )
    cohort.refresh_from_db()
    _roster_event(
        actor=actor,
        organization=organization,
        cohort=cohort,
        academic_group=academic_group,
        event_type=RosterEventType.COURSE_GROUP_CREATED,
        details={
            "roster_mode": resolved_roster_mode,
            "staff_count": CohortStaffAssignment.objects.filter(
                cohort=cohort, ended_at__isnull=True
            ).count(),
        },
    )
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
    expected_cohort_version: int,
    release: CourseRelease | None = None,
) -> LearningCohort:
    cohort = LearningCohort.objects.select_for_update().get(pk=cohort.pk)
    if not can_manage_course_group(actor, cohort):  # type: ignore[arg-type]
        raise LearningPermissionDenied("No puede administrar este grupo de curso.")
    _require_version(cohort.lock_version, expected_cohort_version, "El grupo de curso")
    if release is not None and release.id != cohort.release_id:
        raise CohortReleaseImmutable("El release de la cohorte es inmutable.")
    _validate_window(access_starts_at, access_ends_at)
    cohort.name = name
    cohort.description = description
    cohort.access_starts_at = access_starts_at
    cohort.access_ends_at = access_ends_at
    cohort.updated_by = actor
    cohort.lock_version += 1
    cohort.full_clean()
    cohort.save(
        update_fields=[
            "name",
            "description",
            "access_starts_at",
            "access_ends_at",
            "updated_by",
            "updated_at",
            "lock_version",
        ]
    )
    return cohort


@transaction.atomic
def archive_cohort(
    *, actor: object, cohort: LearningCohort, expected_cohort_version: int
) -> LearningCohort:
    cohort = LearningCohort.objects.select_for_update().get(pk=cohort.pk)
    if not can_manage_cohorts(actor, cohort.organization):  # type: ignore[arg-type]
        raise LearningPermissionDenied("No puede archivar grupos de curso.")
    _require_version(cohort.lock_version, expected_cohort_version, "El grupo de curso")
    if cohort.status == CohortStatus.ARCHIVED:
        return cohort
    now = timezone.now()
    cohort.status = CohortStatus.ARCHIVED
    cohort.archived_by = actor
    cohort.archived_at = now
    cohort.updated_by = actor
    cohort.lock_version += 1
    cohort.full_clean()
    cohort.save(
        update_fields=[
            "status",
            "archived_by",
            "archived_at",
            "updated_by",
            "updated_at",
            "lock_version",
        ]
    )
    return cohort


@transaction.atomic
def replace_cohort_staff(
    *,
    actor: object,
    cohort: LearningCohort,
    staff: list[dict[str, object]],
    expected_cohort_version: int,
    emit_event: bool = True,
) -> LearningCohort:
    """Replace staff by closing history rows instead of mutating their role."""

    cohort = LearningCohort.objects.select_for_update().get(pk=cohort.pk)
    if not can_manage_course_group(actor, cohort):  # type: ignore[arg-type]
        raise LearningPermissionDenied("No puede administrar docentes de este grupo.")
    _require_version(cohort.lock_version, expected_cohort_version, "El grupo de curso")
    requested = {row["membership_id"]: str(row["role"]) for row in staff}
    if len(requested) != len(staff):
        raise EnrollmentConflict("No repitas docentes en el grupo de curso.")
    memberships = list(
        Membership.objects.select_for_update()
        .filter(
            organization=cohort.organization,
            status=MembershipStatus.ACTIVE,
            pk__in=requested,
        )
        .select_related("user")
    )
    if len(memberships) != len(requested) or any(
        not membership.user.is_active for membership in memberships
    ):
        raise LearningPermissionDenied(
            "Cada docente debe ser una membresía activa de la organización."
        )
    if any(
        RoleCode.INSTRUCTOR not in active_roles(membership)
        for membership in memberships
    ):
        raise LearningPermissionDenied(
            "Cada integrante del equipo docente debe tener el rol institucional docente."
        )
    now = timezone.now()
    existing = {
        row.membership_id: row
        for row in CohortStaffAssignment.objects.select_for_update().filter(
            cohort=cohort, ended_at__isnull=True
        )
    }
    changed = False
    for membership_id, row in existing.items():
        if membership_id not in requested or row.role != requested[membership_id]:
            row.ended_at = now
            row.ended_by = actor
            row.save(update_fields=["ended_at", "ended_by"])
            changed = True
    for membership in memberships:
        existing_row = existing.get(membership.id)
        if existing_row is None or existing_row.role != requested[membership.id]:
            CohortStaffAssignment.objects.create(
                cohort=cohort,
                membership=membership,
                role=requested[membership.id],
                started_by=actor,
                started_at=now,
            )
            changed = True
    if not changed:
        return cohort
    cohort.lock_version += 1
    cohort.updated_by = actor
    cohort.save(update_fields=["lock_version", "updated_by", "updated_at"])
    if emit_event:
        _roster_event(
            actor=actor,
            organization=cohort.organization,
            cohort=cohort,
            event_type=RosterEventType.STAFF_ASSIGNED,
            details={
                "staff_count": len(requested),
                "course_group_version": cohort.lock_version,
            },
        )
    return cohort


def _active_academic_group_learners(group: AcademicGroup) -> list[Membership]:
    return list(
        Membership.objects.filter(
            academic_groups__group=group,
            academic_groups__role=AcademicGroupRole.LEARNER,
            academic_groups__status=AcademicGroupMemberStatus.ACTIVE,
            status=MembershipStatus.ACTIVE,
            user__is_active=True,
        )
        .select_related("user")
        .order_by("id")
    )


def preview_cohort_roster_sync(
    *,
    actor: object,
    cohort: LearningCohort,
    expected_cohort_version: int,
    expected_academic_group_version: int,
) -> dict[str, object]:
    """Return a deterministic plan. This function intentionally never writes."""

    cohort = LearningCohort.objects.select_related("academic_group").get(pk=cohort.pk)
    if not can_manage_course_group(actor, cohort):  # type: ignore[arg-type]
        raise LearningPermissionDenied("No puede sincronizar este grupo de curso.")
    if cohort.academic_group is None or cohort.roster_mode != CohortRosterMode.SYNCED:
        raise EnrollmentConflict("El grupo de curso no usa un padrón sincronizado.")
    _require_version(cohort.lock_version, expected_cohort_version, "El grupo de curso")
    group = cohort.academic_group
    _require_version(
        group.lock_version,
        expected_academic_group_version,
        "El grupo académico",
    )
    learners = _active_academic_group_learners(group)
    desired_ids = {membership.id for membership in learners}
    enrollments = {
        enrollment.membership_id: enrollment
        for enrollment in CourseEnrollment.objects.filter(
            organization=cohort.organization, course=cohort.course
        )
        .exclude(status=EnrollmentStatus.REVOKED)
        .select_related("current_release_assignment")
    }
    active_assignments = {
        assignment.enrollment_id: assignment
        for assignment in EnrollmentCohortAssignment.objects.filter(
            enrollment__organization=cohort.organization,
            enrollment__course=cohort.course,
            ended_at__isnull=True,
        ).select_related("enrollment__current_release_assignment")
    }
    target_assignments = {
        assignment.enrollment.membership_id: assignment
        for assignment in active_assignments.values()
        if assignment.cohort_id == cohort.id
    }
    creates: list[str] = []
    assigns: list[str] = []
    transfers: list[str] = []
    reactivations: list[str] = []
    conflicts: list[str] = []
    unchanged: list[str] = []
    for membership in learners:
        enrollment = enrollments.get(membership.id)
        if enrollment is None:
            creates.append(str(membership.id))
            continue
        assignment = active_assignments.get(enrollment.id)
        if assignment is not None and assignment.cohort_id == cohort.id:
            if enrollment.status == EnrollmentStatus.SUSPENDED and (
                enrollment.access_provenance
                == EnrollmentCohortSource.ACADEMIC_GROUP_SYNC
            ):
                reactivations.append(str(membership.id))
            else:
                unchanged.append(str(membership.id))
            continue
        current_release = enrollment.current_release_assignment
        if current_release is None or current_release.release_id != cohort.release_id:
            conflicts.append(str(membership.id))
        elif assignment is None:
            assigns.append(str(membership.id))
        else:
            transfers.append(str(membership.id))
    suspensions: list[str] = []
    unassignments: list[str] = []
    for membership_id, assignment in target_assignments.items():
        if membership_id in desired_ids:
            continue
        if (
            assignment.enrollment.access_provenance
            == EnrollmentCohortSource.ACADEMIC_GROUP_SYNC
        ):
            suspensions.append(str(membership_id))
        else:
            unassignments.append(str(membership_id))
    return {
        "course_group_id": str(cohort.id),
        "academic_group_id": str(group.id),
        "expected_cohort_version": cohort.lock_version,
        "expected_academic_group_version": group.lock_version,
        "creates": creates,
        "assigns": assigns,
        "transfers": transfers,
        "reactivations": reactivations,
        "suspensions": suspensions,
        "unassignments": unassignments,
        "conflicts": conflicts,
    }


def _close_cohort_assignment(
    *, assignment: EnrollmentCohortAssignment, actor: object, now: datetime
) -> None:
    assignment.ended_by = actor
    assignment.ended_at = now
    assignment.save(update_fields=["ended_by", "ended_at"])


def _assign_cohort(
    *,
    actor: object,
    enrollment: CourseEnrollment,
    cohort: LearningCohort,
    source: EnrollmentCohortSource,
    reason: str,
    now: datetime,
) -> EnrollmentCohortAssignment:
    previous = (
        EnrollmentCohortAssignment.objects.select_for_update()
        .filter(enrollment=enrollment, ended_at__isnull=True)
        .first()
    )
    if previous is not None:
        _close_cohort_assignment(assignment=previous, actor=actor, now=now)
    assignment = EnrollmentCohortAssignment(
        enrollment=enrollment,
        cohort=cohort,
        source=source,
        reason=reason,
        started_by=actor,
        started_at=now,
    )
    assignment.full_clean()
    assignment.save()
    enrollment.cohort = cohort
    enrollment.access_window_mode = EnrollmentWindowMode.INHERIT
    enrollment.access_starts_at = None
    enrollment.access_ends_at = None
    enrollment.lock_version += 1
    enrollment.full_clean()
    enrollment.save(
        update_fields=[
            "cohort",
            "access_window_mode",
            "access_starts_at",
            "access_ends_at",
            "lock_version",
        ]
    )
    release_assignment = enrollment.current_release_assignment
    if (
        release_assignment is not None
        and release_assignment.release_id == cohort.release_id
    ):
        progress = CourseProgress.objects.select_for_update().get(
            release_assignment=release_assignment
        )
        _initialize_activity_progress(
            progress=progress, cohort=cohort, actor=actor, now=now
        )
        _recalculate_progress(progress, now)
        progress.lock_version += 1
        progress.full_clean()
        progress.save()
    return assignment


@transaction.atomic
def confirm_cohort_roster_sync(
    *,
    actor: object,
    cohort: LearningCohort,
    expected_cohort_version: int,
    expected_academic_group_version: int,
    reason: str,
) -> dict[str, object]:
    """Apply a previewed roster change atomically and append its audit evidence."""

    cohort = (
        LearningCohort.objects.select_for_update()
        .select_related("organization", "course", "release")
        .get(pk=cohort.pk)
    )
    if cohort.academic_group is None:
        raise EnrollmentConflict("El grupo de curso no tiene padrón académico.")
    group = AcademicGroup.objects.select_for_update().get(pk=cohort.academic_group_id)
    plan = preview_cohort_roster_sync(
        actor=actor,
        cohort=cohort,
        expected_cohort_version=expected_cohort_version,
        expected_academic_group_version=expected_academic_group_version,
    )
    if plan["conflicts"]:
        raise EnrollmentConflict(
            "La sincronización tiene conflictos de release y no escribió cambios."
        )
    now = timezone.now()
    learners = _active_academic_group_learners(group)
    desired_ids = {membership.id for membership in learners}
    enrollments = {
        enrollment.membership_id: enrollment
        for enrollment in CourseEnrollment.objects.select_for_update(of=("self",))
        .filter(organization=cohort.organization, course=cohort.course)
        .exclude(status=EnrollmentStatus.REVOKED)
        .select_related("current_release_assignment")
    }
    for membership in learners:
        enrollment = enrollments.get(membership.id)
        if enrollment is None:
            _create_enrollment_rows(
                actor=actor,
                organization=cohort.organization,
                course=cohort.course,
                membership=membership,
                release=cohort.release,
                cohort=cohort,
                access_starts_at=None,
                access_ends_at=None,
                access_provenance=EnrollmentCohortSource.ACADEMIC_GROUP_SYNC,
                access_window_mode=EnrollmentWindowMode.INHERIT,
                cohort_source=EnrollmentCohortSource.ACADEMIC_GROUP_SYNC,
                cohort_reason=reason,
            )
            continue
        current = (
            EnrollmentCohortAssignment.objects.select_for_update()
            .filter(enrollment=enrollment, ended_at__isnull=True)
            .first()
        )
        if current is None or current.cohort_id != cohort.id:
            _assign_cohort(
                actor=actor,
                enrollment=enrollment,
                cohort=cohort,
                source=(
                    EnrollmentCohortSource.ACADEMIC_GROUP_SYNC
                    if enrollment.access_provenance
                    == EnrollmentCohortSource.ACADEMIC_GROUP_SYNC
                    else EnrollmentCohortSource.TRANSFER
                ),
                reason=reason,
                now=now,
            )
        if (
            enrollment.status == EnrollmentStatus.SUSPENDED
            and enrollment.access_provenance
            == EnrollmentCohortSource.ACADEMIC_GROUP_SYNC
        ):
            enrollment.status = EnrollmentStatus.ACTIVE
            enrollment.suspended_at = None
            enrollment.status_changed_by = actor
            enrollment.status_changed_at = now
            enrollment.lock_version += 1
            enrollment.full_clean()
            enrollment.save(
                update_fields=[
                    "status",
                    "suspended_at",
                    "status_changed_by",
                    "status_changed_at",
                    "lock_version",
                ]
            )
            assignment = enrollment.current_release_assignment
            if assignment:
                _event(
                    event_type=LearningEventType.ENROLLMENT_REACTIVATED,
                    enrollment=enrollment,
                    assignment=assignment,
                    progress=assignment.progress,
                    actor=actor,
                    occurred_at=now,
                )
    active_target = list(
        EnrollmentCohortAssignment.objects.select_for_update(of=("self",))
        .filter(cohort=cohort, ended_at__isnull=True)
        .select_related("enrollment__current_release_assignment__progress")
    )
    for assignment in active_target:
        enrollment = assignment.enrollment
        if enrollment.membership_id in desired_ids:
            continue
        inherited_window = enrollment.effective_access_window()
        _close_cohort_assignment(assignment=assignment, actor=actor, now=now)
        enrollment.cohort = None
        if enrollment.access_provenance == EnrollmentCohortSource.ACADEMIC_GROUP_SYNC:
            enrollment.status = EnrollmentStatus.SUSPENDED
            enrollment.suspended_at = now
            enrollment.status_changed_by = actor
            enrollment.status_changed_at = now
        else:
            enrollment.access_window_mode = EnrollmentWindowMode.INDIVIDUAL
            enrollment.access_starts_at, enrollment.access_ends_at = inherited_window
        enrollment.lock_version += 1
        enrollment.full_clean()
        enrollment.save()
        if (
            enrollment.access_provenance == EnrollmentCohortSource.ACADEMIC_GROUP_SYNC
            and enrollment.current_release_assignment
        ):
            _event(
                event_type=LearningEventType.ENROLLMENT_SUSPENDED,
                enrollment=enrollment,
                assignment=enrollment.current_release_assignment,
                progress=enrollment.current_release_assignment.progress,
                actor=actor,
                occurred_at=now,
            )
    cohort.lock_version += 1
    cohort.updated_by = actor
    cohort.save(update_fields=["lock_version", "updated_by", "updated_at"])
    _roster_event(
        actor=actor,
        organization=cohort.organization,
        academic_group=group,
        cohort=cohort,
        event_type=RosterEventType.COURSE_GROUP_SYNCED,
        details={
            "reason": reason.strip(),
            "course_group_version": cohort.lock_version,
            "created": len(plan["creates"]),
            "assigned": len(plan["assigns"]),
            "transferred": len(plan["transfers"]),
            "suspended": len(plan["suspensions"]),
        },
    )
    return plan


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
    access_provenance: EnrollmentCohortSource = EnrollmentCohortSource.MANUAL,
    access_window_mode: EnrollmentWindowMode = EnrollmentWindowMode.INDIVIDUAL,
    cohort_source: EnrollmentCohortSource | None = None,
    cohort_reason: str = "Matrícula individual",
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
        access_provenance=access_provenance,
        access_window_mode=access_window_mode,
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
    if cohort is not None:
        cohort_assignment = EnrollmentCohortAssignment(
            enrollment=enrollment,
            cohort=cohort,
            source=cohort_source or access_provenance,
            reason=cohort_reason.strip(),
            started_by=actor,
            started_at=now,
        )
        cohort_assignment.full_clean()
        cohort_assignment.save()
        _initialize_activity_progress(
            progress=progress, cohort=cohort, actor=actor, now=now
        )
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
    expected_cohort_version: int | None = None,
    access_starts_at: datetime | None = None,
    access_ends_at: datetime | None = None,
    source: EnrollmentCohortSource = EnrollmentCohortSource.MANUAL,
    reason: str = "Matrícula individual",
) -> CourseEnrollment:
    if cohort is None and not can_manage_enrollments(actor, organization):  # type: ignore[arg-type]
        raise LearningPermissionDenied("No puede administrar matrículas individuales.")
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
        if not can_manage_course_group(actor, cohort):  # type: ignore[arg-type]
            raise LearningPermissionDenied("No puede administrar este grupo de curso.")
        if expected_cohort_version is not None:
            _require_version(
                cohort.lock_version, expected_cohort_version, "El grupo de curso"
            )
        if (
            cohort.organization_id != organization.id
            or cohort.course_id != course.id
            or (release is not None and release.id != cohort.release_id)
        ):
            raise EnrollmentCohortMismatch("La cohorte no corresponde a la matrícula.")
        release = cohort.release
        access_window_mode = (
            EnrollmentWindowMode.INDIVIDUAL
            if access_starts_at is not None or access_ends_at is not None
            else EnrollmentWindowMode.INHERIT
        )
    else:
        release = release or publication.current_release
        access_window_mode = EnrollmentWindowMode.INDIVIDUAL
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
        access_provenance=source,
        access_window_mode=access_window_mode,
        cohort_source=source if cohort is not None else None,
        cohort_reason=reason,
    )


@transaction.atomic
def enroll_cohort_members(
    *,
    actor: object,
    cohort: LearningCohort,
    memberships: Iterable[Membership],
    expected_cohort_version: int,
) -> list[CourseEnrollment]:
    rows = list(memberships)
    if not rows:
        raise EnrollmentConflict("El lote debe contener al menos una membresía.")
    cohort = (
        LearningCohort.objects.select_for_update()
        .select_related("organization", "course", "release__course")
        .get(pk=cohort.pk)
    )
    if not can_manage_course_group(actor, cohort):  # type: ignore[arg-type]
        raise LearningPermissionDenied("No puede administrar este grupo de curso.")
    _require_version(cohort.lock_version, expected_cohort_version, "El grupo de curso")
    results = []
    for membership in rows:
        results.append(
            enroll_member(
                actor=actor,
                organization=cohort.organization,
                course=cohort.course,
                membership=membership,
                cohort=cohort,
                reason="Matrícula manual en grupo de curso",
            )
        )
    cohort.lock_version += 1
    cohort.updated_by = actor
    cohort.save(update_fields=["lock_version", "updated_by", "updated_at"])
    return results


@transaction.atomic
def make_enrollment_individual(
    *,
    actor: object,
    enrollment: CourseEnrollment,
    expected_version: int,
    reason: str,
) -> CourseEnrollment:
    """Keep access deliberately while removing the enrollment from a course group."""

    enrollment = _locked_enrollment(enrollment)
    if not can_manage_enrollment(actor, enrollment):  # type: ignore[arg-type]
        raise LearningPermissionDenied("No puede convertir esta matrícula.")
    _require_enrollment_version(enrollment, expected_version)
    assignment = (
        EnrollmentCohortAssignment.objects.select_for_update()
        .filter(enrollment=enrollment, ended_at__isnull=True)
        .first()
    )
    if assignment is None:
        return enrollment
    starts_at, ends_at = enrollment.effective_access_window()
    now = timezone.now()
    _close_cohort_assignment(assignment=assignment, actor=actor, now=now)
    enrollment.cohort = None
    enrollment.access_provenance = EnrollmentCohortSource.MANUAL
    enrollment.access_window_mode = EnrollmentWindowMode.INDIVIDUAL
    enrollment.access_starts_at = starts_at
    enrollment.access_ends_at = ends_at
    enrollment.lock_version += 1
    enrollment.full_clean()
    enrollment.save()
    _roster_event(
        actor=actor,
        organization=enrollment.organization,
        cohort=assignment.cohort,
        event_type=RosterEventType.ENROLLMENT_UNASSIGNED,
        details={"reason": reason.strip(), "enrollment_id": str(enrollment.id)},
    )
    return enrollment


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
    if not can_manage_enrollment(actor, enrollment):  # type: ignore[arg-type]
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
    if not can_manage_enrollment(actor, enrollment):  # type: ignore[arg-type]
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
    if not can_manage_enrollment(actor, enrollment):  # type: ignore[arg-type]
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
    cohort_assignment = (
        EnrollmentCohortAssignment.objects.select_for_update()
        .filter(enrollment=enrollment, ended_at__isnull=True)
        .first()
    )
    if cohort_assignment is not None:
        _close_cohort_assignment(assignment=cohort_assignment, actor=actor, now=now)
    enrollment.status = EnrollmentStatus.REVOKED
    enrollment.suspended_at = None
    enrollment.revoked_at = now
    enrollment.cohort = None
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
    if not can_manage_enrollment(actor, enrollment):  # type: ignore[arg-type]
        raise LearningPermissionDenied("No puede actualizar releases.")
    _require_enrollment_version(enrollment, expected_enrollment_version)
    if (
        enrollment.status == EnrollmentStatus.REVOKED
        or enrollment.active_cohort_assignment is not None
    ):
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


def _lesson_activity_progress(
    *, progress: CourseProgress, unit_id: uuid.UUID
) -> ActivityProgress | None:
    return (
        ActivityProgress.objects.select_for_update()
        .select_related("group_activity")
        .filter(
            course_progress=progress,
            group_activity__activity_type="lesson",
            group_activity__binding_snapshot__unit_id=str(unit_id),
        )
        .first()
    )


def _transition_activity_progress(
    *,
    activity_progress: ActivityProgress | None,
    status: str,
    actor: object,
    now: datetime,
    evidence: dict[str, object],
    source: str = ActivityProgressSource.LESSON,
) -> None:
    if activity_progress is None:
        return
    if activity_progress.status == status and activity_progress.evidence == evidence:
        return
    if (
        activity_progress.status == ActivityProgressStatus.LOCKED
        and status != ActivityProgressStatus.AVAILABLE.value
    ):
        raise LearningPermissionDenied("La actividad todavía no está disponible.")
    previous_status = activity_progress.status
    activity_progress.status = status
    activity_progress.source = source
    activity_progress.evidence = evidence
    activity_progress.started_at = activity_progress.started_at or now
    activity_progress.completed_at = (
        now
        if status
        in {
            ActivityProgressStatus.COMPLETED,
            ActivityProgressStatus.PASSED,
            ActivityProgressStatus.WAIVED,
        }
        else None
    )
    activity_progress.state_changed_at = now
    activity_progress.state_changed_by = actor
    activity_progress.lock_version += 1
    activity_progress.full_clean()
    activity_progress.save()
    ActivityProgressEvent.objects.create(
        activity_progress=activity_progress,
        previous_status=previous_status,
        new_status=status,
        source=source,
        policy_version=activity_progress.policy_version,
        evidence=evidence,
        actor=actor,
        occurred_at=now,
    )


def _refresh_activity_availability(
    *,
    progress: CourseProgress,
    actor: object,
    now: datetime,
    cohort: LearningCohort | None = None,
) -> None:
    rows_query = (
        ActivityProgress.objects.select_for_update()
        .select_related("group_activity")
        .filter(course_progress=progress)
    )
    if cohort is not None:
        rows_query = rows_query.filter(group_activity__course_group=cohort)
    rows = list(rows_query)
    by_source_id = {str(row.group_activity.source_activity_id): row for row in rows}
    completed = {
        ActivityProgressStatus.COMPLETED,
        ActivityProgressStatus.PASSED,
        ActivityProgressStatus.WAIVED,
    }
    mastered_objectives = {
        str(objective_id)
        for row in rows
        for objective_id in row.evidence.get("mastered_objective_ids", [])
    }
    for row in rows:
        if row.status != ActivityProgressStatus.LOCKED:
            continue
        satisfied = True
        for rule in row.group_activity.availability_rules:
            rule_type = rule.get("type")
            prerequisite = by_source_id.get(rule.get("prerequisite_activity_id"))
            if rule_type == "activity_completed":
                satisfied = (
                    prerequisite is not None and prerequisite.status in completed
                )
            elif rule_type == "activity_passed":
                satisfied = (
                    prerequisite is not None
                    and prerequisite.status == ActivityProgressStatus.PASSED
                )
            elif rule_type == "minimum_grade":
                satisfied = prerequisite is not None and int(
                    prerequisite.evidence.get("grade_basis_points", -1)
                ) >= int(rule.get("threshold_basis_points") or 0)
            elif rule_type == "objective_mastered":
                satisfied = (
                    str(rule.get("learning_objective_id")) in mastered_objectives
                )
            elif rule_type in {"available_from", "available_until"}:
                boundary = datetime.fromisoformat(str(rule.get("available_at")))
                satisfied = (
                    now >= boundary
                    if rule_type == "available_from"
                    else now <= boundary
                )
            if not satisfied:
                break
        if satisfied:
            _transition_activity_progress(
                activity_progress=row,
                status=ActivityProgressStatus.AVAILABLE,
                actor=actor,
                now=now,
                evidence={"availability_rules_satisfied": True},
            )


@transaction.atomic
def record_activity_from_assessment(
    *,
    actor: object | None,
    group_activity_id: uuid.UUID,
    release_assignment_id: uuid.UUID,
    grade_version_id: uuid.UUID,
    occurred_at: datetime,
    grade_basis_points: int | None,
    passed: bool | None,
    mastered_objective_ids: list[str] | None = None,
) -> bool:
    group_activity = CourseGroupActivity.objects.select_related(
        "course_group", "course_release"
    ).get(pk=group_activity_id, activity_type="assessment")
    progress = CourseProgress.objects.select_for_update().get(
        release_assignment_id=release_assignment_id,
        release_assignment__release=group_activity.course_release,
        release_assignment__enrollment__cohort_assignments__cohort=(
            group_activity.course_group
        ),
        release_assignment__enrollment__cohort_assignments__ended_at__isnull=True,
    )
    activity_progress = ActivityProgress.objects.select_for_update().get(
        course_progress=progress, group_activity=group_activity
    )
    method = group_activity.completion_policy.get("method")
    if method == "submission":
        new_status = ActivityProgressStatus.COMPLETED
    elif method == "grade":
        new_status = (
            ActivityProgressStatus.COMPLETED
            if grade_basis_points is not None
            else ActivityProgressStatus.IN_PROGRESS
        )
    elif method == "pass":
        new_status = (
            ActivityProgressStatus.PASSED
            if passed is True
            else ActivityProgressStatus.FAILED
            if passed is False
            else ActivityProgressStatus.IN_PROGRESS
        )
    else:
        raise LearningProgressConflict(
            "La política de evaluación del release no es válida."
        )
    evidence: dict[str, object] = {
        "grade_version_id": str(grade_version_id),
        "grade_basis_points": grade_basis_points,
        "passed": passed,
        "mastered_objective_ids": mastered_objective_ids or [],
    }
    previous_evidence = dict(activity_progress.evidence)
    _transition_activity_progress(
        activity_progress=activity_progress,
        status=new_status,
        actor=actor,
        now=occurred_at,
        evidence=evidence,
        source=ActivityProgressSource.ASSESSMENT,
    )
    _refresh_activity_availability(progress=progress, actor=actor, now=occurred_at)
    progress.started_at = progress.started_at or occurred_at
    _recalculate_progress(progress, occurred_at)
    progress.lock_version += 1
    progress.full_clean()
    progress.save()
    return previous_evidence != evidence or activity_progress.status != new_status


@transaction.atomic
def complete_activity_from_attendance(
    *,
    actor: object,
    group_activity_id: uuid.UUID,
    completed_at: datetime,
    evidence: dict[str, object],
) -> bool:
    from .contracts import effective_course_group_enrollment

    group_activity = CourseGroupActivity.objects.select_related(
        "course_group__organization"
    ).get(pk=group_activity_id, activity_type="live_class")
    enrollment = effective_course_group_enrollment(
        actor=actor,
        organization=group_activity.course_group.organization,
        course_group=group_activity.course_group,
        at=completed_at,
    )
    if enrollment is None or enrollment.current_release_assignment_id is None:
        return False
    progress = CourseProgress.objects.select_for_update().get(
        release_assignment=enrollment.current_release_assignment
    )
    activity_progress = ActivityProgress.objects.select_for_update().get(
        course_progress=progress, group_activity=group_activity
    )
    if activity_progress.status in {
        ActivityProgressStatus.COMPLETED,
        ActivityProgressStatus.PASSED,
        ActivityProgressStatus.WAIVED,
    }:
        return False
    _transition_activity_progress(
        activity_progress=activity_progress,
        status=ActivityProgressStatus.COMPLETED,
        actor=actor,
        now=completed_at,
        evidence=evidence,
        source=ActivityProgressSource.ATTENDANCE,
    )
    _refresh_activity_availability(progress=progress, actor=actor, now=completed_at)
    progress.started_at = progress.started_at or completed_at
    _recalculate_progress(progress, completed_at)
    progress.lock_version += 1
    progress.full_clean()
    progress.save()
    return True


def completion_projection(
    progress: CourseProgress,
    *,
    activity_rows: list[ActivityProgress] | None = None,
) -> dict[str, object]:
    rows = activity_rows
    if rows is None:
        cached = getattr(progress, "_prefetched_objects_cache", {}).get(
            "activity_progress"
        )
        rows = (
            list(cached)
            if cached is not None
            else list(
                ActivityProgress.objects.filter(
                    course_progress=progress
                ).select_related("group_activity")
            )
        )
    cached_enrollment = progress.release_assignment._state.fields_cache.get(
        "enrollment"
    )
    cohort_id = cached_enrollment.cohort_id if cached_enrollment is not None else None
    if cohort_id is not None:
        rows = [row for row in rows if row.group_activity.course_group_id == cohort_id]
    completed_statuses = {
        ActivityProgressStatus.COMPLETED,
        ActivityProgressStatus.PASSED,
        ActivityProgressStatus.WAIVED,
    }
    required_rows = [row for row in rows if row.group_activity.required]
    completed_required = sum(row.status in completed_statuses for row in required_rows)
    snapshot = progress.release_assignment.release.snapshot
    policy = snapshot.get("completion_policy", {}) if isinstance(snapshot, dict) else {}
    require_activities = bool(policy.get("require_required_activities", True))
    activities_satisfied = (
        (
            completed_required == len(required_rows)
            if rows
            else (
                progress.completed_units + progress.completed_required_activities
                == progress.total_units + progress.total_required_activities
            )
        )
        if require_activities
        else True
    )

    evidence_by_activity = {
        str(row.group_activity.source_activity_id): row.evidence for row in rows
    }
    categories = (
        snapshot.get("grading_scheme", {}).get("categories", [])
        if isinstance(snapshot, dict)
        else []
    )
    grade_basis_points: int | None = None
    if categories:
        weighted_grade = 0
        complete_grade = True
        for category in categories:
            category_grade = 0
            for item in category.get("activities", []):
                evidence = evidence_by_activity.get(str(item.get("activity_id")))
                item_grade = evidence.get("grade_basis_points") if evidence else None
                if item_grade is None:
                    complete_grade = False
                    continue
                category_grade += (
                    int(item_grade) * int(item.get("weight_basis_points", 0)) // 10_000
                )
            weighted_grade += (
                category_grade * int(category.get("weight_basis_points", 0)) // 10_000
            )
        if complete_grade:
            grade_basis_points = weighted_grade
    minimum_grade = policy.get("minimum_grade_basis_points")
    grade_satisfied = (
        True
        if minimum_grade is None
        else grade_basis_points is not None and grade_basis_points >= int(minimum_grade)
    )

    live_rows = [
        row for row in required_rows if row.group_activity.activity_type == "live_class"
    ]
    attended = sum(row.status in completed_statuses for row in live_rows)
    attendance_basis_points = (
        attended * 10_000 // len(live_rows) if live_rows else 10_000
    )
    minimum_attendance = policy.get("minimum_attendance_basis_points")
    attendance_satisfied = minimum_attendance is None or attendance_basis_points >= int(
        minimum_attendance
    )

    evidenced_objectives = {
        str(objective_id)
        for row in rows
        for objective_id in row.evidence.get("mastered_objective_ids", [])
    }
    total_objectives = (
        len(snapshot.get("curriculum", {}).get("learning_objectives", []))
        if isinstance(snapshot, dict)
        else 0
    )
    blockers: list[dict[str, str]] = []
    if not activities_satisfied:
        blockers.append(
            {
                "code": "required_activities_pending",
                "message": "Faltan actividades obligatorias por completar.",
            }
        )
    if not grade_satisfied:
        blockers.append(
            {
                "code": (
                    "grade_pending"
                    if grade_basis_points is None
                    else "minimum_grade_not_met"
                ),
                "message": (
                    "La calificación final todavía no está disponible."
                    if grade_basis_points is None
                    else "La calificación final no alcanza el mínimo."
                ),
            }
        )
    if not attendance_satisfied:
        blockers.append(
            {
                "code": "minimum_attendance_not_met",
                "message": "La asistencia no alcanza el mínimo requerido.",
            }
        )
    return {
        "completion": {
            "completed_required": completed_required,
            "total_required": len(required_rows),
            "satisfied": activities_satisfied,
        },
        "mastery": {
            "evidenced_objective_ids": sorted(evidenced_objectives),
            "evidenced_count": len(evidenced_objectives),
            "total_objectives": total_objectives,
        },
        "grade": {
            "basis_points": grade_basis_points,
            "minimum_basis_points": minimum_grade,
            "satisfied": grade_satisfied,
        },
        "attendance": {
            "basis_points": attendance_basis_points,
            "minimum_basis_points": minimum_attendance,
            "satisfied": attendance_satisfied,
        },
        "blockers": blockers,
        "is_complete": not blockers,
    }


def _recalculate_progress(progress: CourseProgress, now: datetime) -> None:
    activity_query = ActivityProgress.objects.filter(
        course_progress=progress
    ).select_related("group_activity")
    cohort_id = progress.release_assignment.enrollment.cohort_id
    if cohort_id is not None:
        activity_query = activity_query.filter(
            group_activity__course_group_id=cohort_id
        )
    activity_rows = list(activity_query)
    if activity_rows:
        completed_statuses = {
            ActivityProgressStatus.COMPLETED,
            ActivityProgressStatus.PASSED,
            ActivityProgressStatus.WAIVED,
        }
        required_rows = [row for row in activity_rows if row.group_activity.required]
        completed_required = sum(
            row.status in completed_statuses for row in required_rows
        )
        required_total = len(required_rows)
        lesson_rows = [
            row for row in activity_rows if row.group_activity.activity_type == "lesson"
        ]
        progress.total_units = len(lesson_rows)
        progress.completed_units = sum(
            row.status in completed_statuses for row in lesson_rows
        )
        progress.completed_required_activities = completed_required
        progress.total_required_activities = required_total
        progress.percent_basis_points = (
            completed_required * 10_000 // required_total if required_total else 10_000
        )
        projection = completion_projection(progress, activity_rows=activity_rows)
        if projection["is_complete"]:
            progress.status = ProgressStatus.COMPLETED
            progress.completed_at = progress.completed_at or now
        elif completed_required == 0 and progress.started_at is None:
            progress.status = ProgressStatus.NOT_STARTED
            progress.completed_at = None
        else:
            progress.status = ProgressStatus.IN_PROGRESS
            progress.completed_at = None
        progress.last_activity_at = now
        return
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
    activity_progress = _lesson_activity_progress(progress=progress, unit_id=unit_id)
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
    if unit_progress.status != UnitProgressStatus.COMPLETED:
        _transition_activity_progress(
            activity_progress=activity_progress,
            status=ActivityProgressStatus.IN_PROGRESS,
            actor=actor,
            now=now,
            evidence={"unit_id": str(unit_id), "action": "opened"},
        )
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
    activity_progress = _lesson_activity_progress(progress=progress, unit_id=unit_id)
    unit_progress = (
        UnitProgress.objects.select_for_update()
        .filter(course_progress=progress, unit_id=unit_id)
        .first()
    )
    if unit_progress and unit_progress.status == UnitProgressStatus.COMPLETED:
        if (
            activity_progress is not None
            and activity_progress.status != ActivityProgressStatus.COMPLETED
        ):
            _transition_activity_progress(
                activity_progress=activity_progress,
                status=ActivityProgressStatus.COMPLETED,
                actor=actor,
                now=now,
                evidence={"unit_id": str(unit_id), "action": "completed"},
            )
            _recalculate_progress(progress, now)
            progress.lock_version += 1
            progress.full_clean()
            progress.save()
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
    _transition_activity_progress(
        activity_progress=activity_progress,
        status=ActivityProgressStatus.COMPLETED,
        actor=actor,
        now=now,
        evidence={"unit_id": str(unit_id), "action": "completed"},
    )
    _refresh_activity_availability(progress=progress, actor=actor, now=now)
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
    activity_progress = _lesson_activity_progress(progress=progress, unit_id=unit_id)
    course_was_completed = progress.status == ProgressStatus.COMPLETED
    unit_progress.status = UnitProgressStatus.IN_PROGRESS
    unit_progress.completed_at = None
    unit_progress.save()
    _transition_activity_progress(
        activity_progress=activity_progress,
        status=ActivityProgressStatus.IN_PROGRESS,
        actor=actor,
        now=now,
        evidence={"unit_id": str(unit_id), "action": "reopened"},
    )
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
