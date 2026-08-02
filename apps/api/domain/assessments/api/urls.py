from django.urls import path

from . import advanced_views, views

BASE = "organizations/<slug:slug>/assessments/"
BANK = BASE + "question-banks/<str:bank_id>/"
QUESTION = BANK + "questions/<uuid:question_id>/"
QREV = QUESTION + "revisions/<uuid:revision_id>/"
ASSESSMENT = BASE + "<slug:assessment_slug>/"
AREV = ASSESSMENT + "revisions/<uuid:revision_id>/"

urlpatterns = [
    path(
        BASE + "course-activities/",
        views.AssessmentCourseActivityCreateView.as_view(),
    ),
    path(
        BASE + "course-activities/<uuid:activity_id>/binding/",
        views.AssessmentActivityBindingView.as_view(),
    ),
    path(BASE + "question-banks/", views.QuestionBankListCreateView.as_view()),
    path(BANK, views.QuestionBankDetailView.as_view()),
    path(BANK + "archive/", views.QuestionBankArchiveView.as_view()),
    path(BANK + "questions/", views.QuestionListCreateView.as_view()),
    path(QUESTION, views.QuestionDetailView.as_view()),
    path(BANK + "versions/", views.QuestionBankVersionListCreateView.as_view()),
    path(
        BANK + "versions/<int:version_number>/",
        views.QuestionBankVersionDetailView.as_view(),
    ),
    path(QREV, views.QuestionRevisionDetailView.as_view()),
    path(QREV + "submit-review/", views.SubmitQuestionRevisionView.as_view()),
    path(QREV + "submit/", views.SubmitQuestionRevisionAliasView.as_view()),
    path(QREV + "request-changes/", views.RequestQuestionChangesView.as_view()),
    path(QREV + "approve/", views.ApproveQuestionRevisionView.as_view()),
    path(QUESTION + "versions/", views.QuestionVersionListView.as_view()),
    path(
        QUESTION + "versions/<int:version_number>/",
        views.QuestionVersionDetailView.as_view(),
    ),
    path(
        QUESTION + "versions/<int:version_number>/create-draft/",
        views.QuestionVersionCreateDraftView.as_view(),
    ),
    path(BASE + "deliveries/", views.DeliveryListCreateView.as_view()),
    path(
        BASE + "deliveries/<uuid:delivery_id>/",
        views.DeliveryDetailView.as_view(),
    ),
    path(
        BASE + "deliveries/<uuid:delivery_id>/activate/",
        views.ActivateDeliveryView.as_view(),
    ),
    path(
        BASE + "deliveries/<uuid:delivery_id>/withdraw/",
        views.WithdrawDeliveryView.as_view(),
    ),
    path(
        BASE + "deliveries/<uuid:delivery_id>/assignments/",
        views.DeliveryAssignmentListCreateView.as_view(),
    ),
    path(
        BASE + "deliveries/<uuid:delivery_id>/assign-cohort/",
        views.AssignDeliveryCohortView.as_view(),
    ),
    path(
        BASE + "deliveries/<uuid:delivery_id>/assignments/<uuid:assignment_id>/revoke/",
        views.RevokeDeliveryAssignmentView.as_view(),
    ),
    path(BASE + "my-deliveries/", views.MyDeliveryListView.as_view()),
    path(
        BASE + "my-deliveries/<uuid:assignment_id>/",
        views.MyDeliveryDetailView.as_view(),
    ),
    path(
        BASE + "my-deliveries/<uuid:assignment_id>/attempts/start/",
        views.StartAttemptView.as_view(),
    ),
    path(BASE + "attempts/<uuid:attempt_id>/", views.AttemptDetailView.as_view()),
    path(
        BASE + "attempts/<uuid:attempt_id>/responses/<uuid:attempt_item_id>/",
        views.SaveResponseView.as_view(),
    ),
    path(
        BASE + "attempts/<uuid:attempt_id>/submit/",
        views.SubmitAttemptView.as_view(),
    ),
    path(
        BASE + "attempts/<uuid:attempt_id>/result/",
        views.AttemptResultView.as_view(),
    ),
    path(BASE + "results/", views.ResultsListView.as_view()),
    path(BASE + "manual-grading/", views.PendingManualListView.as_view()),
    path(
        BASE + "manual-grading/<uuid:response_id>/",
        views.ManualGradeView.as_view(),
    ),
    path(
        BASE + "approved-version-options/",
        views.ApprovedAssessmentVersionOptionsView.as_view(),
    ),
    path(BASE, views.AssessmentListCreateView.as_view()),
    path(ASSESSMENT + "versions/", views.AssessmentVersionListView.as_view()),
    path(
        ASSESSMENT + "versions/<int:version_number>/",
        views.AssessmentVersionDetailView.as_view(),
    ),
    path(
        ASSESSMENT + "versions/<int:version_number>/create-draft/",
        views.AssessmentVersionCreateDraftView.as_view(),
    ),
    path(AREV + "objectives/", views.AssessmentObjectivesView.as_view()),
    path(AREV + "outline/", views.AssessmentOutlineView.as_view()),
    path(AREV + "readiness/", views.AssessmentReadinessView.as_view()),
    path(AREV + "sections/", views.SectionListCreateView.as_view()),
    path(AREV + "sections/order/", views.SectionOrderView.as_view()),
    path(AREV + "pools/", advanced_views.PoolListCreateView.as_view()),
    path(
        AREV + "structure/order/",
        advanced_views.StructureOrderView.as_view(),
    ),
    path(
        AREV + "sections/<uuid:section_id>/",
        views.SectionDetailView.as_view(),
    ),
    path(
        AREV + "sections/<uuid:section_id>/items/",
        views.ItemListCreateView.as_view(),
    ),
    path(
        AREV + "sections/<uuid:section_id>/items/order/",
        views.ItemOrderView.as_view(),
    ),
    path(
        AREV + "sections/<uuid:section_id>/items/<uuid:item_id>/",
        views.ItemDetailView.as_view(),
    ),
    path(AREV + "submit-review/", views.SubmitAssessmentRevisionView.as_view()),
    path(AREV + "submit/", views.SubmitAssessmentRevisionAliasView.as_view()),
    path(AREV + "request-changes/", views.RequestAssessmentChangesView.as_view()),
    path(AREV + "approve/", views.ApproveAssessmentRevisionView.as_view()),
    path(AREV, views.AssessmentRevisionDetailView.as_view()),
    path(BASE + "pools/<uuid:pool_id>/", advanced_views.PoolDetailView.as_view()),
    path(
        BASE + "pools/<uuid:pool_id>/candidates/",
        advanced_views.PoolCandidatesView.as_view(),
    ),
    path(
        BASE + "scoring-policies/<uuid:version_id>/",
        advanced_views.ScoringPolicyDetailView.as_view(),
    ),
    path(
        BASE + "scoring-policies/<uuid:version_id>/revisions/",
        advanced_views.ScoringPolicyRevisionListView.as_view(),
    ),
    path(
        BASE + "scoring-policies/<uuid:version_id>/corrections/",
        advanced_views.ScoringCorrectionView.as_view(),
    ),
    path(
        BASE + "regrade-jobs/",
        advanced_views.RegradeJobListCreateView.as_view(),
    ),
    path(
        BASE + "regrade-jobs/<uuid:job_id>/",
        advanced_views.RegradeJobDetailView.as_view(),
    ),
    path(
        BASE + "regrade-jobs/<uuid:job_id>/attempts/",
        advanced_views.RegradeJobAttemptListView.as_view(),
    ),
    path(
        BASE + "regrade-jobs/<uuid:job_id>/retry-failed/",
        advanced_views.RegradeJobRetryView.as_view(),
    ),
    path(
        BASE + "gradebooks/",
        advanced_views.GradebookListCreateView.as_view(),
    ),
    path(
        BASE + "gradebooks/<uuid:gradebook_id>/",
        advanced_views.GradebookDetailView.as_view(),
    ),
    path(
        BASE + "gradebooks/<uuid:gradebook_id>/activate/",
        advanced_views.GradebookActivateView.as_view(),
    ),
    path(
        BASE + "gradebooks/<uuid:gradebook_id>/columns/",
        advanced_views.GradebookColumnListCreateView.as_view(),
    ),
    path(
        BASE + "gradebooks/<uuid:gradebook_id>/columns/order/",
        advanced_views.GradebookColumnOrderView.as_view(),
    ),
    path(
        BASE + "gradebooks/<uuid:gradebook_id>/columns/<uuid:column_id>/",
        advanced_views.GradebookColumnDetailView.as_view(),
    ),
    path(
        BASE + "gradebooks/<uuid:gradebook_id>/columns/<uuid:column_id>/archive/",
        advanced_views.GradebookColumnArchiveView.as_view(),
    ),
    path(
        BASE + "gradebooks/<uuid:gradebook_id>/entries/",
        advanced_views.GradebookEntryListView.as_view(),
    ),
    path(
        BASE + "gradebooks/<uuid:gradebook_id>/summaries/",
        advanced_views.GradebookSummaryListView.as_view(),
    ),
    path(
        BASE + "gradebooks/<uuid:gradebook_id>/students/<uuid:release_assignment_id>/",
        advanced_views.GradebookStudentView.as_view(),
    ),
    path(
        BASE + "me/gradebooks/",
        advanced_views.MyGradebookListView.as_view(),
    ),
    path(
        BASE + "me/gradebooks/<uuid:gradebook_id>/",
        advanced_views.MyGradebookDetailView.as_view(),
    ),
    path(
        BASE + "analytics/assessments/<uuid:version_id>/",
        advanced_views.AnalyticsAssessmentView.as_view(),
    ),
    path(
        BASE + "analytics/assessments/<uuid:version_id>/items/",
        advanced_views.AnalyticsItemListView.as_view(),
    ),
    path(
        BASE
        + "analytics/assessments/<uuid:version_id>/items/<uuid:assessment_item_id>/",
        advanced_views.AnalyticsItemDetailView.as_view(),
    ),
    path(
        BASE + "analytics/refresh/",
        advanced_views.AnalyticsRefreshView.as_view(),
    ),
    path(
        BASE + "analytics/jobs/<uuid:job_id>/",
        advanced_views.AnalyticsJobView.as_view(),
    ),
    # Keep the dynamic assessment slug route last so reserved workflow paths such
    # as regrade-jobs and gradebooks cannot be shadowed by an assessment lookup.
    path(ASSESSMENT, views.AssessmentDetailView.as_view()),
]
