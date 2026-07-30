from django.urls import path

from .views import (
    RestoreUnitContentView,
    UnitContentVersionDetailView,
    UnitContentVersionListView,
    UnitContentView,
    ValidateUnitContentView,
)

BASE = (
    "organizations/<slug:organization_slug>/courses/<slug:course_slug>/"
    "revisions/<uuid:revision_id>/units/<uuid:unit_id>/content/"
)

urlpatterns = [
    path(BASE, UnitContentView.as_view()),
    path(BASE + "validate/", ValidateUnitContentView.as_view()),
    path(BASE + "versions/", UnitContentVersionListView.as_view()),
    path(
        BASE + "versions/<int:version_number>/",
        UnitContentVersionDetailView.as_view(),
    ),
    path(
        BASE + "versions/<int:version_number>/restore/",
        RestoreUnitContentView.as_view(),
    ),
]
