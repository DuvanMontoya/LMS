# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportMissingTypeArgument=false
from __future__ import annotations

import socket

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

from config.celery import app as celery_app
from domain.assets.storage.boto3_gateway import build_s3_client
from domain.discovery.models import GenerationStatus, SearchGeneration
from domain.events.models import DeliveryStatus, EventConsumerDelivery


class Command(BaseCommand):
    help = "Comprueba DB, Redis/Celery, S3, ClamAV, outbox y búsqueda."

    def handle(self, *args: object, **options: object) -> None:
        issues: list[str] = []
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            issues.append("database_unavailable")
        try:
            cache.set("operational-check", "ok", timeout=10)
            if cache.get("operational-check") != "ok":
                issues.append("redis_unavailable")
            cache.delete("operational-check")
        except Exception:
            issues.append("redis_unavailable")
        try:
            with celery_app.connection_for_read() as broker_connection:
                broker_connection.ensure_connection(max_retries=1, timeout=3)
        except Exception:
            issues.append("celery_broker_unavailable")
        try:
            s3_client = build_s3_client(settings.ASSET_S3_INTERNAL_ENDPOINT or None)
            s3_client.head_bucket(Bucket=settings.ASSET_PRIVATE_BUCKET)
            s3_client.head_bucket(Bucket=settings.ASSET_QUARANTINE_BUCKET)
        except Exception:
            issues.append("object_storage_unavailable")
        try:
            with socket.create_connection(
                (settings.ASSET_CLAMAV_HOST, settings.ASSET_CLAMAV_PORT), timeout=3
            ) as clamav:
                clamav.sendall(b"zPING\0")
                if clamav.recv(16).rstrip(b"\0\r\n") != b"PONG":
                    issues.append("antivirus_unavailable")
        except (OSError, TimeoutError):
            issues.append("antivirus_unavailable")
        oldest = (
            EventConsumerDelivery.objects.filter(
                status__in=(DeliveryStatus.PENDING, DeliveryStatus.FAILED)
            )
            .order_by("created_at")
            .values_list("created_at", flat=True)
            .first()
        )
        if oldest and (timezone.now() - oldest).total_seconds() > 300:
            issues.append("outbox_lag_elevated")
        if SearchGeneration.objects.filter(status=GenerationStatus.BUILDING).exists():
            issues.append("search_generation_building")
        if issues:
            raise CommandError(",".join(sorted(set(issues))))
        self.stdout.write(self.style.SUCCESS("platform_operational_check: PASS"))
