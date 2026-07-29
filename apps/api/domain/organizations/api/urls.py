from django.urls import path

from . import views

urlpatterns = [
    path("access/context/", views.AccessContextView.as_view(), name="access-context"),
    path(
        "organizations/", views.OrganizationListView.as_view(), name="organization-list"
    ),
    path(
        "organizations/<slug:slug>/",
        views.OrganizationDetailView.as_view(),
        name="organization-detail",
    ),
    path(
        "organizations/<slug:slug>/memberships/",
        views.MembershipListCreateView.as_view(),
        name="membership-list",
    ),
    path(
        "organizations/<slug:slug>/memberships/<uuid:membership_id>/",
        views.MembershipDetailView.as_view(),
        name="membership-detail",
    ),
    path(
        "organizations/<slug:slug>/memberships/<uuid:membership_id>/suspend/",
        views.SuspendMembershipView.as_view(),
        name="membership-suspend",
    ),
    path(
        "organizations/<slug:slug>/memberships/<uuid:membership_id>/reactivate/",
        views.ReactivateMembershipView.as_view(),
        name="membership-reactivate",
    ),
    path(
        "organizations/<slug:slug>/memberships/<uuid:membership_id>/revoke/",
        views.RevokeMembershipView.as_view(),
        name="membership-revoke",
    ),
    path(
        "organizations/<slug:slug>/memberships/<uuid:membership_id>/roles/",
        views.ReplaceRolesView.as_view(),
        name="membership-roles",
    ),
    path(
        "organizations/<slug:slug>/memberships/<uuid:membership_id>/events/",
        views.MembershipEventsView.as_view(),
        name="membership-events",
    ),
]
