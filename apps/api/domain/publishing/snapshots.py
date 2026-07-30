# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from typing import Any

from django.db.models import Prefetch

from domain.content.canonical import content_digest
from domain.content.models import UnitContentDocument
from domain.content.validators import validate_content
from domain.courses.choices import AuthoringStatus, CourseStatus, StructureStatus
from domain.courses.models import (
    CourseModule,
    CourseRevision,
    CourseRevisionLearningObjective,
    CourseRevisionSubject,
    CourseUnit,
    CourseUnitLearningObjective,
    CourseUnitTopic,
)

from .canonical import canonical_json_bytes, deep_json_copy
from .exceptions import (
    ReleaseSnapshotInvalid,
    ReleaseSnapshotTooLarge,
    ReleaseSourceNotApproved,
)
from .limits import (
    MAX_CANONICAL_BYTES,
    MAX_LEARNING_OBJECTIVES,
    MAX_MODULES,
    MAX_TOPIC_REFERENCES,
    MAX_UNITS,
)
from .schemas import CURRENT_RELEASE_SCHEMA_VERSION, validate_release_snapshot


def release_revision_queryset():
    topic_links = CourseUnitTopic.objects.select_related("topic__subject").order_by(
        "position"
    )
    objective_links = CourseUnitLearningObjective.objects.select_related(
        "learning_objective"
    ).order_by("position")
    documents = UnitContentDocument.objects.select_related("current_version")
    units = (
        CourseUnit.objects.filter(status=StructureStatus.ACTIVE)
        .prefetch_related(
            Prefetch("topic_alignments", queryset=topic_links),
            Prefetch("objective_alignments", queryset=objective_links),
            Prefetch("content_document", queryset=documents),
        )
        .order_by("position", "id")
    )
    modules = (
        CourseModule.objects.filter(status=StructureStatus.ACTIVE)
        .prefetch_related(Prefetch("units", queryset=units))
        .order_by("position", "id")
    )
    return CourseRevision.objects.select_related(
        "course__organization"
    ).prefetch_related(
        Prefetch(
            "subject_alignments",
            queryset=CourseRevisionSubject.objects.select_related("subject").order_by(
                "position"
            ),
        ),
        Prefetch(
            "objective_alignments",
            queryset=CourseRevisionLearningObjective.objects.select_related(
                "learning_objective"
            ).order_by("position"),
        ),
        Prefetch("modules", queryset=modules),
    )


def load_release_revision(revision: CourseRevision) -> CourseRevision:
    return release_revision_queryset().get(pk=revision.pk)


def _content_snapshot(unit: CourseUnit) -> dict[str, Any]:
    try:
        document = unit.content_document
    except UnitContentDocument.DoesNotExist as error:
        raise ReleaseSnapshotInvalid(
            f"La unidad {unit.id} no tiene documento de contenido."
        ) from error
    version = document.current_version
    if version is None:
        raise ReleaseSnapshotInvalid(
            f"La unidad {unit.id} no tiene versión de contenido vigente."
        )
    validated = validate_content(version.content, schema_version=version.schema_version)
    if (
        validated.digest != version.digest
        or content_digest(version.content) != version.digest
    ):
        raise ReleaseSnapshotInvalid(
            f"El digest de contenido de la unidad {unit.id} es inválido."
        )
    return {
        "schema_version": version.schema_version,
        "document_version": version.number,
        "digest": version.digest,
        "character_count": version.character_count,
        "word_count": version.word_count,
        "node_count": version.node_count,
        "document": deep_json_copy(version.content),
    }


