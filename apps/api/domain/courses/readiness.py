# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportUnknownLambdaType=false
from __future__ import annotations

from collections.abc import Callable, Iterable
from types import MappingProxyType

from .choices import ActivityType, CourseStatus, StructureStatus, SubjectAlignmentType
from .models import CourseCompletionPolicy, CourseRevision

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
    course_objective_ids = {row.learning_objective_id for row in objectives}

    modules = list(
        revision.modules.filter(status=StructureStatus.ACTIVE)
        .prefetch_related(
            "units__topic_alignments__topic",
            "units__objective_alignments__learning_objective",
            "activities__objective_alignments__learning_objective",
            "activities__availability_rules__prerequisite_activity",
            "activities__availability_rules__learning_objective",
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
        activities = [
            activity
            for activity in module.activities.all()
            if activity.status == StructureStatus.ACTIVE
        ]
        activities.sort(key=lambda activity: activity.position or 0)
        if not activities:
            add(
                "module_without_activity",
                module_path,
                "Cada módulo activo debe contener al menos una actividad activa.",
            )
        if not units and not activities:
            add(
                "module_without_unit",
                module_path,
                "Cada módulo activo debe contener al menos una unidad activa.",
            )
        if not _contiguous(activity.position for activity in activities):
            add(
                "activity_order_invalid",
                f"{module_path}.activities",
                "El orden de actividades no es contiguo.",
            )
        active_lesson_unit_ids = {
            activity.lesson_unit_id
            for activity in activities
            if activity.activity_type == ActivityType.LESSON
        }
        if active_lesson_unit_ids != {unit.id for unit in units}:
            add(
                "lesson_unit_mapping_invalid",
                f"{module_path}.activities",
                "Cada unidad activa debe tener exactamente una actividad de lección.",
            )
        for activity in activities:
            activity_path = f"{module_path}.activities.{activity.id}"
            activity_objectives = list(activity.objective_alignments.all())
            if not activity_objectives:
                add(
                    "activity_without_learning_objective",
                    activity_path,
                    f"«{activity.title}» debe trabajar al menos un objetivo del curso.",
                )
            if not _contiguous(link.position for link in activity_objectives):
                add(
                    "activity_objective_order_invalid",
                    f"{activity_path}.learning_objectives",
                    "El orden de objetivos de la actividad no es contiguo.",
                )
            for link in activity_objectives:
                if link.learning_objective_id not in course_objective_ids:
                    add(
                        "activity_objective_outside_course",
                        f"{activity_path}.learning_objectives.{link.learning_objective_id}",
                        "La actividad usa un objetivo ajeno al curso.",
                    )
            rules = list(activity.availability_rules.all())
            if not _contiguous(rule.position for rule in rules):
                add(
                    "activity_rule_order_invalid",
                    f"{activity_path}.availability_rules",
                    "El orden de reglas de disponibilidad no es contiguo.",
                )
            for rule in rules:
                if (
                    rule.prerequisite_activity_id
                    and rule.prerequisite_activity.module.revision_id != revision.id
                ):
                    add(
                        "activity_rule_outside_revision",
                        f"{activity_path}.availability_rules.{rule.id}",
                        "La regla usa una actividad de otra revisión.",
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

    activity_edges: dict[object, set[object]] = {}
    active_activities: list[object] = []
    for module in modules:
        for activity in module.activities.all():
            if activity.status != StructureStatus.ACTIVE:
                continue
            active_activities.append(activity)
            activity_edges.setdefault(activity.id, set())
            for rule in activity.availability_rules.all():
                if rule.prerequisite_activity_id:
                    activity_edges[activity.id].add(rule.prerequisite_activity_id)

    visiting: set[object] = set()
    visited: set[object] = set()

    def visit(activity_id: object) -> bool:
        if activity_id in visiting:
            return True
        if activity_id in visited:
            return False
        visiting.add(activity_id)
        if any(
            visit(required_id) for required_id in activity_edges.get(activity_id, set())
        ):
            return True
        visiting.remove(activity_id)
        visited.add(activity_id)
        return False

    if any(visit(activity_id) for activity_id in activity_edges):
        add(
            "activity_availability_cycle",
            "activities.availability_rules",
            "Las reglas de disponibilidad contienen un ciclo.",
        )

    completion_policy = getattr(revision, "_readiness_completion_policy", None)
    if completion_policy is None:
        completion_policy = CourseCompletionPolicy.objects.filter(
            revision=revision
        ).first()
    if completion_policy is None or completion_policy.confirmed_at is None:
        add(
            "completion_policy_confirmation_required",
            "completion_policy",
            "Confirma cómo completarán el curso los estudiantes.",
        )

    categories = list(revision.grade_categories.prefetch_related("graded_activities"))
    if (
        completion_policy is not None
        and completion_policy.minimum_grade_basis_points is not None
        and not categories
    ):
        add(
            "grading_scheme_required",
            "grading_scheme",
            "La nota mínima exige un esquema de calificación completo.",
        )
    if (
        completion_policy is not None
        and completion_policy.minimum_attendance_basis_points is not None
        and not any(
            activity.activity_type == ActivityType.LIVE_CLASS and activity.required
            for activity in active_activities
        )
    ):
        add(
            "required_live_activity_required",
            "completion_policy.minimum_attendance_basis_points",
            "La asistencia mínima exige al menos una clase en vivo obligatoria.",
        )
    if (
        categories
        and sum(category.weight_basis_points for category in categories) != 10_000
    ):
        add(
            "grade_category_weights_invalid",
            "grading_scheme.categories",
            "Los pesos de categorías deben sumar 10 000 puntos base.",
        )
    for category in categories:
        items = list(category.graded_activities.all())
        if not items or sum(item.weight_basis_points for item in items) != 10_000:
            add(
                "grade_item_weights_invalid",
                f"grading_scheme.categories.{category.id}",
                "Los pesos de actividades calificables deben sumar 10 000 puntos base.",
            )
    # Extension providers share the already-loaded authoring graph. These
    # request-scoped attributes are deliberately non-persistent and keep the
    # stable provider signature while avoiding one query per domain provider.
    revision._readiness_active_activities = tuple(active_activities)
    revision._readiness_course_objective_ids = frozenset(course_objective_ids)
    for provider_name in sorted(_READINESS_PROVIDERS):
        issues.extend(_READINESS_PROVIDERS[provider_name](revision))
    return issues
