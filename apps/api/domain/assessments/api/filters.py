import django_filters

from ..models import Assessment, AssessmentDelivery, QuestionBank


class QuestionBankFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = QuestionBank
        fields = ("status",)


class AssessmentFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(
        field_name="revisions__title", lookup_expr="icontains"
    )

    class Meta:
        model = Assessment
        fields = ("status",)


class DeliveryFilter(django_filters.FilterSet):
    class Meta:
        model = AssessmentDelivery
        fields = ("status", "assessment_version")
