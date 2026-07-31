# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportArgumentType=false
from __future__ import annotations

import uuid
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal
from functools import partial
from typing import Any

from django.db import connection, transaction
from django.utils import timezone

from domain.organizations.models import Organization

from .choices import GradingStatus, JobStatus
from .exceptions import AssessmentConflict, AssessmentInvalid
from .models import (
    AnalyticsRefreshJob,
    AssessmentAnalyticsSnapshot,
    AssessmentDelivery,
    AssessmentGradingPolicy,
    AssessmentGradingRevision,
    AssessmentVersion,
    AttemptGradeVersion,
    AttemptItem,
    AttemptItemGradeVersion,
    ItemAnalyticsSnapshot,
    OptionAnalyticsSnapshot,
)
from .queues import assessment_task_options

ANALYTICS_MIN_SAMPLE_SIZE = 10
DISCRIMINATION_MIN_SAMPLE_SIZE = 20


def _actor_id(actor: object) -> Any:
    actor_id = getattr(actor, "pk", None)
    if actor_id is None:
        raise AssessmentInvalid("Se requiere un actor autenticado.")
    return actor_id


def _basis_points(value: object | None) -> int | None:
    if value is None:
        return None
    return max(
        0,
        min(
            10_000,
            int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
        ),
    )


def _grade_queryset(
    *,
    assessment_version: AssessmentVersion,
    grading_revision: AssessmentGradingRevision,
    delivery: AssessmentDelivery | None,
):
    queryset = AttemptGradeVersion.objects.filter(
        current_for_attempt__assessment_version=assessment_version,
        grading_revision=grading_revision,
        grading_status=GradingStatus.GRADED,
        percent_basis_points__isnull=False,
    )
    if delivery is not None:
        queryset = queryset.filter(
            current_for_attempt__delivery_assignment__delivery=delivery
        )
    return queryset.order_by("id")


def _overall_metrics(grade_ids: list[object]) -> dict[str, int | None]:
    if not grade_ids:
        return {
            "mean": None,
            "median": None,
            "p25": None,
            "p75": None,
            "pass_rate": None,
        }
    table = AttemptGradeVersion._meta.db_table
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                AVG(percent_basis_points::double precision),
                percentile_cont(0.50) WITHIN GROUP (
                    ORDER BY percent_basis_points::double precision
                ),
                percentile_cont(0.25) WITHIN GROUP (
                    ORDER BY percent_basis_points::double precision
                ),
                percentile_cont(0.75) WITHIN GROUP (
                    ORDER BY percent_basis_points::double precision
                ),
                AVG(CASE WHEN passed THEN 10000.0 ELSE 0.0 END)
            FROM {table}
            WHERE id = ANY(%s)
            """,
            [grade_ids],
        )
        mean, median, p25, p75, pass_rate = cursor.fetchone()
    return {
        "mean": _basis_points(mean),
        "median": _basis_points(median),
        "p25": _basis_points(p25),
        "p75": _basis_points(p75),
        "pass_rate": _basis_points(pass_rate),
    }


def _discrimination(
    *,
    grade_ids: list[object],
    assessment_item_id: object,
) -> tuple[Decimal | None, int, bool]:
    item_table = AttemptItemGradeVersion._meta.db_table
    grade_table = AttemptGradeVersion._meta.db_table
    attempt_item_table = AttemptItem._meta.db_table
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                COUNT(*) FILTER (
                    WHERE grade.maximum_score > item.maximum_score
                ),
                corr(
                    item.credit_basis_points::double precision / 10000.0,
                    (
                        (grade.final_score - item.score)::double precision
                        / NULLIF(
                            (grade.maximum_score - item.maximum_score)
                                ::double precision,
                            0.0
                        )
                    )
                )
            FROM {item_table} item
            JOIN {grade_table} grade ON grade.id = item.attempt_grade_id
            JOIN {attempt_item_table} attempt_item
                ON attempt_item.id = item.attempt_item_id
            WHERE grade.id = ANY(%s)
              AND attempt_item.assessment_item_id = %s
              AND grade.maximum_score > item.maximum_score
            """,
            [grade_ids, assessment_item_id],
        )
        sample_size, value = cursor.fetchone()
    if sample_size < DISCRIMINATION_MIN_SAMPLE_SIZE or value is None:
        return None, sample_size, True
    decimal_value = Decimal(str(value)).quantize(
        Decimal("0.000001"), rounding=ROUND_HALF_UP
    )
    return decimal_value, sample_size, False


