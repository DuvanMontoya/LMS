# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportIndexIssue=false, reportOptionalSubscript=false
from __future__ import annotations

from typing import Any

from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from domain.courses.choices import AuthoringStatus
from domain.courses.models import CourseRevision
from domain.organizations.models import Organization
from domain.organizations.selectors import organization_visible_to

from ..exceptions import (
    DraftAlreadyOpen,
    DraftCreationInvalid,
    PublicationAccessDenied,
    PublicationConflict,
    PublicationTransitionInvalid,
    PublishingDomainError,
    ReleaseChainInvalid,
    ReleaseIntegrityFailed,
    ReleaseSnapshotInvalid,
    ReleaseSnapshotTooLarge,
    ReleaseSourceNotApproved,
    ReleaseSourceNotNewer,
    WithdrawalNoteRequired,
)
from ..integrity import IntegrityResult, verify_release
from ..models import CoursePublication, CourseRelease
from ..policies import (
    can_create_draft,
    can_publish,
    can_view_history,
    can_view_published,
    can_withdraw,
)
from ..selectors import (
    active_library_publication,
    active_library_publications,
    organization_course,
    publication_for_history,
    release_for_history,
    releases_for_history,
)
from ..services import (
    create_draft_from_release,
    publish_approved_revision,
    withdraw_publication,
)
from ..snapshots import release_outline, release_previous_next, release_unit
from .serializers import (
    CreateDraftSerializer,
    DraftResultSerializer,
    LibraryCourseSerializer,
    LibraryDetailSerializer,
    PublicationStateSerializer,
    PublishingErrorSerializer,
    PublishResultSerializer,
    PublishSerializer,
    ReleaseDetailSerializer,
    ReleaseOutlineSerializer,
    ReleaseSummarySerializer,
    ReleaseUnitSerializer,
    VerificationSerializer,
    WithdrawSerializer,
)


def _organization(request: Request, slug: str) -> Organization:
    try:
        return organization_visible_to(request.user, slug)
    except Http404 as error:
        raise NotFound(
            {"code": "publication_not_found", "detail": "El recurso no existe."}
        ) from error


def _course(organization: Organization, course_slug: str):
    try:
        return organization_course(organization, course_slug)
    except Http404 as error:
        raise NotFound(
            {"code": "publication_not_found", "detail": "El recurso no existe."}
        ) from error


def _no_store(response: Response) -> Response:
    response["Cache-Control"] = "private, no-store"
    return response


def _integrity_payload(result: IntegrityResult) -> dict[str, Any]:
    return {
        "valid": result.valid,
        "checked_releases": result.checked_releases,
        "issues": [
            {
                "code": issue.code,
                "release_number": issue.release_number,
                "detail": issue.detail,
            }
            for issue in result.issues
        ],
    }


def _release_summary(
    release: CourseRelease, publication: CoursePublication
) -> dict[str, Any]:
    return {
        "number": release.number,
        "title": release.title,
        "summary": release.summary,
        "language_code": release.language_code,
        "estimated_duration_minutes": release.estimated_duration_minutes,
        "module_count": release.module_count,
        "unit_count": release.unit_count,
        "word_count": release.word_count,
        "snapshot_digest": release.snapshot_digest,
        "previous_release_number": release.previous_release.number
        if release.previous_release
        else None,
        "source_revision_id": release.source_revision_id,
        "source_revision_number": release.source_revision.number,
        "created_at": release.created_at,
        "is_current": publication.current_release_id == release.id,
    }


