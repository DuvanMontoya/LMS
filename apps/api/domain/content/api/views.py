# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportCallIssue=false
from __future__ import annotations

import uuid
from typing import Any

from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from domain.courses.models import CourseRevision, CourseUnit
from domain.courses.selectors import (
    course_visible_to_actor,
    revision_visible_to_actor,
)
from domain.organizations.models import Organization
from domain.organizations.selectors import organization_visible_to

from ..exceptions import (
    ContentAccessDenied,
    ContentDocumentConflict,
    ContentDomainError,
    ContentNotEditable,
    ContentRestoreInvalid,
    ContentTooDeep,
    ContentTooLarge,
    ContentVersionNotFound,
)
from ..extraction import has_meaningful_content
from ..policies import can_edit_unit_content
from ..schemas import CURRENT_CONTENT_SCHEMA_VERSION, empty_document
from ..selectors import (
    current_unit_content,
    scoped_unit,
    unit_content_version,
    unit_content_versions,
)
from ..services import restore_unit_content, save_unit_content
from ..validators import validate_content
from .serializers import (
    ContentCurrentSerializer,
    ContentErrorSerializer,
    ContentMetricsSerializer,
    ContentValidateSerializer,
    ContentVersionDetailSerializer,
    ContentVersionSummarySerializer,
    ContentWriteSerializer,
    RestoreContentSerializer,
)


def _context(
    request: Request,
    organization_slug: str,
    course_slug: str,
    revision_id: str,
    unit_id: str,
) -> tuple[Organization, CourseRevision, CourseUnit]:
    try:
        organization = organization_visible_to(request.user, organization_slug)
        course = course_visible_to_actor(request.user, organization, course_slug)
        revision = revision_visible_to_actor(request.user, course, revision_id)
        unit = scoped_unit(revision, unit_id)
    except Http404 as error:
        raise NotFound(
            {"code": "content_not_found", "detail": "El contenido no existe."}
        ) from error
    return organization, revision, unit


def _error_response(error: ContentDomainError) -> Response:
    response_status = status.HTTP_400_BAD_REQUEST
    payload: dict[str, Any] = {
        "code": error.code,
        "detail": error.message,
        "path": error.path,
    }
    if isinstance(error, ContentDocumentConflict):
        response_status = status.HTTP_409_CONFLICT
        payload["current_document_version"] = error.current_version
    elif isinstance(error, ContentAccessDenied):
        response_status = status.HTTP_403_FORBIDDEN
    elif isinstance(error, (ContentVersionNotFound,)):
        response_status = status.HTTP_404_NOT_FOUND
    elif isinstance(error, (ContentTooLarge, ContentTooDeep)):
        response_status = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    elif isinstance(error, (ContentNotEditable, ContentRestoreInvalid)):
        response_status = status.HTTP_409_CONFLICT
    return Response(payload, status=response_status)


def _current_payload(
    *,
    request: Request,
    revision: CourseRevision,
    unit: CourseUnit,
    no_op: bool = False,
) -> dict[str, Any]:
    document = current_unit_content(request.user, revision, unit)
    if document is None or document.current_version is None:
        content = empty_document(str(uuid.uuid4()))
        metrics = validate_content(
            content, schema_version=CURRENT_CONTENT_SCHEMA_VERSION
        ).metrics
        return {
            "document_id": None,
            "document_version": 0,
            "schema_version": CURRENT_CONTENT_SCHEMA_VERSION,
            "content": content,
            "digest": "",
            "updated_at": None,
            "editable": can_edit_unit_content(request.user, revision),
            "is_meaningful": False,
            "character_count": metrics.character_count,
            "word_count": metrics.word_count,
            "node_count": metrics.node_count,
            "no_op": no_op,
        }
    version = document.current_version
    return {
        "document_id": document.id,
        "document_version": version.number,
        "schema_version": version.schema_version,
        "content": version.content,
        "digest": version.digest,
        "updated_at": document.updated_at,
        "editable": can_edit_unit_content(request.user, revision),
        "is_meaningful": has_meaningful_content(version.content),
        "character_count": version.character_count,
        "word_count": version.word_count,
        "node_count": version.node_count,
        "no_op": no_op,
    }