def _selected_option_ids(question_type: str, value: object) -> tuple[str, ...]:
    if question_type == "single_choice" and isinstance(value, str):
        return (value,)
    if question_type == "multiple_choice" and isinstance(value, list):
        return tuple(item for item in value if isinstance(item, str))
    if question_type == "true_false" and isinstance(value, bool):
        return ("true" if value else "false",)
    return ()


def _option_ids(question_type: str, public: dict[str, Any]) -> tuple[str, ...]:
    if question_type in {"single_choice", "multiple_choice"}:
        return tuple(str(option["id"]) for option in public.get("options", []))
    if question_type == "true_false":
        return ("true", "false")
    return ()


@transaction.atomic
def build_analytics_snapshot(
    *,
    assessment_version: AssessmentVersion,
    grading_revision: AssessmentGradingRevision,
    delivery: AssessmentDelivery | None,
    actor: object | None,
) -> AssessmentAnalyticsSnapshot:
    if grading_revision.policy.assessment_version_id != assessment_version.id:
        raise AssessmentInvalid("La revisión no pertenece a esta evaluación.")
    if delivery is not None and (
        delivery.assessment_version_id != assessment_version.id
    ):
        raise AssessmentInvalid("La entrega usa otra versión de evaluación.")
    grades = _grade_queryset(
        assessment_version=assessment_version,
        grading_revision=grading_revision,
        delivery=delivery,
    )
    grade_ids = list(grades.values_list("id", flat=True))
    metrics = _overall_metrics(grade_ids)
    sample_size = len(grade_ids)
    snapshot = AssessmentAnalyticsSnapshot.objects.create(
        assessment_version=assessment_version,
        grading_revision=grading_revision,
        delivery=delivery,
        sample_size=sample_size,
        mean_percent_basis_points=metrics["mean"],
        median_percent_basis_points=(
            metrics["median"] if sample_size >= ANALYTICS_MIN_SAMPLE_SIZE else None
        ),
        p25_percent_basis_points=(
            metrics["p25"] if sample_size >= ANALYTICS_MIN_SAMPLE_SIZE else None
        ),
        p75_percent_basis_points=(
            metrics["p75"] if sample_size >= ANALYTICS_MIN_SAMPLE_SIZE else None
        ),
        pass_rate_basis_points=metrics["pass_rate"],
        created_by_id=getattr(actor, "pk", None),
    )
    if not grade_ids:
        return snapshot
    item_grades = list(
        AttemptItemGradeVersion.objects.filter(attempt_grade_id__in=grade_ids)
        .select_related(
            "attempt_item__question_version",
            "response",
        )
        .order_by("attempt_item__assessment_item_id", "attempt_grade_id")
    )
    grouped: dict[object, list[AttemptItemGradeVersion]] = {}
    for item_grade in item_grades:
        grouped.setdefault(item_grade.attempt_item.assessment_item_id, []).append(
            item_grade
        )
    for assessment_item_id, rows in grouped.items():
        presented = len(rows)
        answered = sum(
            1
            for row in rows
            if row.response is not None
            and row.response.response.get("value") not in (None, "", [], {})
        )
        mean_credit = _basis_points(
            sum(row.credit_basis_points for row in rows) / presented
        )
        assert mean_credit is not None
        discrimination, discrimination_size, suppressed = _discrimination(
            grade_ids=grade_ids,
            assessment_item_id=assessment_item_id,
        )
        first = rows[0]
        question = first.attempt_item.question_version
        item_snapshot = ItemAnalyticsSnapshot.objects.create(
            assessment_snapshot=snapshot,
            assessment_item_id=assessment_item_id,
            question_version=question,
            question_type=question.type,
            presented_count=presented,
            answered_count=answered,
            omitted_count=presented - answered,
            mean_credit_basis_points=mean_credit,
            difficulty_basis_points=mean_credit,
            discrimination=discrimination,
            discrimination_sample_size=discrimination_size,
            discrimination_suppressed=suppressed,
        )
        option_ids = _option_ids(question.type, question.public)
        if sample_size < ANALYTICS_MIN_SAMPLE_SIZE or not option_ids:
            continue
        counts: Counter[str] = Counter()
        for row in rows:
            if row.response is None:
                continue
            counts.update(
                _selected_option_ids(
                    question.type,
                    row.response.response.get("value"),
                )
            )
        OptionAnalyticsSnapshot.objects.bulk_create(
            [
                OptionAnalyticsSnapshot(
                    item_analytics=item_snapshot,
                    option_id=option_id,
                    selected_count=counts[option_id],
                    selected_rate_basis_points=(
                        counts[option_id] * 10_000 // presented
                    ),
                )
                for option_id in option_ids
            ]
        )
    return snapshot


