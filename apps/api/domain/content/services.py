# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from django.db import IntegrityError, transaction

from domain.assets.models import AssetVersion
from domain.courses.choices import (
    EDITABLE_AUTHORING_STATUSES,
    CourseStatus,
    LessonKind,
)
from domain.courses.models import CourseRevision, CourseUnit
from domain.courses.policies import can_manage_course
from domain.organizations.models import Organization

from .asset_references import create_asset_references, validate_asset_references
from .canonical import deep_json_copy
from .exceptions import (
    ContentAccessDenied,
    ContentDeliveryInvalid,
    ContentDocumentConflict,
    ContentNotApplicable,
    ContentNotEditable,
    ContentRestoreInvalid,
    ContentVersionNotFound,
)
from .lesson_resources import validate_lesson_resource
from .models import UnitContentDocument, UnitContentVersion, UnitLessonResource
from .schemas import CURRENT_CONTENT_SCHEMA_VERSION, migrate_document
from .validators import ValidatedContent, validate_content


@dataclass(frozen=True)
class SaveContentResult:
    document: UnitContentDocument
    version: UnitContentVersion
    no_op: bool


def _require(condition: bool, error: type[Exception], message: str) -> None:
    if not condition:
        raise error(message)


def _finish_revision(revision: CourseRevision, actor: Any) -> CourseRevision:
    """Advance authoring concurrency after a delivery-resource mutation."""

    revision.lock_version += 1
    revision.updated_by = actor
    revision.save(update_fields=["lock_version", "updated_by", "updated_at"])
    return revision


def _lock_context(
    *,
    actor: object,
    organization: Organization,
    revision: CourseRevision,
    unit: CourseUnit,
) -> tuple[CourseRevision, CourseUnit]:
    locked_revision = (
        CourseRevision.objects.select_for_update()
        .select_related("course__organization")
        .get(pk=revision.pk)
    )
    _require(
        locked_revision.course.organization_id == organization.id,
        ContentAccessDenied,
        "La revisión no pertenece a la organización.",
    )
    _require(
        can_manage_course(actor, locked_revision.course.organization),
        ContentAccessDenied,
        "No tienes capacidad para editar contenido.",
    )
    _require(
        locked_revision.course.status == CourseStatus.ACTIVE
        and locked_revision.authoring_status in EDITABLE_AUTHORING_STATUSES,
        ContentNotEditable,
        "La revisión no admite cambios de contenido.",
    )
    locked_unit = (
        CourseUnit.objects.select_for_update()
        .select_related("module__revision")
        .get(pk=unit.pk)
    )
    _require(
        locked_unit.module.revision_id == locked_revision.id,
        ContentAccessDenied,
        "La unidad no pertenece a la revisión.",
    )
    return locked_revision, locked_unit


def _locked_document(unit: CourseUnit) -> UnitContentDocument | None:
    return (
        UnitContentDocument.objects.select_for_update(of=("self",))
        .select_related("current_version")
        .filter(unit=unit)
        .first()
    )


def _expected_version(
    document: UnitContentDocument | None, expected_document_version: int
) -> int:
    current_number = (
        document.current_version.number
        if document is not None and document.current_version is not None
        else 0
    )
    if expected_document_version != current_number:
        raise ContentDocumentConflict(
            "El contenido cambió desde que abriste el editor.",
            current_version=current_number,
        )
    return current_number


def _append_version(
    *,
    document: UnitContentDocument,
    validated: ValidatedContent,
    schema_version: int,
    number: int,
    actor: Any,
) -> UnitContentVersion:
    version = UnitContentVersion.objects.create(
        document=document,
        number=number,
        schema_version=schema_version,
        content=validated.content,
        plain_text=validated.metrics.plain_text,
        character_count=validated.metrics.character_count,
        word_count=validated.metrics.word_count,
        node_count=validated.metrics.node_count,
        digest=validated.digest,
        created_by=actor,
    )
    document.current_version = version
    document.updated_by = actor
    document.save(update_fields=["current_version", "updated_by", "updated_at"])
    return version


