# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportCallIssue=false, reportArgumentType=false, reportUnknownLambdaType=false, reportIndexIssue=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false
from __future__ import annotations

from typing import Any

from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response as ApiResponse
from rest_framework.views import APIView

from domain.learning.models import LearningCohort
from domain.learning.policies import can_manage_course_group
from domain.organizations.models import Organization
from domain.organizations.selectors import organization_visible_to
from domain.publishing.models import CourseRelease

from ..analytics import create_analytics_refresh_job
from ..choices import GradebookStatus
from ..exceptions import AssessmentDomainError
from ..gradebooks import (
    activate_gradebook,
    add_gradebook_column,
    archive_gradebook_column,
    create_gradebook,
    reorder_gradebook_columns,
    update_gradebook_column,
)
from ..grading import create_scoring_correction
from ..models import (
    AnalyticsRefreshJob,
    AssessmentAnalyticsSnapshot,
    AssessmentDelivery,
    AssessmentGradingPolicy,
    AssessmentGradingRevision,
    AssessmentItemPool,
    AssessmentRevision,
    AssessmentVersion,
    CourseGradebook,
    GradebookColumn,
    QuestionVersion,
    RegradeJob,
)
from ..policies import (
    can_manage_authoring,
    can_manage_gradebook,
    can_manage_regrading,
    can_refresh_analytics,
    can_view_analytics,
    can_view_authoring,
    can_view_gradebook,
    can_view_regrading,
)
from ..regrading import create_regrade_job, retry_failed_regrade_job
from ..selectors import deliveries_for, gradebooks_for
from ..services import (
    create_assessment_pool,
    reorder_assessment_structure,
    replace_pool_candidates,
    update_assessment_pool,
)
from .advanced_serializers import (
    AnalyticsJobSerializer,
    AnalyticsRefreshSerializer,
    AnalyticsSnapshotSerializer,
    AssessmentPoolSerializer,
    GradebookColumnCreateSerializer,
    GradebookColumnOrderSerializer,
    GradebookColumnSerializer,
    GradebookColumnUpdateSerializer,
    GradebookCreateSerializer,
    GradebookEntrySerializer,
    GradebookSerializer,
    GradebookStudentPayloadSerializer,
    GradebookSummarySerializer,
    GradingPolicySerializer,
    GradingRevisionMetadataSerializer,
    GradingRevisionSerializer,
    ItemAnalyticsSerializer,
    PoolCandidatesSerializer,
    PoolCreateSerializer,
    PoolUpdateSerializer,
    RegradeJobAttemptSerializer,
    RegradeJobCreateSerializer,
    RegradeJobSerializer,
    RegradeRetrySerializer,
    ScoringCorrectionSerializer,
    StructureOrderSerializer,
)
from .serializers import AssessmentExpectedVersionSerializer


def _organization(request: Request, slug: str) -> Organization:
    return organization_visible_to(request.user, slug)


def _require(value: bool) -> None:
    if not value:
        raise PermissionDenied("assessment_permission_denied")


def _domain_call(operation: Any):
    try:
        return operation()
    except AssessmentDomainError as error:
        payload: dict[str, object] = {"code": error.code, "detail": error.message}
        if error.path:
            payload["path"] = error.path
        return ApiResponse(payload, status=error.status_code)


def _version(organization: Organization, version_id: str) -> AssessmentVersion:
    return get_object_or_404(
        AssessmentVersion,
        pk=version_id,
        assessment__organization=organization,
    )


def _revision(
    organization: Organization,
    assessment_slug: str,
    revision_id: str,
) -> AssessmentRevision:
    return get_object_or_404(
        AssessmentRevision,
        pk=revision_id,
        assessment__organization=organization,
        assessment__slug=assessment_slug,
    )


def _pool(organization: Organization, pool_id: str) -> AssessmentItemPool:
    return get_object_or_404(
        AssessmentItemPool,
        pk=pool_id,
        revision__assessment__organization=organization,
    )


def _question_versions(
    organization: Organization, identifiers: list[object]
) -> list[QuestionVersion]:
    versions = list(
        QuestionVersion.objects.filter(
            id__in=identifiers,
            question__bank__organization=organization,
        ).select_related("question__bank")
    )
    by_id = {version.id: version for version in versions}
    if len(by_id) != len(identifiers):
        raise PermissionDenied("assessment_question_version_not_available")
    return [by_id[identifier] for identifier in identifiers]


