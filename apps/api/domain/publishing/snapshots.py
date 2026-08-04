# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from typing import Any

from django.db.models import Prefetch

from domain.assets.models import AssetVariant
from domain.assets.selectors import preferred_variants
from domain.catalog.models import (
    Concept,
    ConceptPrerequisite,
    LearningObjectiveConcept,
    SubjectPrerequisite,
    Topic,
    TopicConcept,
)
from domain.content.canonical import content_digest
from domain.content.exceptions import ContentDeliveryInvalid
from domain.content.lesson_resources import validate_lesson_resource
from domain.content.models import (
    ContentAssetReference,
    UnitContentDocument,
    UnitLessonResource,
)
from domain.content.schemas import CURRENT_CONTENT_SCHEMA_VERSION, migrate_document
from domain.content.validators import validate_content
from domain.courses.activity_extensions import activity_binding_snapshot
from domain.courses.choices import (
    AuthoringStatus,
    CourseStatus,
    LessonKind,
    StructureStatus,
)
from domain.courses.models import (
    CourseActivity,
    CourseActivityAvailabilityRule,
    CourseActivityLearningObjective,
    CourseCompletionPolicy,
    CourseGradeCategory,
    CourseModule,
    CourseRevision,
    CourseRevisionLearningObjective,
    CourseRevisionSubject,
    CourseUnit,
    CourseUnitLearningObjective,
    CourseUnitTopic,
    MediaCMSVideoBinding,
)

from .canonical import canonical_json_bytes, deep_json_copy
from .exceptions import (
    ReleaseSnapshotInvalid,
    ReleaseSnapshotTooLarge,
    ReleaseSourceNotApproved,
)
from .limits import (
    MAX_CANONICAL_BYTES,
    MAX_LEARNING_OBJECTIVES,
    MAX_MODULES,
    MAX_TOPIC_REFERENCES,
    MAX_UNITS,
)
from .schemas import CURRENT_RELEASE_SCHEMA_VERSION, validate_release_snapshot


def release_revision_queryset():
    topic_links = CourseUnitTopic.objects.select_related("topic__subject").order_by(
        "position"
    )
    objective_links = CourseUnitLearningObjective.objects.select_related(
        "learning_objective"
    ).order_by("position")
    references = ContentAssetReference.objects.select_related(
        "asset_version__asset"
    ).prefetch_related(
        Prefetch(
            "asset_version__variants",
            queryset=AssetVariant.objects.order_by("role", "created_at"),
        )
    )
    documents = UnitContentDocument.objects.select_related(
        "current_version"
    ).prefetch_related(
        Prefetch("current_version__asset_references", queryset=references)
    )
    units = (
        CourseUnit.objects.filter(status=StructureStatus.ACTIVE)
        .select_related(
            "mediacms_video_binding",
            "lesson_resource__asset_version__asset",
        )
        .prefetch_related(
            Prefetch("topic_alignments", queryset=topic_links),
            Prefetch("objective_alignments", queryset=objective_links),
            Prefetch("content_document", queryset=documents),
            Prefetch(
                "lesson_resource__asset_version__variants",
                queryset=AssetVariant.objects.order_by("role", "created_at"),
            ),
        )
        .order_by("position", "id")
    )
    activity_objectives = CourseActivityLearningObjective.objects.select_related(
        "learning_objective"
    ).order_by("position")
    activity_rules = CourseActivityAvailabilityRule.objects.select_related(
        "prerequisite_activity", "learning_objective"
    ).order_by("position")
    activities = (
        CourseActivity.objects.filter(status=StructureStatus.ACTIVE)
        .select_related("lesson_unit")
        .prefetch_related(
            Prefetch("objective_alignments", queryset=activity_objectives),
            Prefetch("availability_rules", queryset=activity_rules),
        )
        .order_by("position", "id")
    )
    modules = (
        CourseModule.objects.filter(status=StructureStatus.ACTIVE)
        .prefetch_related(
            Prefetch("units", queryset=units),
            Prefetch("activities", queryset=activities),
        )
        .order_by("position", "id")
    )
    return CourseRevision.objects.select_related(
        "course__organization"
    ).prefetch_related(
        Prefetch(
            "subject_alignments",
            queryset=CourseRevisionSubject.objects.select_related("subject").order_by(
                "position"
            ),
        ),
        Prefetch(
            "objective_alignments",
            queryset=CourseRevisionLearningObjective.objects.select_related(
                "learning_objective"
            ).order_by("position"),
        ),
        Prefetch("modules", queryset=modules),
        Prefetch(
            "grade_categories",
            queryset=CourseGradeCategory.objects.prefetch_related(
                "graded_activities"
            ).order_by("position", "id"),
        ),
    )