def _domain_error(error: PublishingDomainError) -> Response:
    mapping: list[tuple[type[PublishingDomainError], str, int]] = [
        (
            PublicationAccessDenied,
            "publication_permission_denied",
            status.HTTP_403_FORBIDDEN,
        ),
        (PublicationConflict, "publication_conflict", status.HTTP_409_CONFLICT),
        (
            PublicationTransitionInvalid,
            "publication_transition_invalid",
            status.HTTP_409_CONFLICT,
        ),
        (ReleaseSourceNotApproved, "release_source_not_approved", 400),
        (ReleaseSourceNotNewer, "release_source_not_newer", 409),
        (ReleaseSnapshotInvalid, "release_snapshot_invalid", 400),
        (ReleaseSnapshotTooLarge, "release_snapshot_too_large", 413),
        (ReleaseChainInvalid, "release_chain_invalid", 409),
        (ReleaseIntegrityFailed, "release_integrity_failed", 409),
        (DraftAlreadyOpen, "draft_already_open", 409),
        (DraftCreationInvalid, "draft_creation_invalid", 409),
        (WithdrawalNoteRequired, "withdrawal_note_required", 400),
    ]
    for error_type, code, response_status in mapping:
        if isinstance(error, error_type):
            return Response(
                {"code": code, "detail": str(error)}, status=response_status
            )
    return Response(
        {"code": "publication_operation_rejected", "detail": "Operación inválida."},
        status=400,
    )


class PublicationStateView(APIView):
    @extend_schema(
        responses={200: PublicationStateSerializer, 403: PublishingErrorSerializer}
    )
    def get(self, request: Request, slug: str, course_slug: str) -> Response:
        organization = _organization(request, slug)
        if not can_view_history(request.user, organization):
            raise PermissionDenied("publication_permission_denied")
        course = _course(organization, course_slug)
        publication = (
            CoursePublication.objects.filter(course=course)
            .select_related("current_release")
            .first()
        )
        approved = (
            CourseRevision.objects.filter(
                course=course, authoring_status=AuthoringStatus.APPROVED
            )
            .order_by("-number")
            .first()
        )
        payload = {
            "has_publication": publication is not None,
            "status": publication.status if publication else None,
            "lock_version": publication.lock_version if publication else 0,
            "current_release_number": publication.current_release.number
            if publication
            else None,
            "first_published_at": publication.first_published_at
            if publication
            else None,
            "last_published_at": publication.last_published_at if publication else None,
            "withdrawn_at": publication.withdrawn_at if publication else None,
            "withdrawal_note": publication.withdrawal_note if publication else "",
            "approved_revision_id": approved.id if approved else None,
        }
        return _no_store(Response(PublicationStateSerializer(payload).data))


class PublishRevisionView(APIView):
    @extend_schema(
        request=PublishSerializer,
        responses={
            200: PublishResultSerializer,
            400: PublishingErrorSerializer,
            403: PublishingErrorSerializer,
            409: PublishingErrorSerializer,
        },
    )
    def post(
        self, request: Request, slug: str, course_slug: str, revision_id: str
    ) -> Response:
        organization = _organization(request, slug)
        if not can_publish(request.user, organization):
            raise PermissionDenied("publication_permission_denied")
        course = _course(organization, course_slug)
        revision = get_object_or_404(CourseRevision, id=revision_id, course=course)
        serializer = PublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = publish_approved_revision(
                actor=request.user,
                organization=organization,
                course=course,
                revision=revision,
                expected_publication_version=serializer.validated_data[
                    "expected_publication_version"
                ],
            )
        except PublishingDomainError as error:
            return _domain_error(error)
        return Response(
            PublishResultSerializer(
                {
                    "release_number": result.release.number,
                    "snapshot_digest": result.release.snapshot_digest,
                    "publication_status": result.publication.status,
                    "publication_version": result.publication.lock_version,
                    "already_released": result.already_released,
                    "is_current": result.is_current,
                }
            ).data
        )


class WithdrawPublicationView(APIView):
    @extend_schema(
        request=WithdrawSerializer,
        responses={
            200: PublicationStateSerializer,
            400: PublishingErrorSerializer,
            403: PublishingErrorSerializer,
            409: PublishingErrorSerializer,
        },
    )
    def post(self, request: Request, slug: str, course_slug: str) -> Response:
        organization = _organization(request, slug)
        if not can_withdraw(request.user, organization):
            raise PermissionDenied("publication_permission_denied")
        course = _course(organization, course_slug)
        serializer = WithdrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            publication = withdraw_publication(
                actor=request.user,
                organization=organization,
                course=course,
                expected_publication_version=serializer.validated_data[
                    "expected_publication_version"
                ],
                note=serializer.validated_data["note"],
            )
        except PublishingDomainError as error:
            return _domain_error(error)
        payload = {
            "has_publication": True,
            "status": publication.status,
            "lock_version": publication.lock_version,
            "current_release_number": publication.current_release.number,
            "first_published_at": publication.first_published_at,
            "last_published_at": publication.last_published_at,
            "withdrawn_at": publication.withdrawn_at,
            "withdrawal_note": publication.withdrawal_note,
            "approved_revision_id": None,
        }
        return _no_store(Response(PublicationStateSerializer(payload).data))


