from django.urls import path

from . import views

BASE = "organizations/<slug:slug>/courses/"
REVISION = BASE + "<slug:course_slug>/revisions/<uuid:revision_id>/"

urlpatterns = [
    path(
        BASE + "teaching-exceptions/",
        views.CourseTeachingExceptionListCreateView.as_view(),
    ),
    path(
        BASE + "teaching-exceptions/<uuid:exception_id>/close/",
        views.CloseCourseTeachingExceptionView.as_view(),
    ),
    path(BASE, views.CourseListCreateView.as_view()),
    path(BASE + "<slug:course_slug>/", views.CourseDetailView.as_view()),
    path(BASE + "<slug:course_slug>/archive/", views.ArchiveCourseView.as_view()),
    path(BASE + "<slug:course_slug>/restore/", views.RestoreCourseView.as_view()),
    path(BASE + "<slug:course_slug>/revisions/", views.RevisionListView.as_view()),
    path(REVISION, views.RevisionDetailView.as_view()),
    path(REVISION + "transitions/", views.TransitionListView.as_view()),
    path(REVISION + "subjects/", views.SubjectAlignmentView.as_view()),
    path(REVISION + "learning-objectives/", views.ObjectiveAlignmentView.as_view()),
    path(REVISION + "outline/", views.OutlineView.as_view()),
    path(REVISION + "readiness/", views.ReadinessView.as_view()),
    path(REVISION + "modules/", views.ModuleListCreateView.as_view()),
    path(REVISION + "modules/order/", views.ModuleOrderView.as_view()),
    path(REVISION + "modules/<uuid:module_id>/", views.ModuleDetailView.as_view()),
    path(
        REVISION + "modules/<uuid:module_id>/archive/",
        views.ArchiveModuleView.as_view(),
    ),
    path(
        REVISION + "modules/<uuid:module_id>/restore/",
        views.RestoreModuleView.as_view(),
    ),
    path(
        REVISION + "modules/<uuid:module_id>/units/",
        views.UnitListCreateView.as_view(),
    ),
    path(
        REVISION + "modules/<uuid:module_id>/units/order/",
        views.UnitOrderView.as_view(),
    ),
    path(
        REVISION + "modules/<uuid:module_id>/activities/",
        views.ActivityListCreateView.as_view(),
    ),
    path(
        REVISION + "modules/<uuid:module_id>/activities/order/",
        views.ActivityOrderView.as_view(),
    ),
    path(
        REVISION + "activities/<uuid:activity_id>/",
        views.ActivityDetailView.as_view(),
    ),
    path(
        REVISION + "activities/<uuid:activity_id>/move/",
        views.MoveActivityView.as_view(),
    ),
    path(
        REVISION + "activities/<uuid:activity_id>/learning-objectives/",
        views.ActivityObjectiveView.as_view(),
    ),
    path(
        REVISION + "activities/<uuid:activity_id>/availability-rules/",
        views.ActivityAvailabilityRulesView.as_view(),
    ),
    path(REVISION + "completion-policy/", views.CompletionPolicyView.as_view()),
    path(REVISION + "grading-scheme/", views.GradingSchemeView.as_view()),
    path(REVISION + "units/<uuid:unit_id>/", views.UnitDetailView.as_view()),
    path(
        REVISION + "units/<uuid:unit_id>/archive/",
        views.ArchiveUnitView.as_view(),
    ),
    path(
        REVISION + "units/<uuid:unit_id>/restore/",
        views.RestoreUnitView.as_view(),
    ),
    path(REVISION + "units/<uuid:unit_id>/topics/", views.UnitTopicView.as_view()),
    path(
        REVISION + "units/<uuid:unit_id>/learning-objectives/",
        views.UnitObjectiveView.as_view(),
    ),
    path(REVISION + "submit-review/", views.SubmitReviewView.as_view()),
    path(REVISION + "request-changes/", views.RequestChangesView.as_view()),
    path(REVISION + "approve/", views.ApproveRevisionView.as_view()),
]
