# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from domain.events.models import DomainEvent
from domain.events.registry import ConsumerDefinition, register_consumer

from .indexers import (
    assessment_version_document,
    asset_document,
    question_version_document,
    release_documents,
)
from .models import (
    GenerationStatus,
    SearchAudience,
    SearchGeneration,
    SearchIndexJob,
    SearchIndexJobStatus,
    SearchIndexOperation,
    SearchSourceType,
)
from .services import rebuild_search_index, upsert_search_document

SEARCH_EVENTS = frozenset(
    {
        "publishing.course_release.published.v1",
        "publishing.course_publication.withdrawn.v1",
        "assets.asset_version.ready.v1",
        "assets.asset_version.rejected.v1",
        "assets.asset_version.failed.v1",
        "assessments.question_revision.approved.v1",
        "assessments.assessment_revision.approved.v1",
    }
)


def _source(event: DomainEvent) -> tuple[str, object | None, object | None, str]:
    if event.event_type.startswith("publishing.course_release"):
        return (
            SearchSourceType.COURSE_RELEASE,
            event.payload.get("course_id"),
            event.payload.get("course_release_id"),
            SearchIndexOperation.UPSERT,
        )
    if event.event_type.startswith("publishing.course_publication"):
        return (
            SearchSourceType.COURSE_RELEASE,
            event.payload.get("course_id"),
            event.payload.get("release_id"),
            SearchIndexOperation.DEACTIVATE,
        )
    if event.event_type.startswith("assets.asset_version"):
        return (
            SearchSourceType.ASSET_VERSION,
            None,
            event.payload.get("asset_version_id"),
            SearchIndexOperation.UPSERT
            if event.event_type.endswith("ready.v1")
            else SearchIndexOperation.DEACTIVATE,
        )
    if event.event_type.startswith("assessments.question_revision"):
        return (
            SearchSourceType.QUESTION_VERSION,
            None,
            event.payload.get("question_version_id"),
            SearchIndexOperation.UPSERT,
        )
    return (
        SearchSourceType.ASSESSMENT_VERSION,
        None,
        event.payload.get("assessment_version_id"),
        SearchIndexOperation.UPSERT,
    )


def _incremental_update(event: DomainEvent, generation: SearchGeneration) -> None:
    if event.event_type == "publishing.course_release.published.v1":
        from domain.publishing.models import CourseRelease

        release = CourseRelease.objects.select_related("course__organization").get(
            pk=event.payload["course_release_id"]
        )
        generation.documents.filter(
            audience=SearchAudience.LEARNING,
            metadata__course_id=str(release.course_id),
        ).update(is_active=False)
        for document in release_documents(release):
            upsert_search_document(generation, document)
    elif event.event_type == "publishing.course_publication.withdrawn.v1":
        generation.documents.filter(
            audience=SearchAudience.LEARNING,
            metadata__course_id=str(event.payload["course_id"]),
        ).update(is_active=False)
    elif event.event_type.startswith("assets.asset_version"):
        from domain.assets.models import AssetVersion

        version = AssetVersion.objects.select_related(
            "asset__current_version", "asset__organization"
        ).get(pk=event.payload["asset_version_id"])
        generation.documents.filter(
            source_type=SearchSourceType.ASSET_VERSION,
            source_id=version.asset_id,
        ).update(is_active=False)
        if event.event_type == "assets.asset_version.ready.v1":
            upsert_search_document(generation, asset_document(version.asset))
    elif event.event_type == "assessments.question_revision.approved.v1":
        from domain.assessments.models import QuestionVersion

        version = QuestionVersion.objects.select_related(
            "question__bank__organization"
        ).get(pk=event.payload["question_version_id"])
        generation.documents.filter(
            source_type=SearchSourceType.QUESTION_VERSION,
            source_id=version.question_id,
        ).update(is_active=False)
        upsert_search_document(generation, question_version_document(version))
    elif event.event_type == "assessments.assessment_revision.approved.v1":
        from domain.assessments.models import AssessmentVersion

        version = AssessmentVersion.objects.select_related(
            "assessment__organization"
        ).get(pk=event.payload["assessment_version_id"])
        generation.documents.filter(
            source_type=SearchSourceType.ASSESSMENT_VERSION,
            source_id=version.assessment_id,
        ).update(is_active=False)
        upsert_search_document(generation, assessment_version_document(version))
    generation.document_count = generation.documents.filter(is_active=True).count()
    generation.save(update_fields=("document_count",))


def consume_search_event(event: DomainEvent) -> None:
    if event.organization is None:
        return
    source_type, source_id, source_version_id, operation = _source(event)
    job, _ = SearchIndexJob.objects.get_or_create(
        event=event,
        operation=operation,
        defaults={
            "organization": event.organization,
            "source_type": source_type,
            "source_id": source_id,
            "source_version_id": source_version_id,
        },
    )
    if job.status == SearchIndexJobStatus.COMPLETED:
        return
    try:
        with transaction.atomic():
            job = SearchIndexJob.objects.select_for_update().get(pk=job.pk)
            if job.status == SearchIndexJobStatus.COMPLETED:
                return
            job.status = SearchIndexJobStatus.PROCESSING
            job.attempt_count += 1
            job.started_at = timezone.now()
            job.last_error_code = ""
            job.save()
            generation = (
                SearchGeneration.objects.select_for_update()
                .filter(organization=event.organization, status=GenerationStatus.ACTIVE)
                .first()
            )
            if generation is None:
                generation = rebuild_search_index(
                    organization=event.organization, actor=event.actor
                )
            else:
                _incremental_update(event, generation)
            job.generation = generation
            job.status = SearchIndexJobStatus.COMPLETED
            job.completed_at = timezone.now()
            job.save()
    except Exception:
        SearchIndexJob.objects.filter(pk=job.pk).update(
            status=SearchIndexJobStatus.FAILED,
            last_error_code="index_update_failed",
            completed_at=timezone.now(),
        )
        raise


def register_consumers() -> None:
    register_consumer(
        ConsumerDefinition(
            name="discovery.search_indexer.v1",
            event_types=SEARCH_EVENTS,
            handler=consume_search_event,
        )
    )
