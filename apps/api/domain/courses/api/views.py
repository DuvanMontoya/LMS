# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportMissingTypeArgument=false, reportAttributeAccessIssue=false, reportCallIssue=false, reportOptionalMemberAccess=false, reportOptionalSubscript=false, reportArgumentType=false, reportIndexIssue=false
from __future__ import annotations

from typing import Any, cast

from django.db.models import OuterRef, Prefetch, QuerySet, Subquery
from django.http import Http404
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from domain.catalog.models import LearningObjective, Subject, Topic
from domain.organizations.models import Organization
from domain.organizations.selectors import organization_visible_to

from ..choices import AuthoringStatus, StructureStatus
from ..exceptions import (
    CourseAccessDenied,
    CourseArchived,
    CourseArchivedCatalogReference,
    CourseCrossOrganizationRelation,
    CourseCurriculumAlignmentInvalid,
    CourseDomainError,
    CourseLimitExceeded,
    CourseOrderInvalid,
    CourseRevisionConflict,
    CourseRevisionNotEditable,
    CourseRevisionNotReady,
    CourseRevisionTransitionInvalid,
    CourseSlugReserved,
    CourseStructureInvalid,
)
from ..models import Course, CourseModule, CourseRevision, CourseUnit
from ..policies import (
    can_manage_course,
    can_view_approved_course,
    can_view_course_authoring,
)
from ..readiness import revision_readiness_issues
from ..selectors import (
    course_outline,
    course_review_history,
    course_visible_to_actor,
    courses_visible_to_actor,
    revision_visible_to_actor,
    revisions_visible_to_actor,
)
from ..services import (
    approve_revision,
    archive_course,
    archive_module,
    archive_unit,
    create_course,
    create_module,
    create_unit,
    replace_module_order,
    replace_revision_learning_objectives,
    replace_revision_subjects,
    replace_unit_learning_objectives,
    replace_unit_order,
    replace_unit_topics,
    request_revision_changes,
    restore_course,
    restore_module,
    restore_unit,
    submit_revision_for_review,
    update_module,
    update_revision_metadata,
    update_unit,
)
from .filters import CourseFilter
from .serializers import (
    CourseCreateSerializer,
    CourseListSerializer,
    CoursePageSerializer,
    CourseSerializer,
    ExpectedVersionSerializer,
    ModuleCreateSerializer,
    ModuleMutationSerializer,
    ModuleSerializer,
    ModuleUpdateSerializer,
    MutationResultSerializer,
    OutlineSerializer,
    ReadinessSerializer,
    ReplaceObjectivesSerializer,
    ReplaceOrderSerializer,
    ReplaceSubjectsSerializer,
    ReplaceTopicsSerializer,
    RequestChangesSerializer,
    RevisionMetadataUpdateSerializer,
    RevisionObjectiveSerializer,
    RevisionSerializer,
    RevisionSubjectSerializer,
    TransitionSerializer,
    UnitCreateSerializer,
    UnitMutationSerializer,
    UnitObjectiveSerializer,
    UnitSerializer,
    UnitTopicSerializer,
    UnitUpdateSerializer,
    WorkflowActionSerializer,
)


class CoursePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def _organization(request: Request, slug: str) -> Organization:
    try:
        return organization_visible_to(request.user, slug)
    except Http404 as error:
        raise NotFound(
            {"code": "course_not_found", "detail": "El curso no existe."}
        ) from error


def _course(request: Request, organization: Organization, course_slug: str):
    try:
        return course_visible_to_actor(request.user, organization, course_slug)
    except Http404 as error:
        raise NotFound(
            {"code": "course_not_found", "detail": "El curso no existe."}
        ) from error


def _revision(request: Request, course: Any, revision_id: str) -> CourseRevision:
    try:
        return revision_visible_to_actor(request.user, course, revision_id)
    except Http404 as error:
        raise NotFound(
            {"code": "revision_not_found", "detail": "La revisión no existe."}
        ) from error


def _require_manage(request: Request, organization: Organization) -> None:
    if not can_manage_course(request.user, organization):
        raise PermissionDenied("course_permission_denied")


def _require_course_view(request: Request, organization: Organization) -> None:
    if not (
        can_view_course_authoring(request.user, organization)
        or can_view_approved_course(request.user, organization)
    ):
        raise PermissionDenied("course_permission_denied")


