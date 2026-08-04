# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from django.core.exceptions import ObjectDoesNotExist

from domain.assets.choices import AssetKind, AssetVersionStatus, VariantRole
from domain.courses.choices import LessonKind, StructureStatus
from domain.courses.models import CourseRevision, CourseUnit

from .asset_references import ASSET_NODE_KINDS
from .canonical import content_digest
from .exceptions import ContentDeliveryInvalid, ContentDomainError
from .extraction import has_meaningful_content, iter_nodes
from .lesson_resources import lesson_resource_rule, validate_lesson_resource
from .models import UnitContentDocument
from .schemas import schema_registry
from .validators import validate_content


def enrich_content_outline(revision: CourseRevision) -> None:
    metadata = {
        row["unit_id"]: row
        for row in UnitContentDocument.objects.filter(
            unit__module__revision=revision
        ).values(
            "unit_id",
            "current_version__number",
            "current_version__character_count",
            "updated_at",
        )
    }
    for module in revision.modules.all():
        for unit in module.units.all():
            if unit.lesson_kind != LessonKind.DOCUMENT:
                unit.content_status = "not_applicable"
                unit.content_version = None
                unit.content_updated_at = None
                unit.delivery_status = _non_document_delivery_status(unit)
                continue
            row = metadata.get(unit.id)
            if row is None or row["current_version__number"] is None:
                unit.content_status = "missing"
                unit.content_version = None
                unit.content_updated_at = None
            else:
                unit.content_status = (
                    "ready" if row["current_version__character_count"] > 0 else "empty"
                )
                unit.content_version = row["current_version__number"]
                unit.content_updated_at = row["updated_at"]
            unit.delivery_status = f"document_{unit.content_status}"


def _non_document_delivery_status(unit: CourseUnit) -> str:
    if unit.lesson_kind == LessonKind.MEDIACMS_VIDEO:
        try:
            return (
                "mediacms_ready"
                if unit.mediacms_video_binding.media_friendly_token
                else "mediacms_missing"
            )
        except ObjectDoesNotExist:
            return "mediacms_missing"
    try:
        resource = unit.lesson_resource
    except ObjectDoesNotExist:
        return "resource_missing"
    try:
        validate_lesson_resource(unit=unit, version=resource.asset_version)
    except ContentDeliveryInvalid:
        return "resource_invalid"
    return "resource_ready"


def content_readiness_issues(revision: CourseRevision) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    units = (
        CourseUnit.objects.filter(
            module__revision=revision,
            module__status=StructureStatus.ACTIVE,
            status=StructureStatus.ACTIVE,
        )
        .select_related("module", "content_document__current_version")
        .select_related("lesson_resource__asset_version__asset")
        .order_by("module__position", "position", "id")
    )
    for unit in units:
        path = f"modules.{unit.module_id}.units.{unit.id}.content"
        if unit.lesson_kind != LessonKind.DOCUMENT:
            issues.extend(_lesson_resource_readiness_issues(unit))
            continue
        try:
            document = unit.content_document
        except ObjectDoesNotExist:
            document = None
        if document is None or document.current_version is None:
            issues.append(
                {
                    "code": "unit_content_missing",
                    "path": path,
                    "message": f"La unidad «{unit.title}» todavía no tiene contenido académico.",
                }
            )
            continue
        current = document.current_version
        if current.schema_version not in schema_registry():
            issues.append(
                {
                    "code": "unit_content_schema_unsupported",
                    "path": path,
                    "message": f"El contenido de «{unit.title}» usa un schema no soportado.",
                }
            )
            continue
        if content_digest(current.content) != current.digest:
            issues.append(
                {
                    "code": "unit_content_digest_mismatch",
                    "path": path,
                    "message": f"El contenido de «{unit.title}» no supera la verificación de integridad.",
                }
            )
            continue
        try:
            validate_content(current.content, schema_version=current.schema_version)
        except ContentDomainError:
            issues.append(
                {
                    "code": "unit_content_invalid",
                    "path": path,
                    "message": f"El contenido de «{unit.title}» ya no cumple el contrato.",
                }
            )
            continue
        if not has_meaningful_content(current.content):
            issues.append(
                {
                    "code": "unit_content_empty",
                    "path": path,
                    "message": f"La unidad «{unit.title}» no contiene contenido académico significativo.",
                }
            )
        issues.extend(_asset_readiness_issues(unit, current))
    return issues


