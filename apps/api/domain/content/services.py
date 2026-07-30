# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.db import IntegrityError, transaction

from domain.courses.choices import EDITABLE_AUTHORING_STATUSES, CourseStatus
from domain.courses.models import CourseRevision, CourseUnit
from domain.courses.policies import can_manage_course
from domain.organizations.models import Organization

from .exceptions import (
    ContentAccessDenied,
    ContentDocumentConflict,
    ContentNotEditable,
    ContentRestoreInvalid,
    ContentSchemaUnsupported,
    ContentVersionNotFound,
)
from .models import UnitContentDocument, UnitContentVersion
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
    document = _locked_document(locked_unit)
    current_number = _expected_version(document, expected_document_version)
    validated = validate_content(content, schema_version=schema_version)
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
    document = _locked_document(locked_unit)
    current_number = _expected_version(document, expected_document_version)
    if document is None:
        raise ContentRestoreInvalid("No existe un documento que pueda restaurarse.")
    historical = UnitContentVersion.objects.filter(
        document=document, number=version_number
    ).first()
    if historical is None:
        raise ContentVersionNotFound("La versión solicitada no existe.")
    if historical.schema_version != CURRENT_CONTENT_SCHEMA_VERSION:
        raise ContentSchemaUnsupported(
            "La versión histórica requiere una migración explícita.",
            path="schema_version",
        )
    migrated = migrate_document(
        historical.content,
        from_version=historical.schema_version,
        to_version=CURRENT_CONTENT_SCHEMA_VERSION,
    )
    validated = validate_content(
        migrated, schema_version=CURRENT_CONTENT_SCHEMA_VERSION
    )
    version = _append_version(
        document=document,
        validated=validated,
        schema_version=CURRENT_CONTENT_SCHEMA_VERSION,
        number=current_number + 1,
        actor=actor,
    )
    return SaveContentResult(document, version, False)