@transaction.atomic
def create_analytics_refresh_job(
    *,
    actor: object,
    organization: Organization,
    assessment_version: AssessmentVersion,
    grading_revision: AssessmentGradingRevision,
    delivery: AssessmentDelivery | None = None,
) -> AnalyticsRefreshJob:
    if assessment_version.assessment.organization_id != organization.id:
        raise AssessmentInvalid("La evaluación pertenece a otra organización.")
    policy = AssessmentGradingPolicy.objects.select_for_update().get(
        assessment_version=assessment_version
    )
    if grading_revision.policy_id != policy.id:
        raise AssessmentInvalid("La revisión no pertenece a esta policy.")
    if delivery is not None:
        if delivery.organization_id != organization.id:
            raise AssessmentInvalid("La entrega pertenece a otra organización.")
        if delivery.assessment_version_id != assessment_version.id:
            raise AssessmentInvalid("La entrega usa otra versión de evaluación.")
    if (
        AnalyticsRefreshJob.objects.select_for_update()
        .filter(
            organization=organization,
            assessment_version=assessment_version,
            grading_revision=grading_revision,
            delivery=delivery,
            status__in=[JobStatus.QUEUED, JobStatus.RUNNING],
        )
        .exists()
    ):
        raise AssessmentConflict("Ya existe un refresh activo para este alcance.")
    task_id = uuid.uuid4()
    job = AnalyticsRefreshJob.objects.create(
        organization=organization,
        assessment_version=assessment_version,
        grading_revision=grading_revision,
        delivery=delivery,
        task_id=task_id,
        created_by_id=_actor_id(actor),
    )
    from .tasks import refresh_analytics_task

    transaction.on_commit(
        partial(
            refresh_analytics_task.apply_async,
            args=[str(job.id)],
            task_id=str(task_id),
            **assessment_task_options("analytics"),
        )
    )
    return job


def process_analytics_job(job_id: str) -> None:
    with transaction.atomic():
        job = AnalyticsRefreshJob.objects.select_for_update().get(pk=job_id)
        if job.status not in {JobStatus.QUEUED, JobStatus.RUNNING}:
            return
        job.status = JobStatus.RUNNING
        job.started_at = job.started_at or timezone.now()
        job.error_code = ""
        job.save(update_fields=["status", "started_at", "error_code"])
    try:
        build_analytics_snapshot(
            assessment_version=job.assessment_version,
            grading_revision=job.grading_revision,
            delivery=job.delivery,
            actor=None,
        )
    except Exception:
        with transaction.atomic():
            failed = AnalyticsRefreshJob.objects.select_for_update().get(pk=job_id)
            failed.status = JobStatus.FAILED
            failed.error_code = "analytics_refresh_failed"
            failed.completed_at = timezone.now()
            failed.save(update_fields=["status", "error_code", "completed_at"])
        raise
    with transaction.atomic():
        completed = AnalyticsRefreshJob.objects.select_for_update().get(pk=job_id)
        completed.status = JobStatus.COMPLETED
        completed.error_code = ""
        completed.completed_at = timezone.now()
        completed.save(update_fields=["status", "error_code", "completed_at"])
