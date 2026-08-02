import uuid

import django_filters
from django.db.models import QuerySet

from domain.learning.models import CourseEnrollment, LearningCohort


class CohortFilter(django_filters.FilterSet):
    course = django_filters.UUIDFilter(field_name="course_id")
    release_number = django_filters.NumberFilter(field_name="release__number")
    search = django_filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = LearningCohort
        fields = ("course", "release_number", "status")


class EnrollmentFilter(django_filters.FilterSet):
    course = django_filters.UUIDFilter(field_name="course_id")
    cohort = django_filters.UUIDFilter(method="filter_cohort")
    release_number = django_filters.NumberFilter(
        field_name="current_release_assignment__release__number"
    )
    progress_status = django_filters.CharFilter(
        field_name="current_release_assignment__progress__status"
    )
    search = django_filters.CharFilter(
        field_name="membership__user__email", lookup_expr="icontains"
    )
    individual = django_filters.BooleanFilter(method="filter_individual")

    def filter_cohort(
        self,
        queryset: QuerySet[CourseEnrollment],
        _name: str,
        value: uuid.UUID | None,
    ) -> QuerySet[CourseEnrollment]:
        if value is None:
            return queryset.none()
        return queryset.filter(
            cohort_assignments__cohort_id=value,
            cohort_assignments__ended_at__isnull=True,
        )

    def filter_individual(
        self,
        queryset: QuerySet[CourseEnrollment],
        _name: str,
        value: bool | None,
    ) -> QuerySet[CourseEnrollment]:
        active_group = {"cohort_assignments__ended_at__isnull": True}
        return (
            queryset.exclude(**active_group)
            if value
            else queryset.filter(**active_group)
        )

    class Meta:
        model = CourseEnrollment
        fields = ("course", "cohort", "status", "release_number", "progress_status")
