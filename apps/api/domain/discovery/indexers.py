# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Any

from domain.assessments.choices import LifecycleStatus
from domain.assessments.models import AssessmentVersion, QuestionVersion
from domain.assets.choices import AssetStatus, AssetVersionStatus
from domain.assets.models import Asset
from domain.catalog.models import Concept, LearningObjective, Subject, Topic
from domain.publishing.choices import PublicationStatus
from domain.publishing.models import CoursePublication, CourseRelease

from .models import SearchAudience, SearchSourceType
from .normalization import normalize_title


@dataclass(frozen=True)
class SearchDocumentDTO:
    source_type: str
    source_id: uuid.UUID
    source_version_id: uuid.UUID | None
    audience: str
    language: str
    title: str
    subtitle: str
    body: str
    url_path: str
    metadata: dict[str, Any]

    @property
    def normalized_title(self) -> str:
        return normalize_title(self.title)

    @property
    def digest(self) -> str:
        payload = {
            "source_type": self.source_type,
            "source_id": str(self.source_id),
            "source_version_id": str(self.source_version_id)
            if self.source_version_id
            else None,
            "audience": self.audience,
            "language": self.language,
            "title": self.title,
            "subtitle": self.subtitle,
            "body": self.body,
            "url_path": self.url_path,
            "metadata": self.metadata,
        }
        return hashlib.sha256(
            json.dumps(
                payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()


def _semantic_text(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [text for item in value for text in _semantic_text(item)]
    if not isinstance(value, dict):
        return []
    allowed = {
        "text",
        "title",
        "summary",
        "description",
        "statement",
        "alt",
        "transcript",
    }
    output: list[str] = []
    for key, item in value.items():
        if key in allowed:
            output.extend(_semantic_text(item))
        elif key in {
            "content",
            "document",
            "modules",
            "units",
            "topics",
            "learning_objectives",
        }:
            output.extend(_semantic_text(item))
    return output


def release_documents(release: CourseRelease) -> list[SearchDocumentDTO]:
    snapshot = release.snapshot
    course = snapshot.get("course", {}) if isinstance(snapshot, dict) else {}
    language = str(course.get("language_code") or release.language_code or "es")
    base = f"/organizaciones/{release.course.organization.slug}/biblioteca/{release.course.slug}"
    documents = [
        SearchDocumentDTO(
            source_type=SearchSourceType.COURSE_RELEASE,
            source_id=release.course_id,
            source_version_id=release.id,
            audience=SearchAudience.LEARNING,
            language=language if language in {"es", "en"} else "es",
            title=release.title,
            subtitle=str(course.get("subtitle") or ""),
            body=" ".join(
                _semantic_text(
                    {
                        "summary": release.summary,
                        "content": snapshot.get("curriculum", {}),
                    }
                )
            ),
            url_path=base,
            metadata={
                "release_id": str(release.id),
                "course_id": str(release.course_id),
            },
        )
    ]
    for module in snapshot.get("modules", []):
        for unit in module.get("units", []):
            try:
                unit_id = uuid.UUID(str(unit["id"]))
            except (KeyError, ValueError, TypeError):
                continue
            documents.append(
                SearchDocumentDTO(
                    source_type=SearchSourceType.COURSE_UNIT,
                    source_id=unit_id,
                    source_version_id=release.id,
                    audience=SearchAudience.LEARNING,
                    language=language if language in {"es", "en"} else "es",
                    title=str(unit.get("title") or "Unidad"),
                    subtitle=str(module.get("title") or ""),
                    body=" ".join(_semantic_text(unit)),
                    url_path=f"/organizaciones/{release.course.organization.slug}/aprender/{release.course.slug}/unidades/{unit_id}",
                    metadata={
                        "release_id": str(release.id),
                        "course_id": str(release.course_id),
                        "unit_id": str(unit_id),
                    },
                )
            )
    return documents


def catalog_documents(organization: object) -> list[SearchDocumentDTO]:
    slug = organization.slug
    documents: list[SearchDocumentDTO] = []
    for subject in Subject.objects.filter(
        discipline__area__organization=organization, status="active"
    ):
        documents.append(
            SearchDocumentDTO(
                SearchSourceType.CATALOG_SUBJECT,
                subject.id,
                None,
                SearchAudience.AUTHORING,
                "es",
                subject.name,
                "Asignatura",
                subject.description,
                f"/organizaciones/{slug}/curriculo/asignaturas/{subject.id}",
                {},
            )
        )
    for topic in Topic.objects.filter(
        subject__discipline__area__organization=organization, status="active"
    ):
        documents.append(
            SearchDocumentDTO(
                SearchSourceType.CATALOG_TOPIC,
                topic.id,
                None,
                SearchAudience.AUTHORING,
                "es",
                topic.title,
                topic.subject.name,
                topic.description,
                f"/organizaciones/{slug}/curriculo/asignaturas/{topic.subject_id}",
                {},
            )
        )
    for concept in Concept.objects.filter(organization=organization, status="active"):
        documents.append(
            SearchDocumentDTO(
                SearchSourceType.CATALOG_CONCEPT,
                concept.id,
                None,
                SearchAudience.AUTHORING,
                "es",
                concept.name,
                "Concepto",
                concept.definition,
                f"/organizaciones/{slug}/curriculo/conceptos",
                {},
            )
        )
    for objective in LearningObjective.objects.filter(
        subject__discipline__area__organization=organization, status="active"
    ):
        documents.append(
            SearchDocumentDTO(
                SearchSourceType.LEARNING_OBJECTIVE,
                objective.id,
                None,
                SearchAudience.AUTHORING,
                "es",
                objective.code,
                objective.subject.name,
                f"{objective.statement} {objective.description}",
                f"/organizaciones/{slug}/curriculo/objetivos",
                {},
            )
        )
    return documents


def authoring_documents(organization: object) -> list[SearchDocumentDTO]:
    """Build author-only documents from explicitly public, non-operational fields."""
    documents: list[SearchDocumentDTO] = []
    assets = Asset.objects.filter(
        organization=organization,
        status=AssetStatus.ACTIVE,
        current_version__status=AssetVersionStatus.READY,
    ).select_related("current_version", "organization")
    for asset in assets:
        documents.append(asset_document(asset))
    question_versions = QuestionVersion.objects.filter(
        question__bank__organization=organization,
        question__status=LifecycleStatus.ACTIVE,
        question__bank__status=LifecycleStatus.ACTIVE,
    ).select_related("question__bank__organization")
    question_versions = question_versions.order_by("question_id", "-number").distinct(
        "question_id"
    )
    for version in question_versions:
        documents.append(question_version_document(version))
    assessment_versions = AssessmentVersion.objects.filter(
        assessment__organization=organization,
        assessment__status=LifecycleStatus.ACTIVE,
    ).select_related("assessment__organization")
    assessment_versions = assessment_versions.order_by(
        "assessment_id", "-number"
    ).distinct("assessment_id")
    for version in assessment_versions:
        documents.append(assessment_version_document(version))
    return documents


def asset_document(asset: Asset) -> SearchDocumentDTO:
    version = asset.current_version
    if version is None or version.status != AssetVersionStatus.READY:
        raise ValueError("Sólo se indexan versiones de asset listas.")
    return SearchDocumentDTO(
        SearchSourceType.ASSET_VERSION,
        asset.id,
        version.id,
        SearchAudience.AUTHORING,
        "es",
        asset.name,
        "Recurso",
        asset.description,
        f"/organizaciones/{asset.organization.slug}/recursos/{asset.id}",
        {"asset_id": str(asset.id), "asset_version_id": str(version.id)},
    )


def question_version_document(version: QuestionVersion) -> SearchDocumentDTO:
    question = version.question
    return SearchDocumentDTO(
        SearchSourceType.QUESTION_VERSION,
        question.id,
        version.id,
        SearchAudience.AUTHORING,
        "es",
        question.code,
        question.bank.name,
        " ".join(_semantic_text(version.public)),
        f"/organizaciones/{question.bank.organization.slug}/evaluaciones/bancos/{question.bank_id}",
        {
            "bank_id": str(question.bank_id),
            "question_id": str(question.id),
            "question_version_id": str(version.id),
        },
    )


def assessment_version_document(version: AssessmentVersion) -> SearchDocumentDTO:
    return SearchDocumentDTO(
        SearchSourceType.ASSESSMENT_VERSION,
        version.assessment_id,
        version.id,
        SearchAudience.AUTHORING,
        "es",
        version.title,
        "Evaluación",
        " ".join([version.description, *_semantic_text(version.public_snapshot)]),
        f"/organizaciones/{version.assessment.organization.slug}/evaluaciones/{version.assessment.slug}",
        {
            "assessment_id": str(version.assessment_id),
            "assessment_version_id": str(version.id),
        },
    )


def organization_documents(organization: object) -> list[SearchDocumentDTO]:
    documents = [
        *catalog_documents(organization),
        *authoring_documents(organization),
    ]
    publications = CoursePublication.objects.filter(
        course__organization=organization, status=PublicationStatus.ACTIVE
    ).select_related("current_release__course__organization")
    for publication in publications:
        documents.extend(release_documents(publication.current_release))
    return documents
