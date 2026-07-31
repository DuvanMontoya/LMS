# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportCallIssue=false
from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from domain.organizations.models import Organization
from domain.organizations.selectors import organization_visible_to

from ..delivery.services import (
    asset_access_descriptor,
    authorized_original_descriptor,
)
from ..exceptions import (
    AssetAccessDenied,
    AssetConflict,
    AssetDomainError,
    AssetUploadExpired,
    AssetUploadInvalid,
    AssetUploadRateLimited,
)
from ..models import Asset, AssetProcessingJob, AssetUploadSession, AssetVersion
from ..policies import (
    can_access_asset_version_in_authoring,
    can_manage_assets,
    can_view_asset_library,
    can_view_asset_security,
)
from ..selectors import asset_detail, assets_for_library
from ..services import (
    archive_asset,
    promote_asset_version,
    reprocess_asset_version,
    restore_asset,
    update_asset_metadata,
)
from ..uploads.services import (
    abort_asset_upload,
    complete_asset_upload,
    initialize_asset_upload,
    record_upload_part,
    sign_upload_part,
)
from .serializers import (
    AssetAccessDescriptorSerializer,
    AssetDetailSerializer,
    AssetErrorSerializer,
    AssetSummarySerializer,
    AssetUpdateSerializer,
    AssetUsageSerializer,
    AssetVersionSerializer,
    ExpectedLockSerializer,
    ProcessingJobSerializer,
    RecordPartSerializer,
    SignedPartSerializer,
    SignPartSerializer,
    UploadInitializeSerializer,
    UploadInstructionsSerializer,
    UploadSessionSerializer,
    serialize_descriptor,
)

ERROR_RESPONSES = {
    400: AssetErrorSerializer,
    403: AssetErrorSerializer,
    404: AssetErrorSerializer,
    409: AssetErrorSerializer,
    413: AssetErrorSerializer,
    415: AssetErrorSerializer,
    422: AssetErrorSerializer,
    429: AssetErrorSerializer,
}


def _organization(request: Request, slug: str) -> Organization:
    try:
        return organization_visible_to(request.user, slug)
    except Http404 as error:
        raise NotFound(
            {"code": "asset_not_found", "detail": "El recurso no existe."}
        ) from error


def _require_view(request: Request, organization: Organization) -> None:
    if not can_view_asset_library(request.user, organization):
        raise PermissionDenied(
            {"code": "asset_permission_denied", "detail": "Acceso denegado."}
        )


def _asset_or_404(organization: Organization, asset_id: uuid.UUID) -> Asset:
    asset = asset_detail(organization, asset_id)
    if asset is None:
        raise NotFound({"code": "asset_not_found", "detail": "El recurso no existe."})
    return asset


def _version_or_404(
    organization: Organization, asset_id: uuid.UUID, version_id: uuid.UUID
) -> AssetVersion:
    version = (
        AssetVersion.objects.filter(
            pk=version_id,
            asset_id=asset_id,
            asset__organization=organization,
        )
        .select_related("asset__organization")
        .prefetch_related("variants")
        .first()
    )
    if version is None:
        raise NotFound(
            {"code": "asset_version_not_found", "detail": "El recurso no existe."}
        )
    return version


def _session_or_404(
    request: Request, organization: Organization, session_id: uuid.UUID
) -> AssetUploadSession:
    session = (
        AssetUploadSession.objects.filter(
            pk=session_id, organization=organization, created_by=request.user
        )
        .prefetch_related("parts")
        .first()
    )
    if session is None:
        raise NotFound(
            {"code": "upload_session_not_found", "detail": "El recurso no existe."}
        )
    return session