def load_release_revision(revision: CourseRevision) -> CourseRevision:
    return release_revision_queryset().get(pk=revision.pk)


def _content_snapshot(unit: CourseUnit) -> dict[str, Any]:
    try:
        document = unit.content_document
    except UnitContentDocument.DoesNotExist as error:
        raise ReleaseSnapshotInvalid(
            f"La unidad {unit.id} no tiene documento de contenido."
        ) from error
    version = document.current_version
    if version is None:
        raise ReleaseSnapshotInvalid(
            f"La unidad {unit.id} no tiene versión de contenido vigente."
        )
    migrated_content = migrate_document(
        version.content,
        from_version=version.schema_version,
        to_version=CURRENT_CONTENT_SCHEMA_VERSION,
    )
    validated = validate_content(
        migrated_content, schema_version=CURRENT_CONTENT_SCHEMA_VERSION
    )
    if (
        validated.digest != version.digest
        or content_digest(version.content) != version.digest
    ):
        raise ReleaseSnapshotInvalid(
            f"El digest de contenido de la unidad {unit.id} es inválido."
        )
    return {
        "schema_version": CURRENT_CONTENT_SCHEMA_VERSION,
        "document_version": version.number,
        "digest": version.digest,
        "character_count": version.character_count,
        "word_count": version.word_count,
        "node_count": version.node_count,
        "document": deep_json_copy(migrated_content),
    }


def _media_snapshot(unit: CourseUnit) -> dict[str, str] | None:
    if unit.lesson_kind != LessonKind.MEDIACMS_VIDEO:
        return None
    try:
        binding = unit.mediacms_video_binding
    except MediaCMSVideoBinding.DoesNotExist as error:
        raise ReleaseSnapshotInvalid(
            f"La unidad de vídeo {unit.id} no tiene un vídeo MediaCMS seleccionado."
        ) from error
    return {
        "provider": "mediacms_lti",
        "media_friendly_token": binding.media_friendly_token,
    }


def _resource_snapshot(unit: CourseUnit) -> tuple[dict[str, str], Any]:
    try:
        resource = unit.lesson_resource
    except UnitLessonResource.DoesNotExist as error:
        raise ReleaseSnapshotInvalid(
            f"La unidad {unit.id} no tiene el archivo requerido por su modalidad."
        ) from error
    version = resource.asset_version
    try:
        validate_lesson_resource(unit=unit, version=version)
    except ContentDeliveryInvalid as error:
        raise ReleaseSnapshotInvalid(
            f"El archivo de la unidad {unit.id} no cumple su modalidad."
        ) from error
    return (
        {
            "kind": "asset",
            "asset_version_id": str(version.id),
        },
        version,
    )


def _delivery_snapshot(unit: CourseUnit) -> tuple[dict[str, Any], Any | None]:
    if unit.lesson_kind == LessonKind.DOCUMENT:
        return {"kind": "document", "content": _content_snapshot(unit)}, None
    if unit.lesson_kind == LessonKind.MEDIACMS_VIDEO:
        media = _media_snapshot(unit)
        assert media is not None
        return {"kind": "mediacms_lti", "media": media}, None
    resource, version = _resource_snapshot(unit)
    return resource, version


