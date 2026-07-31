from django.urls import path

from . import views

ORG = "organizations/<slug:organization_slug>/"
ASSETS = ORG + "assets/"
ASSET = ASSETS + "<uuid:asset_id>/"
VERSION = ASSET + "versions/<uuid:version_id>/"
UPLOAD = ORG + "uploads/<uuid:session_id>/"

urlpatterns = [
    path(ASSETS, views.AssetListView.as_view()),
    path(ASSET, views.AssetDetailView.as_view()),
    path(ASSET + "archive/", views.AssetArchiveView.as_view()),
    path(ASSET + "restore/", views.AssetRestoreView.as_view()),
    path(ASSET + "versions/", views.AssetVersionListView.as_view()),
    path(VERSION, views.AssetVersionDetailView.as_view()),
    path(VERSION + "promote/", views.AssetVersionPromoteView.as_view()),
    path(VERSION + "reprocess/", views.AssetVersionReprocessView.as_view()),
    path(VERSION + "access/", views.AssetAccessView.as_view()),
    path(VERSION + "original-download/", views.AssetOriginalDownloadView.as_view()),
    path(ASSET + "usage/", views.AssetUsageView.as_view()),
    path(ORG + "uploads/", views.UploadInitializeView.as_view()),
    path(UPLOAD, views.UploadDetailView.as_view()),
    path(
        UPLOAD + "parts/<int:part_number>/sign/",
        views.UploadPartSignView.as_view(),
    ),
    path(
        UPLOAD + "parts/<int:part_number>/record/",
        views.UploadPartRecordView.as_view(),
    ),
    path(UPLOAD + "complete/", views.UploadCompleteView.as_view()),
    path(UPLOAD + "abort/", views.UploadAbortView.as_view()),
    path(
        ORG + "processing-jobs/<uuid:job_id>/",
        views.ProcessingJobDetailView.as_view(),
    ),
]