def _domain_call(operation: Callable[..., Any], /, **kwargs: Any) -> Any:
    try:
        return operation(**kwargs)
    except AssetAccessDenied as error:
        raise NotFound(
            {"code": "asset_not_found", "detail": "El recurso no existe."}
        ) from error
    except AssetUploadExpired as error:
        raise ValidationError(
            {"code": "upload_session_expired", "detail": str(error)},
            code="upload_session_expired",
        ) from error
    except AssetUploadRateLimited as error:
        exc = PermissionDenied({"code": "upload_rate_limited", "detail": str(error)})
        exc.status_code = status.HTTP_429_TOO_MANY_REQUESTS
        raise exc from error
    except AssetConflict as error:
        exc = ValidationError({"code": "asset_version_conflict", "detail": str(error)})
        exc.status_code = status.HTTP_409_CONFLICT
        raise exc from error
    except AssetUploadInvalid as error:
        raise ValidationError(
            {"code": "asset_validation_failed", "detail": str(error)},
            code="asset_validation_failed",
        ) from error
    except AssetDomainError as error:
        raise ValidationError(
            {"code": "asset_validation_failed", "detail": str(error)}
        ) from error


def _asset_context(request: Request, organization: Organization) -> dict[str, bool]:
    return {"show_security": can_view_asset_security(request.user, organization)}


class AssetListView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter("kind", str, required=False),
            OpenApiParameter("status", str, required=False),
            OpenApiParameter("search", str, required=False),
        ],
        responses={200: AssetSummarySerializer(many=True), **ERROR_RESPONSES},
    )
    def get(self, request: Request, organization_slug: str) -> Response:
        organization = _organization(request, organization_slug)
        _require_view(request, organization)
        assets = assets_for_library(
            organization,
            kind=request.query_params.get("kind", ""),
            status=request.query_params.get("status", ""),
            query=request.query_params.get("search", ""),
        )[:200]
        return Response(
            AssetSummarySerializer(
                assets, many=True, context=_asset_context(request, organization)
            ).data
        )


class AssetDetailView(APIView):
    @extend_schema(responses={200: AssetDetailSerializer, **ERROR_RESPONSES})
    def get(
        self, request: Request, organization_slug: str, asset_id: uuid.UUID
    ) -> Response:
        organization = _organization(request, organization_slug)
        _require_view(request, organization)
        asset = _asset_or_404(organization, asset_id)
        return Response(
            AssetDetailSerializer(
                asset, context=_asset_context(request, organization)
            ).data
        )

    @extend_schema(
        request=AssetUpdateSerializer,
        responses={200: AssetDetailSerializer, **ERROR_RESPONSES},
    )
    def patch(
        self, request: Request, organization_slug: str, asset_id: uuid.UUID
    ) -> Response:
        organization = _organization(request, organization_slug)
        asset = _asset_or_404(organization, asset_id)
        serializer = AssetUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = _domain_call(
            update_asset_metadata,
            actor=request.user,
            organization=organization,
            asset=asset,
            **serializer.validated_data,
        )
        refreshed = _asset_or_404(organization, updated.id)
        return Response(
            AssetDetailSerializer(
                refreshed, context=_asset_context(request, organization)
            ).data
        )


class AssetStateView(APIView):
    operation: Callable[..., Asset]

    @extend_schema(
        request=ExpectedLockSerializer,
        responses={200: AssetSummarySerializer, **ERROR_RESPONSES},
    )
    def post(
        self, request: Request, organization_slug: str, asset_id: uuid.UUID
    ) -> Response:
        organization = _organization(request, organization_slug)
        asset = _asset_or_404(organization, asset_id)
        serializer = ExpectedLockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = _domain_call(
            self.operation,
            actor=request.user,
            organization=organization,
            asset=asset,
            **serializer.validated_data,
        )
        return Response(
            AssetSummarySerializer(
                updated, context=_asset_context(request, organization)
            ).data
        )


class AssetArchiveView(AssetStateView):
    operation = staticmethod(archive_asset)


class AssetRestoreView(AssetStateView):
    operation = staticmethod(restore_asset)


