# pyright: reportArgumentType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

import base64
import hashlib
import json
import math
import struct
import subprocess
import tempfile
import time
import wave
from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from PIL import Image, ImageDraw
from pypdf import PdfWriter

from domain.assets.choices import AssetKind, AssetVersionStatus
from domain.assets.models import Asset
from domain.assets.policies import can_upload_asset
from domain.assets.storage.boto3_gateway import build_s3_client
from domain.assets.uploads.services import (
    complete_asset_upload,
    initialize_asset_upload,
)
from domain.organizations.choices import MembershipStatus
from domain.organizations.models import Membership, Organization

if TYPE_CHECKING:
    from domain.identity.models import User


@dataclass(frozen=True)
class DemoAsset:
    kind: str
    name: str
    description: str
    filename: str
    mime_type: str
    create: Callable[[Path], None]


def _create_image(path: Path) -> None:
    image = Image.new("RGB", (960, 540), "#13213c")
    draw = ImageDraw.Draw(image)
    draw.rectangle((48, 48, 912, 492), outline="#55c2ff", width=6)
    draw.text((96, 235), "LMS · Asset académico de demostración", fill="#ffffff")
    image.save(path, format="PNG", optimize=True)


def _create_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    with path.open("wb") as target:
        writer.write(target)


def _create_audio(path: Path) -> None:
    sample_rate = 44_100
    duration_seconds = 2
    amplitude = 8_000
    with wave.open(str(path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(sample_rate)
        frames = bytearray()
        for index in range(sample_rate * duration_seconds):
            value = int(amplitude * math.sin(2 * math.pi * 440 * index / sample_rate))
            frames.extend(struct.pack("<h", value))
        target.writeframes(bytes(frames))


def _create_video(path: Path) -> None:
    command = [
        settings.ASSET_FFMPEG_PATH,
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "color=c=0x13213c:s=640x360:d=2:r=24",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=2",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        "-movflags",
        "+faststart",
        "-y",
        str(path),
    ]
    try:
        subprocess.run(
            command,
            check=True,
            shell=False,
            timeout=60,
            capture_output=True,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise CommandError(
            "No fue posible generar el video demo con FFmpeg."
        ) from error


def _write_text(value: str) -> Callable[[Path], None]:
    def create(path: Path) -> None:
        path.write_text(value, encoding="utf-8", newline="\n")

    return create


DEMO_ASSETS = (
    DemoAsset(
        AssetKind.IMAGE,
        "Imagen académica demo",
        "Imagen reproducible para validar variantes responsivas.",
        "imagen-academica-demo.png",
        "image/png",
        _create_image,
    ),
    DemoAsset(
        AssetKind.DOCUMENT,
        "Documento académico demo",
        "PDF reproducible para validar inspección documental.",
        "documento-academico-demo.pdf",
        "application/pdf",
        _create_pdf,
    ),
    DemoAsset(
        AssetKind.AUDIO,
        "Audio académico demo",
        "Tono breve reproducible para validar transcodificación.",
        "audio-academico-demo.wav",
        "audio/wav",
        _create_audio,
    ),
    DemoAsset(
        AssetKind.VIDEO,
        "Video académico demo",
        "Video sintético breve para validar playback y poster.",
        "video-academico-demo.mp4",
        "video/mp4",
        _create_video,
    ),
    DemoAsset(
        AssetKind.CAPTION,
        "Subtítulos académicos demo",
        "WebVTT reproducible asociado a medios accesibles.",
        "subtitulos-academicos-demo.vtt",
        "text/vtt",
        _write_text(
            "WEBVTT\n\n00:00:00.000 --> 00:00:01.500\n"
            "Recurso académico de demostración.\n"
        ),
    ),
    DemoAsset(
        AssetKind.DATASET,
        "Dataset CSV demo",
        "Datos tabulares pequeños para validar perfilado seguro.",
        "dataset-academico-demo.csv",
        "text/csv",
        _write_text("periodo,estudiantes,promedio\n2025-1,32,4.2\n2025-2,35,4.4\n"),
    ),
    DemoAsset(
        AssetKind.DATASET,
        "Dataset JSON demo",
        "Datos estructurados pequeños para validar metadatos.",
        "dataset-academico-demo.json",
        "application/json",
        _write_text(
            json.dumps(
                {
                    "curso": "Demostración",
                    "indicadores": [{"periodo": "2025-2", "promedio": 4.4}],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        ),
    ),
)


class Command(BaseCommand):
    help = "Crea y procesa assets académicos reproducibles sólo para desarrollo local."

    def handle(self, *args: object, **options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("Los assets demo sólo se permiten con DEBUG=True.")
        organization = Organization.objects.filter(slug="organizacion-demo").first()
        if organization is None:
            raise CommandError(
                "Ejecuta primero pnpm demo:organizations para crear el contexto demo."
            )
        actor = self._find_upload_actor(organization)
        if actor is None:
            raise CommandError(
                "La organización demo no tiene un miembro activo autorizado para "
                "cargar recursos."
            )

        created = 0
        skipped = 0
        client = build_s3_client(settings.ASSET_S3_INTERNAL_ENDPOINT or None)
        with tempfile.TemporaryDirectory(prefix="lms-demo-assets-") as directory:
            root = Path(directory)
            for specification in DEMO_ASSETS:
                current_asset = (
                    Asset.objects.filter(
                        organization=organization,
                        name=specification.name,
                        current_version__status=AssetVersionStatus.READY,
                    )
                    .select_related("current_version")
                    .first()
                )
                if current_asset is not None and self._object_is_available(
                    client=client,
                    asset=current_asset,
                ):
                    skipped += 1
                    self.stdout.write(f"SKIP {specification.name}: ya está listo.")
                    continue
                if current_asset is not None:
                    self.stdout.write(
                        self.style.WARNING(
                            f"REPAIR {specification.name}: el objeto actual no existe; "
                            "se creará una nueva versión."
                        )
                    )
                self._create_and_process(
                    specification=specification,
                    root=root,
                    organization=organization,
                    actor=actor,
                )
                created += 1
                self.stdout.write(self.style.SUCCESS(f"READY {specification.name}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Assets demo listos: creados={created}, omitidos={skipped}."
            )
        )

    @staticmethod
    def _find_upload_actor(organization: Organization) -> User | None:
        memberships = list(
            Membership.objects.filter(
                organization=organization,
                status=MembershipStatus.ACTIVE.value,
            ).select_related("user")
        )
        preferred_emails = ("author@demo.local", "administrator@demo.local")
        memberships.sort(
            key=lambda membership: (
                preferred_emails.index(membership.user.email)
                if membership.user.email in preferred_emails
                else len(preferred_emails),
                membership.user.email,
            )
        )
        for membership in memberships:
            if can_upload_asset(membership.user, organization):
                return membership.user
        return None

    @staticmethod
    def _object_is_available(*, client: BaseClient, asset: Asset) -> bool:
        version = asset.current_version
        if version is None or not version.storage_bucket or not version.storage_key:
            return False
        try:
            response = client.head_object(
                Bucket=version.storage_bucket,
                Key=version.storage_key,
            )
        except (BotoCoreError, ClientError):
            return False
        return int(response.get("ContentLength", -1)) == version.size_bytes

    def _create_and_process(
        self,
        *,
        specification: DemoAsset,
        root: Path,
        organization: Organization,
        actor: User,
    ) -> None:
        source = root / specification.filename
        specification.create(source)
        payload = source.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        existing = (
            Asset.objects.filter(
                organization=organization,
                name=specification.name,
                kind=specification.kind,
            )
            .order_by("created_at")
            .first()
        )
        instructions = initialize_asset_upload(
            actor=actor,
            organization=organization,
            asset_id=existing.id if existing else None,
            kind=specification.kind,
            name=specification.name,
            description=specification.description,
            filename=specification.filename,
            declared_mime_type=specification.mime_type,
            size_bytes=len(payload),
            expected_sha256=digest,
        )
        session = instructions.session
        if session.upload_method != "single":
            raise CommandError("Los assets demo deben caber en una carga simple.")
        client = build_s3_client(settings.ASSET_S3_INTERNAL_ENDPOINT or None)
        client.put_object(
            Bucket=session.quarantine_bucket,
            Key=session.quarantine_key,
            Body=BytesIO(payload),
            ContentType="application/octet-stream",
            Metadata={"upload-session": str(session.id)},
            ChecksumAlgorithm="SHA256",
            ChecksumSHA256=base64.b64encode(bytes.fromhex(digest)).decode("ascii"),
            ServerSideEncryption=settings.ASSET_S3_SERVER_SIDE_ENCRYPTION,
        )
        complete_asset_upload(
            actor=actor,
            organization=organization,
            session_id=session.id,
        )
        deadline = time.monotonic() + 180
        version = session.asset_version
        while time.monotonic() < deadline:
            version.refresh_from_db()
            if version.status == AssetVersionStatus.READY:
                return
            if version.status in {
                AssetVersionStatus.REJECTED,
                AssetVersionStatus.FAILED,
            }:
                raise CommandError(
                    f"{specification.name} terminó en {version.status}: "
                    f"{version.failure_code or 'sin código'}."
                )
            time.sleep(1)
        raise CommandError(
            f"El procesamiento de {specification.name} excedió 180 segundos."
        )
