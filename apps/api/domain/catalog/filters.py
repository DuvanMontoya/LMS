# pyright: reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportMissingTypeArgument=false, reportAttributeAccessIssue=false
from __future__ import annotations

from django.db.models import Q, QuerySet
from django_filters import rest_framework as filters

from .models import (
    AcademicArea,
    CatalogStatus,
    Concept,
    Discipline,
    LearningObjective,
    Subject,
)


class AreaFilter(filters.FilterSet):
    status = filters.ChoiceFilter(choices=CatalogStatus.choices)
    search = filters.CharFilter(method="filter_search")

    class Meta:
        model = AcademicArea
        fields: list[str] = []

    def filter_search(self, queryset: QuerySet, _: str, value: str) -> QuerySet:
        return queryset.filter(Q(name__icontains=value) | Q(slug__icontains=value))


class DisciplineFilter(filters.FilterSet):
    area = filters.UUIDFilter(field_name="area_id")
    status = filters.ChoiceFilter(choices=CatalogStatus.choices)
    search = filters.CharFilter(method="filter_search")

    class Meta:
        model = Discipline
        fields: list[str] = []

    def filter_search(self, queryset: QuerySet, _: str, value: str) -> QuerySet:
        return queryset.filter(Q(name__icontains=value) | Q(slug__icontains=value))


class SubjectFilter(filters.FilterSet):
    area = filters.UUIDFilter(field_name="discipline__area_id")
    discipline = filters.UUIDFilter(field_name="discipline_id")
    status = filters.ChoiceFilter(choices=CatalogStatus.choices)
    search = filters.CharFilter(method="filter_search")

    class Meta:
        model = Subject
        fields: list[str] = []

    def filter_search(self, queryset: QuerySet, _: str, value: str) -> QuerySet:
        return queryset.filter(Q(name__icontains=value) | Q(slug__icontains=value))


class ConceptFilter(filters.FilterSet):
    ids = filters.CharFilter(method="filter_ids")
    subject = filters.UUIDFilter(method="filter_subject")
    status = filters.ChoiceFilter(choices=CatalogStatus.choices)
    search = filters.CharFilter(method="filter_search")

    class Meta:
        model = Concept
        fields: list[str] = []

    def filter_search(self, queryset: QuerySet, _: str, value: str) -> QuerySet:
        return queryset.filter(
            Q(name__icontains=value)
            | Q(slug__icontains=value)
            | Q(definition__icontains=value)
        )

    def filter_ids(self, queryset: QuerySet, _: str, value: str) -> QuerySet:
        ids = [item.strip() for item in value.split(",") if item.strip()]
        return queryset.filter(id__in=ids[:100])

    def filter_subject(self, queryset: QuerySet, _: str, value: str) -> QuerySet:
        return queryset.filter(
            Q(topic_links__topic__subject_id=value)
            | Q(objective_links__learning_objective__subject_id=value)
        ).distinct()


class LearningObjectiveFilter(filters.FilterSet):
    subject = filters.UUIDFilter(field_name="subject_id")
    status = filters.ChoiceFilter(choices=CatalogStatus.choices)
    cognitive_level = filters.ChoiceFilter(
        choices=LearningObjective._meta.get_field("cognitive_level").choices
    )
    search = filters.CharFilter(method="filter_search")

    class Meta:
        model = LearningObjective
        fields: list[str] = []

    def filter_search(self, queryset: QuerySet, _: str, value: str) -> QuerySet:
        return queryset.filter(Q(code__icontains=value) | Q(statement__icontains=value))
