import django_filters

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
    cohort = django_filters.UUIDFilter(field_name="cohort_id")
    release_number = django_filters.NumberFilter(
        field_name="current_release_assignment__release__number"
    )
    progress_status = django_filters.CharFilter(
        field_name="current_release_assignment__progress__status"
    )
    search = django_filters.CharFilter(
        field_name="membership__user__email", lookup_expr="icontains"
    )

    class Meta:
        model = CourseEnrollment
        fields = ("course", "cohort", "status", "release_number", "progress_status")