class UnitContentView(APIView):
    @extend_schema(
        responses={
            200: ContentCurrentSerializer,
            404: ContentErrorSerializer,
        }
    )
    def get(
        self,
        request: Request,
        organization_slug: str,
        course_slug: str,
        revision_id: str,
        unit_id: str,
    ) -> Response:
        _organization, revision, unit = _context(
            request, organization_slug, course_slug, revision_id, unit_id
        )
        return Response(
            ContentCurrentSerializer(
                _current_payload(request=request, revision=revision, unit=unit)
            ).data
        )

    @extend_schema(
        request=ContentWriteSerializer,
        responses={
            200: ContentCurrentSerializer,
            400: ContentErrorSerializer,
            403: ContentErrorSerializer,
            404: ContentErrorSerializer,
            409: ContentErrorSerializer,
            413: ContentErrorSerializer,
        },
    )
    def put(
        self,
        request: Request,
        organization_slug: str,
        course_slug: str,
        revision_id: str,
        unit_id: str,
    ) -> Response:
        organization, revision, unit = _context(
            request, organization_slug, course_slug, revision_id, unit_id
        )
        serializer = ContentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = save_unit_content(
                actor=request.user,
                organization=organization,
                revision=revision,
                unit=unit,
                **serializer.validated_data,
            )
        except ContentDomainError as error:
            return _error_response(error)
        revision.refresh_from_db()
        return Response(
            ContentCurrentSerializer(
                _current_payload(
                    request=request,
                    revision=revision,
                    unit=unit,
                    no_op=result.no_op,
                )
            ).data
        )


class ValidateUnitContentView(APIView):
    @extend_schema(
        request=ContentValidateSerializer,
        responses={
            200: ContentMetricsSerializer,
            400: ContentErrorSerializer,
            403: ContentErrorSerializer,
            413: ContentErrorSerializer,
        },
    )
    def post(
        self,
        request: Request,
        organization_slug: str,
        course_slug: str,
        revision_id: str,
        unit_id: str,
    ) -> Response:
        _organization, revision, _unit = _context(
            request, organization_slug, course_slug, revision_id, unit_id
        )
        if not can_edit_unit_content(request.user, revision):
            raise PermissionDenied("content_permission_denied")
        serializer = ContentValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            validated = validate_content(**serializer.validated_data)
        except ContentDomainError as error:
            return _error_response(error)
        return Response(
            ContentMetricsSerializer(
                {
                    "character_count": validated.metrics.character_count,
                    "word_count": validated.metrics.word_count,
                    "node_count": validated.metrics.node_count,
                    "is_meaningful": has_meaningful_content(validated.content),
                }
            ).data
        )


class UnitContentVersionListView(APIView):
    @extend_schema(responses={200: ContentVersionSummarySerializer(many=True)})
    def get(
        self,
        request: Request,
        organization_slug: str,
        course_slug: str,
        revision_id: str,
        unit_id: str,
    ) -> Response:
        _organization, revision, unit = _context(
            request, organization_slug, course_slug, revision_id, unit_id
        )
        document = current_unit_content(request.user, revision, unit)
        current_number = (
            document.current_version.number
            if document is not None and document.current_version is not None
            else None
        )
        return Response(
            ContentVersionSummarySerializer(
                unit_content_versions(request.user, revision, unit),
                many=True,
                context={"current_number": current_number},
            ).data
        )


class UnitContentVersionDetailView(APIView):
    @extend_schema(
        responses={
            200: ContentVersionDetailSerializer,
            404: ContentErrorSerializer,
        }
    )
    def get(
        self,
        request: Request,
        organization_slug: str,
        course_slug: str,
        revision_id: str,
        unit_id: str,
        version_number: int,
    ) -> Response:
        _organization, revision, unit = _context(
            request, organization_slug, course_slug, revision_id, unit_id
        )
        try:
            version = unit_content_version(request.user, revision, unit, version_number)
        except Http404 as error:
            raise NotFound(
                {"code": "content_version_not_found", "detail": "La versión no existe."}
            ) from error
        document = current_unit_content(request.user, revision, unit)
        return Response(
            ContentVersionDetailSerializer(
                version,
                context={
                    "current_number": (
                        document.current_version.number
                        if document is not None and document.current_version is not None
                        else None
                    )
                },
            ).data
        )


class RestoreUnitContentView(APIView):
    @extend_schema(
        request=RestoreContentSerializer,
        responses={
            200: ContentCurrentSerializer,
            400: ContentErrorSerializer,
            403: ContentErrorSerializer,
            404: ContentErrorSerializer,
            409: ContentErrorSerializer,
        },
    )
    def post(
        self,
        request: Request,
        organization_slug: str,
        course_slug: str,
        revision_id: str,
        unit_id: str,
        version_number: int,
    ) -> Response:
        organization, revision, unit = _context(
            request, organization_slug, course_slug, revision_id, unit_id
        )
        serializer = RestoreContentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            restore_unit_content(
                actor=request.user,
                organization=organization,
                revision=revision,
                unit=unit,
                version_number=version_number,
                **serializer.validated_data,
            )
        except ContentDomainError as error:
            return _error_response(error)
        revision.refresh_from_db()
        return Response(
            ContentCurrentSerializer(
                _current_payload(request=request, revision=revision, unit=unit)
            ).data
        )
