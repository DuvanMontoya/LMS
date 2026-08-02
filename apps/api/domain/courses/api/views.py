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
from domain.organizations.capabilities import Capability
from domain.organizations.models import Membership, Organization
from domain.organizations.policies import has_capability
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
from ..models import (
    Course,
    CourseActivity,
    CourseModule,
    CourseRevision,
    CourseTeachingException,
    CourseUnit,
)
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
    AvailabilityRuleInput,
    GradeCategoryInput,
    GradedActivityInput,
    approve_revision,
    archive_course,
    archive_module,
    archive_unit,
    assign_course_teaching_exception,
    close_course_teaching_exception,
    confirm_completion_policy,
    create_activity,
    create_course,
    create_module,
    create_unit,
    replace_activity_availability_rules,
    replace_activity_learning_objectives,
    replace_activity_order,
    replace_grading_scheme,
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
    AssignCourseTeachingExceptionSerializer,
    CloseCourseTeachingExceptionSerializer,
    ConfirmCompletionPolicySerializer,
    CourseActivityCreateSerializer,
    CourseActivityMutationSerializer,
    CourseActivitySerializer,
    CourseCompletionPolicySerializer,
    CourseCreateSerializer,
    CourseListSerializer,
    CoursePageSerializer,
    CourseSerializer,
    CourseTeachingExceptionSerializer,
    ExpectedVersionSerializer,
    GradeCategorySerializer,
    GradingSchemeResponseSerializer,
    ModuleCreateSerializer,
    ModuleMutationSerializer,
    ModuleSerializer,
    ModuleUpdateSerializer,
    MutationResultSerializer,
    OutlineSerializer,
    ReadinessSerializer,
    ReplaceActivityRulesSerializer,
    ReplaceGradingSchemeSerializer,
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


def _can_manage_teaching_exceptions(
    request: Request, organization: Organization
) -> bool:
    return has_capability(
        request.user,
        organization,
        Capability.CATALOG_TEACHING_RESPONSIBILITY_MANAGE,
    )


