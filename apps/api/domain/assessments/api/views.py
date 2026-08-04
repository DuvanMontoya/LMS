# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportCallIssue=false, reportOptionalMemberAccess=false, reportOptionalSubscript=false, reportArgumentType=false, reportIndexIssue=false, reportGeneralTypeIssues=false, reportUnknownLambdaType=false
from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response as ApiResponse
from rest_framework.views import APIView

from domain.catalog.models import LearningObjective
from domain.courses.models import CourseActivity, CourseModule
from domain.learning.models import (
    CourseGroupActivity,
    EnrollmentCohortAssignment,
    EnrollmentReleaseAssignment,
    LearningCohort,
)
from domain.learning.policies import (
    can_manage_course_group,
    has_institutional_learning_scope,
)
from domain.organizations.models import Organization
from domain.organizations.selectors import organization_visible_to
from domain.publishing.models import CourseRelease

from ..assets import assessment_asset_descriptors, question_asset_descriptors
from ..choices import AuthoringStatus, LifecycleStatus, ResponseStatus
from ..course_activities import (
    bind_assessment_activity,
    create_and_bind_assessment_activity,
)
from ..exceptions import AssessmentDomainError
from ..models import (
    Assessment,
    AssessmentDelivery,
    AssessmentItem,
    AssessmentRevision,
    AssessmentSection,
    AssessmentVersion,
    Attempt,
    AttemptItem,
    DeliveryAssignment,
    Question,
    QuestionBank,
    QuestionRevision,
    QuestionVersion,
)
from ..policies import (
    can_approve_authoring,
    can_approve_questions,
    can_grade_manually,
    can_manage_authoring,
    can_manage_banks,
    can_manage_deliveries,
    can_manage_questions,
    can_review_authoring,
    can_review_questions,
    can_submit_authoring,
    can_submit_questions,
    can_version_banks,
    can_view_authoring,
    can_view_banks,
    can_view_deliveries,
    can_view_questions,
    can_view_results,
)
from ..selectors import (
    assessments_for,
    attempts_for_results,
    deliveries_for,
    learner_assignments,
    learner_attempts,
    question_banks_for,
    responses_for_manual_grading,
)
from ..services import (
    activate_delivery,
    add_assessment_item,
    add_assessment_section,
    archive_question_bank,
    assessment_readiness,
    assign_delivery_batch,
    create_assessment,
    create_assessment_revision_from_version,
    create_delivery,
    create_question,
    create_question_bank,
    create_question_bank_version,
    create_question_revision_from_version,
    grade_response_manually,
    materialize_course_group_assessments,
    reorder_assessment_items,
    reorder_assessment_sections,
    replace_assessment_objectives,
    revoke_delivery_assignment,
    save_response,
    start_attempt,
    submit_attempt,
    transition_assessment_revision,
    transition_question_revision,
    update_assessment_item,
    update_assessment_revision,
    update_assessment_section,
    update_question_bank,
    update_question_revision,
    withdraw_delivery,
)
from .filters import AssessmentFilter, DeliveryFilter, QuestionBankFilter
from .serializers import (
    ApprovedQuestionVersionOptionSerializer,
    AssessmentActivityBindingInputSerializer,
    AssessmentActivityBindingSerializer,
    AssessmentAssetAccessResponseSerializer,
    AssessmentAssetAccessSerializer,
    AssessmentCourseActivityCreateSerializer,
    AssessmentCreateSerializer,
    AssessmentExpectedVersionSerializer,
    AssessmentOutlineSerializer,
    AssessmentPageSerializer,
    AssessmentReadinessSerializer,
    AssessmentRevisionSerializer,
    AssessmentRevisionUpdateSerializer,
    AssessmentSerializer,
    AssessmentTransitionInputSerializer,
    AssessmentVersionSerializer,
    AssignmentCreateSerializer,
    AttemptResultPageSerializer,
    AttemptResultSerializer,
    AttemptSerializer,
    CohortAssignmentCreateSerializer,
    DeliveryAssignmentSerializer,
    DeliveryCreateSerializer,
    DeliveryPageSerializer,
    DeliverySerializer,
    ItemCreateSerializer,
    ItemSerializer,
    ItemUpdateSerializer,
    LearnerDeliverySerializer,
    ManualGradeDecisionSerializer,
    ManualGradeSerializer,
    MaterializeCourseGroupAssessmentsResultSerializer,
    ObjectiveReplaceSerializer,
    OrderedIdsSerializer,
    PendingManualSerializer,
    QuestionBankCreateSerializer,
    QuestionBankPageSerializer,
    QuestionBankSerializer,
    QuestionBankUpdateSerializer,
    QuestionBankVersionSerializer,
    QuestionCreateSerializer,
    QuestionPageSerializer,
    QuestionPreviewSerializer,
    QuestionRevisionSerializer,
    QuestionRevisionUpdateSerializer,
    QuestionSerializer,
    QuestionVersionSerializer,
    ResponseSaveSerializer,
    SectionCreateSerializer,
    SectionSerializer,
    SectionUpdateSerializer,
    VersionSourceSerializer,
    WithdrawalSerializer,
)


class AssessmentPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


def _organization(request: Request, slug: str) -> Organization:
    return organization_visible_to(request.user, slug)


def _delivery_visible_to(
    *, actor: object, organization: Organization, delivery_id: str
) -> AssessmentDelivery:
    return get_object_or_404(deliveries_for(organization, actor=actor), pk=delivery_id)


def _domain_error(error: AssessmentDomainError) -> ApiResponse:
    payload: dict[str, object] = {"code": error.code, "detail": error.message}
    if error.path:
        payload["path"] = error.path
    return ApiResponse(payload, status=error.status_code)


class AssessmentActivityBindingView(APIView):
    @extend_schema(
        operation_id="assessment_course_activity_binding_create",
        request=AssessmentActivityBindingInputSerializer,
        responses={201: AssessmentActivityBindingSerializer},
    )
    def post(self, request: Request, slug: str, activity_id: UUID) -> ApiResponse:
        organization = _organization(request, slug)
        serializer = AssessmentActivityBindingInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        activity = get_object_or_404(
            CourseActivity.objects.select_related("module__revision__course"),
            pk=activity_id,
            module__revision__course__organization=organization,
        )
        assessment_version = get_object_or_404(
            AssessmentVersion.objects.select_related("assessment"),
            pk=serializer.validated_data["assessment_version_id"],
            assessment__organization=organization,
        )
        result = _call(
            lambda: bind_assessment_activity(
                actor=request.user,
                organization=organization,
                activity=activity,
                assessment_version=assessment_version,
                expected_revision_version=serializer.validated_data[
                    "expected_revision_version"
                ],
            )
        )
        if isinstance(result, ApiResponse):
            return result
        binding, revision_lock_version = result
        return ApiResponse(
            AssessmentActivityBindingSerializer(
                {
                    "id": binding.id,
                    "activity_id": binding.activity_id,
                    "assessment_version_id": binding.assessment_version_id,
                    "revision_lock_version": revision_lock_version,
                }
            ).data,
            status=status.HTTP_201_CREATED,
        )


