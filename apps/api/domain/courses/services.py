# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportUnknownLambdaType=false
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from domain.catalog.models import (
    CatalogStatus,
    LearningObjective,
    Subject,
    Topic,
)
from domain.events.services import record_domain_event
from domain.organizations.capabilities import Capability
from domain.organizations.choices import MembershipStatus, RoleCode
from domain.organizations.models import Membership, Organization
from domain.organizations.policies import active_roles, has_capability

from .activity_extensions import clone_activity_binding
from .choices import (
    EDITABLE_AUTHORING_STATUSES,
    OPEN_AUTHORING_STATUSES,
    ActivityCompletionMethod,
    ActivityType,
    AuthoringStatus,
    AvailabilityRuleType,
    CourseStatus,
    StructureStatus,
    SubjectAlignmentType,
)
from .exceptions import (
    CourseAccessDenied,
    CourseArchived,
    CourseArchivedCatalogReference,
    CourseCrossOrganizationRelation,
    CourseCurriculumAlignmentInvalid,
    CourseLimitExceeded,
    CourseOrderInvalid,
    CourseRevisionAlreadyOpen,
    CourseRevisionConflict,
    CourseRevisionNotEditable,
    CourseRevisionNotReady,
    CourseRevisionTransitionInvalid,
    CourseSlugReserved,
    CourseStructureInvalid,
)
from .models import (
    Course,
    CourseActivity,
    CourseActivityAvailabilityRule,
    CourseActivityLearningObjective,
    CourseCompletionPolicy,
    CourseGradeCategory,
    CourseGradedActivity,
    CourseModule,
    CourseRevision,
    CourseRevisionLearningObjective,
    CourseRevisionSubject,
    CourseRevisionTransition,
    CourseTeachingException,
    CourseUnit,
    CourseUnitLearningObjective,
    CourseUnitTopic,
)
from .policies import (
    can_approve_revision,
    can_manage_course,
    can_review_revision,
    can_submit_revision,
    has_course_academic_responsibility,
)
from .readiness import revision_readiness_issues

MAX_ACTIVE_MODULES = 100
MAX_ACTIVE_UNITS_PER_MODULE = 200
MAX_ACTIVE_ACTIVITIES_PER_MODULE = 300


@dataclass(frozen=True)
class AvailabilityRuleInput:
    rule_type: AvailabilityRuleType
    prerequisite_activity: CourseActivity | None = None
    learning_objective: LearningObjective | None = None
    threshold_basis_points: int | None = None
    available_at: datetime | None = None


@dataclass(frozen=True)
class GradedActivityInput:
    activity: CourseActivity
    weight_basis_points: int
    required: bool = True


@dataclass(frozen=True)
class GradeCategoryInput:
    code: str
    title: str
    weight_basis_points: int
    activities: Sequence[GradedActivityInput]


def _require(condition: bool, error: type[Exception], message: str) -> None:
    if not condition:
        raise error(message)


@transaction.atomic
def assign_course_teaching_exception(
    *,
    actor: object,
    organization: Organization,
    course: Course,
    membership: Membership,
    starts_on: date,
    ends_on: date | None,
    rationale: str,
) -> CourseTeachingException:
    _require(
        has_capability(  # type: ignore[arg-type]
            actor,  # pyright: ignore[reportArgumentType]
            organization,
            Capability.CATALOG_TEACHING_RESPONSIBILITY_MANAGE,
        ),
        CourseAccessDenied,
        "No tienes capacidad para asignar excepciones académicas.",
    )
    _require(
        course.organization_id == organization.id
        and membership.organization_id == organization.id
        and membership.status == MembershipStatus.ACTIVE.value
        and bool(
            active_roles(membership)
            & {RoleCode.AUTHOR, RoleCode.REVIEWER, RoleCode.INSTRUCTOR}
        ),
        CourseCrossOrganizationRelation,
        "La persona no es elegible para esta responsabilidad académica.",
    )
    exception = CourseTeachingException(
        course=course,
        membership=membership,
        starts_on=starts_on,
        ends_on=ends_on,
        rationale=rationale,
        created_by=actor,
    )
    exception.full_clean()
    exception.save()
    return exception


@transaction.atomic
def close_course_teaching_exception(
    *, actor: object, exception: CourseTeachingException, ended_on: date
) -> CourseTeachingException:
    _require(
        has_capability(  # type: ignore[arg-type]
            actor,  # pyright: ignore[reportArgumentType]
            exception.course.organization,
            Capability.CATALOG_TEACHING_RESPONSIBILITY_MANAGE,
        ),
        CourseAccessDenied,
        "No tienes capacidad para cerrar excepciones académicas.",
    )
    locked = CourseTeachingException.objects.select_for_update().get(pk=exception.pk)
    if locked.ended_at is not None:
        return locked
    _require(
        ended_on >= locked.starts_on,
        CourseStructureInvalid,
        "La fecha de cierre precede el inicio.",
    )
    locked.ends_on = ended_on
    locked.ended_by = actor
    locked.ended_at = timezone.now()
    locked.full_clean()
    locked.save(update_fields=["ends_on", "ended_by", "ended_at"])
    return locked


def _require_manage(actor: object, organization: Organization) -> None:
    _require(
        can_manage_course(actor, organization),
        CourseAccessDenied,
        "No tienes capacidad para administrar cursos.",
    )


def _lock_revision(
    *,
    actor: object,
    revision: CourseRevision,
    organization: Organization,
    expected_version: int,
) -> CourseRevision:
    locked = (
        CourseRevision.objects.select_for_update()
        .select_related("course__organization")
        .get(pk=revision.pk)
    )
    _require(
        locked.course.organization_id == organization.id,
        CourseCrossOrganizationRelation,
        "La revisión no pertenece a la organización.",
    )
    _require(
        has_course_academic_responsibility(actor, organization, course=locked.course),
        CourseAccessDenied,
        "No tienes responsabilidad académica sobre este curso.",
    )
    _require(
        expected_version == locked.lock_version,
        CourseRevisionConflict,
        "La revisión cambió desde que la abriste.",
    )
    return locked


def _require_editable(revision: CourseRevision) -> None:
    _require(
        revision.course.status == CourseStatus.ACTIVE,
        CourseArchived,
        "El curso está archivado.",
    )
    _require(
        revision.authoring_status in EDITABLE_AUTHORING_STATUSES,
        CourseRevisionNotEditable,
        "La revisión no admite modificaciones.",
    )


def _finish(revision: CourseRevision, actor: Any) -> CourseRevision:
    revision.lock_version += 1
    revision.updated_by = actor
    revision.save(update_fields=["lock_version", "updated_by", "updated_at"])
    return revision


def _validate_catalog_entity(
    entity: Any, organization: Organization, *, active: bool = True
) -> None:
    entity_organization = entity.organization
    _require(
        entity_organization.id == organization.id,
        CourseCrossOrganizationRelation,
        "La referencia curricular pertenece a otra organización.",
    )
    if active:
        _require(
            entity.status == CatalogStatus.ACTIVE,
            CourseArchivedCatalogReference,
            "La referencia curricular está archivada.",
        )