def _mutation(revision: CourseRevision) -> Response:
    return Response(
        MutationResultSerializer(
            {"revision_id": revision.id, "lock_version": revision.lock_version}
        ).data
    )


def _domain_error(error: CourseDomainError) -> Response:
    if isinstance(error, CourseRevisionConflict):
        return Response(
            {
                "code": "revision_conflict",
                "detail": "La revisión cambió desde que la abriste. Actualiza la información antes de guardar nuevamente.",
            },
            status=status.HTTP_409_CONFLICT,
        )
    if isinstance(error, CourseRevisionNotReady):
        return Response(
            {
                "code": "revision_not_ready",
                "detail": "La revisión todavía tiene problemas de integridad.",
                "issues": error.issues,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    mapping: list[tuple[type[CourseDomainError], str, int]] = [
        (CourseAccessDenied, "course_permission_denied", status.HTTP_403_FORBIDDEN),
        (CourseArchived, "course_archived", status.HTTP_400_BAD_REQUEST),
        (CourseSlugReserved, "course_slug_reserved", status.HTTP_400_BAD_REQUEST),
        (
            CourseRevisionNotEditable,
            "revision_not_editable",
            status.HTTP_400_BAD_REQUEST,
        ),
        (
            CourseRevisionTransitionInvalid,
            "revision_transition_invalid",
            status.HTTP_400_BAD_REQUEST,
        ),
        (CourseOrderInvalid, "order_invalid", status.HTTP_400_BAD_REQUEST),
        (
            CourseCurriculumAlignmentInvalid,
            "curriculum_alignment_invalid",
            status.HTTP_400_BAD_REQUEST,
        ),
        (
            CourseCrossOrganizationRelation,
            "cross_organization_relation",
            status.HTTP_400_BAD_REQUEST,
        ),
        (
            CourseArchivedCatalogReference,
            "archived_catalog_reference",
            status.HTTP_400_BAD_REQUEST,
        ),
        (CourseLimitExceeded, "course_limit_exceeded", status.HTTP_400_BAD_REQUEST),
        (
            CourseStructureInvalid,
            "course_structure_invalid",
            status.HTTP_400_BAD_REQUEST,
        ),
    ]
    for error_type, code, response_status in mapping:
        if isinstance(error, error_type):
            return Response(
                {"code": code, "detail": str(error)}, status=response_status
            )
    return Response(
        {"code": "course_operation_rejected", "detail": "La operación no es válida."},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _scoped_subjects(organization: Organization, ids: list[object]) -> list[Subject]:
    rows = list(
        Subject.objects.filter(
            id__in=ids, discipline__area__organization=organization
        ).select_related("discipline__area")
    )
    if len(rows) != len(set(ids)):
        raise CourseCrossOrganizationRelation(
            "Una asignatura no pertenece a la organización."
        )
    by_id = {row.id: row for row in rows}
    return [by_id[item] for item in ids]


def _scoped_objectives(
    organization: Organization, ids: list[object]
) -> list[LearningObjective]:
    rows = list(
        LearningObjective.objects.filter(
            id__in=ids, subject__discipline__area__organization=organization
        ).select_related("subject__discipline__area")
    )
    if len(rows) != len(set(ids)):
        raise CourseCrossOrganizationRelation(
            "Un objetivo no pertenece a la organización."
        )
    by_id = {row.id: row for row in rows}
    return [by_id[item] for item in ids]


class CourseListCreateView(APIView):
    queryset = Course.objects.none()
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = CourseFilter
    ordering_fields = ("created_at", "title", "updated_at")
    ordering = ("-created_at",)

    @extend_schema(
        operation_id="organizations_courses_list",
        parameters=[
            OpenApiParameter("status", str, OpenApiParameter.QUERY),
            OpenApiParameter("authoring_status", str, OpenApiParameter.QUERY),
            OpenApiParameter("subject", OpenApiTypes.UUID, OpenApiParameter.QUERY),
            OpenApiParameter("search", str, OpenApiParameter.QUERY),
            OpenApiParameter("ordering", str, OpenApiParameter.QUERY),
            OpenApiParameter("page", int, OpenApiParameter.QUERY),
            OpenApiParameter("page_size", int, OpenApiParameter.QUERY),
        ],
        responses={200: CoursePageSerializer},
    )
    def get(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        _require_course_view(request, organization)
        visible_revision_queryset = CourseRevision.objects.filter(
            course_id=OuterRef("pk")
        )
        if not can_view_course_authoring(request.user, organization):
            visible_revision_queryset = visible_revision_queryset.filter(
                authoring_status=AuthoringStatus.APPROVED
            )
        latest_visible = visible_revision_queryset.order_by("-number")
        visible_revisions = CourseRevision.objects.all()
        if not can_view_course_authoring(request.user, organization):
            visible_revisions = visible_revisions.filter(
                authoring_status=AuthoringStatus.APPROVED
            )
        visible_revisions = visible_revisions.prefetch_related(
            "subject_alignments__subject"
        )
        queryset = (
            courses_visible_to_actor(request.user, organization)
            .annotate(
                current_revision_id=Subquery(latest_visible.values("id")[:1]),
                current_authoring_status=Subquery(
                    latest_visible.values("authoring_status")[:1]
                ),
                current_summary=Subquery(latest_visible.values("summary")[:1]),
                title=Subquery(latest_visible.values("title")[:1]),
                updated_at=Subquery(latest_visible.values("updated_at")[:1]),
            )
            .prefetch_related(
                Prefetch(
                    "revisions",
                    queryset=visible_revisions,
                    to_attr="visible_revisions",
                )
            )
        )
        for backend in self.filter_backends:
            queryset = cast(
                QuerySet,
                backend().filter_queryset(request, queryset, self),
            )
        paginator = CoursePagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(
            CourseListSerializer(page, many=True).data
        )

    @extend_schema(request=CourseCreateSerializer, responses={201: RevisionSerializer})
    def post(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        _require_manage(request, organization)
        serializer = CourseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        primary_id = data.pop("primary_subject_id")
        supporting_ids = data.pop("supporting_subject_ids")
        objective_ids = data.pop("learning_objective_ids")
        try:
            primary = _scoped_subjects(organization, [primary_id])[0]
            supporting = _scoped_subjects(organization, supporting_ids)
            objectives = _scoped_objectives(organization, objective_ids)
            revision = create_course(
                actor=request.user,
                organization=organization,
                primary_subject=primary,
                supporting_subjects=supporting,
                learning_objectives=objectives,
                **data,
            )
        except CourseDomainError as error:
            return _domain_error(error)
        return Response(
            RevisionSerializer(revision).data, status=status.HTTP_201_CREATED
        )


class CourseDetailView(APIView):
    @extend_schema(responses={200: CourseSerializer})
    def get(self, request: Request, slug: str, course_slug: str) -> Response:
        organization = _organization(request, slug)
        return Response(
            CourseSerializer(_course(request, organization, course_slug)).data
        )


class CourseActionView(APIView):
    action = ""

    @extend_schema(request=None, responses={200: CourseSerializer})
    def post(self, request: Request, slug: str, course_slug: str) -> Response:
        organization = _organization(request, slug)
        _require_manage(request, organization)
        course = _course(request, organization, course_slug)
        try:
            result = (
                archive_course(
                    actor=request.user, organization=organization, course=course
                )
                if self.action == "archive"
                else restore_course(
                    actor=request.user, organization=organization, course=course
                )
            )
        except CourseDomainError as error:
            return _domain_error(error)
        return Response(CourseSerializer(result).data)


class ArchiveCourseView(CourseActionView):
    action = "archive"


class RestoreCourseView(CourseActionView):
    action = "restore"


class RevisionListView(APIView):
    @extend_schema(responses={200: RevisionSerializer(many=True)})
    def get(self, request: Request, slug: str, course_slug: str) -> Response:
        organization = _organization(request, slug)
        course = _course(request, organization, course_slug)
        return Response(
            RevisionSerializer(
                revisions_visible_to_actor(request.user, course), many=True
            ).data
        )


class RevisionDetailView(APIView):
    @extend_schema(responses={200: RevisionSerializer})
    def get(
        self, request: Request, slug: str, course_slug: str, revision_id: str
    ) -> Response:
        organization = _organization(request, slug)
        course = _course(request, organization, course_slug)
        return Response(
            RevisionSerializer(_revision(request, course, revision_id)).data
        )

    @extend_schema(
        request=RevisionMetadataUpdateSerializer, responses={200: RevisionSerializer}
    )
    def patch(
        self, request: Request, slug: str, course_slug: str, revision_id: str
    ) -> Response:
        organization = _organization(request, slug)
        _require_manage(request, organization)
        course = _course(request, organization, course_slug)
        revision = _revision(request, course, revision_id)
        serializer = RevisionMetadataUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        expected_version = data.pop("expected_version")
        try:
            result = update_revision_metadata(
                actor=request.user,
                organization=organization,
                revision=revision,
                expected_version=expected_version,
                **data,
            )
        except CourseDomainError as error:
            return _domain_error(error)
        return Response(RevisionSerializer(result).data)


class TransitionListView(APIView):
    @extend_schema(responses={200: TransitionSerializer(many=True)})
    def get(
        self, request: Request, slug: str, course_slug: str, revision_id: str
    ) -> Response:
        organization = _organization(request, slug)
        course = _course(request, organization, course_slug)
        return Response(
            TransitionSerializer(
                course_review_history(request.user, course, revision_id), many=True
            ).data
        )


class SubjectAlignmentView(APIView):
    @extend_schema(responses={200: RevisionSubjectSerializer(many=True)})
    def get(
        self, request: Request, slug: str, course_slug: str, revision_id: str
    ) -> Response:
        organization = _organization(request, slug)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        return Response(
            RevisionSubjectSerializer(
                revision.subject_alignments.select_related("subject").order_by(
                    "position"
                ),
                many=True,
            ).data
        )

    @extend_schema(
        request=ReplaceSubjectsSerializer, responses={200: MutationResultSerializer}
    )
    def put(
        self, request: Request, slug: str, course_slug: str, revision_id: str
    ) -> Response:
        organization = _organization(request, slug)
        _require_manage(request, organization)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        serializer = ReplaceSubjectsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            primary = _scoped_subjects(organization, [data["primary_subject_id"]])[0]
            supporting = _scoped_subjects(organization, data["supporting_subject_ids"])
            result = replace_revision_subjects(
                actor=request.user,
                organization=organization,
                revision=revision,
                expected_version=data["expected_version"],
                primary_subject=primary,
                supporting_subjects=supporting,
            )
        except CourseDomainError as error:
            return _domain_error(error)
        return _mutation(result)


class ObjectiveAlignmentView(APIView):
    @extend_schema(responses={200: RevisionObjectiveSerializer(many=True)})
    def get(
        self, request: Request, slug: str, course_slug: str, revision_id: str
    ) -> Response:
        organization = _organization(request, slug)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        return Response(
            RevisionObjectiveSerializer(
                revision.objective_alignments.select_related(
                    "learning_objective__subject"
                ).order_by("position"),
                many=True,
            ).data
        )

    @extend_schema(
        request=ReplaceObjectivesSerializer, responses={200: MutationResultSerializer}
    )
    def put(
        self, request: Request, slug: str, course_slug: str, revision_id: str
    ) -> Response:
        organization = _organization(request, slug)
        _require_manage(request, organization)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        serializer = ReplaceObjectivesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            objectives = _scoped_objectives(
                organization, data["learning_objective_ids"]
            )
            result = replace_revision_learning_objectives(
                actor=request.user,
                organization=organization,
                revision=revision,
                expected_version=data["expected_version"],
                learning_objectives=objectives,
            )
        except CourseDomainError as error:
            return _domain_error(error)
        return _mutation(result)


def _module(
    revision: CourseRevision, module_id: str, *, include_archived: bool = True
) -> CourseModule:
    queryset = CourseModule.objects.filter(revision=revision)
    if not include_archived:
        queryset = queryset.filter(status=StructureStatus.ACTIVE)
    try:
        return get_object_or_404(queryset, pk=module_id)
    except Http404 as error:
        raise NotFound(
            {"code": "module_not_found", "detail": "El módulo no existe."}
        ) from error


def _unit(revision: CourseRevision, unit_id: str) -> CourseUnit:
    try:
        return get_object_or_404(
            CourseUnit.objects.select_related("module"),
            pk=unit_id,
            module__revision=revision,
        )
    except Http404 as error:
        raise NotFound(
            {"code": "unit_not_found", "detail": "La unidad no existe."}
        ) from error


class ModuleListCreateView(APIView):
    @extend_schema(responses={200: ModuleSerializer(many=True)})
    def get(
        self, request: Request, slug: str, course_slug: str, revision_id: str
    ) -> Response:
        organization = _organization(request, slug)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        return Response(
            ModuleSerializer(
                revision.modules.all().order_by("position", "created_at"), many=True
            ).data
        )

    @extend_schema(
        request=ModuleCreateSerializer, responses={201: ModuleMutationSerializer}
    )
    def post(
        self, request: Request, slug: str, course_slug: str, revision_id: str
    ) -> Response:
        organization = _organization(request, slug)
        _require_manage(request, organization)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        serializer = ModuleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        expected_version = data.pop("expected_version")
        try:
            module, locked = create_module(
                actor=request.user,
                organization=organization,
                revision=revision,
                expected_version=expected_version,
                **data,
            )
        except CourseDomainError as error:
            return _domain_error(error)
        payload = ModuleSerializer(module).data
        payload["revision_id"] = locked.id
        payload["lock_version"] = locked.lock_version
        return Response(payload, status=status.HTTP_201_CREATED)


class ModuleOrderView(APIView):
    @extend_schema(
        request=ReplaceOrderSerializer, responses={200: MutationResultSerializer}
    )
    def put(
        self, request: Request, slug: str, course_slug: str, revision_id: str
    ) -> Response:
        organization = _organization(request, slug)
        _require_manage(request, organization)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        serializer = ReplaceOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = replace_module_order(
                actor=request.user,
                organization=organization,
                revision=revision,
                **serializer.validated_data,
            )
        except CourseDomainError as error:
            return _domain_error(error)
        return _mutation(result)


class ModuleDetailView(APIView):
    @extend_schema(responses={200: ModuleSerializer})
    def get(
        self,
        request: Request,
        slug: str,
        course_slug: str,
        revision_id: str,
        module_id: str,
    ) -> Response:
        organization = _organization(request, slug)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        return Response(ModuleSerializer(_module(revision, module_id)).data)

    @extend_schema(
        request=ModuleUpdateSerializer, responses={200: ModuleMutationSerializer}
    )
    def patch(
        self,
        request: Request,
        slug: str,
        course_slug: str,
        revision_id: str,
        module_id: str,
    ) -> Response:
        organization = _organization(request, slug)
        _require_manage(request, organization)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        serializer = ModuleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        expected_version = data.pop("expected_version")
        try:
            module, locked = update_module(
                actor=request.user,
                organization=organization,
                module=_module(revision, module_id),
                expected_version=expected_version,
                **data,
            )
        except CourseDomainError as error:
            return _domain_error(error)
        payload = ModuleSerializer(module).data
        payload["lock_version"] = locked.lock_version
        return Response(payload)


class ModuleActionView(APIView):
    action = ""

    @extend_schema(
        request=ExpectedVersionSerializer, responses={200: ModuleMutationSerializer}
    )
    def post(
        self,
        request: Request,
        slug: str,
        course_slug: str,
        revision_id: str,
        module_id: str,
    ) -> Response:
        organization = _organization(request, slug)
        _require_manage(request, organization)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        serializer = ExpectedVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            module, locked = (
                archive_module(
                    actor=request.user,
                    organization=organization,
                    module=_module(revision, module_id),
                    **serializer.validated_data,
                )
                if self.action == "archive"
                else restore_module(
                    actor=request.user,
                    organization=organization,
                    module=_module(revision, module_id),
                    **serializer.validated_data,
                )
            )
        except CourseDomainError as error:
            return _domain_error(error)
        payload = ModuleSerializer(module).data
        payload["lock_version"] = locked.lock_version
        return Response(payload)


class ArchiveModuleView(ModuleActionView):
    action = "archive"


class RestoreModuleView(ModuleActionView):
    action = "restore"


class UnitListCreateView(APIView):
    @extend_schema(responses={200: UnitSerializer(many=True)})
    def get(
        self,
        request: Request,
        slug: str,
        course_slug: str,
        revision_id: str,
        module_id: str,
    ) -> Response:
        organization = _organization(request, slug)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        return Response(
            UnitSerializer(
                _module(revision, module_id)
                .units.all()
                .order_by("position", "created_at"),
                many=True,
            ).data
        )

    @extend_schema(
        request=UnitCreateSerializer, responses={201: UnitMutationSerializer}
    )
    def post(
        self,
        request: Request,
        slug: str,
        course_slug: str,
        revision_id: str,
        module_id: str,
    ) -> Response:
        organization = _organization(request, slug)
        _require_manage(request, organization)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        serializer = UnitCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        expected_version = data.pop("expected_version")
        try:
            unit, locked = create_unit(
                actor=request.user,
                organization=organization,
                module=_module(revision, module_id, include_archived=False),
                expected_version=expected_version,
                **data,
            )
        except CourseDomainError as error:
            return _domain_error(error)
        payload = UnitSerializer(unit).data
        payload["lock_version"] = locked.lock_version
        return Response(payload, status=status.HTTP_201_CREATED)


class UnitOrderView(APIView):
    @extend_schema(
        request=ReplaceOrderSerializer, responses={200: MutationResultSerializer}
    )
    def put(
        self,
        request: Request,
        slug: str,
        course_slug: str,
        revision_id: str,
        module_id: str,
    ) -> Response:
        organization = _organization(request, slug)
        _require_manage(request, organization)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        serializer = ReplaceOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = replace_unit_order(
                actor=request.user,
                organization=organization,
                module=_module(revision, module_id, include_archived=False),
                **serializer.validated_data,
            )
        except CourseDomainError as error:
            return _domain_error(error)
        return _mutation(result)


class UnitDetailView(APIView):
    @extend_schema(responses={200: UnitSerializer})
    def get(
        self,
        request: Request,
        slug: str,
        course_slug: str,
        revision_id: str,
        unit_id: str,
    ) -> Response:
        organization = _organization(request, slug)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        return Response(UnitSerializer(_unit(revision, unit_id)).data)

    @extend_schema(
        request=UnitUpdateSerializer, responses={200: UnitMutationSerializer}
    )
    def patch(
        self,
        request: Request,
        slug: str,
        course_slug: str,
        revision_id: str,
        unit_id: str,
    ) -> Response:
        organization = _organization(request, slug)
        _require_manage(request, organization)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        serializer = UnitUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        expected_version = data.pop("expected_version")
        try:
            unit, locked = update_unit(
                actor=request.user,
                organization=organization,
                unit=_unit(revision, unit_id),
                expected_version=expected_version,
                **data,
            )
        except CourseDomainError as error:
            return _domain_error(error)
        payload = UnitSerializer(unit).data
        payload["lock_version"] = locked.lock_version
        return Response(payload)


class UnitActionView(APIView):
    action = ""

    @extend_schema(
        request=ExpectedVersionSerializer, responses={200: UnitMutationSerializer}
    )
    def post(
        self,
        request: Request,
        slug: str,
        course_slug: str,
        revision_id: str,
        unit_id: str,
    ) -> Response:
        organization = _organization(request, slug)
        _require_manage(request, organization)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        serializer = ExpectedVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            unit, locked = (
                archive_unit(
                    actor=request.user,
                    organization=organization,
                    unit=_unit(revision, unit_id),
                    **serializer.validated_data,
                )
                if self.action == "archive"
                else restore_unit(
                    actor=request.user,
                    organization=organization,
                    unit=_unit(revision, unit_id),
                    **serializer.validated_data,
                )
            )
        except CourseDomainError as error:
            return _domain_error(error)
        payload = UnitSerializer(unit).data
        payload["lock_version"] = locked.lock_version
        return Response(payload)


class ArchiveUnitView(UnitActionView):
    action = "archive"


class RestoreUnitView(UnitActionView):
    action = "restore"


class UnitTopicView(APIView):
    @extend_schema(responses={200: UnitTopicSerializer(many=True)})
    def get(
        self,
        request: Request,
        slug: str,
        course_slug: str,
        revision_id: str,
        unit_id: str,
    ) -> Response:
        organization = _organization(request, slug)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        return Response(
            UnitTopicSerializer(
                _unit(revision, unit_id).topic_alignments.select_related(
                    "topic__subject"
                ),
                many=True,
            ).data
        )

    @extend_schema(
        request=ReplaceTopicsSerializer, responses={200: MutationResultSerializer}
    )
    def put(
        self,
        request: Request,
        slug: str,
        course_slug: str,
        revision_id: str,
        unit_id: str,
    ) -> Response:
        organization = _organization(request, slug)
        _require_manage(request, organization)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        serializer = ReplaceTopicsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        topics = list(
            Topic.objects.filter(
                id__in=data["topic_ids"],
                subject__discipline__area__organization=organization,
            ).select_related("subject__discipline__area")
        )
        if len(topics) != len(set(data["topic_ids"])):
            return _domain_error(
                CourseCrossOrganizationRelation(
                    "Un tema no pertenece a la organización."
                )
            )
        by_id = {item.id: item for item in topics}
        try:
            result = replace_unit_topics(
                actor=request.user,
                organization=organization,
                unit=_unit(revision, unit_id),
                expected_version=data["expected_version"],
                topics=[by_id[item] for item in data["topic_ids"]],
            )
        except CourseDomainError as error:
            return _domain_error(error)
        return _mutation(result)


class UnitObjectiveView(APIView):
    @extend_schema(responses={200: UnitObjectiveSerializer(many=True)})
    def get(
        self,
        request: Request,
        slug: str,
        course_slug: str,
        revision_id: str,
        unit_id: str,
    ) -> Response:
        organization = _organization(request, slug)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        return Response(
            UnitObjectiveSerializer(
                _unit(revision, unit_id).objective_alignments.select_related(
                    "learning_objective__subject"
                ),
                many=True,
            ).data
        )

    @extend_schema(
        request=ReplaceObjectivesSerializer, responses={200: MutationResultSerializer}
    )
    def put(
        self,
        request: Request,
        slug: str,
        course_slug: str,
        revision_id: str,
        unit_id: str,
    ) -> Response:
        organization = _organization(request, slug)
        _require_manage(request, organization)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        serializer = ReplaceObjectivesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            result = replace_unit_learning_objectives(
                actor=request.user,
                organization=organization,
                unit=_unit(revision, unit_id),
                expected_version=data["expected_version"],
                learning_objectives=_scoped_objectives(
                    organization, data["learning_objective_ids"]
                ),
            )
        except CourseDomainError as error:
            return _domain_error(error)
        return _mutation(result)


class OutlineView(APIView):
    @extend_schema(responses={200: OutlineSerializer})
    def get(
        self, request: Request, slug: str, course_slug: str, revision_id: str
    ) -> Response:
        organization = _organization(request, slug)
        course = _course(request, organization, course_slug)
        return Response(
            OutlineSerializer(course_outline(request.user, course, revision_id)).data
        )


class ReadinessView(APIView):
    @extend_schema(responses={200: ReadinessSerializer})
    def get(
        self, request: Request, slug: str, course_slug: str, revision_id: str
    ) -> Response:
        organization = _organization(request, slug)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        issues = revision_readiness_issues(revision)
        return Response(
            ReadinessSerializer({"ready": not issues, "issues": issues}).data
        )


class WorkflowView(APIView):
    action = ""

    @extend_schema(
        request=WorkflowActionSerializer, responses={200: RevisionSerializer}
    )
    def post(
        self, request: Request, slug: str, course_slug: str, revision_id: str
    ) -> Response:
        organization = _organization(request, slug)
        course = _course(request, organization, course_slug)
        revision = _revision(request, course, revision_id)
        serializer_class = (
            RequestChangesSerializer
            if self.action == "request_changes"
            else WorkflowActionSerializer
        )
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            if self.action == "submit":
                result = submit_revision_for_review(
                    actor=request.user,
                    organization=organization,
                    revision=revision,
                    **data,
                )
            elif self.action == "request_changes":
                result = request_revision_changes(
                    actor=request.user,
                    organization=organization,
                    revision=revision,
                    **data,
                )
            else:
                result = approve_revision(
                    actor=request.user,
                    organization=organization,
                    revision=revision,
                    **data,
                )
        except CourseDomainError as error:
            return _domain_error(error)
        return Response(RevisionSerializer(result).data)


class SubmitReviewView(WorkflowView):
    action = "submit"


class RequestChangesView(WorkflowView):
    action = "request_changes"


class ApproveRevisionView(WorkflowView):
    action = "approve"