class AssessmentCourseActivityCreateView(APIView):
    @extend_schema(
        operation_id="assessment_course_activity_create",
        request=AssessmentCourseActivityCreateSerializer,
        responses={201: AssessmentActivityBindingSerializer},
    )
    def post(self, request: Request, slug: str) -> ApiResponse:
        organization = _organization(request, slug)
        serializer = AssessmentCourseActivityCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        module = get_object_or_404(
            CourseModule.objects.select_related("revision__course"),
            pk=serializer.validated_data["module_id"],
            revision__course__organization=organization,
        )
        assessment_version = get_object_or_404(
            AssessmentVersion.objects.select_related("assessment"),
            pk=serializer.validated_data["assessment_version_id"],
            assessment__organization=organization,
        )
        result = _call(
            lambda: create_and_bind_assessment_activity(
                actor=request.user,
                organization=organization,
                module=module,
                assessment_version=assessment_version,
                expected_revision_version=serializer.validated_data[
                    "expected_revision_version"
                ],
                required=serializer.validated_data["required"],
            )
        )
        if isinstance(result, ApiResponse):
            return result
        binding, activity, revision_lock_version = result
        return ApiResponse(
            AssessmentActivityBindingSerializer(
                {
                    "id": binding.id,
                    "activity_id": activity.id,
                    "assessment_version_id": binding.assessment_version_id,
                    "revision_lock_version": revision_lock_version,
                }
            ).data,
            status=status.HTTP_201_CREATED,
        )


def _call(operation: Callable[[], Any]) -> ApiResponse | Any:
    try:
        return operation()
    except AssessmentDomainError as error:
        return _domain_error(error)


def _paginate(
    request: Request, queryset: Any, serializer: type[Any], view: APIView
) -> ApiResponse:
    paginator = AssessmentPagination()
    page = paginator.paginate_queryset(queryset, request, view=view)
    return paginator.get_paginated_response(serializer(page, many=True).data)


def _require(check: bool) -> None:
    if not check:
        raise PermissionDenied("assessment_permission_denied")


def _bank(organization: Organization, bank_id: str) -> QuestionBank:
    lookup = Q(slug=bank_id)
    try:
        lookup |= Q(pk=UUID(bank_id))
    except ValueError:
        pass
    return get_object_or_404(QuestionBank, lookup, organization=organization)


def _question(organization: Organization, bank_id: str, question_id: str) -> Question:
    bank = _bank(organization, bank_id)
    return get_object_or_404(
        Question,
        pk=question_id,
        bank=bank,
    )


def _assessment(organization: Organization, assessment_slug: str) -> Assessment:
    return get_object_or_404(
        Assessment, organization=organization, slug=assessment_slug
    )


def _revision(assessment: Assessment, revision_id: str) -> AssessmentRevision:
    return get_object_or_404(AssessmentRevision, pk=revision_id, assessment=assessment)


