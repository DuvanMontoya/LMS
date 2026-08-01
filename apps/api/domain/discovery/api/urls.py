from django.urls import path

from .views import (
    SearchIndexJobsView,
    SearchIndexView,
    SearchRebuildView,
    SearchSuggestionsView,
    SearchView,
)

urlpatterns = [
    path(
        "organizations/<slug:organization_slug>/search/",
        SearchView.as_view(),
        name="academic-search",
    ),
    path(
        "organizations/<slug:organization_slug>/search/suggestions/",
        SearchSuggestionsView.as_view(),
        name="academic-search-suggestions",
    ),
    path("platform/search-index/", SearchIndexView.as_view(), name="search-index"),
    path(
        "platform/search-index/rebuild/",
        SearchRebuildView.as_view(),
        name="search-index-rebuild",
    ),
    path(
        "platform/search-index/jobs/",
        SearchIndexJobsView.as_view(),
        name="search-index-jobs",
    ),
]
