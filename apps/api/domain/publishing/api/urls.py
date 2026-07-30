from django.urls import path

from . import views

COURSE = "organizations/<slug:slug>/courses/<slug:course_slug>/"
RELEASE = COURSE + "releases/<int:release_number>/"
LIBRARY = "organizations/<slug:slug>/library/courses/"

urlpatterns = [
    path(COURSE + "publication/", views.PublicationStateView.as_view()),
    path(
        COURSE + "revisions/<uuid:revision_id>/publish/",
        views.PublishRevisionView.as_view(),
    ),
    path(COURSE + "publication/withdraw/", views.WithdrawPublicationView.as_view()),
    path(COURSE + "releases/", views.ReleaseListView.as_view()),
    path(RELEASE, views.ReleaseDetailView.as_view()),
    path(RELEASE + "outline/", views.ReleaseOutlineView.as_view()),
    path(
        RELEASE + "units/<uuid:unit_id>/",
        views.ReleaseUnitView.as_view(),
    ),
    path(RELEASE + "verify/", views.ReleaseVerifyView.as_view()),
    path(RELEASE + "create-draft/", views.CreateDraftView.as_view()),
    path(LIBRARY, views.LibraryListView.as_view()),
    path(LIBRARY + "<slug:course_slug>/", views.LibraryDetailView.as_view()),
    path(
        LIBRARY + "<slug:course_slug>/outline/",
        views.LibraryOutlineView.as_view(),
    ),
    path(
        LIBRARY + "<slug:course_slug>/units/<uuid:unit_id>/",
        views.LibraryUnitView.as_view(),
    ),
]
