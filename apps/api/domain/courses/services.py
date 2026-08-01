# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportUnknownLambdaType=false
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
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
from domain.organizations.models import Organization

from .choices import (
    EDITABLE_AUTHORING_STATUSES,
    OPEN_AUTHORING_STATUSES,
    AuthoringStatus,
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
    CourseModule,
    CourseRevision,
    CourseRevisionLearningObjective,
    CourseRevisionSubject,
    CourseRevisionTransition,
    CourseUnit,
    CourseUnitLearningObjective,
    CourseUnitTopic,
)
from .policies import (
    can_approve_revision,
    can_manage_course,
    can_review_revision,
    can_submit_revision,
)
from .readiness import revision_readiness_issues

MAX_ACTIVE_MODULES = 100
MAX_ACTIVE_UNITS_PER_MODULE = 200


def _require(condition: bool, error: type[Exception], message: str) -> None:
    if not condition:
        raise error(message)


def _require_manage(actor: object, organization: Organization) -> None:
    _require(
        can_manage_course(actor, organization),
        CourseAccessDenied,
        "No tienes capacidad para administrar cursos.",
    )


def _lock_revision(
    *,
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
    return unit, _finish(locked, actor)


@transaction.atomic
def update_unit(
    *,
    actor: Any,
    organization: Organization,
    unit: CourseUnit,
    expected_version: int,
    **changes: object,
) -> tuple[CourseUnit, CourseRevision]:
    _require_manage(actor, organization)
    locked_unit = (
        CourseUnit.objects.select_for_update()
        .select_related("module__revision__course__organization")
        .get(pk=unit.pk)
    )
    locked = _lock_revision(
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
    for field, value in changes.items():
        setattr(locked_unit, field, value)
    locked_unit.updated_by = actor
    locked_unit.full_clean()
    locked_unit.save(update_fields=[*changes, "updated_by", "updated_at"])
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
        revision=locked_module.revision,
        organization=organization,
        expected_version=expected_version,
    )
    _require_editable(locked)
    units = list(_active_units(locked_module).select_for_update())
    _validate_order(ordered_ids, [unit.id for unit in units])
    by_id = {unit.id: unit for unit in units}
    for position, unit_id in enumerate(ordered_ids, start=1):
        by_id[unit_id].position = position
    CourseUnit.objects.bulk_update(units, ["position"])
    return _finish(locked, actor)


def _compact_units(module: CourseModule) -> None:
    units = list(_active_units(module).select_for_update())
    for position, unit in enumerate(units, start=1):
        unit.position = position
    CourseUnit.objects.bulk_update(units, ["position"])


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
    _compact_units(locked_unit.module)
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
    return locked_unit, _finish(locked, actor)


def _locked_active_unit(
    *, unit: CourseUnit, organization: Organization, expected_version: int
) -> tuple[CourseUnit, CourseRevision]:
    locked_unit = (
        CourseUnit.objects.select_for_update()
        .select_related("module__revision__course__organization")
        .get(pk=unit.pk)
    )
    revision = _lock_revision(
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
        unit=unit, organization=organization, expected_version=expected_version
    )
    _require(
        len({topic.id for topic in topics}) == len(topics),
        CourseCurriculumAlignmentInvalid,
        "Los temas no pueden repetirse.",
    )
    subject_ids = set(revision.subject_alignments.values_list("subject_id", flat=True))
    for topic in topics:
        _validate_catalog_entity(topic, organization)
        _require(
            topic.subject_id in subject_ids,
            CourseCurriculumAlignmentInvalid,
            "Cada tema debe pertenecer a una asignatura alineada.",
        )
    locked_unit.topic_alignments.all().delete()
    CourseUnitTopic.objects.bulk_create(
        [
            CourseUnitTopic(
                unit=locked_unit, topic=topic, position=index, created_by=actor
            )
            for index, topic in enumerate(topics, start=1)
        ]
    )
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
        unit=unit, organization=organization, expected_version=expected_version
    )
    _require(
        len({item.id for item in learning_objectives}) == len(learning_objectives),
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
            "La unidad sólo puede usar objetivos alineados con el curso.",
        )
    locked_unit.objective_alignments.all().delete()
    CourseUnitLearningObjective.objects.bulk_create(
        [
            CourseUnitLearningObjective(
                unit=locked_unit,
                learning_objective=objective,
                position=index,
                created_by=actor,
            )
            for index, objective in enumerate(learning_objectives, start=1)
        ]
    )
    return _finish(revision, actor)


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
    CourseRevisionTransition.objects.create(
        revision=revision,
        from_status=None,
        to_status=AuthoringStatus.DRAFT,
        actor=actor,
        note="Revisión creada desde un release inmutable.",
    )
    return RevisionStructureClone(revision, units_by_source_id)