class ReleaseListView(APIView):
    @extend_schema(responses={200: ReleaseSummarySerializer(many=True)})
    def get(self, request: Request, slug: str, course_slug: str) -> Response:
        organization = _organization(request, slug)
        try:
            publication = publication_for_history(
                request.user, organization, course_slug
            )
        except Http404 as error:
            raise NotFound(
                {"code": "release_not_found", "detail": "El release no existe."}
            ) from error
        payload = [
            _release_summary(release, publication)
            for release in releases_for_history(request.user, publication)
        ]
        return _no_store(Response(ReleaseSummarySerializer(payload, many=True).data))


class HistoricalReleaseMixin:
    def release(
        self, request: Request, slug: str, course_slug: str, release_number: int
    ) -> tuple[CoursePublication, CourseRelease]:
        organization = _organization(request, slug)
        try:
            publication = publication_for_history(
                request.user, organization, course_slug
            )
            release = release_for_history(request.user, publication, release_number)
        except Http404 as error:
            raise NotFound(
                {"code": "release_not_found", "detail": "El release no existe."}
            ) from error
        return publication, release


class ReleaseDetailView(HistoricalReleaseMixin, APIView):
    @extend_schema(responses={200: ReleaseDetailSerializer})
    def get(
        self, request: Request, slug: str, course_slug: str, release_number: int
    ) -> Response:
        publication, release = self.release(request, slug, course_slug, release_number)
        payload = {
            **_release_summary(release, publication),
            "schema_version": release.schema_version,
            "snapshot_size_bytes": release.snapshot_size_bytes,
            "course": release.snapshot["course"],
            "curriculum": release.snapshot["curriculum"],
        }
        return _no_store(Response(ReleaseDetailSerializer(payload).data))


class ReleaseOutlineView(HistoricalReleaseMixin, APIView):
    @extend_schema(responses={200: ReleaseOutlineSerializer})
    def get(
        self, request: Request, slug: str, course_slug: str, release_number: int
    ) -> Response:
        _publication, release = self.release(request, slug, course_slug, release_number)
        payload = {
            "release_number": release.number,
            "modules": release_outline(release.snapshot),
        }
        return _no_store(Response(ReleaseOutlineSerializer(payload).data))


class ReleaseUnitView(HistoricalReleaseMixin, APIView):
    @extend_schema(responses={200: ReleaseUnitSerializer})
    def get(
        self,
        request: Request,
        slug: str,
        course_slug: str,
        release_number: int,
        unit_id: str,
    ) -> Response:
        _publication, release = self.release(request, slug, course_slug, release_number)
        try:
            unit = release_unit(release.snapshot, str(unit_id))
            navigation = release_previous_next(release.snapshot, str(unit_id))
        except ReleaseSnapshotInvalid as error:
            raise NotFound(
                {"code": "release_not_found", "detail": "La unidad no existe."}
            ) from error
        payload = {
            "release_number": release.number,
            "course": release.snapshot["course"],
            "unit": unit,
            "navigation": navigation,
        }
        return _no_store(Response(ReleaseUnitSerializer(payload).data))


class ReleaseVerifyView(HistoricalReleaseMixin, APIView):
    @extend_schema(responses={200: VerificationSerializer})
    def get(
        self, request: Request, slug: str, course_slug: str, release_number: int
    ) -> Response:
        _publication, release = self.release(request, slug, course_slug, release_number)
        return _no_store(
            Response(
                VerificationSerializer(_integrity_payload(verify_release(release))).data
            )
        )


