# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportUnknownLambdaType=false
from __future__ import annotations

from collections.abc import Callable, Iterable
from types import MappingProxyType

from .choices import CourseStatus, StructureStatus, SubjectAlignmentType
from .models import CourseRevision

type ReadinessIssue = dict[str, str]
type ReadinessProvider = Callable[[CourseRevision], list[ReadinessIssue]]
_READINESS_PROVIDERS: dict[str, ReadinessProvider] = {}


def register_readiness_provider(name: str, provider: ReadinessProvider) -> None:
    """Register one deterministic extension without touching the database."""

    normalized = name.strip()
    if not normalized:
        raise ValueError("El nombre del proveedor de readiness es obligatorio.")
    if normalized in _READINESS_PROVIDERS:
        raise ValueError(f"El proveedor de readiness '{normalized}' ya existe.")
    _READINESS_PROVIDERS[normalized] = provider


def registered_readiness_providers():
    return MappingProxyType(_READINESS_PROVIDERS)


def _contiguous(values: Iterable[int | None]) -> bool:
    positions = list(values)
    return positions == list(range(1, len(positions) + 1))


def revision_readiness_issues(revision: CourseRevision) -> list[ReadinessIssue]:
    issues: list[ReadinessIssue] = []

    def add(code: str, path: str, message: str) -> None:
        issues.append({"code": code, "path": path, "message": message})

    if revision.course.status != CourseStatus.ACTIVE:
        add("course_archived", "course", "El curso debe estar activo.")
    if not revision.title.strip():
        add("title_required", "metadata.title", "El título es obligatorio.")
    if not revision.summary.strip():
        add("summary_required", "metadata.summary", "El resumen es obligatorio.")

    subjects = list(
        revision.subject_alignments.select_related("subject").order_by("position")
    )
    primary_count = sum(
        row.alignment_type == SubjectAlignmentType.PRIMARY for row in subjects
    )
    if primary_count != 1:
        add(
            "primary_subject_required",
            "curriculum.subjects",
            "Debe existir exactamente una asignatura principal.",
        )
    if not subjects:
        add(
            "subject_required",
            "curriculum.subjects",
            "Debe existir al menos una asignatura alineada.",
        )
    if not _contiguous(row.position for row in subjects):
        add(
            "subject_order_invalid",
            "curriculum.subjects",
            "El orden de asignaturas no es contiguo.",
        )
    for row in subjects:
        if row.subject.status != "active":
            add(
                "archived_subject",
                f"subjects.{row.subject_id}",
                "Una asignatura alineada está archivada.",
            )

    objectives = list(
        revision.objective_alignments.select_related("learning_objective").order_by(
            "position"
        )
    )
    if not objectives:
        add(
            "learning_objective_required",
            "curriculum.learning_objectives",
            "Debe existir al menos un objetivo de aprendizaje.",
        )
    if not _contiguous(row.position for row in objectives):
        add(
            "objective_order_invalid",
            "curriculum.learning_objectives",
            "El orden de objetivos no es contiguo.",
        )
    for row in objectives:
        if row.learning_objective.status != "active":
            add(
                "archived_learning_objective",
                f"learning_objectives.{row.learning_objective_id}",
                "Un objetivo alineado está archivado.",
            )

    modules = list(
        revision.modules.filter(status=StructureStatus.ACTIVE)
        .prefetch_related(
            "units__topic_alignments__topic",
            "units__objective_alignments__learning_objective",
        )
        .order_by("position")
    )
    if not modules:
        add(
            "module_required",
            "modules",
            "Debe existir al menos un módulo activo.",
        )
    if not _contiguous(module.position for module in modules):
        add(
            "module_order_invalid",
            "modules",
            "El orden de módulos no es contiguo.",
        )
    for module in modules:
        units = [
            unit for unit in module.units.all() if unit.status == StructureStatus.ACTIVE
        ]
        units.sort(key=lambda unit: unit.position or 0)
        module_path = f"modules.{module.id}"
        if not units:
            add(
                "module_without_unit",
                module_path,
                "Cada módulo activo debe contener al menos una unidad activa.",
            )
        if not _contiguous(unit.position for unit in units):
            add(
                "unit_order_invalid",
                f"{module_path}.units",
                "El orden de unidades no es contiguo.",
            )
        for unit in units:
            unit_path = f"{module_path}.units.{unit.id}"
            objective_links = list(unit.objective_alignments.all())
            if not objective_links:
                add(
                    "unit_without_learning_objective",
                    unit_path,
                    "Cada unidad activa debe estar relacionada con al menos un objetivo de aprendizaje.",
                )
            if not _contiguous(link.position for link in objective_links):
                add(
                    "unit_objective_order_invalid",
                    f"{unit_path}.learning_objectives",
                    "El orden de objetivos de la unidad no es contiguo.",
                )
            for link in objective_links:
                if link.learning_objective.status != "active":
                    add(
                        "archived_unit_learning_objective",
                        f"{unit_path}.learning_objectives.{link.learning_objective_id}",
                        "Un objetivo de la unidad está archivado.",
                    )
            topic_links = list(unit.topic_alignments.all())
            if not _contiguous(link.position for link in topic_links):
                add(
                    "unit_topic_order_invalid",
                    f"{unit_path}.topics",
                    "El orden de temas de la unidad no es contiguo.",
                )
            for link in topic_links:
                if link.topic.status != "active":
                    add(
                        "archived_unit_topic",
                        f"{unit_path}.topics.{link.topic_id}",
                        "Un tema de la unidad está archivado.",
                    )
    for provider_name in sorted(_READINESS_PROVIDERS):
        issues.extend(_READINESS_PROVIDERS[provider_name](revision))
    return issues
