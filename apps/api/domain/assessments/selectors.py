from __future__ import annotations

from django.db.models import QuerySet

from domain.learning.contracts import visible_course_group_ids_for_actor
from domain.learning.policies import has_institutional_learning_scope
from domain.organizations.models import Organization

from .models import (
    AnalyticsRefreshJob,
    Assessment,
    AssessmentAnalyticsSnapshot,
    AssessmentDelivery,
    Attempt,
    CourseGradebook,
    DeliveryAssignment,
    QuestionBank,
    RegradeJob,
    Response,
)


def question_banks_for(organization: Organization) -> QuerySet[QuestionBank]:
    return QuestionBank.objects.filter(organization=organization).order_by("name", "id")


def assessments_for(organization: Organization) -> QuerySet[Assessment]:
    return Assessment.objects.filter(organization=organization).order_by("slug", "id")


def deliveries_for(
    organization: Organization, *, actor: object | None = None
) -> QuerySet[AssessmentDelivery]:
    queryset = (
        AssessmentDelivery.objects.filter(organization=organization)
        .select_related(
            "assessment_version",
            "course_release",
            "course_group_activity__course_group",
        )
        .order_by("-created_at")
    )
    if actor is None or has_institutional_learning_scope(actor, organization):  # type: ignore[arg-type]
        return queryset
    group_ids = visible_course_group_ids_for_actor(
        actor=actor, organization=organization
    )
    return queryset.filter(
        course_group_activity__course_group_id__in=group_ids,
        migration_review_required=False,
    )


def gradebooks_for(
    organization: Organization, *, actor: object
) -> QuerySet[CourseGradebook]:
    queryset = CourseGradebook.objects.filter(organization=organization).select_related(
        "course_release", "course_group", "academic_period"
    )
    if has_institutional_learning_scope(actor, organization):  # type: ignore[arg-type]
        return queryset
    group_ids = visible_course_group_ids_for_actor(
        actor=actor, organization=organization
    )
    return queryset.filter(
        course_group_id__in=group_ids, migration_review_required=False
    )


def attempts_for_results(
    organization: Organization, *, actor: object
) -> QuerySet[Attempt]:
    queryset = Attempt.objects.filter(
        delivery_assignment__delivery__organization=organization
    ).select_related("assessment_version")
    if has_institutional_learning_scope(actor, organization):  # type: ignore[arg-type]
        return queryset
    group_ids = visible_course_group_ids_for_actor(
        actor=actor, organization=organization
    )
    return queryset.filter(
        delivery_assignment__delivery__course_group_activity__course_group_id__in=group_ids,
        delivery_assignment__delivery__migration_review_required=False,
    )


def responses_for_manual_grading(
    organization: Organization, *, actor: object
) -> QuerySet[Response]:
    queryset = Response.objects.filter(
        attempt_item__attempt__delivery_assignment__delivery__organization=organization
    )
    if has_institutional_learning_scope(actor, organization):  # type: ignore[arg-type]
        return queryset
    group_ids = visible_course_group_ids_for_actor(
        actor=actor, organization=organization
    )
    return queryset.filter(
        attempt_item__attempt__delivery_assignment__delivery__course_group_activity__course_group_id__in=group_ids,
        attempt_item__attempt__delivery_assignment__delivery__migration_review_required=False,
    )


def regrade_jobs_for(
    organization: Organization, *, actor: object
) -> QuerySet[RegradeJob]:
    queryset = RegradeJob.objects.filter(organization=organization).select_related(
        "assessment_version", "grading_revision", "delivery"
    )
    if has_institutional_learning_scope(actor, organization):  # type: ignore[arg-type]
        return queryset
    return queryset.filter(delivery__in=deliveries_for(organization, actor=actor))


def analytics_snapshots_for(
    organization: Organization, *, actor: object
) -> QuerySet[AssessmentAnalyticsSnapshot]:
    queryset = AssessmentAnalyticsSnapshot.objects.filter(
        assessment_version__assessment__organization=organization
    )
    if has_institutional_learning_scope(actor, organization):  # type: ignore[arg-type]
        return queryset
    return queryset.filter(delivery__in=deliveries_for(organization, actor=actor))


def analytics_refresh_jobs_for(
    organization: Organization, *, actor: object
) -> QuerySet[AnalyticsRefreshJob]:
    queryset = AnalyticsRefreshJob.objects.filter(organization=organization)
    if has_institutional_learning_scope(actor, organization):  # type: ignore[arg-type]
        return queryset
    return queryset.filter(delivery__in=deliveries_for(organization, actor=actor))


def learner_assignments(
    *, actor: object, organization: Organization
) -> QuerySet[DeliveryAssignment]:
    return (
        DeliveryAssignment.objects.filter(
            delivery__organization=organization,
            release_assignment__enrollment__membership__user=actor,
        )
        .select_related(
            "delivery__assessment_version",
            "delivery__course_release",
            "release_assignment__enrollment__membership",
            "release_assignment__enrollment__current_release_assignment",
        )
        .prefetch_related("attempts")
        .order_by("-assigned_at")
    )


def learner_attempts(*, actor: object, organization: Organization) -> QuerySet[Attempt]:
    return (
        Attempt.objects.filter(
            delivery_assignment__delivery__organization=organization,
            delivery_assignment__release_assignment__enrollment__membership__user=actor,
        )
        .select_related(
            "assessment_version",
            "delivery_assignment__delivery",
        )
        .order_by("-created_at")
    )