class CreateDraftView(HistoricalReleaseMixin, APIView):
    @extend_schema(
        request=CreateDraftSerializer,
        responses={
            201: DraftResultSerializer,
            403: PublishingErrorSerializer,
            409: PublishingErrorSerializer,
        },
    )
    def post(
        self, request: Request, slug: str, course_slug: str, release_number: int
    ) -> Response:
        organization = _organization(request, slug)
        if not can_create_draft(request.user, organization):
            raise PermissionDenied("publication_permission_denied")
        course = _course(organization, course_slug)
        serializer = CreateDraftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            revision = create_draft_from_release(
                actor=request.user,
                organization=organization,
                course=course,
                release_number=release_number,
                expected_publication_version=serializer.validated_data[
                    "expected_publication_version"
                ],
            )
        except PublishingDomainError as error:
            return _domain_error(error)
        return Response(
            DraftResultSerializer(
                {
                    "revision_id": revision.id,
                    "revision_number": revision.number,
                    "lock_version": revision.lock_version,
                }
            ).data,
            status=status.HTTP_201_CREATED,
        )


def _library_course(publication: CoursePublication) -> dict[str, Any]:
    release = publication.current_release
    course = release.snapshot["course"]
    return {
        "course_id": course["id"],
        "slug": course["slug"],
        "title": release.title,
        "summary": release.summary,
        "language_code": release.language_code,
        "estimated_duration_minutes": release.estimated_duration_minutes,
        "module_count": release.module_count,
        "unit_count": release.unit_count,
        "word_count": release.word_count,
        "release_number": release.number,
    }


class LibraryListView(APIView):
    @extend_schema(responses={200: LibraryCourseSerializer(many=True)})
    def get(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        if not can_view_published(request.user, organization):
            raise PermissionDenied("publication_permission_denied")
        payload = [
            _library_course(publication)
            for publication in active_library_publications(
                request.user, organization
            ).order_by("current_release__title")
        ]
        return _no_store(Response(LibraryCourseSerializer(payload, many=True).data))


class LibraryMixin:
    def publication(
        self, request: Request, slug: str, course_slug: str
    ) -> CoursePublication:
        organization = _organization(request, slug)
        if not can_view_published(request.user, organization):
            raise PermissionDenied("publication_permission_denied")
        try:
            return active_library_publication(request.user, organization, course_slug)
        except Http404 as error:
            raise NotFound(
                {"code": "publication_not_found", "detail": "El curso no existe."}
            ) from error


class LibraryDetailView(LibraryMixin, APIView):
    @extend_schema(responses={200: LibraryDetailSerializer})
    def get(self, request: Request, slug: str, course_slug: str) -> Response:
        publication = self.publication(request, slug, course_slug)
        release = publication.current_release
        course = release.snapshot["course"]
        payload = {
            **_library_course(publication),
            "subtitle": course["subtitle"],
            "description": course["description"],
            "subjects": release.snapshot["curriculum"]["subjects"],
            "learning_objectives": release.snapshot["curriculum"][
                "learning_objectives"
            ],
            "outline": release_outline(release.snapshot),
        }
        return _no_store(Response(LibraryDetailSerializer(payload).data))


class LibraryOutlineView(LibraryMixin, APIView):
    @extend_schema(responses={200: ReleaseOutlineSerializer})
    def get(self, request: Request, slug: str, course_slug: str) -> Response:
        release = self.publication(request, slug, course_slug).current_release
        payload = {
            "release_number": release.number,
            "modules": release_outline(release.snapshot),
        }
        return _no_store(Response(ReleaseOutlineSerializer(payload).data))


class LibraryUnitView(LibraryMixin, APIView):
    @extend_schema(responses={200: ReleaseUnitSerializer})
    def get(
        self,
        request: Request,
        slug: str,
        course_slug: str,
        unit_id: str,
    ) -> Response:
        release = self.publication(request, slug, course_slug).current_release
        try:
            unit = release_unit(release.snapshot, str(unit_id))
            navigation = release_previous_next(release.snapshot, str(unit_id))
        except ReleaseSnapshotInvalid as error:
            raise NotFound(
                {"code": "release_not_found", "detail": "La unidad no existe."}
            ) from error
        payload = {
            "release_number": release.number,
            "course": release.snapshot["course"],
            "unit": unit,
            "navigation": navigation,
        }
        return _no_store(Response(ReleaseUnitSerializer(payload).data))