class AssetVersionListView(APIView):
    @extend_schema(
        responses={200: AssetVersionSerializer(many=True), **ERROR_RESPONSES}
    )
    def get(
        self, request: Request, organization_slug: str, asset_id: uuid.UUID
    ) -> Response:
        organization = _organization(request, organization_slug)
        _require_view(request, organization)
        asset = _asset_or_404(organization, asset_id)
        return Response(
            AssetVersionSerializer(
                asset.versions.all(),
                many=True,
                context=_asset_context(request, organization),
            ).data
        )


class AssetVersionDetailView(APIView):
    @extend_schema(responses={200: AssetVersionSerializer, **ERROR_RESPONSES})
    def get(
        self,
        request: Request,
        organization_slug: str,
        asset_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> Response:
        organization = _organization(request, organization_slug)
        _require_view(request, organization)
        version = _version_or_404(organization, asset_id, version_id)
        return Response(
            AssetVersionSerializer(
                version, context=_asset_context(request, organization)
            ).data
        )


class AssetVersionPromoteView(APIView):
    @extend_schema(
        request=ExpectedLockSerializer,
        responses={200: AssetSummarySerializer, **ERROR_RESPONSES},
    )
    def post(
        self,
        request: Request,
        organization_slug: str,
        asset_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> Response:
        organization = _organization(request, organization_slug)
        version = _version_or_404(organization, asset_id, version_id)
        serializer = ExpectedLockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        asset = _domain_call(
            promote_asset_version,
            actor=request.user,
            organization=organization,
            version=version,
            **serializer.validated_data,
        )
        return Response(
            AssetSummarySerializer(
                asset, context=_asset_context(request, organization)
            ).data
        )


class AssetVersionReprocessView(APIView):
    @extend_schema(
        request=None,
        responses={202: ProcessingJobSerializer, **ERROR_RESPONSES},
    )
    def post(
        self,
        request: Request,
        organization_slug: str,
        asset_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> Response:
        organization = _organization(request, organization_slug)
        version = _version_or_404(organization, asset_id, version_id)
        job = _domain_call(
            reprocess_asset_version,
            actor=request.user,
            organization=organization,
            version=version,
        )
        return Response(
            ProcessingJobSerializer(job).data, status=status.HTTP_202_ACCEPTED
        )


class UploadInitializeView(APIView):
    @extend_schema(
        request=UploadInitializeSerializer,
        responses={201: UploadInstructionsSerializer, **ERROR_RESPONSES},
    )
    def post(self, request: Request, organization_slug: str) -> Response:
        organization = _organization(request, organization_slug)
        serializer = UploadInitializeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instructions = _domain_call(
            initialize_asset_upload,
            actor=request.user,
            organization=organization,
            **serializer.validated_data,
        )
        payload = {
            "session_id": instructions.session.id,
            "asset_id": instructions.session.asset_id,
            "asset_version_id": instructions.session.asset_version_id,
            "upload_method": instructions.session.upload_method,
            "expires_at": instructions.session.expires_at,
            "post": (
                {"url": instructions.post.url, "fields": instructions.post.fields}
                if instructions.post
                else None
            ),
            "part_size_bytes": instructions.part_size_bytes,
        }
        return Response(payload, status=status.HTTP_201_CREATED)


class UploadDetailView(APIView):
    @extend_schema(responses={200: UploadSessionSerializer, **ERROR_RESPONSES})
    def get(
        self, request: Request, organization_slug: str, session_id: uuid.UUID
    ) -> Response:
        organization = _organization(request, organization_slug)
        session = _session_or_404(request, organization, session_id)
        return Response(UploadSessionSerializer(session).data)


class UploadPartSignView(APIView):
    @extend_schema(
        request=SignPartSerializer,
        responses={200: SignedPartSerializer, **ERROR_RESPONSES},
    )
    def post(
        self,
        request: Request,
        organization_slug: str,
        session_id: uuid.UUID,
        part_number: int,
    ) -> Response:
        organization = _organization(request, organization_slug)
        serializer = SignPartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        url = _domain_call(
            sign_upload_part,
            actor=request.user,
            organization=organization,
            session_id=session_id,
            part_number=part_number,
            **serializer.validated_data,
        )
        return Response({"part_number": part_number, "url": url})


class UploadPartRecordView(APIView):
    @extend_schema(
        request=RecordPartSerializer,
        responses={200: UploadSessionSerializer, **ERROR_RESPONSES},
    )
    def post(
        self,
        request: Request,
        organization_slug: str,
        session_id: uuid.UUID,
        part_number: int,
    ) -> Response:
        organization = _organization(request, organization_slug)
        serializer = RecordPartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _domain_call(
            record_upload_part,
            actor=request.user,
            organization=organization,
            session_id=session_id,
            part_number=part_number,
            **serializer.validated_data,
        )
        session = _session_or_404(request, organization, session_id)
        return Response(UploadSessionSerializer(session).data)


class UploadCompleteView(APIView):
    @extend_schema(
        request=None,
        responses={202: ProcessingJobSerializer, **ERROR_RESPONSES},
    )
    def post(
        self, request: Request, organization_slug: str, session_id: uuid.UUID
    ) -> Response:
        organization = _organization(request, organization_slug)
        job = _domain_call(
            complete_asset_upload,
            actor=request.user,
            organization=organization,
            session_id=session_id,
        )
        return Response(
            ProcessingJobSerializer(job).data, status=status.HTTP_202_ACCEPTED
        )


class UploadAbortView(APIView):
    @extend_schema(
        request=None, responses={200: UploadSessionSerializer, **ERROR_RESPONSES}
    )
    def post(
        self, request: Request, organization_slug: str, session_id: uuid.UUID
    ) -> Response:
        organization = _organization(request, organization_slug)
        session = _domain_call(
            abort_asset_upload,
            actor=request.user,
            organization=organization,
            session_id=session_id,
        )
        return Response(UploadSessionSerializer(session).data)


class ProcessingJobDetailView(APIView):
    @extend_schema(responses={200: ProcessingJobSerializer, **ERROR_RESPONSES})
    def get(
        self, request: Request, organization_slug: str, job_id: uuid.UUID
    ) -> Response:
        organization = _organization(request, organization_slug)
        _require_view(request, organization)
        job = (
            AssetProcessingJob.objects.filter(
                pk=job_id, asset_version__asset__organization=organization
            )
            .select_related("asset_version")
            .first()
        )
        if job is None:
            raise NotFound(
                {"code": "asset_not_found", "detail": "El recurso no existe."}
            )
        return Response(ProcessingJobSerializer(job).data)


class AssetAccessView(APIView):
    original = False

    @extend_schema(
        request=None,
        responses={200: AssetAccessDescriptorSerializer, **ERROR_RESPONSES},
    )
    def post(
        self,
        request: Request,
        organization_slug: str,
        asset_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> Response:
        organization = _organization(request, organization_slug)
        version = _version_or_404(organization, asset_id, version_id)
        if self.original:
            descriptor = _domain_call(
                authorized_original_descriptor,
                actor=request.user,
                version=version,
            )
        else:
            if not can_access_asset_version_in_authoring(request.user, version):
                raise NotFound(
                    {
                        "code": "asset_access_denied",
                        "detail": "El recurso no existe.",
                    }
                )
            descriptor = _domain_call(asset_access_descriptor, version=version)
        return Response(serialize_descriptor(descriptor))


class AssetOriginalDownloadView(AssetAccessView):
    original = True


class AssetUsageView(APIView):
    @extend_schema(responses={200: AssetUsageSerializer, **ERROR_RESPONSES})
    def get(
        self, request: Request, organization_slug: str, asset_id: uuid.UUID
    ) -> Response:
        organization = _organization(request, organization_slug)
        _require_view(request, organization)
        _asset_or_404(organization, asset_id)
        if not can_manage_assets(request.user, organization):
            raise PermissionDenied(
                {"code": "asset_permission_denied", "detail": "Acceso denegado."}
            )
        # Content and publishing register their usage providers without assets
        # importing either downstream domain.
        from ..usage import collect_asset_usage

        return Response(collect_asset_usage(asset_id=asset_id))
