# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportUnknownLambdaType=false
from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from domain.learning.models import EnrollmentReleaseAssignment
from domain.organizations.models import Organization
from domain.publishing.integrity import verify_release
from domain.publishing.models import CourseRelease

from .choices import (
    AttemptAggregation,
    GradebookColumnStatus,
    GradebookEntryStatus,
    GradebookStatus,
    GradebookSummaryStatus,
    GradingStatus,
)
from .exceptions import AssessmentConflict, AssessmentInvalid
from .models import (
    AssessmentDelivery,
    Attempt,
    CourseGradebook,
    GradebookColumn,
    GradebookEntry,
    GradebookSummary,
)


def _actor_id(actor: object) -> Any:
    actor_id = getattr(actor, "pk", None)
    if actor_id is None:
        raise AssessmentInvalid("Se requiere un actor autenticado.")
    return actor_id


def _require_expected(actual: int, expected: int) -> None:
    if actual != expected:
        raise AssessmentConflict("El gradebook cambió durante la edición.")


def _require_draft(gradebook: CourseGradebook) -> None:
    if gradebook.status != GradebookStatus.DRAFT:
        raise AssessmentConflict("Un gradebook activo no admite cambios estructurales.")


def _validate_release(
    *, organization: Organization, course_release: CourseRelease
) -> None:
    if course_release.course.organization_id != organization.id:
        raise AssessmentInvalid("El release pertenece a otra organización.")
    if not verify_release(course_release).valid:
        raise AssessmentInvalid("El release no supera la verificación de integridad.")


@transaction.atomic
def create_gradebook(
    *,
    actor: object,
    organization: Organization,
    course_release: CourseRelease,
) -> CourseGradebook:
    _validate_release(organization=organization, course_release=course_release)
    existing = CourseGradebook.objects.select_for_update().filter(
        course_release=course_release
    )
    if existing.exists():
        raise AssessmentConflict("El release ya tiene gradebook.")
    return CourseGradebook.objects.create(
        organization=organization,
        course_release=course_release,
        created_by_id=_actor_id(actor),
        updated_by_id=_actor_id(actor),
    )


def _validate_delivery(
    *, gradebook: CourseGradebook, delivery: AssessmentDelivery
) -> None:
    if delivery.organization_id != gradebook.organization_id:
        raise AssessmentInvalid("La entrega pertenece a otra organización.")
    if delivery.course_release_id != gradebook.course_release_id:
        raise AssessmentInvalid("La entrega pertenece a otro release.")


@transaction.atomic
def add_gradebook_column(
    *,
    actor: object,
    gradebook: CourseGradebook,
    expected_version: int,
    delivery: AssessmentDelivery,
    title: str,
    weight_basis_points: int,
    required: bool,
    attempt_aggregation: str,
) -> tuple[CourseGradebook, GradebookColumn]:
    locked = CourseGradebook.objects.select_for_update().get(pk=gradebook.pk)
    _require_expected(locked.lock_version, expected_version)
    _require_draft(locked)
    _validate_delivery(gradebook=locked, delivery=delivery)
    if not title.strip():
        raise AssessmentInvalid("La columna exige un título.")
    if not 1 <= weight_basis_points <= 10_000:
        raise AssessmentInvalid("El peso debe estar entre 1 y 10000.")
    if attempt_aggregation not in AttemptAggregation.values:
        raise AssessmentInvalid("La agregación de intentos no es válida.")
    position = locked.columns.select_for_update().count() + 1
    column = GradebookColumn(
        gradebook=locked,
        delivery=delivery,
        title=title.strip(),
        position=position,
        weight_basis_points=weight_basis_points,
        required=required,
        attempt_aggregation=attempt_aggregation,
        created_by_id=_actor_id(actor),
        updated_by_id=_actor_id(actor),
    )
    column.full_clean()
    column.save()
    locked.lock_version += 1
    locked.updated_by_id = _actor_id(actor)
    locked.save(update_fields=["lock_version", "updated_by", "updated_at"])
    return locked, column


@transaction.atomic
def update_gradebook_column(
    *,
    actor: object,
    gradebook: CourseGradebook,
    column: GradebookColumn,
    expected_version: int,
    title: str,
    weight_basis_points: int,
    required: bool,
    attempt_aggregation: str,
) -> tuple[CourseGradebook, GradebookColumn]:
    locked = CourseGradebook.objects.select_for_update().get(pk=gradebook.pk)
    _require_expected(locked.lock_version, expected_version)
    _require_draft(locked)
    locked_column = GradebookColumn.objects.select_for_update().get(pk=column.pk)
    if locked_column.gradebook_id != locked.id:
        raise AssessmentInvalid("La columna pertenece a otro gradebook.")
    if not title.strip():
        raise AssessmentInvalid("La columna exige un título.")
    if not 1 <= weight_basis_points <= 10_000:
        raise AssessmentInvalid("El peso debe estar entre 1 y 10000.")
    if attempt_aggregation not in AttemptAggregation.values:
        raise AssessmentInvalid("La agregación de intentos no es válida.")
    locked_column.title = title.strip()
    locked_column.weight_basis_points = weight_basis_points
    locked_column.required = required
    locked_column.attempt_aggregation = attempt_aggregation
    locked_column.updated_by_id = _actor_id(actor)
    locked_column.full_clean()
    locked_column.save()
    locked.lock_version += 1
    locked.updated_by_id = _actor_id(actor)
    locked.save(update_fields=["lock_version", "updated_by", "updated_at"])
    return locked, locked_column


