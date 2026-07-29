from __future__ import annotations

from collections.abc import Iterable

from django.db.models import QuerySet

from domain.organizations.models import Organization

from .models import (
    AcademicArea,
    Concept,
    Discipline,
    LearningObjective,
    Subject,
    Topic,
)


def areas_visible_to(
    organization: Organization, statuses: Iterable[str]
) -> QuerySet[AcademicArea]:
    return AcademicArea.objects.filter(
        organization=organization, status__in=statuses
    ).order_by("name")


def disciplines_visible_to(
    organization: Organization, statuses: Iterable[str]
) -> QuerySet[Discipline]:
    return (
        Discipline.objects.filter(area__organization=organization, status__in=statuses)
        .select_related("area")
        .order_by("name")
    )


def subjects_visible_to(
    organization: Organization, statuses: Iterable[str]
) -> QuerySet[Subject]:
    return (
        Subject.objects.filter(
            discipline__area__organization=organization, status__in=statuses
        )
        .select_related("discipline__area")
        .order_by("name")
    )


def topics_visible_to(subject: Subject, statuses: Iterable[str]) -> QuerySet[Topic]:
    return (
        Topic.objects.filter(subject=subject, status__in=statuses)
        .select_related("subject__discipline__area")
        .order_by("path")
    )


def concepts_visible_to(
    organization: Organization, statuses: Iterable[str]
) -> QuerySet[Concept]:
    return Concept.objects.filter(
        organization=organization, status__in=statuses
    ).order_by("name")


def learning_objectives_visible_to(
    organization: Organization, statuses: Iterable[str]
) -> QuerySet[LearningObjective]:
    return (
        LearningObjective.objects.filter(
            subject__discipline__area__organization=organization,
            status__in=statuses,
        )
        .select_related("subject__discipline__area")
        .order_by("code")
    )
