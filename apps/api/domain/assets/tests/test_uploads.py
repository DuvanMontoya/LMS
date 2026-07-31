from __future__ import annotations

from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from domain.assets.choices import AssetVersionStatus, UploadStatus
from domain.assets.exceptions import AssetUploadInvalid
from domain.assets.models import AssetProcessingJob
from domain.assets.uploads.services import (
    abort_asset_upload,
    complete_asset_upload,
    initialize_asset_upload,
)

from .support import FakeStorageGateway, celery_result, owner_context


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class UploadServiceTests(TestCase):
    def setUp(self) -> None:
        cache.clear()
        self.owner, self.organization = owner_context("uploads")
        self.gateway = FakeStorageGateway()

    def initialize(self, *, size: int = 12):
        return initialize_asset_upload(
            actor=self.owner,
            organization=self.organization,
            asset_id=None,
            kind="image",
            name="Diagram",
            description="Own test asset",
            filename="../../diagram.png",
            declared_mime_type="image/png",
            size_bytes=size,
            expected_sha256="",
            gateway=self.gateway,
        )

    def test_simple_upload_uses_server_key_and_dispatches_after_commit(self) -> None:
        instructions = self.initialize()
        session = instructions.session
        self.assertEqual(session.upload_method, "single")
        self.assertNotIn("diagram", session.quarantine_key)
        self.gateway.objects[(session.quarantine_bucket, session.quarantine_key)] = (
            b"hello world!"
        )
        self.gateway.metadata[(session.quarantine_bucket, session.quarantine_key)] = {
            "upload-session": str(session.id)
        }
        with (
            patch(
                "domain.assets.processing.tasks.process_asset_version_task.delay",
                return_value=celery_result(),
            ) as delay,
            self.captureOnCommitCallbacks(execute=True),
        ):
            first = complete_asset_upload(
                actor=self.owner,
                organization=self.organization,
                session_id=session.id,
                gateway=self.gateway,
            )
        second = complete_asset_upload(
            actor=self.owner,
            organization=self.organization,
            session_id=session.id,
            gateway=self.gateway,
        )
        session.refresh_from_db()
        session.asset_version.refresh_from_db()
        self.assertEqual(first.id, second.id)
        self.assertEqual(session.status, UploadStatus.COMPLETED)
        self.assertEqual(session.asset_version.status, AssetVersionStatus.UPLOADED)
        self.assertEqual(AssetProcessingJob.objects.count(), 1)
        delay.assert_called_once_with(str(first.id))

    def test_head_size_or_metadata_mismatch_fails_closed(self) -> None:
        instructions = self.initialize()
        session = instructions.session
        self.gateway.objects[(session.quarantine_bucket, session.quarantine_key)] = (
            b"wrong"
        )
        self.gateway.metadata[(session.quarantine_bucket, session.quarantine_key)] = {
            "upload-session": "foreign"
        }
        with self.assertRaises(AssetUploadInvalid):
            complete_asset_upload(
                actor=self.owner,
                organization=self.organization,
                session_id=session.id,
                gateway=self.gateway,
            )

    def test_abort_is_idempotent_and_marks_version_failed(self) -> None:
        session = self.initialize().session
        first = abort_asset_upload(
            actor=self.owner,
            organization=self.organization,
            session_id=session.id,
            gateway=self.gateway,
        )
        second = abort_asset_upload(
            actor=self.owner,
            organization=self.organization,
            session_id=session.id,
            gateway=self.gateway,
        )
        first.asset_version.refresh_from_db()
        self.assertEqual(first.id, second.id)
        self.assertEqual(second.status, UploadStatus.ABORTED)
        self.assertEqual(first.asset_version.failure_code, "upload_aborted")
