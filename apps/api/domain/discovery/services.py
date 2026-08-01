# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
    TrigramSimilarity,
)
from django.db import transaction
from django.db.models import F, FloatField, Q, QuerySet, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from config.observability.metrics import (
    safe_attributes,
    search_duration,
    search_queries,
)
from config.observability.tracing import domain_span
from domain.learning.choices import EnrollmentStatus
from domain.learning.models import CourseEnrollment
from domain.organizations.capabilities import Capability
from domain.organizations.choices import MembershipStatus
from domain.organizations.policies import has_capability
from domain.publishing.choices import PublicationStatus

from .indexers import SearchDocumentDTO, organization_documents
from .models import GenerationStatus, SearchAudience, SearchDocument, SearchGeneration
from .normalization import normalize_query, normalize_title
from .snippets import safe_snippet


@dataclass(frozen=True)
class SearchPage:
    query: str
    results: list[dict[str, Any]]
    page: int
    page_size: int
    total: int
    timing_bucket: str


def upsert_search_document(
    generation: SearchGeneration, dto: SearchDocumentDTO
) -> None:
    existing = (
        SearchDocument.objects.filter(
            generation=generation,
            source_type=dto.source_type,
            source_id=dto.source_id,
            source_version_id=dto.source_version_id,
            audience=dto.audience,
        )
        .only("content_digest", "is_active")
        .first()
    )
    if existing is not None and existing.content_digest == dto.digest:
        if not existing.is_active:
            SearchDocument.objects.filter(pk=existing.pk).update(is_active=True)
        return
    document, _ = SearchDocument.objects.update_or_create(
        generation=generation,
        source_type=dto.source_type,
        source_id=dto.source_id,
        source_version_id=dto.source_version_id,
        audience=dto.audience,
        defaults={
            "organization": generation.organization,
            "language_code": dto.language,
            "title": dto.title[:300],
            "subtitle": dto.subtitle[:500],
            "body_plain_text": dto.body[:200_000],
            "normalized_title": dto.normalized_title[:300],
            "url_path": dto.url_path[:1000],
            "metadata": dto.metadata,
            "content_digest": dto.digest,
            "indexed_at": timezone.now(),
            "is_active": True,
        },
    )
    configuration = "english" if dto.language == "en" else "spanish"
    SearchDocument.objects.filter(pk=document.pk).update(
        search_vector=(
            SearchVector("title", weight="A", config=configuration)
            + SearchVector("subtitle", weight="B", config=configuration)
            + SearchVector("body_plain_text", weight="C", config=configuration)
        )
    )


def rebuild_search_index(
    *, organization: object, actor: object | None = None
) -> SearchGeneration:
    with transaction.atomic():
        locked = type(organization).objects.select_for_update().get(pk=organization.pk)
        previous_number = (
            SearchGeneration.objects.filter(organization=locked)
            .order_by("-number")
            .values_list("number", flat=True)
            .first()
            or 0
        )
        generation = SearchGeneration.objects.create(
            organization=locked,
            number=previous_number + 1,
            status=GenerationStatus.BUILDING,
            started_at=timezone.now(),
            created_by=actor,
        )
    try:
        with domain_span("discovery.rebuild", {"search.generation": generation.number}):
            for dto in organization_documents(organization):
                upsert_search_document(generation, dto)
        count = generation.documents.filter(is_active=True).count()
        with transaction.atomic():
            type(organization).objects.select_for_update().get(pk=organization.pk)
            SearchGeneration.objects.filter(
                organization=organization, status=GenerationStatus.ACTIVE
            ).update(status=GenerationStatus.SUPERSEDED)
            generation.status = GenerationStatus.ACTIVE
            generation.document_count = count
            generation.completed_at = timezone.now()
            generation.save(update_fields=("status", "document_count", "completed_at"))
    except Exception:
        generation.status = GenerationStatus.FAILED
        generation.failure_code = "rebuild_failed"
        generation.completed_at = timezone.now()
        generation.save(update_fields=("status", "failure_code", "completed_at"))
        raise
    return generation