class PoolListCreateView(APIView):
    @extend_schema(responses=AssessmentPoolSerializer(many=True))
    def get(
        self, request: Request, slug: str, assessment_slug: str, revision_id: str
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_authoring(request.user, organization))
        revision = _revision(organization, assessment_slug, revision_id)
        pools = revision.item_pools.prefetch_related(
            "candidates__question_version"
        ).order_by("position", "id")
        return ApiResponse(AssessmentPoolSerializer(pools, many=True).data)

    @extend_schema(request=PoolCreateSerializer, responses=AssessmentPoolSerializer)
    def post(
        self, request: Request, slug: str, assessment_slug: str, revision_id: str
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_authoring(request.user, organization))
        serializer = PoolCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        identifiers = values.pop("question_version_ids")
        result = _domain_call(
            lambda: create_assessment_pool(
                actor=request.user,
                revision=_revision(organization, assessment_slug, revision_id),
                question_versions=_question_versions(organization, identifiers),
                **values,
            )
        )
        if isinstance(result, ApiResponse):
            return result
        _, pool = result
        return ApiResponse(
            AssessmentPoolSerializer(pool).data,
            status=status.HTTP_201_CREATED,
        )


class PoolDetailView(APIView):
    @extend_schema(responses=AssessmentPoolSerializer)
    def get(self, request: Request, slug: str, pool_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_authoring(request.user, organization))
        return ApiResponse(AssessmentPoolSerializer(_pool(organization, pool_id)).data)

    @extend_schema(request=PoolUpdateSerializer, responses=AssessmentPoolSerializer)
    def patch(self, request: Request, slug: str, pool_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_authoring(request.user, organization))
        serializer = PoolUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pool = _pool(organization, pool_id)
        result = _domain_call(
            lambda: update_assessment_pool(
                actor=request.user,
                revision=pool.revision,
                pool=pool,
                **serializer.validated_data,
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(AssessmentPoolSerializer(result[1]).data)


class PoolCandidatesView(APIView):
    @extend_schema(request=PoolCandidatesSerializer, responses=AssessmentPoolSerializer)
    def put(self, request: Request, slug: str, pool_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_authoring(request.user, organization))
        serializer = PoolCandidatesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        pool = _pool(organization, pool_id)
        result = _domain_call(
            lambda: replace_pool_candidates(
                actor=request.user,
                revision=pool.revision,
                pool=pool,
                expected_version=values["expected_version"],
                question_versions=_question_versions(
                    organization, values["question_version_ids"]
                ),
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(AssessmentPoolSerializer(result[1]).data)


class StructureOrderView(APIView):
    @extend_schema(
        request=StructureOrderSerializer,
        responses=AssessmentExpectedVersionSerializer,
    )
    def put(
        self, request: Request, slug: str, assessment_slug: str, revision_id: str
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_authoring(request.user, organization))
        serializer = StructureOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _domain_call(
            lambda: reorder_assessment_structure(
                actor=request.user,
                revision=_revision(organization, assessment_slug, revision_id),
                **serializer.validated_data,
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse({"lock_version": result.lock_version})


def _can_read_grading_payload(request: Request, organization: Organization) -> bool:
    return can_manage_regrading(request.user, organization) or can_manage_authoring(
        request.user, organization
    )


class ScoringPolicyDetailView(APIView):
    @extend_schema(responses=GradingPolicySerializer)
    def get(self, request: Request, slug: str, version_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(
            can_view_regrading(request.user, organization)
            or can_view_authoring(request.user, organization)
        )
        policy = get_object_or_404(
            AssessmentGradingPolicy.objects.select_related("current_revision"),
            assessment_version=_version(organization, version_id),
        )
        if _can_read_grading_payload(request, organization):
            return ApiResponse(GradingPolicySerializer(policy).data)
        data = {
            "id": policy.id,
            "assessment_version_id": policy.assessment_version_id,
            "lock_version": policy.lock_version,
            "current_revision": (
                GradingRevisionMetadataSerializer(policy.current_revision).data
                if policy.current_revision
                else None
            ),
            "created_at": policy.created_at,
            "updated_at": policy.updated_at,
        }
        return ApiResponse(data)


class ScoringPolicyRevisionListView(APIView):
    @extend_schema(
        operation_id="assessment_scoring_policy_revisions_list",
        responses=GradingRevisionSerializer(many=True),
    )
    def get(self, request: Request, slug: str, version_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(
            can_view_regrading(request.user, organization)
            or can_view_authoring(request.user, organization)
        )
        policy = get_object_or_404(
            AssessmentGradingPolicy,
            assessment_version=_version(organization, version_id),
        )
        rows = policy.revisions.order_by("number")
        serializer_class = (
            GradingRevisionSerializer
            if _can_read_grading_payload(request, organization)
            else GradingRevisionMetadataSerializer
        )
        return ApiResponse(serializer_class(rows, many=True).data)


class ScoringCorrectionView(APIView):
    @extend_schema(
        request=ScoringCorrectionSerializer,
        responses=GradingRevisionSerializer,
    )
    def post(self, request: Request, slug: str, version_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_regrading(request.user, organization))
        serializer = ScoringCorrectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        expected_version = values.pop("expected_version")
        result = _domain_call(
            lambda: create_scoring_correction(
                actor=request.user,
                assessment_version=_version(organization, version_id),
                expected_policy_version=expected_version,
                **values,
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(
            GradingRevisionSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )


class RegradeJobListCreateView(APIView):
    @extend_schema(responses=RegradeJobSerializer(many=True))
    def get(self, request: Request, slug: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_regrading(request.user, organization))
        rows = (
            RegradeJob.objects.filter(organization=organization)
            .select_related("assessment_version", "grading_revision", "delivery")
            .order_by("-created_at", "-id")
        )
        return ApiResponse(RegradeJobSerializer(rows, many=True).data)

    @extend_schema(request=RegradeJobCreateSerializer, responses=RegradeJobSerializer)
    def post(self, request: Request, slug: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_regrading(request.user, organization))
        serializer = RegradeJobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        values.pop("preserve_manual_grades")
        version = _version(organization, str(values.pop("assessment_version_id")))
        grading_revision = get_object_or_404(
            AssessmentGradingRevision,
            pk=values.pop("grading_revision_id"),
            policy__assessment_version=version,
        )
        delivery_id = values.pop("delivery_id", None)
        delivery = (
            get_object_or_404(
                AssessmentDelivery,
                pk=delivery_id,
                organization=organization,
            )
            if delivery_id
            else None
        )
        result = _domain_call(
            lambda: create_regrade_job(
                actor=request.user,
                organization=organization,
                assessment_version=version,
                grading_revision=grading_revision,
                delivery=delivery,
                **values,
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(
            RegradeJobSerializer(result).data,
            status=status.HTTP_202_ACCEPTED,
        )


def _regrade_job(organization: Organization, job_id: str) -> RegradeJob:
    return get_object_or_404(
        RegradeJob.objects.select_related(
            "assessment_version", "grading_revision", "delivery"
        ),
        pk=job_id,
        organization=organization,
    )


class RegradeJobDetailView(APIView):
    @extend_schema(
        operation_id="assessment_regrade_job_retrieve",
        responses=RegradeJobSerializer,
    )
    def get(self, request: Request, slug: str, job_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_regrading(request.user, organization))
        return ApiResponse(
            RegradeJobSerializer(_regrade_job(organization, job_id)).data
        )


class RegradeJobAttemptListView(APIView):
    @extend_schema(
        operation_id="assessment_regrade_job_attempts_list",
        responses=RegradeJobAttemptSerializer(many=True),
    )
    def get(self, request: Request, slug: str, job_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_regrading(request.user, organization))
        rows = _regrade_job(organization, job_id).attempt_items.order_by("id")
        return ApiResponse(RegradeJobAttemptSerializer(rows, many=True).data)


class RegradeJobRetryView(APIView):
    @extend_schema(request=RegradeRetrySerializer, responses=RegradeJobSerializer)
    def post(self, request: Request, slug: str, job_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_regrading(request.user, organization))
        serializer = RegradeRetrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _domain_call(
            lambda: retry_failed_regrade_job(
                actor=request.user,
                job=_regrade_job(organization, job_id),
                **serializer.validated_data,
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(RegradeJobSerializer(result).data)


def _gradebook(
    organization: Organization, gradebook_id: str, *, actor: object
) -> CourseGradebook:
    return get_object_or_404(
        gradebooks_for(organization, actor=actor).prefetch_related("columns"),
        pk=gradebook_id,
    )


class GradebookListCreateView(APIView):
    @extend_schema(responses=GradebookSerializer(many=True))
    def get(self, request: Request, slug: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_gradebook(request.user, organization))
        rows = gradebooks_for(organization, actor=request.user).prefetch_related(
            "columns"
        )
        return ApiResponse(GradebookSerializer(rows, many=True).data)

    @extend_schema(request=GradebookCreateSerializer, responses=GradebookSerializer)
    def post(self, request: Request, slug: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_gradebook(request.user, organization))
        serializer = GradebookCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        release = get_object_or_404(
            CourseRelease,
            pk=serializer.validated_data["course_release_id"],
            course__organization=organization,
        )
        course_group = get_object_or_404(
            LearningCohort.objects.select_related("academic_period"),
            pk=serializer.validated_data["course_group_id"],
            organization=organization,
            release=release,
            migration_review_required=False,
        )
        _require(can_manage_course_group(request.user, course_group))
        result = _domain_call(
            lambda: create_gradebook(
                actor=request.user,
                organization=organization,
                course_release=release,
                course_group=course_group,
                academic_period=course_group.academic_period,
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(
            GradebookSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )


class GradebookDetailView(APIView):
    @extend_schema(
        operation_id="assessment_gradebook_retrieve",
        responses=GradebookSerializer,
    )
    def get(self, request: Request, slug: str, gradebook_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_gradebook(request.user, organization))
        return ApiResponse(
            GradebookSerializer(
                _gradebook(organization, gradebook_id, actor=request.user)
            ).data
        )


class GradebookActivateView(APIView):
    @extend_schema(
        request=AssessmentExpectedVersionSerializer,
        responses=GradebookSerializer,
    )
    def post(self, request: Request, slug: str, gradebook_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_gradebook(request.user, organization))
        serializer = AssessmentExpectedVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _domain_call(
            lambda: activate_gradebook(
                actor=request.user,
                gradebook=_gradebook(organization, gradebook_id, actor=request.user),
                **serializer.validated_data,
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(GradebookSerializer(result).data)


class GradebookColumnListCreateView(APIView):
    @extend_schema(
        operation_id="assessment_gradebook_columns_list",
        responses=GradebookColumnSerializer(many=True),
    )
    def get(self, request: Request, slug: str, gradebook_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_gradebook(request.user, organization))
        rows = _gradebook(
            organization, gradebook_id, actor=request.user
        ).columns.order_by("position", "id")
        return ApiResponse(GradebookColumnSerializer(rows, many=True).data)

    @extend_schema(
        request=GradebookColumnCreateSerializer,
        responses=GradebookColumnSerializer,
    )
    def post(self, request: Request, slug: str, gradebook_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_gradebook(request.user, organization))
        serializer = GradebookColumnCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        delivery = get_object_or_404(
            deliveries_for(organization, actor=request.user),
            pk=values.pop("delivery_id"),
        )
        gradebook = _gradebook(organization, gradebook_id, actor=request.user)
        result = _domain_call(
            lambda: add_gradebook_column(
                actor=request.user,
                gradebook=gradebook,
                delivery=delivery,
                **values,
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(
            GradebookColumnSerializer(result[1]).data,
            status=status.HTTP_201_CREATED,
        )


def _column(gradebook: CourseGradebook, column_id: str) -> GradebookColumn:
    return get_object_or_404(GradebookColumn, pk=column_id, gradebook=gradebook)


class GradebookColumnDetailView(APIView):
    @extend_schema(
        request=GradebookColumnUpdateSerializer,
        responses=GradebookColumnSerializer,
    )
    def patch(
        self, request: Request, slug: str, gradebook_id: str, column_id: str
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_gradebook(request.user, organization))
        serializer = GradebookColumnUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        gradebook = _gradebook(organization, gradebook_id, actor=request.user)
        result = _domain_call(
            lambda: update_gradebook_column(
                actor=request.user,
                gradebook=gradebook,
                column=_column(gradebook, column_id),
                **serializer.validated_data,
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(GradebookColumnSerializer(result[1]).data)


class GradebookColumnOrderView(APIView):
    @extend_schema(
        request=GradebookColumnOrderSerializer,
        responses=GradebookSerializer,
    )
    def put(self, request: Request, slug: str, gradebook_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_gradebook(request.user, organization))
        serializer = GradebookColumnOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _domain_call(
            lambda: reorder_gradebook_columns(
                actor=request.user,
                gradebook=_gradebook(organization, gradebook_id, actor=request.user),
                **serializer.validated_data,
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(GradebookSerializer(result).data)


class GradebookColumnArchiveView(APIView):
    @extend_schema(
        request=AssessmentExpectedVersionSerializer,
        responses=GradebookColumnSerializer,
    )
    def post(
        self, request: Request, slug: str, gradebook_id: str, column_id: str
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_manage_gradebook(request.user, organization))
        serializer = AssessmentExpectedVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        gradebook = _gradebook(organization, gradebook_id, actor=request.user)
        result = _domain_call(
            lambda: archive_gradebook_column(
                actor=request.user,
                gradebook=gradebook,
                column=_column(gradebook, column_id),
                **serializer.validated_data,
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(GradebookColumnSerializer(result[1]).data)


class GradebookEntryListView(APIView):
    @extend_schema(
        operation_id="assessment_gradebook_entries_list",
        responses=GradebookEntrySerializer(many=True),
    )
    def get(self, request: Request, slug: str, gradebook_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_gradebook(request.user, organization))
        rows = (
            _gradebook(organization, gradebook_id, actor=request.user)
            .columns.filter(entries__isnull=False)
            .values_list("entries", flat=True)
        )
        from ..models import GradebookEntry

        entries = (
            GradebookEntry.objects.filter(id__in=rows)
            .select_related(
                "release_assignment__enrollment__membership__user",
                "release_assignment__enrollment__cohort",
            )
            .order_by("release_assignment_id", "column__position")
        )
        return ApiResponse(GradebookEntrySerializer(entries, many=True).data)


class GradebookSummaryListView(APIView):
    @extend_schema(
        operation_id="assessment_gradebook_summaries_list",
        responses=GradebookSummarySerializer(many=True),
    )
    def get(self, request: Request, slug: str, gradebook_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_gradebook(request.user, organization))
        rows = (
            _gradebook(organization, gradebook_id, actor=request.user)
            .summaries.select_related(
                "release_assignment__enrollment__membership__user",
                "release_assignment__enrollment__cohort",
            )
            .order_by("release_assignment_id")
        )
        return ApiResponse(GradebookSummarySerializer(rows, many=True).data)


class GradebookStudentView(APIView):
    @extend_schema(
        operation_id="assessment_gradebook_student_retrieve",
        responses=GradebookStudentPayloadSerializer,
    )
    def get(
        self,
        request: Request,
        slug: str,
        gradebook_id: str,
        release_assignment_id: str,
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_gradebook(request.user, organization))
        gradebook = _gradebook(organization, gradebook_id, actor=request.user)
        entries = gradebook.columns.filter(
            entries__release_assignment_id=release_assignment_id
        ).values_list("entries", flat=True)
        from ..models import GradebookEntry, GradebookSummary

        summary = get_object_or_404(
            GradebookSummary,
            gradebook=gradebook,
            release_assignment_id=release_assignment_id,
        )
        return ApiResponse(
            {
                "gradebook": GradebookSerializer(gradebook).data,
                "entries": GradebookEntrySerializer(
                    GradebookEntry.objects.filter(id__in=entries).order_by(
                        "column__position"
                    ),
                    many=True,
                ).data,
                "summary": GradebookSummarySerializer(summary).data,
            }
        )


class MyGradebookListView(APIView):
    @extend_schema(
        operation_id="assessment_my_gradebooks_list",
        responses=GradebookSerializer(many=True),
    )
    def get(self, request: Request, slug: str) -> ApiResponse:
        organization = _organization(request, slug)
        rows = (
            CourseGradebook.objects.filter(
                organization=organization,
                status=GradebookStatus.ACTIVE,
                summaries__release_assignment__enrollment__membership__user=request.user,
            )
            .select_related("course_release")
            .prefetch_related("columns")
            .distinct()
        )
        return ApiResponse(GradebookSerializer(rows, many=True).data)


class MyGradebookDetailView(APIView):
    @extend_schema(
        operation_id="assessment_my_gradebook_retrieve",
        responses=GradebookStudentPayloadSerializer,
    )
    def get(self, request: Request, slug: str, gradebook_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        gradebook = get_object_or_404(
            CourseGradebook.objects.select_related("course_release").prefetch_related(
                "columns"
            ),
            pk=gradebook_id,
            organization=organization,
            status=GradebookStatus.ACTIVE,
            summaries__release_assignment__enrollment__membership__user=request.user,
        )
        summary = get_object_or_404(
            gradebook.summaries,
            release_assignment__enrollment__membership__user=request.user,
        )
        entries = gradebook.columns.filter(
            entries__release_assignment=summary.release_assignment
        ).values_list("entries", flat=True)
        from ..models import GradebookEntry

        return ApiResponse(
            {
                "gradebook": GradebookSerializer(gradebook).data,
                "entries": GradebookEntrySerializer(
                    GradebookEntry.objects.filter(id__in=entries).order_by(
                        "column__position"
                    ),
                    many=True,
                ).data,
                "summary": GradebookSummarySerializer(summary).data,
            }
        )


def _analytics_scope(request: Request, version: AssessmentVersion):
    queryset = AssessmentAnalyticsSnapshot.objects.filter(assessment_version=version)
    delivery_id = request.query_params.get("delivery")
    revision_id = request.query_params.get("grading_revision")
    queryset = (
        queryset.filter(delivery_id=delivery_id)
        if delivery_id
        else queryset.filter(delivery__isnull=True)
    )
    if revision_id:
        queryset = queryset.filter(grading_revision_id=revision_id)
    return queryset.order_by("-created_at", "-id")


def _latest_analytics_snapshot(
    request: Request, version: AssessmentVersion
) -> AssessmentAnalyticsSnapshot:
    snapshot = _analytics_scope(request, version).first()
    if snapshot is None:
        raise Http404
    return snapshot


class AnalyticsAssessmentView(APIView):
    @extend_schema(
        operation_id="assessment_analytics_retrieve",
        responses=AnalyticsSnapshotSerializer,
    )
    def get(self, request: Request, slug: str, version_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_analytics(request.user, organization))
        snapshot = _latest_analytics_snapshot(
            request, _version(organization, version_id)
        )
        return ApiResponse(AnalyticsSnapshotSerializer(snapshot).data)


class AnalyticsItemListView(APIView):
    @extend_schema(
        operation_id="assessment_analytics_items_list",
        responses=ItemAnalyticsSerializer(many=True),
    )
    def get(self, request: Request, slug: str, version_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_analytics(request.user, organization))
        snapshot = _latest_analytics_snapshot(
            request, _version(organization, version_id)
        )
        return ApiResponse(
            ItemAnalyticsSerializer(snapshot.items.all(), many=True).data
        )


class AnalyticsItemDetailView(APIView):
    @extend_schema(
        operation_id="assessment_analytics_item_retrieve",
        responses=ItemAnalyticsSerializer,
    )
    def get(
        self, request: Request, slug: str, version_id: str, assessment_item_id: str
    ) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_analytics(request.user, organization))
        snapshot = _latest_analytics_snapshot(
            request, _version(organization, version_id)
        )
        item = get_object_or_404(snapshot.items, assessment_item_id=assessment_item_id)
        return ApiResponse(ItemAnalyticsSerializer(item).data)


class AnalyticsRefreshView(APIView):
    @extend_schema(request=AnalyticsRefreshSerializer, responses=AnalyticsJobSerializer)
    def post(self, request: Request, slug: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_refresh_analytics(request.user, organization))
        serializer = AnalyticsRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        version = _version(organization, str(values["assessment_version_id"]))
        revision = get_object_or_404(
            AssessmentGradingRevision,
            pk=values["grading_revision_id"],
            policy__assessment_version=version,
        )
        delivery_id = values.get("delivery_id")
        delivery = (
            get_object_or_404(
                AssessmentDelivery,
                pk=delivery_id,
                organization=organization,
            )
            if delivery_id
            else None
        )
        result = _domain_call(
            lambda: create_analytics_refresh_job(
                actor=request.user,
                organization=organization,
                assessment_version=version,
                grading_revision=revision,
                delivery=delivery,
            )
        )
        if isinstance(result, ApiResponse):
            return result
        return ApiResponse(
            AnalyticsJobSerializer(result).data,
            status=status.HTTP_202_ACCEPTED,
        )


class AnalyticsJobView(APIView):
    @extend_schema(
        operation_id="assessment_analytics_job_retrieve",
        responses=AnalyticsJobSerializer,
    )
    def get(self, request: Request, slug: str, job_id: str) -> ApiResponse:
        organization = _organization(request, slug)
        _require(can_view_analytics(request.user, organization))
        job = get_object_or_404(
            AnalyticsRefreshJob, pk=job_id, organization=organization
        )
        return ApiResponse(AnalyticsJobSerializer(job).data)
