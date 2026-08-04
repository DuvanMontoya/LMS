# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
"""Rules for the single private resource delivered by a typed lesson."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from domain.assets.choices import (
    AssetKind,
    AssetStatus,
    AssetVersionStatus,
    VariantRole,
)
from domain.assets.models import AssetVersion
from domain.courses.choices import LessonKind
from domain.courses.models import CourseUnit

from .exceptions import ContentDeliveryInvalid


@dataclass(frozen=True)
class LessonResourceRule:
    asset_kind: AssetKind
    extensions: frozenset[str]
    mime_types: frozenset[str]


_RESOURCE_RULES = MappingProxyType(
    {
        LessonKind.LATEX_SOURCE: LessonResourceRule(
            asset_kind=AssetKind.DOCUMENT,
            extensions=frozenset({".tex"}),
            mime_types=frozenset({"application/x-tex", "text/x-tex"}),
        ),
        LessonKind.MARKDOWN_SOURCE: LessonResourceRule(
            asset_kind=AssetKind.DOCUMENT,
            extensions=frozenset({".md"}),
            mime_types=frozenset({"text/markdown", "text/x-markdown"}),
        ),
        LessonKind.PDF: LessonResourceRule(
            asset_kind=AssetKind.DOCUMENT,
            extensions=frozenset({".pdf"}),
            mime_types=frozenset({"application/pdf"}),
        ),
        LessonKind.SLIDES: LessonResourceRule(
            asset_kind=AssetKind.DOCUMENT,
            extensions=frozenset({".pdf", ".pptx"}),
            mime_types=frozenset(
                {
                    "application/pdf",
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                }
            ),
        ),
        LessonKind.AUDIO: LessonResourceRule(
            asset_kind=AssetKind.AUDIO,
            extensions=frozenset({".m4a", ".mp3", ".mp4", ".ogg", ".wav"}),
            mime_types=frozenset(
                {
                    "audio/mp4",
                    "audio/mpeg",
                    "audio/ogg",
                    "audio/wav",
                }
            ),
        ),
    }
)


def lesson_resource_rule(lesson_kind: LessonKind) -> LessonResourceRule | None:
    return _RESOURCE_RULES.get(lesson_kind)


def validate_lesson_resource(
    *, unit: CourseUnit, version: AssetVersion
) -> LessonResourceRule:
    rule = lesson_resource_rule(unit.lesson_kind)
    if rule is None:
        raise ContentDeliveryInvalid(
            "Esta modalidad no admite un archivo de entrega.", path="lesson_kind"
        )
    if version.asset.organization_id != unit.module.revision.course.organization_id:
        raise ContentDeliveryInvalid(
            "El archivo pertenece a otra organización.", path="asset_version_id"
        )
    if version.asset.status != AssetStatus.ACTIVE:
        raise ContentDeliveryInvalid(
            "No se puede vincular un archivo archivado.", path="asset_version_id"
        )
    if version.status != AssetVersionStatus.READY:
        raise ContentDeliveryInvalid(
            "El archivo debe estar listo antes de vincularlo.", path="asset_version_id"
        )
    if version.asset.kind != rule.asset_kind:
        raise ContentDeliveryInvalid(
            "El tipo de archivo no corresponde a la modalidad de la lección.",
            path="asset_version_id",
        )
    if version.extension not in rule.extensions or (
        version.detected_mime_type not in rule.mime_types
    ):
        raise ContentDeliveryInvalid(
            "La extensión o el MIME verificado no corresponde a la modalidad de la lección.",
            path="asset_version_id",
        )
    if (
        rule.asset_kind == AssetKind.AUDIO
        and not version.variants.filter(role=VariantRole.AUDIO_PLAYBACK).exists()
    ):
        raise ContentDeliveryInvalid(
            "El audio todavía no tiene la variante de reproducción privada.",
            path="asset_version_id",
        )
    return rule
