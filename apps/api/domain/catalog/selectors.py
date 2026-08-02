from __future__ import annotations

from collections.abc import Iterable

from django.db.models import Q, QuerySet
from django.utils import timezone

from domain.organizations.models import Organization

from .models import (
    AcademicArea,
    Concept,
    Discipline,
    LearningObjective,
    Subject,
    SubjectTeachingResponsibility,
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


def responsible_subjects_for_actor(
    *, actor: object, organization: Organization
) -> QuerySet[Subject]:
    today = timezone.localdate()
    responsibility_ids = SubjectTeachingResponsibility.objects.filter(
        subject__discipline__area__organization=organization,
        membership__user=actor,
        membership__status="active",
        starts_on__lte=today,
        ended_at__isnull=True,
    ).filter(Q(ends_on__isnull=True) | Q(ends_on__gte=today))
    return Subject.objects.filter(
        teaching_responsibilities__in=responsibility_ids,
        status="active",
    ).distinct()


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