@transaction.atomic
def reorder_gradebook_columns(
    *,
    actor: object,
    gradebook: CourseGradebook,
    expected_version: int,
    column_ids: list[object],
) -> CourseGradebook:
    locked = CourseGradebook.objects.select_for_update().get(pk=gradebook.pk)
    _require_expected(locked.lock_version, expected_version)
    _require_draft(locked)
    columns = list(locked.columns.select_for_update().order_by("position", "id"))
    existing_ids = {column.id for column in columns}
    if len(column_ids) != len(existing_ids) or set(column_ids) != existing_ids:
        raise AssessmentInvalid("El orden debe incluir exactamente todas las columnas.")
    by_id = {column.id: column for column in columns}
    temporary_offset = len(columns) + 1
    for column in columns:
        column.position += temporary_offset
        column.save(update_fields=["position", "updated_at"])
    for position, column_id in enumerate(column_ids, start=1):
        column = by_id[column_id]
        column.position = position
        column.updated_by_id = _actor_id(actor)
        column.save(update_fields=["position", "updated_by", "updated_at"])
    locked.lock_version += 1
    locked.updated_by_id = _actor_id(actor)
    locked.save(update_fields=["lock_version", "updated_by", "updated_at"])
    return locked


@transaction.atomic
def archive_gradebook_column(
    *,
    actor: object,
    gradebook: CourseGradebook,
    column: GradebookColumn,
    expected_version: int,
) -> tuple[CourseGradebook, GradebookColumn]:
    locked = CourseGradebook.objects.select_for_update().get(pk=gradebook.pk)
    _require_expected(locked.lock_version, expected_version)
    _require_draft(locked)
    locked_column = GradebookColumn.objects.select_for_update().get(pk=column.pk)
    if locked_column.gradebook_id != locked.id:
        raise AssessmentInvalid("La columna pertenece a otro gradebook.")
    locked_column.status = GradebookColumnStatus.ARCHIVED
    locked_column.updated_by_id = _actor_id(actor)
    locked_column.save(update_fields=["status", "updated_by", "updated_at"])
    ordered_columns = list(
        locked.columns.select_for_update().order_by("position", "id")
    )
    active_columns = [
        item for item in ordered_columns if item.status == GradebookColumnStatus.ACTIVE
    ]
    archived_columns = [
        item
        for item in ordered_columns
        if item.status == GradebookColumnStatus.ARCHIVED
    ]
    normalized_columns = [*active_columns, *archived_columns]
    temporary_offset = len(normalized_columns) + 1
    for item in normalized_columns:
        item.position += temporary_offset
        item.save(update_fields=["position", "updated_at"])
    for position, item in enumerate(normalized_columns, start=1):
        item.position = position
        item.updated_by_id = _actor_id(actor)
        item.save(update_fields=["position", "updated_by", "updated_at"])
    locked.lock_version += 1
    locked.updated_by_id = _actor_id(actor)
    locked.save(update_fields=["lock_version", "updated_by", "updated_at"])
    return locked, locked_column


def _selected_attempt(
    *, column: GradebookColumn, release_assignment: EnrollmentReleaseAssignment
) -> Attempt | None:
    attempts = list(
        Attempt.objects.filter(
            delivery_assignment__delivery=column.delivery,
            delivery_assignment__release_assignment=release_assignment,
            submitted_at__isnull=False,
        )
        .select_related("current_grade")
        .order_by("attempt_number")
    )
    if not attempts:
        return None
    if column.attempt_aggregation == AttemptAggregation.LATEST:
        return max(attempts, key=lambda item: item.attempt_number)
    return max(
        attempts,
        key=lambda item: (
            item.current_grade is not None
            and item.current_grade.percent_basis_points is not None,
            (
                item.current_grade.percent_basis_points
                if item.current_grade
                and item.current_grade.percent_basis_points is not None
                else -1
            ),
            item.attempt_number,
        ),
    )