def build_release_snapshot(
    *,
    revision: CourseRevision,
    release_number: int,
    previous_release_digest: str | None,
) -> tuple[dict[str, Any], bytes]:
    if (
        revision.authoring_status != AuthoringStatus.APPROVED
        or revision.course.status != CourseStatus.ACTIVE
    ):
        raise ReleaseSourceNotApproved(
            "La revisión debe estar aprobada y el curso activo."
        )
    subjects = [
        {
            "id": str(link.subject_id),
            "slug": link.subject.slug,
            "name": link.subject.name,
            "alignment_type": link.alignment_type,
            "position": link.position,
        }
        for link in revision.subject_alignments.all()
    ]
    objectives = [
        {
            "id": str(link.learning_objective_id),
            "code": link.learning_objective.code,
            "statement": link.learning_objective.statement,
            "description": link.learning_objective.description,
            "cognitive_level": link.learning_objective.cognitive_level,
            "subject_id": str(link.learning_objective.subject_id),
            "position": link.position,
        }
        for link in revision.objective_alignments.all()
    ]
    modules: list[dict[str, Any]] = []
    asset_versions: dict[str, Any] = {}
    unit_count = 0
    topic_count = 0
    used_topic_ids: set[Any] = set()
    for module in revision.modules.all():
        units: list[dict[str, Any]] = []
        for unit in module.units.all():
            delivery, delivery_asset = _delivery_snapshot(unit)
            if unit.lesson_kind == LessonKind.DOCUMENT:
                document = unit.content_document
                if document.current_version is not None:
                    for reference in document.current_version.asset_references.all():
                        asset_versions[str(reference.asset_version_id)] = (
                            reference.asset_version
                        )
            elif delivery_asset is not None:
                asset_versions[str(delivery_asset.id)] = delivery_asset
            topics = [
                {
                    "id": str(link.topic_id),
                    "slug": link.topic.slug,
                    "title": link.topic.title,
                    "subject_id": str(link.topic.subject_id),
                    "subject_slug": link.topic.subject.slug,
                    "position": link.position,
                }
                for link in unit.topic_alignments.all()
            ]
            unit_objectives = [
                {
                    "id": str(link.learning_objective_id),
                    "code": link.learning_objective.code,
                    "statement": link.learning_objective.statement,
                    "position": link.position,
                }
                for link in unit.objective_alignments.all()
            ]
            units.append(
                {
                    "id": str(unit.id),
                    "title": unit.title,
                    "summary": unit.summary,
                    "estimated_duration_minutes": unit.estimated_duration_minutes,
                    "lesson_kind": unit.lesson_kind,
                    "position": unit.position,
                    "topics": topics,
                    "learning_objectives": unit_objectives,
                    "delivery": delivery,
                }
            )
            unit_count += 1
            topic_count += len(topics)
            used_topic_ids.update(link.topic_id for link in unit.topic_alignments.all())
        activities = [
            {
                "id": str(activity.id),
                "type": activity.activity_type,
                "title": activity.title,
                "summary": activity.summary,
                "estimated_duration_minutes": activity.estimated_duration_minutes,
                "position": activity.position,
                "required": activity.required,
                "completion_policy": {
                    "method": activity.completion_method,
                    "minimum_attendance_basis_points": (
                        activity.minimum_attendance_basis_points
                    ),
                    "minimum_grade_basis_points": activity.minimum_grade_basis_points,
                },
                "availability_rules": [
                    {
                        "type": rule.rule_type,
                        "prerequisite_activity_id": (
                            str(rule.prerequisite_activity_id)
                            if rule.prerequisite_activity_id
                            else None
                        ),
                        "learning_objective_id": (
                            str(rule.learning_objective_id)
                            if rule.learning_objective_id
                            else None
                        ),
                        "threshold_basis_points": rule.threshold_basis_points,
                        "available_at": (
                            rule.available_at.isoformat() if rule.available_at else None
                        ),
                        "position": rule.position,
                    }
                    for rule in activity.availability_rules.all()
                ],
                "learning_objectives": [
                    {
                        "id": str(link.learning_objective_id),
                        "code": link.learning_objective.code,
                        "statement": link.learning_objective.statement,
                        "position": link.position,
                    }
                    for link in activity.objective_alignments.all()
                ],
                "binding": activity_binding_snapshot(activity),
            }
            for activity in module.activities.all()
        ]
        modules.append(
            {
                "id": str(module.id),
                "title": module.title,
                "description": module.description,
                "position": module.position,
                "activities": activities,
                "units": units,
            }
        )
    if len(modules) > MAX_MODULES:
        raise ReleaseSnapshotTooLarge("El release supera el máximo de módulos.")
    if unit_count > MAX_UNITS:
        raise ReleaseSnapshotTooLarge("El release supera el máximo de unidades.")
    if len(objectives) > MAX_LEARNING_OBJECTIVES:
        raise ReleaseSnapshotTooLarge("El release supera el máximo de objetivos.")
    if topic_count > MAX_TOPIC_REFERENCES:
        raise ReleaseSnapshotTooLarge(
            "El release supera el máximo de referencias a temas."
        )
    topic_links = list(
        TopicConcept.objects.filter(topic_id__in=used_topic_ids)
        .select_related("topic", "concept")
        .order_by("topic_id", "position")
    )
    objective_ids = [
        link.learning_objective_id for link in revision.objective_alignments.all()
    ]
    objective_links = list(
        LearningObjectiveConcept.objects.filter(learning_objective_id__in=objective_ids)
        .select_related("learning_objective", "concept")
        .order_by("learning_objective_id", "position")
    )
    concept_ids = {
        *(link.concept_id for link in topic_links),
        *(link.concept_id for link in objective_links),
    }
    concept_edges = list(
        ConceptPrerequisite.objects.filter(concept_id__in=concept_ids)
        .select_related("concept", "prerequisite")
        .order_by("concept_id", "prerequisite_id")
    )
    concept_ids.update(edge.prerequisite_id for edge in concept_edges)
    concepts = list(Concept.objects.filter(id__in=concept_ids).order_by("slug", "id"))
    subject_ids = [link.subject_id for link in revision.subject_alignments.all()]
    subject_edges = list(
        SubjectPrerequisite.objects.filter(subject_id__in=subject_ids)
        .select_related("subject", "prerequisite")
        .order_by("subject_id", "prerequisite_id")
    )
    topics_used = list(
        Topic.objects.filter(id__in=used_topic_ids)
        .select_related("subject")
        .order_by("subject_id", "path")
    )
    completion_policy = CourseCompletionPolicy.objects.get(revision=revision)
    snapshot: dict[str, Any] = {
        "schema_version": CURRENT_RELEASE_SCHEMA_VERSION,
        "release_number": release_number,
        "previous_release_digest": previous_release_digest,
        "organization": {
            "id": str(revision.course.organization_id),
            "slug": revision.course.organization.slug,
        },
        "course": {
            "id": str(revision.course_id),
            "slug": revision.course.slug,
            "source_revision_id": str(revision.id),
            "source_revision_number": revision.number,
            "title": revision.title,
            "subtitle": revision.subtitle or None,
            "summary": revision.summary,
            "description": revision.description,
            "language_code": revision.language_code,
            "estimated_duration_minutes": revision.estimated_duration_minutes,
        },
        "curriculum": {
            "subjects": subjects,
            "topics": [
                {
                    "id": str(topic.id),
                    "slug": topic.slug,
                    "title": topic.title,
                    "subject_id": str(topic.subject_id),
                }
                for topic in topics_used
            ],
            "concepts": [
                {
                    "id": str(concept.id),
                    "slug": concept.slug,
                    "name": concept.name,
                    "definition": concept.definition,
                }
                for concept in concepts
            ],
            "learning_objectives": objectives,
            "topic_concepts": [
                {
                    "topic_id": str(link.topic_id),
                    "concept_id": str(link.concept_id),
                    "position": link.position,
                }
                for link in topic_links
            ],
            "objective_concepts": [
                {
                    "learning_objective_id": str(link.learning_objective_id),
                    "concept_id": str(link.concept_id),
                    "position": link.position,
                }
                for link in objective_links
            ],
            "subject_prerequisites": [
                {
                    "subject_id": str(edge.subject_id),
                    "prerequisite_id": str(edge.prerequisite_id),
                    "prerequisite_slug": edge.prerequisite.slug,
                    "prerequisite_name": edge.prerequisite.name,
                    "kind": edge.kind,
                    "rationale": edge.rationale,
                }
                for edge in subject_edges
            ],
            "concept_prerequisites": [
                {
                    "concept_id": str(edge.concept_id),
                    "prerequisite_id": str(edge.prerequisite_id),
                    "kind": edge.kind,
                    "rationale": edge.rationale,
                }
                for edge in concept_edges
            ],
        },
        "completion_policy": {
            "version": completion_policy.lock_version,
            "require_required_activities": (
                completion_policy.require_required_activities
            ),
            "minimum_grade_basis_points": (
                completion_policy.minimum_grade_basis_points
            ),
            "minimum_attendance_basis_points": (
                completion_policy.minimum_attendance_basis_points
            ),
        },
        "grading_scheme": {
            "categories": [
                {
                    "id": str(category.id),
                    "code": category.code,
                    "title": category.title,
                    "position": category.position,
                    "weight_basis_points": category.weight_basis_points,
                    "activities": [
                        {
                            "activity_id": str(item.activity_id),
                            "weight_basis_points": item.weight_basis_points,
                            "required": item.required,
                        }
                        for item in category.graded_activities.all()
                    ],
                }
                for category in revision.grade_categories.all()
            ]
        },
        "modules": modules,
        "assets": [
            _asset_manifest_entry(asset_versions[version_id])
            for version_id in sorted(asset_versions)
        ],
    }
    validate_release_snapshot(snapshot)
    canonical = canonical_json_bytes(snapshot)
    if len(canonical) > MAX_CANONICAL_BYTES:
        raise ReleaseSnapshotTooLarge("El release supera 50 MiB canónicos.")
    return snapshot, canonical