@transaction.atomic
def save_unit_content(
    *,
    actor: Any,
    organization: Organization,
    revision: CourseRevision,
    unit: CourseUnit,
    expected_document_version: int,
    schema_version: int,
    content: object,
) -> SaveContentResult:
    _locked_revision, locked_unit = _lock_context(
        actor=actor, organization=organization, revision=revision, unit=unit
    )
    _require(
        locked_unit.lesson_kind == LessonKind.DOCUMENT,
        ContentNotApplicable,
        "Sólo una lección de documento admite contenido semántico.",
    )
    document = _locked_document(locked_unit)
    current_number = _expected_version(document, expected_document_version)
    validated = validate_content(content, schema_version=schema_version)
    references = validate_asset_references(validated.content, organization=organization)
    if (
        document is not None
        and document.current_version is not None
        and document.current_version.digest == validated.digest
        and document.current_version.schema_version == schema_version
    ):
        return SaveContentResult(document, document.current_version, True)
    if document is None:
        try:
            with transaction.atomic():
                document = UnitContentDocument.objects.create(
                    unit=locked_unit, created_by=actor, updated_by=actor
                )
        except IntegrityError:
            document = _locked_document(locked_unit)
            if document is None:
                raise
            current_number = _expected_version(document, expected_document_version)
    version = _append_version(
        document=document,
        validated=validated,
        schema_version=schema_version,
        number=current_number + 1,
        actor=actor,
    )
    create_asset_references(version, references)
    return SaveContentResult(document, version, False)


@transaction.atomic
def restore_unit_content(
    *,
    actor: Any,
    organization: Organization,
    revision: CourseRevision,
    unit: CourseUnit,
    expected_document_version: int,
    version_number: int,
) -> SaveContentResult:
    _locked_revision, locked_unit = _lock_context(
        actor=actor, organization=organization, revision=revision, unit=unit
    )
    _require(
        locked_unit.lesson_kind == LessonKind.DOCUMENT,
        ContentNotApplicable,
        "Sólo una lección de documento admite contenido semántico.",
    )
    document = _locked_document(locked_unit)
    current_number = _expected_version(document, expected_document_version)
    if document is None:
        raise ContentRestoreInvalid("No existe un documento que pueda restaurarse.")
    historical = UnitContentVersion.objects.filter(
        document=document, number=version_number
    ).first()
    if historical is None:
        raise ContentVersionNotFound("La versión solicitada no existe.")
    migrated = migrate_document(
        historical.content,
        from_version=historical.schema_version,
        to_version=CURRENT_CONTENT_SCHEMA_VERSION,
    )
    validated = validate_content(
        migrated, schema_version=CURRENT_CONTENT_SCHEMA_VERSION
    )
    references = validate_asset_references(validated.content, organization=organization)
    version = _append_version(
        document=document,
        validated=validated,
        schema_version=CURRENT_CONTENT_SCHEMA_VERSION,
        number=current_number + 1,
        actor=actor,
    )
    create_asset_references(version, references)
    return SaveContentResult(document, version, False)


@transaction.atomic
def clone_current_unit_documents(
    *, actor: Any, units_by_source_id: dict[UUID, CourseUnit]
) -> list[UnitContentDocument]:
    """Clone current content only; historical versions never cross the boundary."""

    source_ids = list(units_by_source_id)
    documents = list(
        UnitContentDocument.objects.select_for_update(of=("self",))
        .select_related("current_version")
        .filter(unit_id__in=source_ids, unit__lesson_kind=LessonKind.DOCUMENT)
    )
    document_source_ids = {
        source_id
        for source_id, unit in units_by_source_id.items()
        if unit.lesson_kind == LessonKind.DOCUMENT
    }
    if len(documents) != len(document_source_ids):
        raise ContentRestoreInvalid(
            "No todas las lecciones de documento tienen contenido vigente."
        )
    created: list[UnitContentDocument] = []
    by_source = {document.unit_id: document for document in documents}
    for source_id in source_ids:
        if source_id not in document_source_ids:
            continue
        source_document = by_source[source_id]
        source_version = source_document.current_version
        if source_version is None:
            raise ContentRestoreInvalid(
                "Una unidad fuente no tiene versión de contenido vigente."
            )
        validated = validate_content(
            deep_json_copy(source_version.content),
            schema_version=source_version.schema_version,
        )
        if validated.digest != source_version.digest:
            raise ContentRestoreInvalid(
                "El contenido fuente no supera la verificación de integridad."
            )
        target = units_by_source_id[source_id]
        references = validate_asset_references(
            validated.content,
            organization=target.module.revision.course.organization,
        )
        target_document = UnitContentDocument.objects.create(
            unit=target,
            created_by=actor,
            updated_by=actor,
        )
        cloned_version = _append_version(
            document=target_document,
            validated=validated,
            schema_version=source_version.schema_version,
            number=1,
            actor=actor,
        )
        create_asset_references(cloned_version, references)
        created.append(target_document)
    return created


