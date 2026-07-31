# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

import json

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from domain.assets.choices import AssetVersionStatus, UploadStatus
from domain.assets.models import AssetUploadSession
from domain.assets.storage.boto3_gateway import storage_gateway


class Command(BaseCommand):
    help = "Expire stale asset upload sessions and abort their multipart uploads."

    def handle(self, *args: object, **options: object) -> None:
        session_ids = list(
            AssetUploadSession.objects.filter(
                expires_at__lte=timezone.now(),
                status__in=[
                    UploadStatus.INITIATED,
                    UploadStatus.UPLOADING,
                    UploadStatus.UPLOADED,
                ],
            ).values_list("id", flat=True)
        )
        gateway = storage_gateway()
        expired = 0
        for session_id in session_ids:
            with transaction.atomic():
                session = (
                    AssetUploadSession.objects.select_for_update()
                    .select_related("asset_version")
                    .filter(pk=session_id)
                    .first()
                )
                if session is None or session.status not in {
                    UploadStatus.INITIATED,
                    UploadStatus.UPLOADING,
                    UploadStatus.UPLOADED,
                }:
                    continue
                if session.multipart_upload_id:
                    gateway.abort_multipart_upload(
                        bucket=session.quarantine_bucket,
                        key=session.quarantine_key,
                        upload_id=session.multipart_upload_id,
                    )
                else:
                    gateway.delete_object(
                        bucket=session.quarantine_bucket, key=session.quarantine_key
                    )
                session.status = UploadStatus.EXPIRED
                session.failure_code = "upload_session_expired"
                session.save(update_fields=["status", "failure_code"])
                version = session.asset_version
                version.status = AssetVersionStatus.FAILED
                version.failed_at = timezone.now()
                version.failure_code = "upload_session_expired"
                version.save(update_fields=["status", "failed_at", "failure_code"])
                expired += 1
        self.stdout.write(json.dumps({"expired_sessions": expired}, sort_keys=True))