def _asset_manifest_entry(version: Any) -> dict[str, Any]:
    return {
        "asset_version_id": str(version.id),
        "asset_id": str(version.asset_id),
        "kind": version.asset.kind,
        "sha256": version.sha256,
        "detected_mime_type": version.detected_mime_type,
        "size_bytes": version.size_bytes,
        "metadata": deep_json_copy(version.technical_metadata),
        "variants": [
            {
                "role": variant.role,
                "mime_type": variant.mime_type,
                "sha256": variant.sha256,
                "width": variant.width,
                "height": variant.height,
                "duration_milliseconds": variant.duration_milliseconds,
            }
            for variant in preferred_variants(version)
        ],
    }


def snapshot_metrics(snapshot: dict[str, Any]) -> dict[str, int]:
    modules = snapshot["modules"]
    units = [unit for module in modules for unit in module["units"]]
    return {
        "module_count": len(modules),
        "unit_count": len(units),
        "word_count": sum(
            unit["delivery"]["content"]["word_count"]
            if snapshot["schema_version"] >= 6
            and unit["delivery"]["kind"] == "document"
            else unit["content"]["word_count"]
            if snapshot["schema_version"] < 6
            else 0
            for unit in units
        ),
    }


def release_outline(snapshot: object) -> list[dict[str, Any]]:
    validate_release_snapshot(snapshot)
    assert isinstance(snapshot, dict)
    return [
        {
            "id": module["id"],
            "title": module["title"],
            "description": module["description"],
            "position": module["position"],
            "activities": [
                {
                    "id": activity["id"],
                    "type": activity["type"],
                    "title": activity["title"],
                    "summary": activity["summary"],
                    "estimated_duration_minutes": activity[
                        "estimated_duration_minutes"
                    ],
                    "position": activity["position"],
                    "required": activity["required"],
                    "completion_policy": deep_json_copy(activity["completion_policy"]),
                    "availability_rules": deep_json_copy(
                        activity["availability_rules"]
                    ),
                    "binding": deep_json_copy(activity["binding"]),
                }
                for activity in (
                    module["activities"]
                    if snapshot["schema_version"] >= 3
                    else [
                        {
                            "id": unit["id"],
                            "type": "lesson",
                            "title": unit["title"],
                            "summary": unit["summary"],
                            "estimated_duration_minutes": unit[
                                "estimated_duration_minutes"
                            ],
                            "position": unit["position"],
                            "required": True,
                            "completion_policy": {
                                "method": "view",
                                "minimum_attendance_basis_points": None,
                                "minimum_grade_basis_points": None,
                            },
                            "availability_rules": [],
                            "binding": {
                                "provider": "content",
                                "unit_id": unit["id"],
                            },
                        }
                        for unit in module["units"]
                    ]
                )
            ],
            "units": [
                {
                    "id": unit["id"],
                    "title": unit["title"],
                    "summary": unit["summary"],
                    "estimated_duration_minutes": unit["estimated_duration_minutes"],
                    "lesson_kind": (
                        unit["lesson_kind"]
                        if snapshot["schema_version"] >= 4
                        else "document"
                    ),
                    "position": unit["position"],
                }
                for unit in module["units"]
            ],
        }
        for module in snapshot["modules"]
    ]


