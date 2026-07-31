from __future__ import annotations

import io
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from domain.assets.choices import AssetKind, AssetVersionStatus, UploadStatus
from domain.assets.management.commands import bootstrap_demo_assets
from domain.assets.models import Asset, AssetUploadSession, AssetVersion
from domain.assets.storage.administration import BucketState
from domain.assets.uploads.services import initialize_asset_upload
from domain.organizations.services import create_organization_with_owner

from .support import FakeStorageGateway, owner_context


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class AssetManagementCommandTests(TestCase):
    def setUp(self) -> None:
        cache.clear()

    def test_demo_file_builders_are_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "image.png"
            pdf = root / "document.pdf"
            audio = root / "audio.wav"
            text = root / "data.txt"
            bootstrap_demo_assets._create_image(image)
            bootstrap_demo_assets._create_pdf(pdf)
            bootstrap_demo_assets._create_audio(audio)
            bootstrap_demo_assets._write_text("safe\n")(text)
            self.assertGreater(image.stat().st_size, 100)
            self.assertGreater(pdf.stat().st_size, 100)
            self.assertGreater(audio.stat().st_size, 100)
            self.assertEqual(text.read_text(encoding="utf-8"), "safe\n")

    @override_settings(DEBUG=True)
    def test_demo_command_iterates_catalog_and_requires_context(self) -> None:
        with self.assertRaisesMessage(Exception, "pnpm demo:organizations"):
            call_command("bootstrap_demo_assets")

        owner = get_user_model().objects.create_user(
            email="owner@demo.local",
            password="CorrectHorseBatteryStaple42!",
        )
        create_organization_with_owner(
            actor=owner,
            name="Organización demo",
            slug="organizacion-demo",
        )
        output = io.StringIO()
        with patch.object(
            bootstrap_demo_assets.Command,
            "_create_and_process",
        ) as create_and_process:
            call_command("bootstrap_demo_assets", stdout=output)
        self.assertEqual(
            create_and_process.call_count, len(bootstrap_demo_assets.DEMO_ASSETS)
        )
        self.assertIn("creados=7", output.getvalue())

    def test_expire_and_reconcile_commands_are_safe_and_idempotent(self) -> None:
        owner, organization = owner_context("commands-expire")
        gateway = FakeStorageGateway()
        session = initialize_asset_upload(
            actor=owner,
            organization=organization,
            asset_id=None,
            kind=AssetKind.IMAGE,
            name="Expired image",
            description="",
            filename="image.png",
            declared_mime_type="image/png",
            size_bytes=12,
            gateway=gateway,
        ).session
        AssetUploadSession.objects.filter(pk=session.pk).update(
            expires_at=timezone.now()
        )
        output = io.StringIO()
        with patch(
            "domain.assets.management.commands.expire_stale_upload_sessions.storage_gateway",
            return_value=gateway,
        ):
            call_command("expire_stale_upload_sessions", stdout=output)
        session.refresh_from_db()
        session.asset_version.refresh_from_db()
        self.assertEqual(session.status, UploadStatus.EXPIRED)
        self.assertEqual(session.asset_version.status, AssetVersionStatus.FAILED)
        self.assertIn("1", output.getvalue())

        report = io.StringIO()
        call_command("reconcile_asset_storage", stdout=report)
        self.assertIn("report-only", report.getvalue())
        repaired = io.StringIO()
        with patch(
            "domain.assets.management.commands.reconcile_asset_storage.call_command"
        ) as nested:
            call_command("reconcile_asset_storage", repair=True, stdout=repaired)
        nested.assert_called_once()
        self.assertIn("safe-repair", repaired.getvalue())

    def test_storage_command_routes_actions_and_translates_domain_errors(self) -> None:
        state = BucketState("bucket", "Enabled", "AES256", True, 1)
        cases = (
            ("validate", "validate_storage_configuration", None),
            ("init", "initialize_storage", (state, state)),
            ("status", "storage_status", (state, state)),
            (
                "smoke",
                "storage_smoke",
                {"size": 1, "checksum_present": True},
            ),
            ("reset-local", "reset_local_storage", None),
        )
        for action, function_name, result in cases:
            output = io.StringIO()
            with patch(
                "domain.assets.management.commands.asset_storage." + function_name,
                return_value=result,
            ):
                call_command("asset_storage", action, stdout=output)
            self.assertTrue(output.getvalue().strip())

    def test_verify_storage_reports_size_and_checksum_drift(self) -> None:
        owner, organization = owner_context("commands-verify")
        asset = Asset.objects.create(
            organization=organization,
            kind=AssetKind.DATASET,
            name="Dataset",
            created_by=owner,
            updated_by=owner,
        )
        payload = b"name,value\none,1\n"
        version = AssetVersion.objects.create(
            asset=asset,
            number=1,
            status=AssetVersionStatus.READY,
            original_filename="data.csv",
            declared_mime_type="text/csv",
            detected_mime_type="text/csv",
            extension=".csv",
            size_bytes=len(payload),
            sha256="f" * 64,
            storage_bucket="private",
            storage_key="objects/data.csv",
            expected_asset_lock_version=1,
            created_by=owner,
        )
        gateway = FakeStorageGateway()
        gateway.objects[(version.storage_bucket, version.storage_key)] = payload
        output = io.StringIO()
        with patch(
            "domain.assets.management.commands.verify_asset_storage.storage_gateway",
            return_value=gateway,
        ):
            call_command("verify_asset_storage", sample=10, stdout=output)
        self.assertIn(str(version.id), output.getvalue())
        self.assertIn('"valid": false', output.getvalue())

    @override_settings(DEBUG=True)
    def test_malware_smoke_command_checks_rejection_and_cleanup(self) -> None:
        owner = get_user_model().objects.create_user(
            email="owner@demo.local",
            password="CorrectHorseBatteryStaple42!",
        )
        organization = create_organization_with_owner(
            actor=owner,
            name="Organización demo",
            slug="organizacion-demo",
        )
        asset = SimpleNamespace(lock_version=1)
        version = MagicMock(
            status=AssetVersionStatus.REJECTED,
            failure_code="malware_detected",
            malware_signature="Eicar-Test-Signature",
            asset=asset,
        )
        session = SimpleNamespace(
            upload_method="single",
            id=organization.id,
            quarantine_bucket="quarantine",
            quarantine_key="uploads/eicar",
            asset_version=version,
        )
        instructions = SimpleNamespace(session=session)
        client = MagicMock()
        client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}, "ResponseMetadata": {"HTTPStatusCode": 404}},
            "HeadObject",
        )
        output = io.StringIO()
        with (
            patch(
                "domain.assets.management.commands.smoke_asset_malware.initialize_asset_upload",
                return_value=instructions,
            ),
            patch(
                "domain.assets.management.commands.smoke_asset_malware.complete_asset_upload"
            ),
            patch(
                "domain.assets.management.commands.smoke_asset_malware.build_s3_client",
                return_value=client,
            ),
            patch(
                "domain.assets.management.commands.smoke_asset_malware.archive_asset"
            ) as archive,
        ):
            call_command("smoke_asset_malware", stdout=output)
        archive.assert_called_once()
        self.assertIn("PASS EICAR", output.getvalue())
