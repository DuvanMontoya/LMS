# pyright: reportArgumentType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandParser

from domain.assets.choices import AssetVersionStatus
from domain.assets.models import AssetVariant, AssetVersion
from domain.assets.storage.boto3_gateway import storage_gateway


class Command(BaseCommand):
    help = "Read-only verification of authoritative asset objects and variants."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--all-checksums", action="store_true")
        parser.add_argument("--sample", type=int, default=25)

    def handle(self, *args: object, **options: object) -> None:
        gateway = storage_gateway()
        missing: list[str] = []
        mismatched: list[str] = []
        checked = 0
        checksum_limit = (
            None if bool(options["all_checksums"]) else max(0, int(options["sample"]))
        )
        objects: list[tuple[str, str, str, int]] = [
            (
                str(version.id),
                version.storage_bucket,
                version.storage_key,
                int(version.size_bytes or 0),
            )
            for version in AssetVersion.objects.filter(
                status=AssetVersionStatus.READY
            ).only("id", "storage_bucket", "storage_key", "size_bytes", "sha256")
        ]
        objects.extend(
            (
                str(variant.id),
                variant.storage_bucket,
                variant.storage_key,
                variant.size_bytes,
            )
            for variant in AssetVariant.objects.only(
                "id", "storage_bucket", "storage_key", "size_bytes", "sha256"
            )
        )
        for object_id, bucket, key, size_bytes in objects:
            try:
                head = gateway.head_object(bucket=bucket, key=key)
            except Exception:
                missing.append(object_id)
                continue
            checked += 1
            if head.size_bytes != size_bytes:
                mismatched.append(object_id)
        checksum_results = self._verify_checksums(checksum_limit)
        payload = {
            "checked_objects": checked,
            "missing_ids": missing,
            "size_mismatch_ids": mismatched,
            **checksum_results,
            "valid": not missing
            and not mismatched
            and not checksum_results["checksum_mismatch_ids"],
        }
        self.stdout.write(json.dumps(payload, sort_keys=True))

    @staticmethod
    def _verify_checksums(limit: int | None) -> dict[str, object]:
        gateway = storage_gateway()
        queryset = AssetVersion.objects.filter(status=AssetVersionStatus.READY).exclude(
            sha256=""
        )
        if limit is not None:
            queryset = queryset.order_by("id")[:limit]
        checked = 0
        mismatched: list[str] = []
        with tempfile.TemporaryDirectory(prefix="lms-asset-verify-") as directory:
            for version in queryset:
                path = Path(directory) / str(version.id)
                gateway.download_to_path(
                    bucket=version.storage_bucket, key=version.storage_key, path=path
                )
                hasher = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        hasher.update(chunk)
                digest = hasher.hexdigest()
                checked += 1
                if digest != version.sha256:
                    mismatched.append(str(version.id))
                path.unlink(missing_ok=True)
        return {
            "checked_checksums": checked,
            "checksum_mismatch_ids": mismatched,
        }
