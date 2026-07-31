from __future__ import annotations

import hashlib
from types import SimpleNamespace
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from domain.assets.choices import (
    AssetVersionStatus,
    ProcessingJobStatus,
    ProcessingJobType,
)
from domain.assets.processing.common import ProcessingResult
from domain.assets.processing.jobs import (
    _validate_detected_contract,
    claim_processing_job,
    process_asset_version,
)
from domain.assets.uploads.services import (
    complete_asset_upload,
    initialize_asset_upload,
)

from .support import FakeStorageGateway, celery_result, owner_context


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class ProcessingJobExtendedTests(TestCase):
    def setUp(self) -> None:
        cache.clear()
        self.owner, self.organization = owner_context("processing-job")
        self.gateway = FakeStorageGateway()

    def _uploaded_job(self, payload: bytes = b"name,value\none,1\n"):
        instructions = initialize_asset_upload(
            actor=self.owner,
            organization=self.organization,
            asset_id=None,
            kind="dataset",
            name="Dataset",
            description="Processing integration",
            filename="data.csv",
            declared_mime_type="text/csv",
            size_bytes=len(payload),
            expected_sha256=hashlib.sha256(payload).hexdigest(),
            gateway=self.gateway,
        )
        session = instructions.session
        location = (session.quarantine_bucket, session.quarantine_key)
        self.gateway.objects[location] = payload
        self.gateway.metadata[location] = {"upload-session": str(session.id)}
        with (
            patch(
                "domain.assets.processing.tasks.process_asset_version_task.delay",
                return_value=celery_result(),
            ),
            self.captureOnCommitCallbacks(execute=True),
        ):
            job = complete_asset_upload(
                actor=self.owner,
                organization=self.organization,
                session_id=session.id,
                gateway=self.gateway,
            )
        return session, job

    @patch("domain.assets.processing.jobs.ClamAVClient.scan_path")
    def test_complete_dataset_pipeline_promotes_and_cleans_quarantine(
        self, scan_path
    ) -> None:
        scan_path.return_value = SimpleNamespace(clean=True, signature="")
        session, job = self._uploaded_job()
        process_asset_version(job.id, gateway=self.gateway)
        job.refresh_from_db()
        version = job.asset_version
        version.refresh_from_db()
        version.asset.refresh_from_db()
        self.assertEqual(job.status, ProcessingJobStatus.COMPLETED)
        self.assertEqual(version.status, AssetVersionStatus.READY)
        self.assertEqual(version.row_count, 1)
        self.assertEqual(version.asset.current_version_id, version.id)
        self.assertNotIn(
            (session.quarantine_bucket, session.quarantine_key),
            self.gateway.objects,
        )
        self.assertTrue(version.storage_key.startswith("organizations/"))
        self.assertIsNone(claim_processing_job(job.id))

    @patch("domain.assets.processing.jobs.ClamAVClient.scan_path")
    def test_infected_upload_is_rejected_and_deleted(self, scan_path) -> None:
        scan_path.return_value = SimpleNamespace(
            clean=False, signature="Eicar-Test-Signature"
        )
        session, job = self._uploaded_job(b"infected test")
        process_asset_version(job.id, gateway=self.gateway)
        job.refresh_from_db()
        version = job.asset_version
        version.refresh_from_db()
        self.assertEqual(version.status, AssetVersionStatus.REJECTED)
        self.assertEqual(version.failure_code, "malware_detected")
        self.assertEqual(version.malware_signature, "Eicar-Test-Signature")
        self.assertNotIn(
            (session.quarantine_bucket, session.quarantine_key),
            self.gateway.objects,
        )

    @patch("domain.assets.processing.jobs.ClamAVClient.scan_path")
    def test_checksum_mismatch_fails_job_without_promotion(self, scan_path) -> None:
        scan_path.return_value = SimpleNamespace(clean=True, signature="")
        session, job = self._uploaded_job()
        self.gateway.objects[(session.quarantine_bucket, session.quarantine_key)] = (
            b"changed after completion"
        )
        process_asset_version(job.id, gateway=self.gateway)
        job.refresh_from_db()
        job.asset_version.refresh_from_db()
        self.assertEqual(job.status, ProcessingJobStatus.FAILED)
        self.assertEqual(job.asset_version.status, AssetVersionStatus.FAILED)

    def test_active_lease_and_missing_job_are_not_claimed(self) -> None:
        _session, job = self._uploaded_job()
        claimed = claim_processing_job(job.id)
        self.assertIsNotNone(claimed)
        self.assertIsNone(claim_processing_job(job.id))
        self.assertIsNone(claim_processing_job(self.organization.id))
        job.refresh_from_db()
        self.assertEqual(job.job_type, ProcessingJobType.INITIAL)

    def test_browser_container_mime_aliases_are_accepted_after_ffprobe(self) -> None:
        cases = (
            ("audio/x-m4a", ".m4a", "audio/mp4", ".m4a"),
            ("audio/m4a", ".m4a", "audio/mp4", ".m4a"),
            ("video/quicktime", ".mov", "video/mp4", ".mp4"),
        )
        for (
            declared_mime,
            declared_extension,
            detected_mime,
            detected_extension,
        ) in cases:
            version = SimpleNamespace(
                asset=SimpleNamespace(
                    kind=("audio" if declared_mime.startswith("audio") else "video")
                ),
                declared_mime_type=declared_mime,
                extension=declared_extension,
            )
            _validate_detected_contract(
                version,
                ProcessingResult(
                    detected_mime_type=detected_mime,
                    extension=detected_extension,
                    technical_metadata={},
                ),
            )
