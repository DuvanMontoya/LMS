# pyright: reportMissingTypeArgument=false
from typing import Any

from django.contrib import admin
from django.http import HttpRequest

from .models import (
    AnalyticsRefreshJob,
    Assessment,
    AssessmentAnalyticsSnapshot,
    AssessmentAssetReference,
    AssessmentDelivery,
    AssessmentGradingPolicy,
    AssessmentGradingRevision,
    AssessmentItemPool,
    AssessmentVersion,
    Attempt,
    AttemptGradeVersion,
    AttemptGradingJob,
    AttemptItemGradeVersion,
    CourseGradebook,
    DeliveryAssignment,
    GradebookColumn,
    GradebookEntry,
    GradebookSummary,
    ItemAnalyticsSnapshot,
    ManualGradeDecision,
    OptionAnalyticsSnapshot,
    Question,
    QuestionBank,
    QuestionBankVersion,
    QuestionVersion,
    RegradeJob,
    RegradeJobAttempt,
    Response,
)


class ReadOnlyAssessmentAdmin(admin.ModelAdmin):
    actions = None

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: Any | None = None
    ) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: Any | None = None
    ) -> bool:
        return False


for model in (
    QuestionBank,
    Question,
    QuestionVersion,
    QuestionBankVersion,
    Assessment,
    AssessmentVersion,
    AssessmentDelivery,
    DeliveryAssignment,
    Attempt,
    Response,
    ManualGradeDecision,
    AssessmentAssetReference,
    AssessmentItemPool,
    AssessmentGradingPolicy,
    AssessmentGradingRevision,
    AttemptGradeVersion,
    AttemptItemGradeVersion,
    AttemptGradingJob,
    RegradeJob,
    RegradeJobAttempt,
    CourseGradebook,
    GradebookColumn,
    GradebookEntry,
    GradebookSummary,
    AssessmentAnalyticsSnapshot,
    ItemAnalyticsSnapshot,
    OptionAnalyticsSnapshot,
    AnalyticsRefreshJob,
):
    admin.site.register(model, ReadOnlyAssessmentAdmin)