def _authorized_queryset(actor: Any, organization: Any) -> QuerySet[SearchDocument]:
    generation = SearchGeneration.objects.filter(
        organization=organization, status=GenerationStatus.ACTIVE
    ).first()
    if generation is None:
        return SearchDocument.objects.none()
    allowed = Q(pk__in=[])
    if has_capability(actor, organization, Capability.SEARCH_AUTHORING_USE):
        allowed |= Q(audience=SearchAudience.AUTHORING)
    if has_capability(actor, organization, Capability.SEARCH_INSTITUTIONAL_USE):
        allowed |= Q(audience=SearchAudience.INSTITUTIONAL)
    actor_id = getattr(actor, "id", None)
    if actor_id:
        now = timezone.now()
        release_ids = (
            CourseEnrollment.objects.filter(
                organization=organization,
                membership__user_id=actor_id,
                membership__status=MembershipStatus.ACTIVE,
                status=EnrollmentStatus.ACTIVE,
                current_release_assignment__ended_at__isnull=True,
                course__publication__status=PublicationStatus.ACTIVE,
            )
            .filter(
                Q(access_starts_at__isnull=True) | Q(access_starts_at__lte=now),
                Q(access_ends_at__isnull=True) | Q(access_ends_at__gt=now),
            )
            .values_list("current_release_assignment__release_id", flat=True)
        )
        allowed |= Q(
            audience=SearchAudience.LEARNING,
            metadata__release_id__in=[str(item) for item in release_ids],
        )
    return SearchDocument.objects.filter(
        generation=generation, organization=organization, is_active=True
    ).filter(allowed)


def search_authorized_documents(
    *,
    actor: Any,
    organization: Any,
    query: str,
    filters: list[str] | None = None,
    page: int = 1,
    page_size: int = 20,
) -> SearchPage:
    started = time.perf_counter()
    normalized = normalize_query(query)
    if filters and len(filters) > 10:
        raise ValueError("Se admiten máximo 10 filtros.")
    page = max(1, page)
    page_size = max(1, min(page_size, 50))
    query_es = SearchQuery(normalized, search_type="websearch", config="spanish")
    query_en = SearchQuery(normalized, search_type="websearch", config="english")
    combined = query_es | query_en
    queryset = _authorized_queryset(actor, organization)
    if filters:
        queryset = queryset.filter(source_type__in=filters)
    queryset = (
        queryset.annotate(
            fts_rank=Coalesce(
                SearchRank(F("search_vector"), combined),
                Value(0.0),
                output_field=FloatField(),
            ),
            title_similarity=TrigramSimilarity(
                "normalized_title", normalize_title(normalized)
            ),
        )
        .annotate(
            final_rank=F("fts_rank") * Value(0.8) + F("title_similarity") * Value(0.2)
        )
        .filter(Q(fts_rank__gt=0.01) | Q(title_similarity__gte=0.25))
        .order_by("-final_rank", "title", "id")
    )
    total = queryset.count()
    start = (page - 1) * page_size
    with domain_span(
        "discovery.search",
        {"search.page_size": page_size, "search.filter_count": len(filters or [])},
    ):
        rows = list(queryset[start : start + page_size])
    results = [
        {
            "source_type": row.source_type,
            "source_id": row.source_id,
            "title": row.title,
            "subtitle": row.subtitle,
            "snippet_segments": [
                segment.__dict__
                for segment in safe_snippet(
                    row.body_plain_text or row.subtitle or row.title, normalized
                )
            ],
            "url_path": row.url_path,
            "metadata": row.metadata,
            "rank_bucket": "high"
            if row.final_rank >= 0.5
            else "medium"
            if row.final_rank >= 0.2
            else "low",
        }
        for row in rows
    ]
    elapsed = time.perf_counter() - started
    attributes = safe_attributes({"outcome": "results" if results else "empty"})
    search_queries.add(1, attributes)
    search_duration.record(elapsed, attributes)
    bucket = (
        "lt_50ms" if elapsed < 0.05 else "lt_200ms" if elapsed < 0.2 else "gte_200ms"
    )
    return SearchPage(normalized, results, page, page_size, total, bucket)


def suggest_authorized_documents(
    *, actor: Any, organization: Any, query: str, limit: int = 8
) -> list[dict[str, str]]:
    normalized = normalize_query(query)
    limit = max(1, min(limit, 10))
    queryset = (
        _authorized_queryset(actor, organization)
        .annotate(
            similarity=TrigramSimilarity(
                "normalized_title", normalize_title(normalized)
            )
        )
        .filter(
            Q(normalized_title__icontains=normalize_title(normalized))
            | Q(similarity__gt=0)
        )
        .order_by("-similarity", "title", "id")[:limit]
    )
    return [
        {
            "title": row.title,
            "source_type": row.source_type,
            "url_path": row.url_path,
        }
        for row in queryset
    ]