@transaction.atomic
def create_course(
    *,
    actor: Any,
    organization: Organization,
    slug: str,
    title: str,
    summary: str,
    primary_subject: Subject,
    supporting_subjects: Sequence[Subject] = (),
    learning_objectives: Sequence[LearningObjective] = (),
    subtitle: str = "",
    description: str = "",
    language_code: str = "es",
    estimated_duration_minutes: int | None = None,
) -> CourseRevision:
    _require_manage(actor, organization)
    subjects = [primary_subject, *supporting_subjects]
    _require(
        len({subject.id for subject in subjects}) == len(subjects),
        CourseCurriculumAlignmentInvalid,
        "Las asignaturas no pueden repetirse.",
    )
    for subject in subjects:
        _validate_catalog_entity(subject, organization)
    _require(
        has_course_academic_responsibility(
            actor, organization, subjects=list(subjects)
        ),
        CourseAccessDenied,
        "No tienes responsabilidad académica sobre todas las asignaturas.",
    )
    subject_ids = {subject.id for subject in subjects}
    for objective in learning_objectives:
        _validate_catalog_entity(objective, organization)
        _require(
            objective.subject_id in subject_ids,
            CourseCurriculumAlignmentInvalid,
            "Cada objetivo debe pertenecer a una asignatura alineada.",
        )
    _require(
        len({objective.id for objective in learning_objectives})
        == len(learning_objectives),
        CourseCurriculumAlignmentInvalid,
        "Los objetivos no pueden repetirse.",
    )
    course = Course(organization=organization, slug=slug, created_by=actor)
    try:
        course.full_clean()
        course.save()
    except (IntegrityError, ValidationError) as error:
        raise CourseSlugReserved(
            "El slug está reservado o ya pertenece a otro curso de la organización."
        ) from error
    revision = CourseRevision(
        course=course,
        number=1,
        title=title,
        subtitle=subtitle,
        summary=summary,
        description=description,
        language_code=language_code,
        estimated_duration_minutes=estimated_duration_minutes,
        status_changed_by=actor,
        created_by=actor,
        updated_by=actor,
    )
    revision.full_clean()
    revision.save()
    CourseCompletionPolicy.objects.create(revision=revision, updated_by=actor)
    CourseRevisionTransition.objects.create(
        revision=revision,
        from_status=None,
        to_status=AuthoringStatus.DRAFT,
        actor=actor,
    )
    CourseRevisionSubject.objects.bulk_create(
        [
            CourseRevisionSubject(
                revision=revision,
                subject=subject,
                alignment_type=(
                    SubjectAlignmentType.PRIMARY
                    if index == 1
                    else SubjectAlignmentType.SUPPORTING
                ),
                position=index,
                created_by=actor,
            )
            for index, subject in enumerate(subjects, start=1)
        ]
    )
    CourseRevisionLearningObjective.objects.bulk_create(
        [
            CourseRevisionLearningObjective(
                revision=revision,
                learning_objective=objective,
                position=index,
                created_by=actor,
            )
            for index, objective in enumerate(learning_objectives, start=1)
        ]
    )
    return revision