def _lesson_resource_readiness_issues(unit: CourseUnit) -> list[dict[str, str]]:
    path = f"modules.{unit.module_id}.units.{unit.id}.delivery"
    if unit.lesson_kind == LessonKind.MEDIACMS_VIDEO:
        try:
            has_media = bool(unit.mediacms_video_binding.media_friendly_token)
        except ObjectDoesNotExist:
            has_media = False
        if has_media:
            return []
        return [
            {
                "code": "unit_delivery_mediacms_missing",
                "path": path,
                "message": f"La lección «{unit.title}» debe seleccionar un vídeo MediaCMS.",
            }
        ]
    if lesson_resource_rule(unit.lesson_kind) is None:
        return [
            {
                "code": "unit_delivery_kind_invalid",
                "path": path,
                "message": "La modalidad de la lección no tiene una entrega válida.",
            }
        ]
    try:
        resource = unit.lesson_resource
    except ObjectDoesNotExist:
        return [
            {
                "code": "unit_delivery_resource_missing",
                "path": path,
                "message": f"La lección «{unit.title}» debe seleccionar un único archivo listo.",
            }
        ]
    try:
        validate_lesson_resource(unit=unit, version=resource.asset_version)
    except ContentDeliveryInvalid:
        return [
            {
                "code": "unit_delivery_resource_invalid",
                "path": path,
                "message": f"El archivo de «{unit.title}» ya no cumple la modalidad seleccionada.",
            }
        ]
    return []


def _asset_readiness_issues(
    unit: CourseUnit, content_version: object
) -> list[dict[str, str]]:
    from .models import UnitContentVersion

    assert isinstance(content_version, UnitContentVersion)
    expected: set[tuple[str, str]] = set()
    for node, _path in iter_nodes(content_version.content):
        node_type = str(node.get("type", ""))
        if node_type not in ASSET_NODE_KINDS:
            continue
        attrs = node.get("attrs")
        if not isinstance(attrs, dict):
            continue
        node_id = str(attrs.get("nodeId", ""))
        expected.add((node_id, "primary"))
        if node_type == "videoAsset" and attrs.get("captionsAssetVersionId"):
            expected.add((node_id, "captions"))
    references = list(
        content_version.asset_references.select_related("asset_version__asset")
        .prefetch_related("asset_version__variants")
        .all()
    )
    actual = {(str(item.node_id), item.reference_role) for item in references}
    base_path = f"modules.{unit.module_id}.units.{unit.id}.content"
    if actual != expected:
        return [
            {
                "code": "asset_missing",
                "path": base_path,
                "message": "Las referencias de assets no coinciden con el documento.",
            }
        ]
    problems: list[dict[str, str]] = []
    required_roles = {
        AssetKind.IMAGE: {VariantRole.IMAGE_THUMBNAIL, VariantRole.IMAGE_MEDIUM},
        AssetKind.AUDIO: {VariantRole.AUDIO_PLAYBACK},
        AssetKind.VIDEO: {VariantRole.VIDEO_PLAYBACK, VariantRole.VIDEO_POSTER},
        AssetKind.CAPTION: {VariantRole.CAPTION_NORMALIZED},
    }
    for reference in references:
        version = reference.asset_version
        code = ""
        if version.asset.organization_id != revision_organization_id(unit):
            code = "asset_missing"
        elif version.status != AssetVersionStatus.READY or not version.sha256:
            code = (
                "caption_not_ready"
                if version.asset.kind == AssetKind.CAPTION
                else "asset_not_ready"
            )
        else:
            present = {variant.role for variant in version.variants.all()}
            if not required_roles.get(version.asset.kind, set()).issubset(present):
                code = "asset_variant_missing"
        if code:
            problems.append(
                {
                    "code": code,
                    "path": f"{base_path}.assets.{reference.node_id}",
                    "message": "El asset referenciado no está listo para publicación.",
                }
            )
    return problems


def revision_organization_id(unit: CourseUnit) -> object:
    return unit.module.revision.course.organization_id
