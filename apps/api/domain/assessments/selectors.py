from __future__ import annotations

from django.db.models import QuerySet

from domain.organizations.models import Organization

from .models import (
    Assessment,
    AssessmentDelivery,
    Attempt,
    DeliveryAssignment,
    QuestionBank,
)


def question_banks_for(organization: Organization) -> QuerySet[QuestionBank]:
    return QuestionBank.objects.filter(organization=organization).order_by("name", "id")


def assessments_for(organization: Organization) -> QuerySet[Assessment]:
    return Assessment.objects.filter(organization=organization).order_by("slug", "id")


def deliveries_for(organization: Organization) -> QuerySet[AssessmentDelivery]:
    return (
        AssessmentDelivery.objects.filter(organization=organization)
        .select_related("assessment_version", "course_release")
        .order_by("-created_at")
    )


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