@transaction.atomic
def update_revision_metadata(
    *,
    actor: Any,
    organization: Organization,
    revision: CourseRevision,
    expected_version: int,
    **changes: object,
) -> CourseRevision:
    _require_manage(actor, organization)
    locked = _lock_revision(
        actor=actor,
        revision=revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(locked)
    allowed = {
        "title",
        "subtitle",
        "summary",
        "description",
        "language_code",
        "estimated_duration_minutes",
    }
    _require(
        set(changes) <= allowed,
        CourseStructureInvalid,
        "La actualización contiene campos internos.",
    )
    for field, value in changes.items():
        setattr(locked, field, value)
    locked.updated_by = actor
    try:
        locked.full_clean()
    except ValidationError as error:
        raise CourseStructureInvalid("La metadata no es válida.") from error
    locked.save(update_fields=[*changes, "updated_by", "updated_at"])
    return _finish(locked, actor)


@transaction.atomic
def replace_revision_subjects(
    *,
    actor: Any,
    organization: Organization,
    revision: CourseRevision,
    expected_version: int,
    primary_subject: Subject,
    supporting_subjects: Sequence[Subject],
) -> CourseRevision:
    _require_manage(actor, organization)
    locked = _lock_revision(
        actor=actor,
        revision=revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(locked)
    subjects = [primary_subject, *supporting_subjects]
    _require(
        len({item.id for item in subjects}) == len(subjects),
        CourseCurriculumAlignmentInvalid,
        "Las asignaturas no pueden repetirse.",
    )
    for subject in subjects:
        _validate_catalog_entity(subject, organization)
    _require(
        has_course_academic_responsibility(
            actor, organization, subjects=list(subjects)
        ),
        CourseAccessDenied,
        "No tienes responsabilidad académica sobre todas las asignaturas.",
    )
    allowed_subject_ids = {item.id for item in subjects}
    invalid_objective = (
        CourseRevisionLearningObjective.objects.filter(revision=locked)
        .exclude(learning_objective__subject_id__in=allowed_subject_ids)
        .exists()
    )
    _require(
        not invalid_objective,
        CourseCurriculumAlignmentInvalid,
        "Retira primero los objetivos de asignaturas que dejarán de estar alineadas.",
    )
    CourseRevisionSubject.objects.filter(revision=locked).delete()
    CourseRevisionSubject.objects.bulk_create(
        [
            CourseRevisionSubject(
                revision=locked,
                subject=subject,
                alignment_type=(
                    SubjectAlignmentType.PRIMARY
                    if index == 1
                    else SubjectAlignmentType.SUPPORTING
                ),
                position=index,
                created_by=actor,
            )
            for index, subject in enumerate(subjects, start=1)
        ]
    )
    return _finish(locked, actor)


@transaction.atomic
def replace_revision_learning_objectives(
    *,
    actor: Any,
    organization: Organization,
    revision: CourseRevision,
    expected_version: int,
    learning_objectives: Sequence[LearningObjective],
) -> CourseRevision:
    _require_manage(actor, organization)
    locked = _lock_revision(
        actor=actor,
        revision=revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(locked)
    _require(
        len({item.id for item in learning_objectives}) == len(learning_objectives),
        CourseCurriculumAlignmentInvalid,
        "Los objetivos no pueden repetirse.",
    )
    subject_ids = set(
        CourseRevisionSubject.objects.filter(revision=locked).values_list(
            "subject_id", flat=True
        )
    )
    for objective in learning_objectives:
        _validate_catalog_entity(objective, organization)
        _require(
            objective.subject_id in subject_ids,
            CourseCurriculumAlignmentInvalid,
            "Cada objetivo debe pertenecer a una asignatura alineada.",
        )
    objective_ids = {item.id for item in learning_objectives}
    invalid_unit_link = (
        CourseUnitLearningObjective.objects.filter(unit__module__revision=locked)
        .exclude(learning_objective_id__in=objective_ids)
        .exists()
    )
    _require(
        not invalid_unit_link,
        CourseCurriculumAlignmentInvalid,
        "Retira primero los objetivos que aún usan las unidades.",
    )
    CourseRevisionLearningObjective.objects.filter(revision=locked).delete()
    CourseRevisionLearningObjective.objects.bulk_create(
        [
            CourseRevisionLearningObjective(
                revision=locked,
                learning_objective=objective,
                position=index,
                created_by=actor,
            )
            for index, objective in enumerate(learning_objectives, start=1)
        ]
    )
    return _finish(locked, actor)


def _active_modules(revision: CourseRevision):
    return CourseModule.objects.filter(
        revision=revision, status=StructureStatus.ACTIVE
    ).order_by("position")


def _active_units(module: CourseModule):
    return CourseUnit.objects.filter(
        module=module, status=StructureStatus.ACTIVE
    ).order_by("position")


@transaction.atomic
def create_module(
    *,
    actor: Any,
    organization: Organization,
    revision: CourseRevision,
    expected_version: int,
    title: str,
    description: str = "",
) -> tuple[CourseModule, CourseRevision]:
    _require_manage(actor, organization)
    locked = _lock_revision(
        actor=actor,
        revision=revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(locked)
    modules = list(_active_modules(locked).select_for_update())
    _require(
        len(modules) < MAX_ACTIVE_MODULES,
        CourseLimitExceeded,
        "La revisión alcanzó el máximo de módulos activos.",
    )
    module = CourseModule(
        revision=locked,
        title=title,
        description=description,
        position=len(modules) + 1,
        created_by=actor,
        updated_by=actor,
    )
    module.full_clean()
    module.save()
    return module, _finish(locked, actor)


@transaction.atomic
def update_module(
    *,
    actor: Any,
    organization: Organization,
    module: CourseModule,
    expected_version: int,
    **changes: object,
) -> tuple[CourseModule, CourseRevision]:
    _require_manage(actor, organization)
    locked_module = (
        CourseModule.objects.select_for_update()
        .select_related("revision__course__organization")
        .get(pk=module.pk)
    )
    locked = _lock_revision(
        actor=actor,
        revision=locked_module.revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(locked)
    _require(
        locked_module.status == StructureStatus.ACTIVE,
        CourseStructureInvalid,
        "El módulo está archivado.",
    )
    _require(
        set(changes) <= {"title", "description"},
        CourseStructureInvalid,
        "La actualización contiene campos internos.",
    )
    for field, value in changes.items():
        setattr(locked_module, field, value)
    locked_module.updated_by = actor
    locked_module.full_clean()
    locked_module.save(update_fields=[*changes, "updated_by", "updated_at"])
    return locked_module, _finish(locked, actor)


def _validate_order(ordered_ids: Sequence[UUID], actual_ids: Sequence[UUID]) -> None:
    _require(
        len(ordered_ids) == len(set(ordered_ids))
        and set(ordered_ids) == set(actual_ids),
        CourseOrderInvalid,
        "El orden debe incluir exactamente todos los elementos activos una sola vez.",
    )


@transaction.atomic
def replace_module_order(
    *,
    actor: Any,
    organization: Organization,
    revision: CourseRevision,
    expected_version: int,
    ordered_ids: Sequence[UUID],
) -> CourseRevision:
    _require_manage(actor, organization)
    locked = _lock_revision(
        actor=actor,
        revision=revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(locked)
    modules = list(_active_modules(locked).select_for_update())
    _validate_order(ordered_ids, [module.id for module in modules])
    by_id = {module.id: module for module in modules}
    for position, module_id in enumerate(ordered_ids, start=1):
        by_id[module_id].position = position
    CourseModule.objects.bulk_update(modules, ["position"])
    return _finish(locked, actor)


def _compact_modules(revision: CourseRevision) -> None:
    modules = list(_active_modules(revision).select_for_update())
    for position, module in enumerate(modules, start=1):
        module.position = position
    CourseModule.objects.bulk_update(modules, ["position"])


@transaction.atomic
def archive_module(
    *,
    actor: Any,
    organization: Organization,
    module: CourseModule,
    expected_version: int,
) -> tuple[CourseModule, CourseRevision]:
    _require_manage(actor, organization)
    locked_module = (
        CourseModule.objects.select_for_update()
        .select_related("revision__course__organization")
        .get(pk=module.pk)
    )
    locked = _lock_revision(
        actor=actor,
        revision=locked_module.revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(locked)
    _require(
        locked_module.status == StructureStatus.ACTIVE,
        CourseStructureInvalid,
        "El módulo ya está archivado.",
    )
    locked_module.status = StructureStatus.ARCHIVED
    locked_module.position = None
    locked_module.archived_by = actor
    locked_module.archived_at = timezone.now()
    locked_module.updated_by = actor
    locked_module.save(
        update_fields=[
            "status",
            "position",
            "archived_by",
            "archived_at",
            "updated_by",
            "updated_at",
        ]
    )
    _compact_modules(locked)
    return locked_module, _finish(locked, actor)


@transaction.atomic
def restore_module(
    *,
    actor: Any,
    organization: Organization,
    module: CourseModule,
    expected_version: int,
) -> tuple[CourseModule, CourseRevision]:
    _require_manage(actor, organization)
    locked_module = (
        CourseModule.objects.select_for_update()
        .select_related("revision__course__organization")
        .get(pk=module.pk)
    )
    locked = _lock_revision(
        actor=actor,
        revision=locked_module.revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(locked)
    _require(
        locked_module.status == StructureStatus.ARCHIVED,
        CourseStructureInvalid,
        "El módulo no está archivado.",
    )
    active_modules = list(_active_modules(locked).select_for_update())
    count = len(active_modules)
    _require(
        count < MAX_ACTIVE_MODULES,
        CourseLimitExceeded,
        "La revisión alcanzó el máximo de módulos activos.",
    )
    locked_module.status = StructureStatus.ACTIVE
    locked_module.position = count + 1
    locked_module.archived_by = None
    locked_module.archived_at = None
    locked_module.updated_by = actor
    locked_module.save(
        update_fields=[
            "status",
            "position",
            "archived_by",
            "archived_at",
            "updated_by",
            "updated_at",
        ]
    )
    return locked_module, _finish(locked, actor)


@transaction.atomic
def create_unit(
    *,
    actor: Any,
    organization: Organization,
    module: CourseModule,
    expected_version: int,
    title: str,
    summary: str = "",
    estimated_duration_minutes: int | None = None,
) -> tuple[CourseUnit, CourseRevision]:
    _require_manage(actor, organization)
    locked_module = (
        CourseModule.objects.select_for_update()
        .select_related("revision__course__organization")
        .get(pk=module.pk)
    )
    locked = _lock_revision(
        actor=actor,
        revision=locked_module.revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(locked)
    _require(
        locked_module.status == StructureStatus.ACTIVE,
        CourseStructureInvalid,
        "No se puede añadir una unidad a un módulo archivado.",
    )
    units = list(_active_units(locked_module).select_for_update())
    _require(
        len(units) < MAX_ACTIVE_UNITS_PER_MODULE,
        CourseLimitExceeded,
        "El módulo alcanzó el máximo de unidades activas.",
    )
    unit = CourseUnit(
        module=locked_module,
        title=title,
        summary=summary,
        estimated_duration_minutes=estimated_duration_minutes,
        position=len(units) + 1,
        created_by=actor,
        updated_by=actor,
    )
    unit.full_clean()
    unit.save()
    activity = CourseActivity(
        id=unit.id,
        module=locked_module,
        activity_type=ActivityType.LESSON,
        lesson_unit=unit,
        title=unit.title,
        summary=unit.summary,
        estimated_duration_minutes=unit.estimated_duration_minutes,
        required=True,
        completion_method=ActivityCompletionMethod.VIEW,
        position=(
            CourseActivity.objects.filter(
                module=locked_module, status=StructureStatus.ACTIVE
            ).count()
            + 1
        ),
        created_by=actor,
        updated_by=actor,
    )
    activity.full_clean()
    activity.save()
    return unit, _finish(locked, actor)


@transaction.atomic
def create_activity(
    *,
    actor: Any,
    organization: Organization,
    module: CourseModule,
    expected_version: int,
    activity_type: ActivityType,
    title: str,
    summary: str = "",
    estimated_duration_minutes: int | None = None,
    required: bool = True,
    completion_method: ActivityCompletionMethod,
    minimum_attendance_basis_points: int | None = None,
    minimum_grade_basis_points: int | None = None,
) -> tuple[CourseActivity, CourseRevision]:
    _require_manage(actor, organization)
    _require(
        activity_type in {ActivityType.LIVE_CLASS, ActivityType.ASSESSMENT},
        CourseStructureInvalid,
        "Las lecciones se crean mediante el contrato de unidad.",
    )
    locked_module = (
        CourseModule.objects.select_for_update()
        .select_related("revision__course__organization")
        .get(pk=module.pk)
    )
    revision = _lock_revision(
        actor=actor,
        revision=locked_module.revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(revision)
    _require(
        locked_module.status == StructureStatus.ACTIVE,
        CourseStructureInvalid,
        "No se puede añadir una actividad a un módulo archivado.",
    )
    activity_count = (
        CourseActivity.objects.select_for_update()
        .filter(module=locked_module, status=StructureStatus.ACTIVE)
        .count()
    )
    _require(
        activity_count < MAX_ACTIVE_ACTIVITIES_PER_MODULE,
        CourseLimitExceeded,
        "El módulo alcanzó el máximo de actividades activas.",
    )
    activity = CourseActivity(
        module=locked_module,
        activity_type=activity_type,
        title=title,
        summary=summary,
        estimated_duration_minutes=estimated_duration_minutes,
        required=required,
        completion_method=completion_method,
        minimum_attendance_basis_points=minimum_attendance_basis_points,
        minimum_grade_basis_points=minimum_grade_basis_points,
        position=activity_count + 1,
        created_by=actor,
        updated_by=actor,
    )
    activity.full_clean()
    activity.save()
    return activity, _finish(revision, actor)


@transaction.atomic
def update_activity_configuration(
    *,
    actor: Any,
    organization: Organization,
    activity: CourseActivity,
    expected_version: int,
    title: str,
    summary: str,
    estimated_duration_minutes: int | None,
    required: bool,
    completion_method: ActivityCompletionMethod,
    minimum_attendance_basis_points: int | None,
    minimum_grade_basis_points: int | None,
) -> tuple[CourseActivity, CourseRevision]:
    _require_manage(actor, organization)
    locked_activity = (
        CourseActivity.objects.select_for_update()
        .select_related("module__revision__course__organization")
        .get(pk=activity.pk)
    )
    revision = _lock_revision(
        actor=actor,
        revision=locked_activity.module.revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(revision)
    _require(
        locked_activity.status == StructureStatus.ACTIVE,
        CourseStructureInvalid,
        "La actividad está archivada.",
    )
    locked_activity.title = title
    locked_activity.summary = summary
    locked_activity.estimated_duration_minutes = estimated_duration_minutes
    locked_activity.required = required
    locked_activity.completion_method = completion_method
    locked_activity.minimum_attendance_basis_points = minimum_attendance_basis_points
    locked_activity.minimum_grade_basis_points = minimum_grade_basis_points
    locked_activity.updated_by = actor
    locked_activity.full_clean()
    locked_activity.save(
        update_fields=(
            "title",
            "summary",
            "estimated_duration_minutes",
            "required",
            "completion_method",
            "minimum_attendance_basis_points",
            "minimum_grade_basis_points",
            "updated_by",
            "updated_at",
        )
    )
    return locked_activity, _finish(revision, actor)


@transaction.atomic
def replace_activity_order(
    *,
    actor: Any,
    organization: Organization,
    module: CourseModule,
    expected_version: int,
    ordered_ids: Sequence[UUID],
) -> CourseRevision:
    _require_manage(actor, organization)
    locked_module = (
        CourseModule.objects.select_for_update()
        .select_related("revision__course__organization")
        .get(pk=module.pk)
    )
    revision = _lock_revision(
        actor=actor,
        revision=locked_module.revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(revision)
    activities = list(
        CourseActivity.objects.select_for_update()
        .filter(module=locked_module, status=StructureStatus.ACTIVE)
        .order_by("position", "created_at")
    )
    _validate_order(ordered_ids, [activity.id for activity in activities])
    by_id = {activity.id: activity for activity in activities}
    for position, activity_id in enumerate(ordered_ids, start=1):
        by_id[activity_id].position = position
    CourseActivity.objects.bulk_update(activities, ["position"])
    return _finish(revision, actor)


@transaction.atomic
def move_activity_to_module(
    *,
    actor: Any,
    organization: Organization,
    activity: CourseActivity,
    target_module: CourseModule,
    expected_version: int,
) -> tuple[CourseActivity, CourseRevision]:
    _require_manage(actor, organization)
    locked_activity = (
        CourseActivity.objects.select_for_update()
        .select_related("module__revision__course__organization")
        .get(pk=activity.pk)
    )
    revision = _lock_revision(
        actor=actor,
        revision=locked_activity.module.revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(revision)
    locked_target = CourseModule.objects.select_for_update().get(pk=target_module.pk)
    _require(
        locked_target.revision_id == revision.id,
        CourseStructureInvalid,
        "El módulo de destino no pertenece a la revisión.",
    )
    _require(
        locked_activity.status == StructureStatus.ACTIVE
        and locked_target.status == StructureStatus.ACTIVE,
        CourseStructureInvalid,
        "La actividad y el módulo de destino deben estar activos.",
    )
    _require(
        locked_activity.activity_type != ActivityType.LESSON,
        CourseStructureInvalid,
        "Las lecciones se mueven junto con su unidad.",
    )
    _require(
        locked_activity.module_id != locked_target.id,
        CourseStructureInvalid,
        "La actividad ya pertenece a ese módulo.",
    )
    source_module_id = locked_activity.module_id
    source_position = locked_activity.position
    source_following = list(
        CourseActivity.objects.select_for_update().filter(
            module_id=source_module_id,
            status=StructureStatus.ACTIVE,
            position__gt=source_position,
        )
    )
    target_count = (
        CourseActivity.objects.select_for_update()
        .filter(module=locked_target, status=StructureStatus.ACTIVE)
        .count()
    )
    for row in source_following:
        row.position = (row.position or 1) - 1
    if source_following:
        CourseActivity.objects.bulk_update(source_following, ["position"])
    locked_activity.module = locked_target
    locked_activity.position = target_count + 1
    locked_activity.updated_by = actor
    locked_activity.full_clean()
    locked_activity.save(
        update_fields=("module", "position", "updated_by", "updated_at")
    )
    return locked_activity, _finish(revision, actor)


@transaction.atomic
def replace_activity_learning_objectives(
    *,
    actor: Any,
    organization: Organization,
    activity: CourseActivity,
    expected_version: int,
    learning_objectives: Sequence[LearningObjective],
) -> CourseRevision:
    _require_manage(actor, organization)
    locked_activity = (
        CourseActivity.objects.select_for_update()
        .select_related("module__revision__course__organization")
        .get(pk=activity.pk)
    )
    revision = _lock_revision(
        actor=actor,
        revision=locked_activity.module.revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(revision)
    _require(
        locked_activity.status == StructureStatus.ACTIVE,
        CourseStructureInvalid,
        "La actividad está archivada.",
    )
    _require(
        len({objective.id for objective in learning_objectives})
        == len(learning_objectives),
        CourseCurriculumAlignmentInvalid,
        "Los objetivos no pueden repetirse.",
    )
    aligned_ids = set(
        revision.objective_alignments.values_list("learning_objective_id", flat=True)
    )
    for objective in learning_objectives:
        _validate_catalog_entity(objective, organization)
        _require(
            objective.id in aligned_ids,
            CourseCurriculumAlignmentInvalid,
            "La actividad sólo puede usar objetivos alineados con el curso.",
        )
    locked_activity.objective_alignments.all().delete()
    CourseActivityLearningObjective.objects.bulk_create(
        [
            CourseActivityLearningObjective(
                activity=locked_activity,
                learning_objective=objective,
                position=position,
                created_by=actor,
            )
            for position, objective in enumerate(learning_objectives, start=1)
        ]
    )
    return _finish(revision, actor)


@transaction.atomic
def replace_activity_availability_rules(
    *,
    actor: Any,
    organization: Organization,
    activity: CourseActivity,
    expected_version: int,
    rules: Sequence[AvailabilityRuleInput],
) -> CourseRevision:
    _require_manage(actor, organization)
    locked_activity = (
        CourseActivity.objects.select_for_update()
        .select_related("module__revision__course__organization")
        .get(pk=activity.pk)
    )
    revision = _lock_revision(
        actor=actor,
        revision=locked_activity.module.revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(revision)
    locked_activity.availability_rules.all().delete()
    for position, rule_input in enumerate(rules, start=1):
        rule = CourseActivityAvailabilityRule(
            activity=locked_activity,
            rule_type=rule_input.rule_type,
            prerequisite_activity=rule_input.prerequisite_activity,
            learning_objective=rule_input.learning_objective,
            threshold_basis_points=rule_input.threshold_basis_points,
            available_at=rule_input.available_at,
            position=position,
            created_by=actor,
        )
        rule.full_clean()
        rule.save()
    issues = [
        issue
        for issue in revision_readiness_issues(revision)
        if issue["code"] == "activity_availability_cycle"
    ]
    if issues:
        raise CourseStructureInvalid(issues[0]["message"])
    return _finish(revision, actor)


@transaction.atomic
def confirm_completion_policy(
    *,
    actor: Any,
    organization: Organization,
    revision: CourseRevision,
    expected_version: int,
    require_required_activities: bool,
    minimum_grade_basis_points: int | None,
    minimum_attendance_basis_points: int | None,
) -> tuple[CourseCompletionPolicy, CourseRevision]:
    _require_manage(actor, organization)
    locked_revision = _lock_revision(
        actor=actor,
        revision=revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(locked_revision)
    policy = CourseCompletionPolicy.objects.select_for_update().get(
        revision=locked_revision
    )
    policy.require_required_activities = require_required_activities
    policy.minimum_grade_basis_points = minimum_grade_basis_points
    policy.minimum_attendance_basis_points = minimum_attendance_basis_points
    policy.confirmed_by = actor
    policy.confirmed_at = timezone.now()
    policy.lock_version += 1
    policy.updated_by = actor
    policy.full_clean()
    policy.save()
    finished_revision = _finish(locked_revision, actor)
    finished_revision._readiness_completion_policy = policy
    return policy, finished_revision


@transaction.atomic
def replace_grading_scheme(
    *,
    actor: Any,
    organization: Organization,
    revision: CourseRevision,
    expected_version: int,
    categories: Sequence[GradeCategoryInput],
) -> tuple[list[CourseGradeCategory], CourseRevision]:
    _require_manage(actor, organization)
    locked = _lock_revision(
        actor=actor,
        revision=revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(locked)
    _require(
        not categories
        or sum(category.weight_basis_points for category in categories) == 10_000,
        CourseStructureInvalid,
        "Los pesos de las categorías deben sumar 10000 puntos base.",
    )
    codes = [category.code for category in categories]
    _require(
        len(codes) == len(set(codes)),
        CourseStructureInvalid,
        "Los códigos de categoría deben ser únicos.",
    )
    activity_ids = [
        item.activity.id for category in categories for item in category.activities
    ]
    _require(
        len(activity_ids) == len(set(activity_ids)),
        CourseStructureInvalid,
        "Una evaluación sólo puede pertenecer a una categoría.",
    )
    for category in categories:
        _require(
            bool(category.activities)
            and sum(item.weight_basis_points for item in category.activities) == 10_000,
            CourseStructureInvalid,
            "Los pesos internos de cada categoría deben sumar 10000 puntos base.",
        )
        _require(
            all(
                item.activity.module.revision_id == locked.id
                and item.activity.activity_type == ActivityType.ASSESSMENT
                and item.activity.status == StructureStatus.ACTIVE
                for item in category.activities
            ),
            CourseStructureInvalid,
            "El esquema sólo admite evaluaciones activas de la misma revisión.",
        )
    CourseGradedActivity.objects.filter(category__revision=locked).delete()
    CourseGradeCategory.objects.filter(revision=locked).delete()
    created: list[CourseGradeCategory] = []
    for position, category_input in enumerate(categories, start=1):
        category = CourseGradeCategory(
            revision=locked,
            code=category_input.code,
            title=category_input.title,
            position=position,
            weight_basis_points=category_input.weight_basis_points,
            created_by=actor,
        )
        category.full_clean()
        category.save()
        for item_input in category_input.activities:
            item = CourseGradedActivity(
                category=category,
                activity=item_input.activity,
                weight_basis_points=item_input.weight_basis_points,
                required=item_input.required,
                created_by=actor,
            )
            item.full_clean()
            item.save()
        created.append(category)
    return created, _finish(locked, actor)


@transaction.atomic
def update_unit(
    *,
    actor: Any,
    organization: Organization,
    unit: CourseUnit,
    expected_version: int,
    topics: Sequence[Topic] | None = None,
    learning_objectives: Sequence[LearningObjective] | None = None,
    **changes: object,
) -> tuple[CourseUnit, CourseRevision]:
    _require_manage(actor, organization)
    locked_unit = (
        CourseUnit.objects.select_for_update()
        .select_related("module__revision__course__organization")
        .get(pk=unit.pk)
    )
    locked = _lock_revision(
        actor=actor,
        revision=locked_unit.module.revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(locked)
    _require(
        locked_unit.status == StructureStatus.ACTIVE
        and locked_unit.module.status == StructureStatus.ACTIVE,
        CourseStructureInvalid,
        "La unidad o su módulo están archivados.",
    )
    _require(
        set(changes) <= {"title", "summary", "estimated_duration_minutes"},
        CourseStructureInvalid,
        "La actualización contiene campos internos.",
    )
    if topics is not None:
        _validate_unit_topics(locked, topics)
    if learning_objectives is not None:
        _validate_unit_learning_objectives(locked, learning_objectives)
    for field, value in changes.items():
        setattr(locked_unit, field, value)
    if changes:
        locked_unit.updated_by = actor
        locked_unit.full_clean()
        locked_unit.save(update_fields=[*changes, "updated_by", "updated_at"])
    activity_changes = {
        field: value
        for field, value in changes.items()
        if field in {"title", "summary", "estimated_duration_minutes"}
    }
    if activity_changes:
        activity = CourseActivity.objects.select_for_update().get(
            lesson_unit=locked_unit
        )
        for field, value in activity_changes.items():
            setattr(activity, field, value)
        activity.updated_by = actor
        activity.full_clean()
        activity.save(update_fields=[*activity_changes, "updated_by", "updated_at"])
    if topics is not None:
        _replace_locked_unit_topics(locked_unit, topics, actor)
    if learning_objectives is not None:
        _replace_locked_unit_learning_objectives(
            locked_unit, learning_objectives, actor
        )
    return locked_unit, _finish(locked, actor)


@transaction.atomic
def replace_unit_order(
    *,
    actor: Any,
    organization: Organization,
    module: CourseModule,
    expected_version: int,
    ordered_ids: Sequence[UUID],
) -> CourseRevision:
    _require_manage(actor, organization)
    locked_module = (
        CourseModule.objects.select_for_update()
        .select_related("revision__course__organization")
        .get(pk=module.pk)
    )
    locked = _lock_revision(
        actor=actor,
        revision=locked_module.revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(locked)
    units = list(_active_units(locked_module).select_for_update())
    _validate_order(ordered_ids, [unit.id for unit in units])
    activities = list(
        CourseActivity.objects.select_for_update().filter(
            module=locked_module, status=StructureStatus.ACTIVE
        )
    )
    _require(
        len(activities) == len(units)
        and all(
            activity.activity_type == ActivityType.LESSON for activity in activities
        ),
        CourseStructureInvalid,
        "Usa el orden unificado cuando el módulo contiene otras actividades.",
    )
    by_id = {unit.id: unit for unit in units}
    for position, unit_id in enumerate(ordered_ids, start=1):
        by_id[unit_id].position = position
    CourseUnit.objects.bulk_update(units, ["position"])
    activities_by_unit = {activity.lesson_unit_id: activity for activity in activities}
    for position, unit_id in enumerate(ordered_ids, start=1):
        activities_by_unit[unit_id].position = position
    CourseActivity.objects.bulk_update(activities, ["position"])
    return _finish(locked, actor)


def _compact_units(module: CourseModule) -> None:
    units = list(_active_units(module).select_for_update())
    for position, unit in enumerate(units, start=1):
        unit.position = position
    CourseUnit.objects.bulk_update(units, ["position"])


def _compact_activities(module: CourseModule) -> None:
    activities = list(
        CourseActivity.objects.select_for_update()
        .filter(module=module, status=StructureStatus.ACTIVE)
        .order_by("position", "created_at")
    )
    for position, activity in enumerate(activities, start=1):
        activity.position = position
    CourseActivity.objects.bulk_update(activities, ["position"])


@transaction.atomic
def archive_unit(
    *,
    actor: Any,
    organization: Organization,
    unit: CourseUnit,
    expected_version: int,
) -> tuple[CourseUnit, CourseRevision]:
    _require_manage(actor, organization)
    locked_unit = (
        CourseUnit.objects.select_for_update()
        .select_related("module__revision__course__organization")
        .get(pk=unit.pk)
    )
    locked = _lock_revision(
        actor=actor,
        revision=locked_unit.module.revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(locked)
    _require(
        locked_unit.status == StructureStatus.ACTIVE,
        CourseStructureInvalid,
        "La unidad ya está archivada.",
    )
    locked_unit.status = StructureStatus.ARCHIVED
    locked_unit.position = None
    locked_unit.archived_by = actor
    locked_unit.archived_at = timezone.now()
    locked_unit.updated_by = actor
    locked_unit.save(
        update_fields=[
            "status",
            "position",
            "archived_by",
            "archived_at",
            "updated_by",
            "updated_at",
        ]
    )
    activity = CourseActivity.objects.select_for_update().get(lesson_unit=locked_unit)
    activity.status = StructureStatus.ARCHIVED
    activity.position = None
    activity.archived_by = actor
    activity.archived_at = locked_unit.archived_at
    activity.updated_by = actor
    activity.save(
        update_fields=[
            "status",
            "position",
            "archived_by",
            "archived_at",
            "updated_by",
            "updated_at",
        ]
    )
    _compact_units(locked_unit.module)
    _compact_activities(locked_unit.module)
    return locked_unit, _finish(locked, actor)


@transaction.atomic
def restore_unit(
    *,
    actor: Any,
    organization: Organization,
    unit: CourseUnit,
    expected_version: int,
) -> tuple[CourseUnit, CourseRevision]:
    _require_manage(actor, organization)
    locked_unit = (
        CourseUnit.objects.select_for_update()
        .select_related("module__revision__course__organization")
        .get(pk=unit.pk)
    )
    locked = _lock_revision(
        actor=actor,
        revision=locked_unit.module.revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(locked)
    _require(
        locked_unit.status == StructureStatus.ARCHIVED
        and locked_unit.module.status == StructureStatus.ACTIVE,
        CourseStructureInvalid,
        "La unidad no puede restaurarse en su estado actual.",
    )
    active_units = list(_active_units(locked_unit.module).select_for_update())
    count = len(active_units)
    _require(
        count < MAX_ACTIVE_UNITS_PER_MODULE,
        CourseLimitExceeded,
        "El módulo alcanzó el máximo de unidades activas.",
    )
    locked_unit.status = StructureStatus.ACTIVE
    locked_unit.position = count + 1
    locked_unit.archived_by = None
    locked_unit.archived_at = None
    locked_unit.updated_by = actor
    locked_unit.save(
        update_fields=[
            "status",
            "position",
            "archived_by",
            "archived_at",
            "updated_by",
            "updated_at",
        ]
    )
    activity = CourseActivity.objects.select_for_update().get(lesson_unit=locked_unit)
    activity.status = StructureStatus.ACTIVE
    activity.position = (
        CourseActivity.objects.filter(
            module=locked_unit.module, status=StructureStatus.ACTIVE
        ).count()
        + 1
    )
    activity.archived_by = None
    activity.archived_at = None
    activity.updated_by = actor
    activity.save(
        update_fields=[
            "status",
            "position",
            "archived_by",
            "archived_at",
            "updated_by",
            "updated_at",
        ]
    )
    return locked_unit, _finish(locked, actor)


def _locked_active_unit(
    *,
    actor: object,
    unit: CourseUnit,
    organization: Organization,
    expected_version: int,
) -> tuple[CourseUnit, CourseRevision]:
    locked_unit = (
        CourseUnit.objects.select_for_update()
        .select_related("module__revision__course__organization")
        .get(pk=unit.pk)
    )
    revision = _lock_revision(
        actor=actor,
        revision=locked_unit.module.revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(revision)
    _require(
        locked_unit.status == StructureStatus.ACTIVE
        and locked_unit.module.status == StructureStatus.ACTIVE,
        CourseStructureInvalid,
        "La unidad o su módulo están archivados.",
    )
    return locked_unit, revision


@transaction.atomic
def replace_unit_topics(
    *,
    actor: Any,
    organization: Organization,
    unit: CourseUnit,
    expected_version: int,
    topics: Sequence[Topic],
) -> CourseRevision:
    _require_manage(actor, organization)
    locked_unit, revision = _locked_active_unit(
        actor=actor,
        unit=unit,
        organization=organization,
        expected_version=expected_version,
    )
    _validate_unit_topics(revision, topics)
    _replace_locked_unit_topics(locked_unit, topics, actor)
    return _finish(revision, actor)


@transaction.atomic
def replace_unit_learning_objectives(
    *,
    actor: Any,
    organization: Organization,
    unit: CourseUnit,
    expected_version: int,
    learning_objectives: Sequence[LearningObjective],
) -> CourseRevision:
    _require_manage(actor, organization)
    locked_unit, revision = _locked_active_unit(
        actor=actor,
        unit=unit,
        organization=organization,
        expected_version=expected_version,
    )
    _validate_unit_learning_objectives(revision, learning_objectives)
    _replace_locked_unit_learning_objectives(locked_unit, learning_objectives, actor)
    return _finish(revision, actor)


def _validate_unit_topics(revision: CourseRevision, topics: Sequence[Topic]) -> None:
    _require(
        len({topic.id for topic in topics}) == len(topics),
        CourseCurriculumAlignmentInvalid,
        "Los temas no pueden repetirse.",
    )
    subject_ids = set(revision.subject_alignments.values_list("subject_id", flat=True))
    organization = revision.course.organization
    for topic in topics:
        _validate_catalog_entity(topic, organization)
        _require(
            topic.subject_id in subject_ids,
            CourseCurriculumAlignmentInvalid,
            "Cada tema debe pertenecer a una asignatura alineada.",
        )


def _replace_locked_unit_topics(
    unit: CourseUnit, topics: Sequence[Topic], actor: Any
) -> None:
    unit.topic_alignments.all().delete()
    CourseUnitTopic.objects.bulk_create(
        [
            CourseUnitTopic(unit=unit, topic=topic, position=index, created_by=actor)
            for index, topic in enumerate(topics, start=1)
        ]
    )


def _validate_unit_learning_objectives(
    revision: CourseRevision,
    learning_objectives: Sequence[LearningObjective],
) -> None:
    _require(
        len({item.id for item in learning_objectives}) == len(learning_objectives),
        CourseCurriculumAlignmentInvalid,
        "Los objetivos no pueden repetirse.",
    )
    aligned_ids = set(
        revision.objective_alignments.values_list("learning_objective_id", flat=True)
    )
    organization = revision.course.organization
    for objective in learning_objectives:
        _validate_catalog_entity(objective, organization)
        _require(
            objective.id in aligned_ids,
            CourseCurriculumAlignmentInvalid,
            "La unidad sólo puede usar objetivos alineados con el curso.",
        )


def _replace_locked_unit_learning_objectives(
    unit: CourseUnit,
    learning_objectives: Sequence[LearningObjective],
    actor: Any,
) -> None:
    unit.objective_alignments.all().delete()
    activity = CourseActivity.objects.select_for_update().get(lesson_unit=unit)
    activity.objective_alignments.all().delete()
    CourseUnitLearningObjective.objects.bulk_create(
        [
            CourseUnitLearningObjective(
                unit=unit,
                learning_objective=objective,
                position=index,
                created_by=actor,
            )
            for index, objective in enumerate(learning_objectives, start=1)
        ]
    )
    CourseActivityLearningObjective.objects.bulk_create(
        [
            CourseActivityLearningObjective(
                activity=activity,
                learning_objective=objective,
                position=index,
                created_by=actor,
            )
            for index, objective in enumerate(learning_objectives, start=1)
        ]
    )


def _transition(
    *,
    revision: CourseRevision,
    actor: Any,
    to_status: AuthoringStatus,
    note: str = "",
) -> CourseRevision:
    previous = AuthoringStatus(revision.authoring_status)
    revision.authoring_status = to_status
    revision.status_changed_at = timezone.now()
    revision.status_changed_by = actor
    revision.save(
        update_fields=[
            "authoring_status",
            "status_changed_at",
            "status_changed_by",
            "updated_at",
        ]
    )
    CourseRevisionTransition.objects.create(
        revision=revision,
        from_status=previous,
        to_status=to_status,
        actor=actor,
        note=note,
    )
    action = {
        AuthoringStatus.IN_REVIEW: "submitted",
        AuthoringStatus.CHANGES_REQUESTED: "changes_requested",
        AuthoringStatus.APPROVED: "approved",
    }.get(to_status)
    if action:
        record_domain_event(
            event_type=f"courses.revision.{action}.v1",
            organization=revision.course.organization,
            aggregate_type="revision",
            aggregate_id=revision.id,
            actor=actor,
            payload={
                "revision_id": str(revision.id),
                "course_id": str(revision.course_id),
            },
        )
    return _finish(revision, actor)


@transaction.atomic
def submit_revision_for_review(
    *,
    actor: Any,
    organization: Organization,
    revision: CourseRevision,
    expected_version: int,
    note: str = "",
) -> CourseRevision:
    _require(
        can_submit_revision(actor, organization),
        CourseAccessDenied,
        "No tienes capacidad para enviar la revisión.",
    )
    locked = _lock_revision(
        actor=actor,
        revision=revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(locked)
    issues = revision_readiness_issues(locked)
    if issues:
        raise CourseRevisionNotReady(issues)
    return _transition(
        revision=locked, actor=actor, to_status=AuthoringStatus.IN_REVIEW, note=note
    )


@transaction.atomic
def request_revision_changes(
    *,
    actor: Any,
    organization: Organization,
    revision: CourseRevision,
    expected_version: int,
    note: str,
) -> CourseRevision:
    _require(
        can_review_revision(actor, organization),
        CourseAccessDenied,
        "No tienes capacidad para revisar.",
    )
    locked = _lock_revision(
        actor=actor,
        revision=revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require(
        locked.authoring_status == AuthoringStatus.IN_REVIEW,
        CourseRevisionTransitionInvalid,
        "La revisión no está en revisión.",
    )
    _require(
        bool(note.strip()),
        CourseRevisionTransitionInvalid,
        "La nota es obligatoria.",
    )
    return _transition(
        revision=locked,
        actor=actor,
        to_status=AuthoringStatus.CHANGES_REQUESTED,
        note=note,
    )


@transaction.atomic
def approve_revision(
    *,
    actor: Any,
    organization: Organization,
    revision: CourseRevision,
    expected_version: int,
    note: str = "",
) -> CourseRevision:
    _require(
        can_approve_revision(actor, organization),
        CourseAccessDenied,
        "No tienes capacidad para aprobar.",
    )
    locked = _lock_revision(
        actor=actor,
        revision=revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require(
        locked.authoring_status == AuthoringStatus.IN_REVIEW,
        CourseRevisionTransitionInvalid,
        "La revisión no está en revisión.",
    )
    issues = revision_readiness_issues(locked)
    if issues:
        raise CourseRevisionNotReady(issues)
    return _transition(
        revision=locked, actor=actor, to_status=AuthoringStatus.APPROVED, note=note
    )


@transaction.atomic
def archive_course(*, actor: Any, organization: Organization, course: Course) -> Course:
    _require_manage(actor, organization)
    locked = (
        Course.objects.select_for_update()
        .select_related("organization")
        .get(pk=course.pk)
    )
    _require(
        locked.organization_id == organization.id,
        CourseCrossOrganizationRelation,
        "El curso pertenece a otra organización.",
    )
    _require(
        locked.status == CourseStatus.ACTIVE,
        CourseArchived,
        "El curso ya está archivado.",
    )
    _require(
        not locked.revisions.filter(
            authoring_status=AuthoringStatus.IN_REVIEW
        ).exists(),
        CourseRevisionTransitionInvalid,
        "No se puede archivar un curso con una revisión en revisión.",
    )
    locked.status = CourseStatus.ARCHIVED
    locked.archived_by = actor
    locked.archived_at = timezone.now()
    locked.save(update_fields=["status", "archived_by", "archived_at"])
    return locked


@transaction.atomic
def restore_course(*, actor: Any, organization: Organization, course: Course) -> Course:
    _require_manage(actor, organization)
    locked = (
        Course.objects.select_for_update()
        .select_related("organization")
        .get(pk=course.pk)
    )
    _require(
        locked.organization_id == organization.id,
        CourseCrossOrganizationRelation,
        "El curso pertenece a otra organización.",
    )
    _require(
        locked.status == CourseStatus.ARCHIVED,
        CourseStructureInvalid,
        "El curso no está archivado.",
    )
    locked.status = CourseStatus.ACTIVE
    locked.archived_by = None
    locked.archived_at = None
    locked.save(update_fields=["status", "archived_by", "archived_at"])
    return locked


@dataclass(frozen=True)
class RevisionStructureClone:
    revision: CourseRevision
    units_by_source_id: dict[UUID, CourseUnit]
    activities_by_source_id: dict[UUID, CourseActivity]


@transaction.atomic
def clone_approved_revision_structure(
    *, actor: Any, source_revision: CourseRevision
) -> RevisionStructureClone:
    """Clone only Courses-owned structure through a stable public contract."""

    source = (
        CourseRevision.objects.select_for_update()
        .select_related("course__organization")
        .prefetch_related(
            "subject_alignments",
            "objective_alignments",
            "modules__units__topic_alignments",
            "modules__units__objective_alignments",
            "modules__activities__objective_alignments",
            "modules__activities__availability_rules",
            "grade_categories__graded_activities",
        )
        .get(pk=source_revision.pk)
    )
    _require(
        source.authoring_status == AuthoringStatus.APPROVED,
        CourseRevisionTransitionInvalid,
        "Sólo una revisión aprobada puede clonarse.",
    )
    _require(
        can_manage_course(actor, source.course.organization),
        CourseAccessDenied,
        "No tienes capacidad para crear la revisión.",
    )
    course = Course.objects.select_for_update().get(pk=source.course_id)
    _require(
        course.status == CourseStatus.ACTIVE,
        CourseArchived,
        "El curso debe estar activo.",
    )
    if CourseRevision.objects.filter(
        course=course, authoring_status__in=OPEN_AUTHORING_STATUSES
    ).exists():
        raise CourseRevisionAlreadyOpen("El curso ya tiene una revisión abierta.")
    next_number = (
        CourseRevision.objects.filter(course=course)
        .order_by("-number")
        .values_list("number", flat=True)
        .first()
        or 0
    ) + 1
    now = timezone.now()
    revision = CourseRevision.objects.create(
        course=course,
        number=next_number,
        based_on_revision=source,
        title=source.title,
        subtitle=source.subtitle,
        summary=source.summary,
        description=source.description,
        language_code=source.language_code,
        estimated_duration_minutes=source.estimated_duration_minutes,
        authoring_status=AuthoringStatus.DRAFT,
        lock_version=1,
        status_changed_at=now,
        status_changed_by=actor,
        created_by=actor,
        updated_by=actor,
    )
    source_policy = source.completion_policy
    CourseCompletionPolicy.objects.create(
        revision=revision,
        require_required_activities=source_policy.require_required_activities,
        minimum_grade_basis_points=source_policy.minimum_grade_basis_points,
        minimum_attendance_basis_points=source_policy.minimum_attendance_basis_points,
        updated_by=actor,
    )
    CourseRevisionSubject.objects.bulk_create(
        [
            CourseRevisionSubject(
                revision=revision,
                subject=link.subject,
                alignment_type=link.alignment_type,
                position=link.position,
                created_by=actor,
            )
            for link in source.subject_alignments.all()
        ]
    )
    CourseRevisionLearningObjective.objects.bulk_create(
        [
            CourseRevisionLearningObjective(
                revision=revision,
                learning_objective=link.learning_objective,
                position=link.position,
                created_by=actor,
            )
            for link in source.objective_alignments.all()
        ]
    )
    units_by_source_id: dict[UUID, CourseUnit] = {}
    activities_by_source_id: dict[UUID, CourseActivity] = {}
    source_modules = sorted(
        (
            module
            for module in source.modules.all()
            if module.status == StructureStatus.ACTIVE
        ),
        key=lambda module: module.position or 0,
    )
    for source_module in source_modules:
        module = CourseModule.objects.create(
            revision=revision,
            title=source_module.title,
            description=source_module.description,
            status=StructureStatus.ACTIVE,
            position=source_module.position,
            created_by=actor,
            updated_by=actor,
        )
        source_units = sorted(
            (
                unit
                for unit in source_module.units.all()
                if unit.status == StructureStatus.ACTIVE
            ),
            key=lambda unit: unit.position or 0,
        )
        source_activities = sorted(
            (
                activity
                for activity in source_module.activities.all()
                if activity.status == StructureStatus.ACTIVE
            ),
            key=lambda activity: activity.position or 0,
        )
        lesson_activities_by_unit_id = {
            activity.lesson_unit_id: activity
            for activity in source_activities
            if activity.activity_type == ActivityType.LESSON
        }
        for source_unit in source_units:
            unit = CourseUnit.objects.create(
                module=module,
                title=source_unit.title,
                summary=source_unit.summary,
                estimated_duration_minutes=source_unit.estimated_duration_minutes,
                status=StructureStatus.ACTIVE,
                position=source_unit.position,
                created_by=actor,
                updated_by=actor,
            )
            units_by_source_id[source_unit.id] = unit
            CourseUnitTopic.objects.bulk_create(
                [
                    CourseUnitTopic(
                        unit=unit,
                        topic=link.topic,
                        position=link.position,
                        created_by=actor,
                    )
                    for link in source_unit.topic_alignments.all()
                ]
            )
            CourseUnitLearningObjective.objects.bulk_create(
                [
                    CourseUnitLearningObjective(
                        unit=unit,
                        learning_objective=link.learning_objective,
                        position=link.position,
                        created_by=actor,
                    )
                    for link in source_unit.objective_alignments.all()
                ]
            )
            source_activity = lesson_activities_by_unit_id[source_unit.id]
            activity = CourseActivity.objects.create(
                id=unit.id,
                module=module,
                activity_type=ActivityType.LESSON,
                lesson_unit=unit,
                title=source_activity.title,
                summary=source_activity.summary,
                estimated_duration_minutes=source_activity.estimated_duration_minutes,
                required=source_activity.required,
                completion_method=source_activity.completion_method,
                minimum_grade_basis_points=source_activity.minimum_grade_basis_points,
                minimum_attendance_basis_points=(
                    source_activity.minimum_attendance_basis_points
                ),
                status=StructureStatus.ACTIVE,
                position=source_activity.position,
                created_by=actor,
                updated_by=actor,
            )
            activities_by_source_id[source_activity.id] = activity
            CourseActivityLearningObjective.objects.bulk_create(
                [
                    CourseActivityLearningObjective(
                        activity=activity,
                        learning_objective=link.learning_objective,
                        position=link.position,
                        created_by=actor,
                    )
                    for link in source_activity.objective_alignments.all()
                ]
            )
        for source_activity in source_activities:
            if source_activity.activity_type == ActivityType.LESSON:
                continue
            activity = CourseActivity.objects.create(
                module=module,
                activity_type=source_activity.activity_type,
                title=source_activity.title,
                summary=source_activity.summary,
                estimated_duration_minutes=source_activity.estimated_duration_minutes,
                required=source_activity.required,
                completion_method=source_activity.completion_method,
                minimum_grade_basis_points=source_activity.minimum_grade_basis_points,
                minimum_attendance_basis_points=(
                    source_activity.minimum_attendance_basis_points
                ),
                status=StructureStatus.ACTIVE,
                position=source_activity.position,
                created_by=actor,
                updated_by=actor,
            )
            activities_by_source_id[source_activity.id] = activity
            CourseActivityLearningObjective.objects.bulk_create(
                [
                    CourseActivityLearningObjective(
                        activity=activity,
                        learning_objective=link.learning_objective,
                        position=link.position,
                        created_by=actor,
                    )
                    for link in source_activity.objective_alignments.all()
                ]
            )
            clone_activity_binding(source=source_activity, target=activity, actor=actor)

    for source_module in source_modules:
        for source_activity in source_module.activities.all():
            target_activity = activities_by_source_id.get(source_activity.id)
            if target_activity is None:
                continue
            CourseActivityAvailabilityRule.objects.bulk_create(
                [
                    CourseActivityAvailabilityRule(
                        activity=target_activity,
                        rule_type=rule.rule_type,
                        prerequisite_activity=activities_by_source_id.get(
                            rule.prerequisite_activity_id
                        ),
                        learning_objective=rule.learning_objective,
                        threshold_basis_points=rule.threshold_basis_points,
                        available_at=rule.available_at,
                        position=rule.position,
                        created_by=actor,
                    )
                    for rule in source_activity.availability_rules.all()
                ]
            )

    for source_category in source.grade_categories.all():
        category = CourseGradeCategory.objects.create(
            revision=revision,
            code=source_category.code,
            title=source_category.title,
            position=source_category.position,
            weight_basis_points=source_category.weight_basis_points,
            created_by=actor,
        )
        CourseGradedActivity.objects.bulk_create(
            [
                CourseGradedActivity(
                    category=category,
                    activity=activities_by_source_id[item.activity_id],
                    weight_basis_points=item.weight_basis_points,
                    required=item.required,
                    created_by=actor,
                )
                for item in source_category.graded_activities.all()
                if item.activity_id in activities_by_source_id
            ]
        )
    CourseRevisionTransition.objects.create(
        revision=revision,
        from_status=None,
        to_status=AuthoringStatus.DRAFT,
        actor=actor,
        note="Revisión creada desde un release inmutable.",
    )
    return RevisionStructureClone(revision, units_by_source_id, activities_by_source_id)
