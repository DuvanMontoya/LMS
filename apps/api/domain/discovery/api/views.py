# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportIndexIssue=false, reportOptionalSubscript=false, reportCallIssue=false, reportPrivateImportUsage=false, reportUnknownLambdaType=false
from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from domain.organizations.capabilities import Capability
from domain.organizations.models import Organization
from domain.organizations.policies import has_capability, organizations_with_capability

from ..models import (
    SearchGeneration,
    SearchIndexJob,
    SearchIndexOperation,
    SearchSourceType,
)
from ..services import search_authorized_documents, suggest_authorized_documents
from ..tasks import process_search_index_job
from .serializers import (
    SearchGenerationSerializer,
    SearchIndexJobSerializer,
    SearchRebuildSerializer,
    SearchResponseSerializer,
    SearchSuggestionSerializer,
)


def _visible_organizations(
    request: Request, capability: Capability
) -> list[Organization]:
    return organizations_with_capability(request.user, capability)


class SearchView(APIView):
    @extend_schema(
        operation_id="organizations_discovery_search",
        parameters=[
            OpenApiParameter("q", OpenApiTypes.STR, required=True),
            OpenApiParameter("types", OpenApiTypes.STR),
            OpenApiParameter("page", OpenApiTypes.INT),
            OpenApiParameter("page_size", OpenApiTypes.INT),
        ],
        responses=SearchResponseSerializer,
    )
    def get(self, request: Request, organization_slug: str) -> Response:
        organization = get_object_or_404(Organization, slug=organization_slug)
        raw_types = request.query_params.get("types", "")
        filters = [item for item in raw_types.split(",") if item]
        if set(filters) - set(SearchSourceType.values):
            return Response({"code": "search_query_invalid"}, status=400)
        try:
            page = search_authorized_documents(
                actor=request.user,
                organization=organization,
                query=request.query_params.get("q", ""),
                filters=filters,
                page=int(request.query_params.get("page", "1")),
                page_size=int(request.query_params.get("page_size", "20")),
            )
        except (ValueError, TypeError):
            return Response({"code": "search_query_invalid"}, status=400)
        payload = {
            "query": page.query,
            "results": page.results,
            "pagination": {
                "page": page.page,
                "page_size": page.page_size,
                "total": page.total,
            },
            "filters": filters,
            "timing_bucket": page.timing_bucket,
        }
        return Response(SearchResponseSerializer(payload).data)


class SearchSuggestionsView(APIView):
    @extend_schema(
        operation_id="organizations_discovery_search_suggestions",
        parameters=[OpenApiParameter("q", OpenApiTypes.STR, required=True)],
        responses=SearchSuggestionSerializer(many=True),
    )
    def get(self, request: Request, organization_slug: str) -> Response:
        organization = get_object_or_404(Organization, slug=organization_slug)
        try:
            suggestions = suggest_authorized_documents(
                actor=request.user,
                organization=organization,
                query=request.query_params.get("q", ""),
            )
        except (ValueError, TypeError):
            return Response({"code": "search_query_invalid"}, status=400)
        return Response(SearchSuggestionSerializer(suggestions, many=True).data)


class SearchIndexView(APIView):
    @extend_schema(
        operation_id="platform_search_generations_list",
        responses=SearchGenerationSerializer(many=True),
    )
    def get(self, request: Request) -> Response:
        organizations = _visible_organizations(request, Capability.SEARCH_INDEX_VIEW)
        rows = SearchGeneration.objects.filter(organization__in=organizations)
        return Response(SearchGenerationSerializer(rows, many=True).data)


class SearchRebuildView(APIView):
    @extend_schema(
        operation_id="platform_search_rebuild_create",
        request=SearchRebuildSerializer,
        responses={202: SearchIndexJobSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = SearchRebuildSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = get_object_or_404(
            Organization, slug=serializer.validated_data["organization_slug"]
        )
        if not has_capability(
            request.user, organization, Capability.SEARCH_INDEX_REBUILD
        ):
            return Response({"code": "search_permission_denied"}, status=403)
        with transaction.atomic():
            generation = SearchGeneration.objects.filter(
                organization=organization, status="active"
            ).first()
            if SearchIndexJob.objects.filter(
                organization=organization,
                status__in=("pending", "processing"),
                operation=SearchIndexOperation.REBUILD,
            ).exists():
                return Response({"code": "search_rebuild_conflict"}, status=409)
            job = SearchIndexJob.objects.create(
                organization=organization,
                generation=generation,
                source_type=SearchSourceType.COURSE_RELEASE,
                operation=SearchIndexOperation.REBUILD,
            )
            transaction.on_commit(lambda: process_search_index_job.delay(str(job.id)))
        return Response(
            SearchIndexJobSerializer(job).data, status=status.HTTP_202_ACCEPTED
        )


class SearchIndexJobsView(APIView):
    @extend_schema(
        operation_id="platform_search_index_jobs_list",
        responses=SearchIndexJobSerializer(many=True),
    )
    def get(self, request: Request) -> Response:
        organizations = _visible_organizations(request, Capability.SEARCH_INDEX_VIEW)
        return Response(
            SearchIndexJobSerializer(
                SearchIndexJob.objects.filter(organization__in=organizations).order_by(
                    "-created_at"
                )[:200],
                many=True,
            ).data
        )