@transaction.atomic
def configure_unit_lesson_resource(
    *,
    actor: Any,
    organization: Organization,
    revision: CourseRevision,
    unit: CourseUnit,
    expected_version: int,
    asset_version_id: UUID,
) -> tuple[UnitLessonResource, CourseRevision]:
    """Bind exactly one READY private asset to a typed lesson."""

    locked_revision, locked_unit = _lock_context(
        actor=actor, organization=organization, revision=revision, unit=unit
    )
    if locked_revision.lock_version != expected_version:
        raise ContentDocumentConflict(
            "La revisión cambió desde que abriste la configuración.",
            current_version=locked_revision.lock_version,
            path="expected_version",
        )
    version = (
        AssetVersion.objects.select_for_update()
        .select_related("asset__organization")
        .filter(pk=asset_version_id)
        .first()
    )
    if version is None:
        raise ContentDeliveryInvalid(
            "La versión de archivo no existe.", path="asset_version_id"
        )
    validate_lesson_resource(unit=locked_unit, version=version)
    binding, created = UnitLessonResource.objects.select_for_update().get_or_create(
        unit=locked_unit,
        defaults={
            "asset_version": version,
            "created_by": actor,
            "updated_by": actor,
        },
    )
    if not created:
        binding.asset_version = version
        binding.updated_by = actor
        binding.save(update_fields=["asset_version", "updated_by", "updated_at"])
    return binding, _finish_revision(locked_revision, actor)


@transaction.atomic
def remove_unit_lesson_resource(
    *,
    actor: Any,
    organization: Organization,
    revision: CourseRevision,
    unit: CourseUnit,
    expected_version: int,
) -> CourseRevision:
    locked_revision, locked_unit = _lock_context(
        actor=actor, organization=organization, revision=revision, unit=unit
    )
    if locked_revision.lock_version != expected_version:
        raise ContentDocumentConflict(
            "La revisión cambió desde que abriste la configuración.",
            current_version=locked_revision.lock_version,
            path="expected_version",
        )
    if locked_unit.lesson_kind == LessonKind.DOCUMENT:
        raise ContentNotApplicable(
            "Una lección de documento no tiene un archivo de entrega único."
        )
    if locked_unit.lesson_kind == LessonKind.MEDIACMS_VIDEO:
        raise ContentNotApplicable(
            "Una lección MediaCMS se configura con su vídeo privado."
        )
    UnitLessonResource.objects.select_for_update().filter(unit=locked_unit).delete()
    return _finish_revision(locked_revision, actor)


@transaction.atomic
def clone_current_unit_lesson_resources(
    *, actor: Any, units_by_source_id: dict[UUID, CourseUnit]
) -> list[UnitLessonResource]:
    """Clone typed-resource bindings; release snapshots pin the same immutable version."""

    source_ids = list(units_by_source_id)
    resources = list(
        UnitLessonResource.objects.select_for_update(of=("self",))
        .select_related("asset_version__asset", "unit")
        .filter(unit_id__in=source_ids)
    )
    by_source_id = {resource.unit_id: resource for resource in resources}
    created: list[UnitLessonResource] = []
    for source_id in sorted(by_source_id, key=str):
        source = by_source_id[source_id]
        target = units_by_source_id[source_id]
        validate_lesson_resource(unit=target, version=source.asset_version)
        created.append(
            UnitLessonResource.objects.create(
                unit=target,
                asset_version=source.asset_version,
                created_by=actor,
                updated_by=actor,
            )
        )
    return created