def release_activity(snapshot: object, activity_id: str) -> dict[str, Any]:
    outline = release_outline(snapshot)
    for module in outline:
        for activity in module["activities"]:
            if activity["id"] == activity_id:
                result = deep_json_copy(activity)
                result["module"] = {
                    "id": module["id"],
                    "title": module["title"],
                    "position": module["position"],
                }
                return result
    raise ReleaseSnapshotInvalid("La actividad no existe en el snapshot.")


def release_unit(snapshot: object, unit_id: str) -> dict[str, Any]:
    validate_release_snapshot(snapshot)
    assert isinstance(snapshot, dict)
    for module in snapshot["modules"]:
        for unit in module["units"]:
            if unit["id"] == unit_id:
                result = deep_json_copy(unit)
                if snapshot["schema_version"] < 6:
                    result["delivery"] = _legacy_unit_delivery(result)
                result["module"] = {
                    "id": module["id"],
                    "title": module["title"],
                    "position": module["position"],
                }
                return result
    raise ReleaseSnapshotInvalid("La unidad no existe en el snapshot.")


def _legacy_unit_delivery(unit: dict[str, Any]) -> dict[str, Any]:
    """Adapt pre-v6 immutable releases without rewriting their historic payload."""

    if unit.get("lesson_kind") == LessonKind.MEDIACMS_VIDEO:
        media = unit.get("media")
        if isinstance(media, dict):
            return {"kind": "mediacms_lti", "media": media}
    content = unit.get("content")
    if isinstance(content, dict):
        return {"kind": "document", "content": content}
    raise ReleaseSnapshotInvalid("La entrega de la unidad histórica es inválida.")


def release_previous_next(snapshot: object, unit_id: str) -> dict[str, Any | None]:
    outline = release_outline(snapshot)
    flattened = [
        {
            "id": unit["id"],
            "title": unit["title"],
            "module_id": module["id"],
            "module_title": module["title"],
        }
        for module in outline
        for unit in module["units"]
    ]
    for index, unit in enumerate(flattened):
        if unit["id"] == unit_id:
            return {
                "position": index + 1,
                "total": len(flattened),
                "previous": deep_json_copy(flattened[index - 1]) if index > 0 else None,
                "next": deep_json_copy(flattened[index + 1])
                if index + 1 < len(flattened)
                else None,
            }
    raise ReleaseSnapshotInvalid("La actividad no existe en el snapshot.")
