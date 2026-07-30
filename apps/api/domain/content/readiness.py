# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from django.core.exceptions import ObjectDoesNotExist

from domain.courses.choices import StructureStatus
from domain.courses.models import CourseRevision, CourseUnit

from .canonical import content_digest
from .exceptions import ContentDomainError
from .extraction import has_meaningful_content
from .models import UnitContentDocument
from .schemas import CURRENT_CONTENT_SCHEMA_VERSION
from .validators import validate_content


def enrich_content_outline(revision: CourseRevision) -> None:
    metadata = {
        row["unit_id"]: row
        for row in UnitContentDocument.objects.filter(
            unit__module__revision=revision
        ).values(
            "unit_id",
            "current_version__number",
            "current_version__character_count",
            "updated_at",
        )
    }
    for module in revision.modules.all():
        for unit in module.units.all():
            row = metadata.get(unit.id)
            if row is None or row["current_version__number"] is None:
                unit.content_status = "missing"
                unit.content_version = None
                unit.content_updated_at = None
            else:
                unit.content_status = (
                    "ready" if row["current_version__character_count"] > 0 else "empty"
                )
                unit.content_version = row["current_version__number"]
                unit.content_updated_at = row["updated_at"]


def content_readiness_issues(revision: CourseRevision) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    units = (
        CourseUnit.objects.filter(
            module__revision=revision,
            module__status=StructureStatus.ACTIVE,
            status=StructureStatus.ACTIVE,
        )
        .select_related("module", "content_document__current_version")
        .order_by("module__position", "position", "id")
    )
    for unit in units:
        path = f"modules.{unit.module_id}.units.{unit.id}.content"
        try:
            document = unit.content_document
        except ObjectDoesNotExist:
            document = None
        if document is None or document.current_version is None:
            issues.append(
                {
                    "code": "unit_content_missing",
                    "path": path,
                    "message": f"La unidad «{unit.title}» todavía no tiene contenido académico.",
                }
            )
            continue
        current = document.current_version
        if current.schema_version != CURRENT_CONTENT_SCHEMA_VERSION:
            issues.append(
                {
                    "code": "unit_content_schema_unsupported",
                    "path": path,
                    "message": f"El contenido de «{unit.title}» usa un schema no soportado.",
                }
            )
            continue
        if content_digest(current.content) != current.digest:
            issues.append(
                {
                    "code": "unit_content_digest_mismatch",
                    "path": path,
                    "message": f"El contenido de «{unit.title}» no supera la verificación de integridad.",
                }
            )
            continue
        try:
            validate_content(current.content, schema_version=current.schema_version)
        except ContentDomainError:
            issues.append(
                {
                    "code": "unit_content_invalid",
                    "path": path,
                    "message": f"El contenido de «{unit.title}» ya no cumple el contrato.",
                }
            )
            continue
        if not has_meaningful_content(current.content):
            issues.append(
                {
                    "code": "unit_content_empty",
                    "path": path,
                    "message": f"La unidad «{unit.title}» no contiene contenido académico significativo.",
                }
            )
    return issues
