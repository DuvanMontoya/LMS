# pyright: reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportMissingTypeArgument=false
from django.db.models import F, Q, QuerySet
from django_filters import rest_framework as filters

from ..choices import AuthoringStatus, CourseStatus
from ..models import Course


class CourseFilter(filters.FilterSet):
    status = filters.ChoiceFilter(choices=CourseStatus.choices)
    authoring_status = filters.ChoiceFilter(
        field_name="current_authoring_status", choices=AuthoringStatus.choices
    )
    subject = filters.UUIDFilter(method="filter_subject")
    search = filters.CharFilter(method="filter_search")

    class Meta:
        model = Course
        fields: list[str] = []

    def filter_search(self, queryset: QuerySet, _: str, value: str) -> QuerySet:
        return queryset.filter(
            Q(slug__icontains=value)
            | Q(title__icontains=value)
            | Q(current_summary__icontains=value)
        )

    def filter_subject(self, queryset: QuerySet, _: str, value: object) -> QuerySet:
        return queryset.filter(
            revisions__id=F("current_revision_id"),
            revisions__subject_alignments__subject_id=value,
        ).distinct()
