from django.urls import path

from . import views

BASE = "organizations/<slug:slug>/courses/"
REVISION = BASE + "<slug:course_slug>/revisions/<uuid:revision_id>/"

urlpatterns = [
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