class QuestionBankListCreateView(APIView):
    @extend_schema(
        operation_id="assessment_question_banks_list",
        responses=QuestionBankPageSerializer,
    )
    def get(self, request: Request, slug: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_banks(request.user, organization))
        queryset = QuestionBankFilter(
            request.query_params, question_banks_for(organization)
        ).qs
        return _paginate(request, queryset, QuestionBankSerializer, self)

    @extend_schema(
        operation_id="assessment_question_banks_create",
        request=QuestionBankCreateSerializer,
        responses={201: QuestionBankSerializer},
    )
    def post(self, request: Request, slug: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_banks(request.user, organization))
        serializer = QuestionBankCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _call(
            lambda: create_question_bank(
                actor=request.user,
                organization=organization,
                **serializer.validated_data,
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(
            QuestionBankSerializer(result).data, status=status.HTTP_201_CREATED
        )


class QuestionBankDetailView(APIView):
    @extend_schema(
        operation_id="assessment_question_bank_retrieve",
        responses=QuestionBankSerializer,
    )
    def get(self, request: Request, slug: str, bank_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_banks(request.user, organization))
        return ApiResponse(QuestionBankSerializer(_bank(organization, bank_id)).data)

    @extend_schema(
        operation_id="assessment_question_bank_update",
        request=QuestionBankUpdateSerializer,
        responses=QuestionBankSerializer,
    )
    def patch(self, request: Request, slug: str, bank_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_banks(request.user, organization))
        serializer = QuestionBankUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _call(
            lambda: update_question_bank(
                actor=request.user,
                bank=_bank(organization, bank_id),
                **serializer.validated_data,
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(QuestionBankSerializer(result).data)


class QuestionBankArchiveView(APIView):
    @extend_schema(
        operation_id="assessment_question_bank_archive",
        request=AssessmentExpectedVersionSerializer,
        responses=QuestionBankSerializer,
    )
    def post(self, request: Request, slug: str, bank_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_banks(request.user, organization))
        serializer = AssessmentExpectedVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _call(
            lambda: archive_question_bank(
                actor=request.user,
                bank=_bank(organization, bank_id),
                expected_version=serializer.validated_data["expected_version"],
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(QuestionBankSerializer(result).data)


class QuestionListCreateView(APIView):
    @extend_schema(
        operation_id="assessment_questions_list",
        parameters=[
            OpenApiParameter("page", int, OpenApiParameter.QUERY),
            OpenApiParameter("page_size", int, OpenApiParameter.QUERY),
        ],
        responses=QuestionPageSerializer,
    )
    def get(self, request: Request, slug: str, bank_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_questions(request.user, organization))
        bank = _bank(organization, bank_id)
        queryset = bank.questions.prefetch_related(
            Prefetch(
                "revisions",
                queryset=QuestionRevision.objects.exclude(status="approved").order_by(
                    "-number"
                ),
                to_attr="_assessment_open_revisions",
            ),
            Prefetch(
                "versions",
                queryset=QuestionVersion.objects.order_by("-number"),
                to_attr="_assessment_versions",
            ),
        ).order_by("code", "id")
        return _paginate(request, queryset, QuestionSerializer, self)

    @extend_schema(
        operation_id="assessment_questions_create",
        request=QuestionCreateSerializer,
        responses={201: QuestionRevisionSerializer},
    )
    def post(self, request: Request, slug: str, bank_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_questions(request.user, organization))
        serializer = QuestionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = _call(
            lambda: create_question(
                actor=request.user,
                bank=_bank(organization, bank_id),
                code=data["code"],
                question_type=data["type"],
                definition=data["definition"],
            )
        )
        if isinstance(result, ApiResponse):
            return result
        _, revision = result
        return ApiResponse(
            QuestionRevisionSerializer(revision).data,
            status=status.HTTP_201_CREATED,
        )


class QuestionDetailView(APIView):
    @extend_schema(
        operation_id="assessment_question_retrieve",
        responses=QuestionSerializer,
    )
    def get(
        self, request: Request, slug: str, bank_id: str, question_id: str
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_questions(request.user, organization))
        return ApiResponse(
            QuestionSerializer(_question(organization, bank_id, question_id)).data
        )


class QuestionPreviewView(APIView):
    @extend_schema(
        operation_id="assessment_question_preview",
        responses=QuestionPreviewSerializer,
    )
    def get(
        self, request: Request, slug: str, bank_id: str, question_id: str
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_questions(request.user, organization))
        question = _question(organization, bank_id, question_id)
        revision = (
            question.revisions.exclude(status="approved").order_by("-number").first()
        )
        version = None if revision else question.versions.order_by("-number").first()
        source = revision or version
        if source is None:
            return ApiResponse(
                {
                    "code": "question_preview_unavailable",
                    "detail": "La pregunta todavía no tiene contenido para previsualizar.",
                },
                status=status.HTTP_409_CONFLICT,
            )
        public = source.definition.get("public") if revision else version.public
        if not isinstance(public, dict):
            return ApiResponse(
                {
                    "code": "question_preview_invalid",
                    "detail": "La vista pública de la pregunta no es válida.",
                },
                status=status.HTTP_409_CONFLICT,
            )
        payload = {
            "assets": question_asset_descriptors(
                question=question,
                public=public,
            ),
            "code": question.code,
            "public": public,
            "type": source.type,
        }
        return ApiResponse(QuestionPreviewSerializer(payload).data)


class QuestionRevisionDetailView(APIView):
    def _get(
        self,
        request: Request,
        organization: Organization,
        bank_id: str,
        question_id: str,
        revision_id: str,
    ) -> QuestionRevision:
        question = _question(organization, bank_id, question_id)
        return get_object_or_404(QuestionRevision, pk=revision_id, question=question)

    @extend_schema(
        operation_id="assessment_question_revision_retrieve",
        responses=QuestionRevisionSerializer,
    )
    def get(
        self,
        request: Request,
        slug: str,
        bank_id: str,
        question_id: str,
        revision_id: str,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_questions(request.user, organization))
        return ApiResponse(
            QuestionRevisionSerializer(
                self._get(request, organization, bank_id, question_id, revision_id)
            ).data
        )

    @extend_schema(
        operation_id="assessment_question_revision_update",
        request=QuestionRevisionUpdateSerializer,
        responses=QuestionRevisionSerializer,
    )
    def patch(
        self,
        request: Request,
        slug: str,
        bank_id: str,
        question_id: str,
        revision_id: str,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_questions(request.user, organization))
        serializer = QuestionRevisionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        revision = self._get(request, organization, bank_id, question_id, revision_id)
        result = _call(
            lambda: update_question_revision(
                actor=request.user,
                revision=revision,
                expected_version=serializer.validated_data["expected_version"],
                definition=serializer.validated_data["definition"],
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(QuestionRevisionSerializer(result).data)


class QuestionRevisionActionView(APIView):
    target_status = ""

    @extend_schema(
        operation_id="assessment_question_revision_transition",
        request=AssessmentTransitionInputSerializer,
        responses=QuestionRevisionSerializer,
    )
    def post(
        self,
        request: Request,
        slug: str,
        bank_id: str,
        question_id: str,
        revision_id: str,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        if self.target_status == "in_review":
            allowed = can_submit_questions(request.user, organization)
        elif self.target_status == "changes_requested":
            allowed = can_review_questions(request.user, organization)
        else:
            allowed = can_approve_questions(request.user, organization)
        _require(allowed)
        serializer = AssessmentTransitionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        revision = get_object_or_404(
            QuestionRevision,
            pk=revision_id,
            question=_question(organization, bank_id, question_id),
        )
        result = _call(
            lambda: transition_question_revision(
                actor=request.user,
                revision=revision,
                expected_version=serializer.validated_data["expected_version"],
                to_status=self.target_status,
                note=serializer.validated_data.get("note", ""),
            )
        )
        if isinstance(result, ApiResponse):
            return result
        transitioned, _ = result
        return ApiResponse(QuestionRevisionSerializer(transitioned).data)


@extend_schema_view(
    post=extend_schema(operation_id="assessment_question_revision_submit")
)
class SubmitQuestionRevisionView(QuestionRevisionActionView):
    target_status = AuthoringStatus.IN_REVIEW


@extend_schema_view(
    post=extend_schema(operation_id="assessment_question_revision_submit_alias")
)
class SubmitQuestionRevisionAliasView(SubmitQuestionRevisionView):
    pass


@extend_schema_view(
    post=extend_schema(operation_id="assessment_question_revision_request_changes")
)
class RequestQuestionChangesView(QuestionRevisionActionView):
    target_status = AuthoringStatus.CHANGES_REQUESTED


@extend_schema_view(
    post=extend_schema(operation_id="assessment_question_revision_approve")
)
class ApproveQuestionRevisionView(QuestionRevisionActionView):
    target_status = AuthoringStatus.APPROVED


class QuestionVersionListView(APIView):
    @extend_schema(
        operation_id="assessment_question_versions_list",
        responses=QuestionVersionSerializer(many=True),
    )
    def get(
        self, request: Request, slug: str, bank_id: str, question_id: str
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_questions(request.user, organization))
        question = _question(organization, bank_id, question_id)
        return ApiResponse(
            QuestionVersionSerializer(question.versions.all(), many=True).data
        )


class ApprovedQuestionVersionOptionsView(APIView):
    @extend_schema(
        operation_id="assessment_approved_question_version_options_list",
        responses=ApprovedQuestionVersionOptionSerializer(many=True),
    )
    def get(self, request: Request, slug: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_questions(request.user, organization))
        versions = (
            QuestionVersion.objects.filter(
                question__bank__organization=organization,
                question__bank__status=LifecycleStatus.ACTIVE,
                question__status=LifecycleStatus.ACTIVE,
            )
            .select_related("question__bank")
            .annotate(
                usage_count=Count("assessment_items", distinct=True)
                + Count("pool_candidates", distinct=True)
            )
            .order_by("question__bank__name", "question__code", "number")
        )
        return ApiResponse(
            ApprovedQuestionVersionOptionSerializer(versions, many=True).data
        )

    @extend_schema(
        operation_id="assessment_question_revision_create_from_version",
        request=VersionSourceSerializer,
        responses={201: QuestionRevisionSerializer},
    )
    def post(
        self,
        request: Request,
        slug: str,
        bank_id: str,
        question_id: str,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_questions(request.user, organization))
        question = _question(organization, bank_id, question_id)
        serializer = VersionSourceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        version = get_object_or_404(
            QuestionVersion,
            pk=serializer.validated_data["version_id"],
            question=question,
        )
        result = _call(
            lambda: create_question_revision_from_version(
                actor=request.user, version=version
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(
            QuestionRevisionSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )


class QuestionVersionDetailView(APIView):
    def _version(
        self,
        organization: Organization,
        bank_id: str,
        question_id: str,
        version_number: int,
    ) -> QuestionVersion:
        return get_object_or_404(
            QuestionVersion,
            question=_question(organization, bank_id, question_id),
            number=version_number,
        )

    @extend_schema(
        operation_id="assessment_question_version_retrieve",
        responses=QuestionVersionSerializer,
    )
    def get(
        self,
        request: Request,
        slug: str,
        bank_id: str,
        question_id: str,
        version_number: int,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_questions(request.user, organization))
        version = self._version(organization, bank_id, question_id, version_number)
        return ApiResponse(QuestionVersionSerializer(version).data)


class QuestionVersionCreateDraftView(QuestionVersionDetailView):
    http_method_names = ["post"]

    @extend_schema(
        operation_id="assessment_question_revision_create_from_selected_version",
        request=None,
        responses={201: QuestionRevisionSerializer},
    )
    def post(
        self,
        request: Request,
        slug: str,
        bank_id: str,
        question_id: str,
        version_number: int,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_questions(request.user, organization))
        version = self._version(organization, bank_id, question_id, version_number)
        result = _call(
            lambda: create_question_revision_from_version(
                actor=request.user, version=version
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(
            QuestionRevisionSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )


class QuestionBankVersionListCreateView(APIView):
    @extend_schema(
        operation_id="assessment_question_bank_versions_list",
        responses=QuestionBankVersionSerializer(many=True),
    )
    def get(self, request: Request, slug: str, bank_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_banks(request.user, organization))
        bank = _bank(organization, bank_id)
        return ApiResponse(
            QuestionBankVersionSerializer(bank.versions.all(), many=True).data
        )

    @extend_schema(
        operation_id="assessment_question_bank_versions_create",
        request=None,
        responses={201: QuestionBankVersionSerializer},
    )
    def post(self, request: Request, slug: str, bank_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_version_banks(request.user, organization))
        result = _call(
            lambda: create_question_bank_version(
                actor=request.user, bank=_bank(organization, bank_id)
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(
            QuestionBankVersionSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )


class QuestionBankVersionDetailView(APIView):
    @extend_schema(
        operation_id="assessment_question_bank_version_retrieve",
        responses=QuestionBankVersionSerializer,
    )
    def get(
        self,
        request: Request,
        slug: str,
        bank_id: str,
        version_number: int,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_banks(request.user, organization))
        version = get_object_or_404(
            _bank(organization, bank_id).versions,
            number=version_number,
        )
        return ApiResponse(QuestionBankVersionSerializer(version).data)


class AssessmentListCreateView(APIView):
    @extend_schema(
        operation_id="assessments_list",
        responses=AssessmentPageSerializer,
    )
    def get(self, request: Request, slug: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_authoring(request.user, organization))
        queryset = (
            AssessmentFilter(request.query_params, assessments_for(organization))
            .qs.distinct()
            .prefetch_related(
                Prefetch(
                    "revisions",
                    queryset=AssessmentRevision.objects.order_by("-number"),
                    to_attr="_latest_revisions",
                ),
                Prefetch(
                    "versions",
                    queryset=AssessmentVersion.objects.order_by("-number"),
                    to_attr="_latest_versions",
                ),
            )
        )
        return _paginate(request, queryset, AssessmentSerializer, self)

    @extend_schema(
        operation_id="assessments_create",
        request=AssessmentCreateSerializer,
        responses={201: AssessmentRevisionSerializer},
    )
    def post(self, request: Request, slug: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_authoring(request.user, organization))
        serializer = AssessmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _call(
            lambda: create_assessment(
                actor=request.user,
                organization=organization,
                **serializer.validated_data,
            )
        )
        if isinstance(result, ApiResponse):
            return result
        _, revision = result
        return ApiResponse(
            AssessmentRevisionSerializer(revision).data,
            status=status.HTTP_201_CREATED,
        )


class ApprovedAssessmentVersionOptionsView(APIView):
    @extend_schema(responses=AssessmentVersionSerializer(many=True))
    def get(self, request: Request, slug: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_deliveries(request.user, organization))
        versions = AssessmentVersion.objects.filter(
            assessment__organization=organization
        )
        if not has_institutional_learning_scope(request.user, organization):
            assigned_version_values = CourseGroupActivity.objects.filter(
                course_group__organization=organization,
                course_group__staff_assignments__membership__user=request.user,
                course_group__staff_assignments__membership__status="active",
                course_group__staff_assignments__ended_at__isnull=True,
                activity_type="assessment",
                binding_snapshot__assessment_version_id__isnull=False,
            ).values_list("binding_snapshot__assessment_version_id", flat=True)
            assigned_version_ids: list[UUID] = []
            for value in assigned_version_values:
                try:
                    assigned_version_ids.append(UUID(str(value)))
                except (TypeError, ValueError):
                    continue
            versions = versions.filter(pk__in=assigned_version_ids)
        versions = versions.order_by("title", "-number")
        return ApiResponse(AssessmentVersionSerializer(versions, many=True).data)


class AssessmentDetailView(APIView):
    @extend_schema(operation_id="assessments_retrieve", responses=AssessmentSerializer)
    def get(self, request: Request, slug: str, assessment_slug: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_authoring(request.user, organization))
        return ApiResponse(
            AssessmentSerializer(_assessment(organization, assessment_slug)).data
        )


class AssessmentRevisionDetailView(APIView):
    @extend_schema(
        operation_id="assessment_revision_retrieve",
        responses=AssessmentRevisionSerializer,
    )
    def get(
        self,
        request: Request,
        slug: str,
        assessment_slug: str,
        revision_id: str,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_authoring(request.user, organization))
        revision = _revision(_assessment(organization, assessment_slug), revision_id)
        return ApiResponse(AssessmentRevisionSerializer(revision).data)

    @extend_schema(
        operation_id="assessment_revision_update",
        request=AssessmentRevisionUpdateSerializer,
        responses=AssessmentRevisionSerializer,
    )
    def patch(
        self,
        request: Request,
        slug: str,
        assessment_slug: str,
        revision_id: str,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_authoring(request.user, organization))
        revision = _revision(_assessment(organization, assessment_slug), revision_id)
        serializer = AssessmentRevisionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        expected_version = values.pop("expected_version")
        result = _call(
            lambda: update_assessment_revision(
                actor=request.user,
                revision=revision,
                expected_version=expected_version,
                values=values,
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(AssessmentRevisionSerializer(result).data)


class AssessmentObjectivesView(APIView):
    @extend_schema(
        operation_id="assessment_revision_objectives_replace",
        request=ObjectiveReplaceSerializer,
        responses=AssessmentRevisionSerializer,
    )
    def put(
        self,
        request: Request,
        slug: str,
        assessment_slug: str,
        revision_id: str,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_authoring(request.user, organization))
        revision = _revision(_assessment(organization, assessment_slug), revision_id)
        serializer = ObjectiveReplaceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        objective_ids = serializer.validated_data["objective_ids"]
        objectives = list(
            LearningObjective.objects.filter(
                id__in=objective_ids,
                subject__discipline__area__organization=organization,
            )
        )
        if len(objectives) != len(set(objective_ids)):
            return ApiResponse(
                {
                    "code": "assessment_invalid",
                    "detail": "Uno o más objetivos no existen en la organización.",
                },
                status=400,
            )
        result = _call(
            lambda: replace_assessment_objectives(
                actor=request.user,
                revision=revision,
                expected_version=serializer.validated_data["expected_version"],
                objectives=objectives,
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(AssessmentRevisionSerializer(result).data)


class AssessmentOutlineView(APIView):
    @extend_schema(
        operation_id="assessment_revision_outline",
        responses=AssessmentOutlineSerializer,
    )
    def get(
        self,
        request: Request,
        slug: str,
        assessment_slug: str,
        revision_id: str,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_authoring(request.user, organization))
        revision = _revision(_assessment(organization, assessment_slug), revision_id)
        sections = revision.sections.prefetch_related(
            "items__question_version__question", "items__objective_links"
        ).all()
        return ApiResponse(
            {
                "revision": AssessmentRevisionSerializer(revision).data,
                "objective_ids": [
                    str(item)
                    for item in revision.objective_links.values_list(
                        "objective_id", flat=True
                    )
                ],
                "sections": [
                    {
                        **SectionSerializer(section).data,
                        "items": ItemSerializer(section.items.all(), many=True).data,
                    }
                    for section in sections
                ],
            }
        )


class AssessmentReadinessView(APIView):
    @extend_schema(
        operation_id="assessment_revision_readiness",
        responses=AssessmentReadinessSerializer,
    )
    def get(
        self,
        request: Request,
        slug: str,
        assessment_slug: str,
        revision_id: str,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_authoring(request.user, organization))
        revision = _revision(_assessment(organization, assessment_slug), revision_id)
        issues = assessment_readiness(revision)
        return ApiResponse({"ready": not issues, "issues": issues})


class SectionListCreateView(APIView):
    @extend_schema(
        operation_id="assessment_sections_list",
        responses=SectionSerializer(many=True),
    )
    def get(
        self,
        request: Request,
        slug: str,
        assessment_slug: str,
        revision_id: str,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_authoring(request.user, organization))
        revision = _revision(_assessment(organization, assessment_slug), revision_id)
        return ApiResponse(SectionSerializer(revision.sections.all(), many=True).data)

    @extend_schema(
        operation_id="assessment_sections_create",
        request=SectionCreateSerializer,
        responses={201: SectionSerializer},
    )
    def post(
        self,
        request: Request,
        slug: str,
        assessment_slug: str,
        revision_id: str,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_authoring(request.user, organization))
        revision = _revision(_assessment(organization, assessment_slug), revision_id)
        serializer = SectionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _call(
            lambda: add_assessment_section(
                actor=request.user,
                revision=revision,
                expected_version=serializer.validated_data["expected_version"],
                title=serializer.validated_data["title"],
                instructions=serializer.validated_data.get("instructions", ""),
            )
        )
        if isinstance(result, ApiResponse):
            return result
        _, section = result
        return ApiResponse(
            SectionSerializer(section).data, status=status.HTTP_201_CREATED
        )


class SectionOrderView(APIView):
    @extend_schema(
        operation_id="assessment_sections_reorder",
        request=OrderedIdsSerializer,
        responses=AssessmentRevisionSerializer,
    )
    def put(
        self,
        request: Request,
        slug: str,
        assessment_slug: str,
        revision_id: str,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_authoring(request.user, organization))
        revision = _revision(_assessment(organization, assessment_slug), revision_id)
        serializer = OrderedIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _call(
            lambda: reorder_assessment_sections(
                actor=request.user,
                revision=revision,
                expected_version=serializer.validated_data["expected_version"],
                section_ids=serializer.validated_data["ids"],
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(AssessmentRevisionSerializer(result).data)


class SectionDetailView(APIView):
    @extend_schema(
        operation_id="assessment_section_retrieve", responses=SectionSerializer
    )
    def get(
        self,
        request: Request,
        slug: str,
        assessment_slug: str,
        revision_id: str,
        section_id: str,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_authoring(request.user, organization))
        revision = _revision(_assessment(organization, assessment_slug), revision_id)
        section = get_object_or_404(AssessmentSection, pk=section_id, revision=revision)
        return ApiResponse(SectionSerializer(section).data)

    @extend_schema(
        operation_id="assessment_section_update",
        request=SectionUpdateSerializer,
        responses=SectionSerializer,
    )
    def patch(
        self,
        request: Request,
        slug: str,
        assessment_slug: str,
        revision_id: str,
        section_id: str,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_authoring(request.user, organization))
        revision = _revision(_assessment(organization, assessment_slug), revision_id)
        section = get_object_or_404(AssessmentSection, pk=section_id, revision=revision)
        serializer = SectionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _call(
            lambda: update_assessment_section(
                actor=request.user,
                revision=revision,
                section=section,
                expected_version=serializer.validated_data["expected_version"],
                title=serializer.validated_data["title"],
                instructions=serializer.validated_data["instructions"],
            )
        )
        if isinstance(result, ApiResponse):
            return result
        _, updated = result
        return ApiResponse(SectionSerializer(updated).data)


class ItemListCreateView(APIView):
    @extend_schema(
        operation_id="assessment_items_create",
        request=ItemCreateSerializer,
        responses={201: ItemSerializer},
    )
    def post(
        self,
        request: Request,
        slug: str,
        assessment_slug: str,
        revision_id: str,
        section_id: str,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_authoring(request.user, organization))
        revision = _revision(_assessment(organization, assessment_slug), revision_id)
        section = get_object_or_404(AssessmentSection, pk=section_id, revision=revision)
        serializer = ItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        question_version = get_object_or_404(
            QuestionVersion,
            pk=data["question_version_id"],
            question__bank__organization=organization,
        )
        objectives = list(
            LearningObjective.objects.filter(
                id__in=data["objective_ids"],
                subject__discipline__area__organization=organization,
            )
        )
        if len(objectives) != len(set(data["objective_ids"])):
            return ApiResponse(
                {
                    "code": "assessment_invalid",
                    "detail": "Uno o más objetivos no existen.",
                },
                status=400,
            )
        result = _call(
            lambda: add_assessment_item(
                actor=request.user,
                revision=revision,
                expected_version=data["expected_version"],
                section=section,
                question_version=question_version,
                points=data["points"],
                required=data["required"],
                objectives=objectives,
            )
        )
        if isinstance(result, ApiResponse):
            return result
        _, item = result
        return ApiResponse(ItemSerializer(item).data, status=status.HTTP_201_CREATED)


class ItemOrderView(APIView):
    @extend_schema(
        operation_id="assessment_items_reorder",
        request=OrderedIdsSerializer,
        responses=AssessmentRevisionSerializer,
    )
    def put(
        self,
        request: Request,
        slug: str,
        assessment_slug: str,
        revision_id: str,
        section_id: str,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_authoring(request.user, organization))
        revision = _revision(_assessment(organization, assessment_slug), revision_id)
        section = get_object_or_404(AssessmentSection, pk=section_id, revision=revision)
        serializer = OrderedIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _call(
            lambda: reorder_assessment_items(
                actor=request.user,
                revision=revision,
                section=section,
                expected_version=serializer.validated_data["expected_version"],
                item_ids=serializer.validated_data["ids"],
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(AssessmentRevisionSerializer(result).data)


class ItemDetailView(APIView):
    @extend_schema(operation_id="assessment_item_retrieve", responses=ItemSerializer)
    def get(
        self,
        request: Request,
        slug: str,
        assessment_slug: str,
        revision_id: str,
        section_id: str,
        item_id: str,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_authoring(request.user, organization))
        revision = _revision(_assessment(organization, assessment_slug), revision_id)
        item = get_object_or_404(
            AssessmentItem,
            pk=item_id,
            section_id=section_id,
            section__revision=revision,
        )
        return ApiResponse(ItemSerializer(item).data)

    @extend_schema(
        operation_id="assessment_item_update",
        request=ItemUpdateSerializer,
        responses=ItemSerializer,
    )
    def patch(
        self,
        request: Request,
        slug: str,
        assessment_slug: str,
        revision_id: str,
        section_id: str,
        item_id: str,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_authoring(request.user, organization))
        revision = _revision(_assessment(organization, assessment_slug), revision_id)
        item = get_object_or_404(
            AssessmentItem,
            pk=item_id,
            section_id=section_id,
            section__revision=revision,
        )
        serializer = ItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        objectives = list(
            LearningObjective.objects.filter(
                id__in=data["objective_ids"],
                subject__discipline__area__organization=organization,
            )
        )
        if len(objectives) != len(set(data["objective_ids"])):
            return ApiResponse(
                {
                    "code": "assessment_invalid",
                    "detail": "Uno o más objetivos no existen.",
                },
                status=400,
            )
        result = _call(
            lambda: update_assessment_item(
                actor=request.user,
                revision=revision,
                item=item,
                expected_version=data["expected_version"],
                points=data["points"],
                required=data["required"],
                objectives=objectives,
            )
        )
        if isinstance(result, ApiResponse):
            return result
        _, updated = result
        return ApiResponse(ItemSerializer(updated).data)


class AssessmentRevisionActionView(APIView):
    target_status = ""

    @extend_schema(
        operation_id="assessment_revision_transition",
        request=AssessmentTransitionInputSerializer,
        responses=AssessmentRevisionSerializer,
    )
    def post(
        self,
        request: Request,
        slug: str,
        assessment_slug: str,
        revision_id: str,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        if self.target_status == "in_review":
            allowed = can_submit_authoring(request.user, organization)
        elif self.target_status == "changes_requested":
            allowed = can_review_authoring(request.user, organization)
        else:
            allowed = can_approve_authoring(request.user, organization)
        _require(allowed)
        revision = _revision(_assessment(organization, assessment_slug), revision_id)
        serializer = AssessmentTransitionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _call(
            lambda: transition_assessment_revision(
                actor=request.user,
                revision=revision,
                expected_version=serializer.validated_data["expected_version"],
                to_status=self.target_status,
                note=serializer.validated_data.get("note", ""),
            )
        )
        if isinstance(result, ApiResponse):
            return result
        transitioned, _ = result
        return ApiResponse(AssessmentRevisionSerializer(transitioned).data)


@extend_schema_view(post=extend_schema(operation_id="assessment_revision_submit"))
class SubmitAssessmentRevisionView(AssessmentRevisionActionView):
    target_status = AuthoringStatus.IN_REVIEW


@extend_schema_view(post=extend_schema(operation_id="assessment_revision_submit_alias"))
class SubmitAssessmentRevisionAliasView(SubmitAssessmentRevisionView):
    pass


@extend_schema_view(
    post=extend_schema(operation_id="assessment_revision_request_changes")
)
class RequestAssessmentChangesView(AssessmentRevisionActionView):
    target_status = AuthoringStatus.CHANGES_REQUESTED


@extend_schema_view(post=extend_schema(operation_id="assessment_revision_approve"))
class ApproveAssessmentRevisionView(AssessmentRevisionActionView):
    target_status = AuthoringStatus.APPROVED


class AssessmentVersionListView(APIView):
    @extend_schema(
        operation_id="assessment_versions_list",
        responses=AssessmentVersionSerializer(many=True),
    )
    def get(self, request: Request, slug: str, assessment_slug: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_authoring(request.user, organization))
        assessment = _assessment(organization, assessment_slug)
        return ApiResponse(
            AssessmentVersionSerializer(assessment.versions.all(), many=True).data
        )

    @extend_schema(
        operation_id="assessment_revision_create_from_version",
        request=VersionSourceSerializer,
        responses={201: AssessmentRevisionSerializer},
    )
    def post(self, request: Request, slug: str, assessment_slug: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_authoring(request.user, organization))
        assessment = _assessment(organization, assessment_slug)
        serializer = VersionSourceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        version = get_object_or_404(
            AssessmentVersion,
            pk=serializer.validated_data["version_id"],
            assessment=assessment,
        )
        result = _call(
            lambda: create_assessment_revision_from_version(
                actor=request.user, version=version
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(
            AssessmentRevisionSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )


class AssessmentVersionDetailView(APIView):
    def _version(
        self,
        organization: Organization,
        assessment_slug: str,
        version_number: int,
    ) -> AssessmentVersion:
        return get_object_or_404(
            AssessmentVersion,
            assessment=_assessment(organization, assessment_slug),
            number=version_number,
        )

    @extend_schema(
        operation_id="assessment_version_retrieve",
        responses=AssessmentVersionSerializer,
    )
    def get(
        self,
        request: Request,
        slug: str,
        assessment_slug: str,
        version_number: int,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_authoring(request.user, organization))
        return ApiResponse(
            AssessmentVersionSerializer(
                self._version(organization, assessment_slug, version_number)
            ).data
        )


class AssessmentVersionCreateDraftView(AssessmentVersionDetailView):
    http_method_names = ["post"]

    @extend_schema(
        operation_id="assessment_revision_create_from_selected_version",
        request=None,
        responses={201: AssessmentRevisionSerializer},
    )
    def post(
        self,
        request: Request,
        slug: str,
        assessment_slug: str,
        version_number: int,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_authoring(request.user, organization))
        version = self._version(organization, assessment_slug, version_number)
        result = _call(
            lambda: create_assessment_revision_from_version(
                actor=request.user, version=version
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(
            AssessmentRevisionSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )


class CourseGroupAssessmentMaterializationView(APIView):
    @extend_schema(
        operation_id="assessment_course_group_deliveries_materialize",
        request=None,
        responses={200: MaterializeCourseGroupAssessmentsResultSerializer},
    )
    def post(self, request: Request, slug: str, course_group_id: UUID) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_deliveries(request.user, organization))
        course_group = get_object_or_404(
            LearningCohort.objects.select_related("course", "release"),
            pk=course_group_id,
            organization=organization,
        )
        _require(can_manage_course_group(request.user, course_group))
        result = _call(
            lambda: materialize_course_group_assessments(
                actor=request.user,
                organization=organization,
                course_group=course_group,
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(
            MaterializeCourseGroupAssessmentsResultSerializer(result).data
        )


class DeliveryListCreateView(APIView):
    @extend_schema(
        operation_id="assessment_deliveries_list",
        responses=DeliveryPageSerializer,
    )
    def get(self, request: Request, slug: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_deliveries(request.user, organization))
        queryset = DeliveryFilter(
            request.query_params,
            deliveries_for(organization, actor=request.user),
        ).qs
        return _paginate(request, queryset, DeliverySerializer, self)

    @extend_schema(
        operation_id="assessment_deliveries_create",
        request=DeliveryCreateSerializer,
        responses={201: DeliverySerializer},
    )
    def post(self, request: Request, slug: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_deliveries(request.user, organization))
        serializer = DeliveryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        version = get_object_or_404(
            AssessmentVersion,
            pk=data["assessment_version_id"],
            assessment__organization=organization,
        )
        release = None
        if data.get("course_release_id"):
            release = get_object_or_404(
                CourseRelease,
                pk=data["course_release_id"],
                course__organization=organization,
            )
        group_activity = None
        if data.get("course_group_activity_id"):
            group_activity = get_object_or_404(
                CourseGroupActivity.objects.select_related(
                    "course_group__organization", "course_release"
                ),
                pk=data["course_group_activity_id"],
                course_group__organization=organization,
                migration_review_required=False,
            )
            _require(can_manage_course_group(request.user, group_activity.course_group))
            if release is None:
                release = group_activity.course_release
        result = _call(
            lambda: create_delivery(
                actor=request.user,
                organization=organization,
                assessment_version=version,
                name=data["name"],
                course_release=release,
                course_group_activity=group_activity,
                opens_at=data.get("opens_at"),
                closes_at=data.get("closes_at"),
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(
            DeliverySerializer(result).data, status=status.HTTP_201_CREATED
        )


class DeliveryDetailView(APIView):
    @extend_schema(
        operation_id="assessment_delivery_retrieve", responses=DeliverySerializer
    )
    def get(self, request: Request, slug: str, delivery_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_deliveries(request.user, organization))
        delivery = _delivery_visible_to(
            actor=request.user, organization=organization, delivery_id=delivery_id
        )
        return ApiResponse(DeliverySerializer(delivery).data)


class DeliveryLifecycleView(APIView):
    action = ""

    @extend_schema(
        operation_id="assessment_delivery_lifecycle",
        request=WithdrawalSerializer,
        responses=DeliverySerializer,
    )
    def post(self, request: Request, slug: str, delivery_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_deliveries(request.user, organization))
        delivery = _delivery_visible_to(
            actor=request.user, organization=organization, delivery_id=delivery_id
        )
        serializer_class = (
            WithdrawalSerializer
            if self.action == "withdraw"
            else AssessmentExpectedVersionSerializer
        )
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        if self.action == "withdraw":

            def operation() -> AssessmentDelivery:
                return withdraw_delivery(
                    actor=request.user,
                    delivery=delivery,
                    expected_version=serializer.validated_data["expected_version"],
                    note=serializer.validated_data["note"],
                )
        else:

            def operation() -> AssessmentDelivery:
                return activate_delivery(
                    actor=request.user,
                    delivery=delivery,
                    expected_version=serializer.validated_data["expected_version"],
                )

        result = _call(operation)
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(DeliverySerializer(result).data)


@extend_schema_view(
    post=extend_schema(
        operation_id="assessment_delivery_activate",
        request=AssessmentExpectedVersionSerializer,
    )
)
class ActivateDeliveryView(DeliveryLifecycleView):
    action = "activate"


@extend_schema_view(
    post=extend_schema(
        operation_id="assessment_delivery_withdraw",
        request=WithdrawalSerializer,
    )
)
class WithdrawDeliveryView(DeliveryLifecycleView):
    action = "withdraw"


class DeliveryAssignmentListCreateView(APIView):
    @extend_schema(
        operation_id="assessment_delivery_assignments_list",
        responses=DeliveryAssignmentSerializer(many=True),
    )
    def get(self, request: Request, slug: str, delivery_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_deliveries(request.user, organization))
        delivery = _delivery_visible_to(
            actor=request.user, organization=organization, delivery_id=delivery_id
        )
        return ApiResponse(
            DeliveryAssignmentSerializer(
                delivery.assignments.select_related(
                    "release_assignment__release",
                    "release_assignment__enrollment__membership__user",
                ),
                many=True,
            ).data
        )

    @extend_schema(
        operation_id="assessment_delivery_assignments_create",
        request=AssignmentCreateSerializer,
        responses={201: DeliveryAssignmentSerializer},
    )
    def post(self, request: Request, slug: str, delivery_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_deliveries(request.user, organization))
        delivery = _delivery_visible_to(
            actor=request.user, organization=organization, delivery_id=delivery_id
        )
        serializer = AssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data: Any = serializer.validated_data
        requested_ids = data.get("release_assignment_ids")
        if requested_ids is None:
            requested_ids = [data["release_assignment_id"]]
        release_assignments = list(
            EnrollmentReleaseAssignment.objects.filter(
                pk__in=requested_ids,
                enrollment__organization=organization,
            )
        )
        if len(release_assignments) != len(set(requested_ids)):
            return ApiResponse(
                {
                    "code": "assessment_invalid",
                    "detail": "Una o más asignaciones de release no existen.",
                },
                status=400,
            )
        result = _call(
            lambda: assign_delivery_batch(
                actor=request.user,
                delivery=delivery,
                release_assignments=release_assignments,
            )
        )
        if isinstance(result, ApiResponse):
            return result
        serialized = DeliveryAssignmentSerializer(result, many=True).data
        payload = (
            serialized
            if data.get("release_assignment_ids") is not None
            else serialized[0]
        )
        return ApiResponse(
            payload,
            status=status.HTTP_201_CREATED,
        )


class AssignDeliveryCohortView(APIView):
    @extend_schema(
        operation_id="assessment_delivery_assign_cohort",
        request=CohortAssignmentCreateSerializer,
        responses={201: DeliveryAssignmentSerializer(many=True)},
    )
    def post(self, request: Request, slug: str, delivery_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_deliveries(request.user, organization))
        delivery = _delivery_visible_to(
            actor=request.user, organization=organization, delivery_id=delivery_id
        )
        serializer = CohortAssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cohort = get_object_or_404(
            LearningCohort,
            pk=serializer.validated_data["cohort_id"],
            organization=organization,
        )
        _require(can_manage_course_group(request.user, cohort))
        current_ids = EnrollmentCohortAssignment.objects.filter(
            cohort=cohort,
            ended_at__isnull=True,
            enrollment__current_release_assignment__isnull=False,
        ).values_list("enrollment__current_release_assignment_id", flat=True)
        assignments = list(
            EnrollmentReleaseAssignment.objects.filter(pk__in=current_ids)
        )
        result = _call(
            lambda: assign_delivery_batch(
                actor=request.user,
                delivery=delivery,
                release_assignments=assignments,
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(
            DeliveryAssignmentSerializer(result, many=True).data,
            status=status.HTTP_201_CREATED,
        )


class RevokeDeliveryAssignmentView(APIView):
    @extend_schema(
        operation_id="assessment_delivery_assignment_revoke",
        request=None,
        responses=DeliveryAssignmentSerializer,
    )
    def post(
        self,
        request: Request,
        slug: str,
        delivery_id: str,
        assignment_id: str,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_deliveries(request.user, organization))
        delivery = _delivery_visible_to(
            actor=request.user, organization=organization, delivery_id=delivery_id
        )
        assignment = get_object_or_404(
            DeliveryAssignment,
            pk=assignment_id,
            delivery=delivery,
        )
        result = _call(
            lambda: revoke_delivery_assignment(
                actor=request.user, assignment=assignment
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(DeliveryAssignmentSerializer(result).data)


class MyDeliveryListView(APIView):
    @extend_schema(
        operation_id="assessment_my_deliveries_list",
        responses=LearnerDeliverySerializer(many=True),
    )
    def get(self, request: Request, slug: str) -> ApiResponse:
        organization = _organization(request, slug)
        queryset = learner_assignments(actor=request.user, organization=organization)
        return ApiResponse(LearnerDeliverySerializer(queryset, many=True).data)


class MyDeliveryDetailView(APIView):
    @extend_schema(
        operation_id="assessment_my_delivery_retrieve",
        responses=LearnerDeliverySerializer,
    )
    def get(self, request: Request, slug: str, assignment_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        assignment = get_object_or_404(
            learner_assignments(actor=request.user, organization=organization),
            pk=assignment_id,
        )
        return ApiResponse(LearnerDeliverySerializer(assignment).data)


class StartAttemptView(APIView):
    @extend_schema(
        operation_id="assessment_attempts_start",
        request=None,
        responses={201: AttemptSerializer},
    )
    def post(self, request: Request, slug: str, assignment_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        assignment = get_object_or_404(
            learner_assignments(actor=request.user, organization=organization),
            pk=assignment_id,
        )
        result = _call(lambda: start_attempt(actor=request.user, assignment=assignment))
        if isinstance(result, ApiResponse):
            return result
        result = (
            Attempt.objects.prefetch_related("items__response")
            .select_related("assessment_version")
            .get(pk=result.pk)
        )
        return ApiResponse(
            AttemptSerializer(result).data, status=status.HTTP_201_CREATED
        )


class AttemptDetailView(APIView):
    @extend_schema(
        operation_id="assessment_attempt_retrieve", responses=AttemptSerializer
    )
    def get(self, request: Request, slug: str, attempt_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        attempt = get_object_or_404(
            learner_attempts(
                actor=request.user, organization=organization
            ).prefetch_related("items__response"),
            pk=attempt_id,
        )
        return ApiResponse(AttemptSerializer(attempt).data)


class AttemptAssetAccessView(APIView):
    @extend_schema(
        operation_id="assessment_attempt_asset_access",
        request=AssessmentAssetAccessSerializer,
        responses={200: AssessmentAssetAccessResponseSerializer},
    )
    def post(self, request: Request, slug: str, attempt_id: UUID) -> ApiResponse:
        organization = _organization(request, slug)
        attempt = get_object_or_404(
            learner_attempts(actor=request.user, organization=organization)
            .prefetch_related("items")
            .select_related("delivery_assignment__delivery"),
            pk=attempt_id,
        )
        serializer = AssessmentAssetAccessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _call(
            lambda: {
                "assets": assessment_asset_descriptors(
                    attempt=attempt,
                    requested_ids=tuple(serializer.validated_data["asset_version_ids"]),
                )
            }
        )
        return result if isinstance(result, ApiResponse) else ApiResponse(result)


class SaveResponseView(APIView):
    @extend_schema(
        operation_id="assessment_responses_save",
        request=ResponseSaveSerializer,
        responses=AttemptSerializer,
    )
    def put(
        self,
        request: Request,
        slug: str,
        attempt_id: str,
        attempt_item_id: str,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        attempt = get_object_or_404(
            learner_attempts(actor=request.user, organization=organization),
            pk=attempt_id,
        )
        item = get_object_or_404(AttemptItem, pk=attempt_item_id, attempt=attempt)
        serializer = ResponseSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _call(
            lambda: save_response(
                actor=request.user,
                attempt=attempt,
                attempt_item=item,
                expected_version=serializer.validated_data["expected_version"],
                payload=serializer.validated_data["response"],
            )
        )
        if isinstance(result, ApiResponse):
            return result
        updated, _ = result
        updated = Attempt.objects.prefetch_related("items__response").get(pk=updated.pk)
        return ApiResponse(AttemptSerializer(updated).data)


class SubmitAttemptView(APIView):
    @extend_schema(
        operation_id="assessment_attempts_submit",
        request=AssessmentExpectedVersionSerializer,
        responses=AttemptResultSerializer,
    )
    def post(self, request: Request, slug: str, attempt_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        attempt = get_object_or_404(
            learner_attempts(actor=request.user, organization=organization),
            pk=attempt_id,
        )
        serializer = AssessmentExpectedVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _call(
            lambda: submit_attempt(
                actor=request.user,
                attempt=attempt,
                expected_version=serializer.validated_data["expected_version"],
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(AttemptResultSerializer(result).data)


class AttemptResultView(APIView):
    @extend_schema(
        operation_id="assessment_attempt_result",
        responses=AttemptResultSerializer,
    )
    def get(self, request: Request, slug: str, attempt_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        attempt = get_object_or_404(
            learner_attempts(
                actor=request.user, organization=organization
            ).prefetch_related(
                "items__response__manual_decisions",
            ),
            pk=attempt_id,
        )
        return ApiResponse(AttemptResultSerializer(attempt).data)


class ResultsListView(APIView):
    @extend_schema(
        operation_id="assessment_results_list",
        responses=AttemptResultPageSerializer,
    )
    def get(self, request: Request, slug: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_results(request.user, organization))
        queryset = attempts_for_results(organization, actor=request.user)
        delivery_id = request.query_params.get("delivery_id")
        if delivery_id:
            queryset = queryset.filter(delivery_assignment__delivery_id=delivery_id)
        return _paginate(request, queryset, AttemptResultSerializer, self)


class PendingManualListView(APIView):
    @extend_schema(
        operation_id="assessment_manual_grading_list",
        responses=PendingManualSerializer(many=True),
    )
    def get(self, request: Request, slug: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_grade_manually(request.user, organization))
        responses = (
            responses_for_manual_grading(organization, actor=request.user)
            .filter(
                status__in=(
                    ResponseStatus.PENDING_MANUAL,
                    ResponseStatus.MANUALLY_GRADED,
                ),
            )
            .select_related(
                "attempt_item__attempt__delivery_assignment__release_assignment__enrollment__membership__user"
            )
            .prefetch_related("manual_decisions")
            .order_by("created_at")
        )
        return ApiResponse(
            [
                {
                    "response_id": str(response.id),
                    "attempt_id": str(response.attempt_item.attempt_id),
                    "attempt_item_id": str(response.attempt_item_id),
                    "points": response.attempt_item.points,
                    "answer": response.response.get("value"),
                    "learner": (
                        response.attempt_item.attempt.delivery_assignment.release_assignment.enrollment.membership.user.get_full_name()
                        or response.attempt_item.attempt.delivery_assignment.release_assignment.enrollment.membership.user.email
                    ),
                    "response_status": response.status,
                    "current_score": response.score,
                    "decision_history": ManualGradeDecisionSerializer(
                        response.manual_decisions.all(), many=True
                    ).data,
                }
                for response in responses
            ]
        )


class ManualGradeView(APIView):
    @extend_schema(
        operation_id="assessment_manual_grading_create",
        request=ManualGradeSerializer,
        responses=ManualGradeDecisionSerializer,
    )
    def post(self, request: Request, slug: str, response_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_grade_manually(request.user, organization))
        response = get_object_or_404(
            responses_for_manual_grading(organization, actor=request.user),
            pk=response_id,
        )
        serializer = ManualGradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _call(
            lambda: grade_response_manually(
                actor=request.user,
                response=response,
                score=serializer.validated_data["score"],
                feedback=serializer.validated_data.get("feedback", ""),
            )
        )
        if isinstance(result, ApiResponse):
            return result
        decision, _ = result
        return ApiResponse(
            ManualGradeDecisionSerializer(decision).data,
            status=status.HTTP_201_CREATED,
        )
