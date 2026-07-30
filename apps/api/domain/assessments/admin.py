from django.contrib import admin

from .models import (
    Assessment,
    AssessmentDelivery,
    AssessmentVersion,
    Attempt,
    DeliveryAssignment,
    ManualGradeDecision,
    Question,
    QuestionBank,
    QuestionBankVersion,
    QuestionVersion,
    Response,
)

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
):
    admin.site.register(model)