def _refresh_gradebook_assignment(
    *,
    gradebook: CourseGradebook,
    release_assignment: EnrollmentReleaseAssignment,
) -> GradebookSummary:
    columns = list(
        gradebook.columns.filter(status=GradebookColumnStatus.ACTIVE).order_by(
            "position", "id"
        )
    )
    completed = 0
    weighted_total = 0
    required_complete = True
    for column in columns:
        entry, _ = GradebookEntry.objects.select_for_update().get_or_create(
            column=column,
            release_assignment=release_assignment,
        )
        attempt = _selected_attempt(
            column=column, release_assignment=release_assignment
        )
        if attempt is None:
            entry.attempt = None
            entry.attempt_grade = None
            entry.status = GradebookEntryStatus.MISSING
            entry.score = Decimal("0.000")
            entry.maximum_score = Decimal("0.000")
            entry.percent_basis_points = None
            entry.passed = None
        else:
            grade = attempt.current_grade
            entry.attempt = attempt
            entry.attempt_grade = grade
            if (
                grade is None
                or grade.grading_status != GradingStatus.GRADED
                or grade.percent_basis_points is None
            ):
                entry.status = GradebookEntryStatus.PENDING
                entry.score = (
                    grade.final_score if grade is not None else Decimal("0.000")
                )
                entry.maximum_score = attempt.maximum_score
                entry.percent_basis_points = None
                entry.passed = None
            else:
                entry.status = GradebookEntryStatus.GRADED
                entry.score = grade.final_score
                entry.maximum_score = grade.maximum_score
                entry.percent_basis_points = grade.percent_basis_points
                entry.passed = grade.passed
                completed += 1
                weighted_total += (
                    grade.percent_basis_points * column.weight_basis_points
                )
        if column.required and entry.status != GradebookEntryStatus.GRADED:
            required_complete = False
        entry.full_clean()
        entry.save()
    summary, _ = GradebookSummary.objects.select_for_update().get_or_create(
        gradebook=gradebook,
        release_assignment=release_assignment,
    )
    summary.status = (
        GradebookSummaryStatus.COMPLETE
        if required_complete
        else GradebookSummaryStatus.INCOMPLETE
    )
    summary.completed_columns = completed
    summary.total_columns = len(columns)
    summary.weighted_percent_basis_points = min(weighted_total // 10_000, 10_000)
    summary.full_clean()
    summary.save()
    return summary


@transaction.atomic
def activate_gradebook(
    *,
    actor: object,
    gradebook: CourseGradebook,
    expected_version: int,
) -> CourseGradebook:
    locked = (
        CourseGradebook.objects.select_for_update()
        .select_related("course_release__course")
        .get(pk=gradebook.pk)
    )
    _require_expected(locked.lock_version, expected_version)
    _require_draft(locked)
    _validate_release(
        organization=locked.organization,
        course_release=locked.course_release,
    )
    columns = list(
        locked.columns.select_for_update()
        .filter(status=GradebookColumnStatus.ACTIVE)
        .select_related("delivery")
        .order_by("position", "id")
    )
    if not columns:
        raise AssessmentInvalid("El gradebook exige al menos una columna activa.")
    if [column.position for column in columns] != list(range(1, len(columns) + 1)):
        raise AssessmentInvalid("Las posiciones activas deben ser contiguas.")
    if sum(column.weight_basis_points for column in columns) != 10_000:
        raise AssessmentInvalid("Los pesos activos deben sumar 10000.")
    for column in columns:
        _validate_delivery(gradebook=locked, delivery=column.delivery)
    now = timezone.now()
    locked.status = GradebookStatus.ACTIVE
    locked.activated_by_id = _actor_id(actor)
    locked.activated_at = now
    locked.updated_by_id = _actor_id(actor)
    locked.lock_version += 1
    locked.full_clean()
    locked.save()
    assignments = EnrollmentReleaseAssignment.objects.filter(
        release=locked.course_release
    ).order_by("assigned_at", "id")
    for release_assignment in assignments:
        _refresh_gradebook_assignment(
            gradebook=locked,
            release_assignment=release_assignment,
        )
    return locked


@transaction.atomic
def refresh_gradebook_for_attempt(*, attempt: Attempt) -> None:
    locked_attempt = (
        Attempt.objects.select_for_update(of=("self",))
        .select_related("delivery_assignment__release_assignment")
        .get(pk=attempt.pk)
    )
    release_assignment = locked_attempt.delivery_assignment.release_assignment
    gradebook_ids = list(
        CourseGradebook.objects.filter(
            status=GradebookStatus.ACTIVE,
            columns__delivery=locked_attempt.delivery_assignment.delivery,
        )
        .values_list("id", flat=True)
        .distinct()
    )
    gradebooks = list(
        CourseGradebook.objects.select_for_update()
        .filter(id__in=gradebook_ids)
        .order_by("id")
    )
    for gradebook in gradebooks:
        _refresh_gradebook_assignment(
            gradebook=gradebook,
            release_assignment=release_assignment,
        )
