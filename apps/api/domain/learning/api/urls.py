from django.urls import path

from . import views

BASE = "organizations/<slug:slug>/learning/"
COHORT = BASE + "cohorts/<uuid:cohort_id>/"
ENROLLMENT = BASE + "enrollments/<uuid:enrollment_id>/"
ME = BASE + "me/enrollments/<uuid:enrollment_id>/"
UNIT = ME + "units/<uuid:unit_id>/"
ACTIVITY = ME + "activities/<uuid:activity_instance_id>/"

urlpatterns = [
    path(BASE + "academic-periods/", views.AcademicPeriodListCreateView.as_view()),
    path(
        BASE + "course-group-activities/",
        views.CourseGroupActivityListView.as_view(),
    ),
    path(BASE + "academic-groups/", views.AcademicGroupListCreateView.as_view()),
    path(
        BASE + "academic-groups/<uuid:group_id>/roster/",
        views.AcademicGroupRosterView.as_view(),
    ),
    path(BASE + "cohorts/", views.CohortListCreateView.as_view()),
    path(COHORT, views.CohortDetailView.as_view()),
    path(COHORT + "archive/", views.CohortArchiveView.as_view()),
    path(COHORT + "enrollments/", views.CohortEnrollmentView.as_view()),
    path(COHORT + "staff/", views.CohortStaffView.as_view()),
    path(COHORT + "sync-preview/", views.CohortSyncPreviewView.as_view()),
    path(COHORT + "sync-confirm/", views.CohortSyncConfirmView.as_view()),
    path(COHORT + "progress/", views.CohortProgressView.as_view()),
    path(BASE + "enrollments/", views.EnrollmentListCreateView.as_view()),
    path(ENROLLMENT, views.EnrollmentDetailView.as_view()),
    path(ENROLLMENT + "progress/", views.EnrollmentProgressView.as_view()),
    path(ENROLLMENT + "suspend/", views.SuspendEnrollmentView.as_view()),
    path(ENROLLMENT + "reactivate/", views.ReactivateEnrollmentView.as_view()),
    path(ENROLLMENT + "revoke/", views.RevokeEnrollmentView.as_view()),
    path(ENROLLMENT + "upgrade-release/", views.UpgradeEnrollmentView.as_view()),
    path(ENROLLMENT + "make-individual/", views.IndividualizeEnrollmentView.as_view()),
    path(BASE + "me/", views.MyLearningView.as_view()),
    path(ME, views.MyEnrollmentView.as_view()),
    path(ME + "outline/", views.MyOutlineView.as_view()),
    path(ACTIVITY, views.MyActivityView.as_view()),
    path(ME + "assets/access/", views.MyAssetAccessView.as_view()),
    path(UNIT, views.MyUnitView.as_view()),
    path(UNIT + "open/", views.OpenUnitView.as_view()),
    path(UNIT + "complete/", views.CompleteUnitView.as_view()),
    path(UNIT + "reopen/", views.ReopenUnitView.as_view()),
    path(ME + "position/", views.PositionView.as_view()),
]