def build_release_snapshot(
    *,
    revision: CourseRevision,
    release_number: int,
    previous_release_digest: str | None,
) -> tuple[dict[str, Any], bytes]:
    if (
        revision.authoring_status != AuthoringStatus.APPROVED
        or revision.course.status != CourseStatus.ACTIVE
    ):
        raise ReleaseSourceNotApproved(
            "La revisión debe estar aprobada y el curso activo."
        )
    subjects = [
        {
            "id": str(link.subject_id),
            "slug": link.subject.slug,
            "name": link.subject.name,
            "alignment_type": link.alignment_type,
            "position": link.position,
        }
        for link in revision.subject_alignments.all()
    ]
    objectives = [
        {
            "id": str(link.learning_objective_id),
            "code": link.learning_objective.code,
            "statement": link.learning_objective.statement,
            "description": link.learning_objective.description,
            "cognitive_level": link.learning_objective.cognitive_level,
            "subject_id": str(link.learning_objective.subject_id),
            "position": link.position,
        }
        for link in revision.objective_alignments.all()
    ]
    modules: list[dict[str, Any]] = []
    unit_count = 0
    topic_count = 0
    for module in revision.modules.all():
        units: list[dict[str, Any]] = []
        for unit in module.units.all():
            topics = [
                {
                    "id": str(link.topic_id),
                    "slug": link.topic.slug,
                    "title": link.topic.title,
                    "subject_id": str(link.topic.subject_id),
                    "subject_slug": link.topic.subject.slug,
                    "position": link.position,
                }
                for link in unit.topic_alignments.all()
            ]
            unit_objectives = [
                {
                    "id": str(link.learning_objective_id),
                    "code": link.learning_objective.code,
                    "statement": link.learning_objective.statement,
                    "position": link.position,
                }
                for link in unit.objective_alignments.all()
            ]
            units.append(
                {
                    "id": str(unit.id),
                    "title": unit.title,
                    "summary": unit.summary,
                    "estimated_duration_minutes": unit.estimated_duration_minutes,
                    "position": unit.position,
                    "topics": topics,
                    "learning_objectives": unit_objectives,
                    "content": _content_snapshot(unit),
                }
            )
            unit_count += 1
            topic_count += len(topics)
        modules.append(
            {
                "id": str(module.id),
                "title": module.title,
                "description": module.description,
                "position": module.position,
                "units": units,
            }
        )
    if len(modules) > MAX_MODULES:
        raise ReleaseSnapshotTooLarge("El release supera el máximo de módulos.")
    if unit_count > MAX_UNITS:
        raise ReleaseSnapshotTooLarge("El release supera el máximo de unidades.")
    if len(objectives) > MAX_LEARNING_OBJECTIVES:
        raise ReleaseSnapshotTooLarge("El release supera el máximo de objetivos.")
    if topic_count > MAX_TOPIC_REFERENCES:
        raise ReleaseSnapshotTooLarge(
            "El release supera el máximo de referencias a temas."
        )
    snapshot: dict[str, Any] = {
        "schema_version": CURRENT_RELEASE_SCHEMA_VERSION,
        "release_number": release_number,
        "previous_release_digest": previous_release_digest,
        "organization": {
            "id": str(revision.course.organization_id),
            "slug": revision.course.organization.slug,
        },
        "course": {
            "id": str(revision.course_id),
            "slug": revision.course.slug,
            "source_revision_id": str(revision.id),
            "source_revision_number": revision.number,
            "title": revision.title,
            "subtitle": revision.subtitle or None,
            "summary": revision.summary,
            "description": revision.description,
            "language_code": revision.language_code,
            "estimated_duration_minutes": revision.estimated_duration_minutes,
        },
        "curriculum": {
            "subjects": subjects,
            "learning_objectives": objectives,
        },
        "modules": modules,
    }
    validate_release_snapshot(snapshot)
    canonical = canonical_json_bytes(snapshot)
    if len(canonical) > MAX_CANONICAL_BYTES:
        raise ReleaseSnapshotTooLarge("El release supera 50 MiB canónicos.")
    return snapshot, canonical


def snapshot_metrics(snapshot: dict[str, Any]) -> dict[str, int]:
    modules = snapshot["modules"]
    units = [unit for module in modules for unit in module["units"]]
    return {
        "module_count": len(modules),
        "unit_count": len(units),
        "word_count": sum(unit["content"]["word_count"] for unit in units),
    }


def release_outline(snapshot: object) -> list[dict[str, Any]]:
    validate_release_snapshot(snapshot)
    assert isinstance(snapshot, dict)
    return [
        {
            "id": module["id"],
            "title": module["title"],
            "description": module["description"],
            "position": module["position"],
            "units": [
                {
                    "id": unit["id"],
                    "title": unit["title"],
                    "summary": unit["summary"],
                    "estimated_duration_minutes": unit["estimated_duration_minutes"],
                    "position": unit["position"],
                }
                for unit in module["units"]
            ],
        }
        for module in snapshot["modules"]
    ]


def release_unit(snapshot: object, unit_id: str) -> dict[str, Any]:
    validate_release_snapshot(snapshot)
    assert isinstance(snapshot, dict)
    for module in snapshot["modules"]:
        for unit in module["units"]:
            if unit["id"] == unit_id:
                result = deep_json_copy(unit)
                result["module"] = {
                    "id": module["id"],
                    "title": module["title"],
                    "position": module["position"],
                }
                return result
    raise ReleaseSnapshotInvalid("La unidad no existe en el snapshot.")


def release_previous_next(snapshot: object, unit_id: str) -> dict[str, Any | None]:
    outline = release_outline(snapshot)
    flattened = [
        {
            "id": unit["id"],
            "title": unit["title"],
            "module_id": module["id"],
            "module_title": module["title"],
        }
        for module in outline
        for unit in module["units"]
    ]
    for index, unit in enumerate(flattened):
        if unit["id"] == unit_id:
            return {
                "position": index + 1,
                "total": len(flattened),
                "previous": deep_json_copy(flattened[index - 1]) if index > 0 else None,
                "next": deep_json_copy(flattened[index + 1])
                if index + 1 < len(flattened)
                else None,
            }
    raise ReleaseSnapshotInvalid("La unidad no existe en el snapshot.")