class CourseTeachingExceptionListCreateView(APIView):
    @extend_schema(responses={200: CourseTeachingExceptionSerializer(many=True)})
    def get(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        if not (
            has_capability(request.user, organization, Capability.CATALOG_VIEW)
            or has_capability(
                request.user,
                organization,
                Capability.CATALOG_TEACHING_RESPONSIBILITY_VIEW,
            )
        ):
            raise PermissionDenied("course_permission_denied")
        queryset = CourseTeachingException.objects.filter(
            course__organization=organization
        ).select_related("course", "membership__user")
        if not _can_manage_teaching_exceptions(request, organization):
            queryset = queryset.filter(membership__user=request.user)
        return Response(CourseTeachingExceptionSerializer(queryset, many=True).data)

    @extend_schema(
        request=AssignCourseTeachingExceptionSerializer,
        responses={201: CourseTeachingExceptionSerializer},
    )
    def post(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        serializer = AssignCourseTeachingExceptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        course = get_object_or_404(
            Course, pk=data["course_id"], organization=organization
        )
        membership = get_object_or_404(
            Membership, pk=data["membership_id"], organization=organization
        )
        try:
            exception = assign_course_teaching_exception(
                actor=request.user,
                organization=organization,
                course=course,
                membership=membership,
                starts_on=data["starts_on"],
                ends_on=data.get("ends_on"),
                rationale=data["rationale"],
            )
        except CourseDomainError as error:
            return _domain_error(error)
        return Response(
            CourseTeachingExceptionSerializer(exception).data,
            status=status.HTTP_201_CREATED,
        )


class CloseCourseTeachingExceptionView(APIView):
    @extend_schema(
        request=CloseCourseTeachingExceptionSerializer,
        responses={200: CourseTeachingExceptionSerializer},
    )
    def post(self, request: Request, slug: str, exception_id: str) -> Response:
        organization = _organization(request, slug)
        serializer = CloseCourseTeachingExceptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        exception = get_object_or_404(
            CourseTeachingException,
            pk=exception_id,
            course__organization=organization,
        )
        try:
            result = close_course_teaching_exception(
                actor=request.user,
                exception=exception,
                ended_on=serializer.validated_data["ended_on"],
            )
        except CourseDomainError as error:
            return _domain_error(error)
        return Response(CourseTeachingExceptionSerializer(result).data)


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


def _activity(revision: CourseRevision, activity_id: str) -> CourseActivity:
    try:
        return get_object_or_404(
            CourseActivity.objects.select_related(
                "module", "lesson_unit"
            ).prefetch_related(
                "objective_alignments__learning_objective",
                "availability_rules__prerequisite_activity",
                "availability_rules__learning_objective",
            ),
            pk=activity_id,
            module__revision=revision,
        )
    except Http404 as error:
        raise NotFound(
            {"code": "activity_not_found", "detail": "La actividad no existe."}
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


class ActivityListCreateView(APIView):
    @extend_schema(responses={200: CourseActivitySerializer(many=True)})
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
        activities = (
            _module(revision, module_id)
            .activities.select_related("lesson_unit")
            .prefetch_related(
                "objective_alignments__learning_objective",
                "availability_rules__prerequisite_activity",
                "availability_rules__learning_objective",
            )
            .order_by("position", "created_at")
        )
        return Response(CourseActivitySerializer(activities, many=True).data)

    @extend_schema(
        request=CourseActivityCreateSerializer,
        responses={201: CourseActivityMutationSerializer},
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
        serializer = CourseActivityCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        expected_version = data.pop("expected_version")
        try:
            activity, locked = create_activity(
                actor=request.user,
                organization=organization,
                module=_module(revision, module_id, include_archived=False),
                expected_version=expected_version,
                **data,
            )
        except CourseDomainError as error:
            return _domain_error(error)
        payload = CourseActivitySerializer(activity).data
        payload["lock_version"] = locked.lock_version
        return Response(payload, status=status.HTTP_201_CREATED)


class ActivityOrderView(APIView):
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
            result = replace_activity_order(
                actor=request.user,
                organization=organization,
                module=_module(revision, module_id, include_archived=False),
                **serializer.validated_data,
            )
        except CourseDomainError as error:
            return _domain_error(error)
        return _mutation(result)


class ActivityDetailView(APIView):
    @extend_schema(responses={200: CourseActivitySerializer})
    def get(
        self,
        request: Request,
        slug: str,
        course_slug: str,
        revision_id: str,
        activity_id: str,
    ) -> Response:
        organization = _organization(request, slug)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        return Response(CourseActivitySerializer(_activity(revision, activity_id)).data)


class ActivityObjectiveView(APIView):
    @extend_schema(
        request=ReplaceObjectivesSerializer, responses={200: MutationResultSerializer}
    )
    def put(
        self,
        request: Request,
        slug: str,
        course_slug: str,
        revision_id: str,
        activity_id: str,
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
            result = replace_activity_learning_objectives(
                actor=request.user,
                organization=organization,
                activity=_activity(revision, activity_id),
                expected_version=data["expected_version"],
                learning_objectives=_scoped_objectives(
                    organization, data["learning_objective_ids"]
                ),
            )
        except CourseDomainError as error:
            return _domain_error(error)
        return _mutation(result)


class ActivityAvailabilityRulesView(APIView):
    @extend_schema(
        request=ReplaceActivityRulesSerializer,
        responses={200: MutationResultSerializer},
    )
    def put(
        self,
        request: Request,
        slug: str,
        course_slug: str,
        revision_id: str,
        activity_id: str,
    ) -> Response:
        organization = _organization(request, slug)
        _require_manage(request, organization)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        serializer = ReplaceActivityRulesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        prerequisite_ids = {
            row["prerequisite_activity_id"]
            for row in data["rules"]
            if row.get("prerequisite_activity_id")
        }
        objective_ids = {
            row["learning_objective_id"]
            for row in data["rules"]
            if row.get("learning_objective_id")
        }
        prerequisites = {
            row.id: row
            for row in CourseActivity.objects.filter(
                id__in=prerequisite_ids, module__revision=revision
            ).select_related("module__revision")
        }
        if len(prerequisites) != len(prerequisite_ids):
            return _domain_error(
                CourseCrossOrganizationRelation(
                    "Una actividad requerida no pertenece a la revisión."
                )
            )
        objectives = {
            row.id: row for row in _scoped_objectives(organization, list(objective_ids))
        }
        rules = [
            AvailabilityRuleInput(
                rule_type=row["rule_type"],
                prerequisite_activity=prerequisites.get(
                    row.get("prerequisite_activity_id")
                ),
                learning_objective=objectives.get(row.get("learning_objective_id")),
                threshold_basis_points=row.get("threshold_basis_points"),
                available_at=row.get("available_at"),
            )
            for row in data["rules"]
        ]
        try:
            result = replace_activity_availability_rules(
                actor=request.user,
                organization=organization,
                activity=_activity(revision, activity_id),
                expected_version=data["expected_version"],
                rules=rules,
            )
        except CourseDomainError as error:
            return _domain_error(error)
        return _mutation(result)


class CompletionPolicyView(APIView):
    @extend_schema(responses={200: CourseCompletionPolicySerializer})
    def get(
        self, request: Request, slug: str, course_slug: str, revision_id: str
    ) -> Response:
        organization = _organization(request, slug)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        return Response(
            CourseCompletionPolicySerializer(revision.completion_policy).data
        )

    @extend_schema(
        request=ConfirmCompletionPolicySerializer,
        responses={200: CourseCompletionPolicySerializer},
    )
    def put(
        self, request: Request, slug: str, course_slug: str, revision_id: str
    ) -> Response:
        organization = _organization(request, slug)
        _require_manage(request, organization)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        serializer = ConfirmCompletionPolicySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            policy, locked = confirm_completion_policy(
                actor=request.user,
                organization=organization,
                revision=revision,
                **serializer.validated_data,
            )
        except CourseDomainError as error:
            return _domain_error(error)
        payload = CourseCompletionPolicySerializer(policy).data
        payload["revision_id"] = locked.id
        payload["revision_lock_version"] = locked.lock_version
        return Response(payload)


class GradingSchemeView(APIView):
    @extend_schema(responses={200: GradeCategorySerializer(many=True)})
    def get(
        self, request: Request, slug: str, course_slug: str, revision_id: str
    ) -> Response:
        organization = _organization(request, slug)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        categories = revision.grade_categories.prefetch_related(
            "graded_activities"
        ).all()
        return Response(GradeCategorySerializer(categories, many=True).data)

    @extend_schema(
        request=ReplaceGradingSchemeSerializer,
        responses={200: GradingSchemeResponseSerializer},
    )
    def put(
        self, request: Request, slug: str, course_slug: str, revision_id: str
    ) -> Response:
        organization = _organization(request, slug)
        _require_manage(request, organization)
        revision = _revision(
            request, _course(request, organization, course_slug), revision_id
        )
        serializer = ReplaceGradingSchemeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category_rows = serializer.validated_data["categories"]
        activity_ids = {
            item["activity_id"]
            for category in category_rows
            for item in category["activities"]
        }
        activities = {
            activity.id: activity
            for activity in CourseActivity.objects.filter(
                module__revision=revision, id__in=activity_ids
            ).select_related("module__revision")
        }
        if len(activities) != len(activity_ids):
            return _domain_error(
                CourseCrossOrganizationRelation(
                    "Una evaluación no pertenece a la revisión."
                )
            )
        categories = [
            GradeCategoryInput(
                code=category["code"],
                title=category["title"],
                weight_basis_points=category["weight_basis_points"],
                activities=[
                    GradedActivityInput(
                        activity=activities[item["activity_id"]],
                        weight_basis_points=item["weight_basis_points"],
                        required=item["required"],
                    )
                    for item in category["activities"]
                ],
            )
            for category in category_rows
        ]
        try:
            created, locked = replace_grading_scheme(
                actor=request.user,
                organization=organization,
                revision=revision,
                expected_version=serializer.validated_data["expected_version"],
                categories=categories,
            )
        except CourseDomainError as error:
            return _domain_error(error)
        loaded = revision.grade_categories.filter(
            id__in=[row.id for row in created]
        ).prefetch_related("graded_activities")
        payload = {
            "categories": GradeCategorySerializer(loaded, many=True).data,
            "revision_id": locked.id,
            "revision_lock_version": locked.lock_version,
        }
        return Response(payload)


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
