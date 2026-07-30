# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportIndexIssue=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportOptionalIterable=false, reportCallIssue=false, reportUnknownLambdaType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from django.db.models import Count, QuerySet
from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from domain.courses.models import Course
from domain.learning.exceptions import LearningDomainError
from domain.learning.models import CourseEnrollment, LearningCohort
from domain.learning.selectors import (
    cohort_progress_summary,
    cohort_visible_to_actor,
    cohorts_visible_to_actor,
    enrollment_visible_to_actor,
    enrollments_visible_to_actor,
    learning_outline,
    learning_unit,
    my_active_enrollments,
    my_enrollment,
    my_learning_payload,
    progress_payload,
    progress_summary,
)
from domain.learning.services import (
    archive_cohort,
    complete_unit,
    create_cohort,
    enroll_cohort_members,
    enroll_member,
    open_unit,
    reactivate_enrollment,
    reopen_unit,
    revoke_enrollment,
    suspend_enrollment,
    update_cohort,
    update_learning_position,
    upgrade_enrollment_release,
)
from domain.organizations.models import Membership, Organization
from domain.organizations.selectors import organization_visible_to
from domain.publishing.models import CourseRelease

from .filters import CohortFilter, EnrollmentFilter
from .serializers import (
    CohortCreateSerializer,
    CohortEnrollmentBatchSerializer,
    CohortReadSerializer,
    CohortUpdateSerializer,
    CompleteUnitSerializer,
    CompletionResultSerializer,
    EnrollmentCreateSerializer,
    EnrollmentLifecycleSerializer,
    EnrollmentReadSerializer,
    ErrorSerializer,
    LearningOutlineSerializer,
    LearningUnitSerializer,
    MyLearningSerializer,
    PaginatedCohortProgressSerializer,
    PaginatedCohortSerializer,
    PaginatedEnrollmentSerializer,
    PositionSerializer,
    ProgressSerializer,
    ReleaseUpgradeSerializer,
)


class LearningPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class PositionThrottle(SimpleRateThrottle):
    scope = "learning_position"
    rate = "12/min"

    def get_cache_key(self, request: Request, view: APIView) -> str | None:
        if not request.user.is_authenticated:
            return None
        enrollment_id = view.kwargs.get("enrollment_id", "unknown")
        return self.cache_format % {
            "scope": self.scope,
            "ident": f"{request.user.pk}:{enrollment_id}",
        }

    def allow_request(self, request: Request, view: APIView) -> bool:
        try:
            return super().allow_request(request, view)
        except Exception:
            return True


def _organization(request: Request, slug: str) -> Organization:
    return organization_visible_to(request.user, slug)


def _error(error: LearningDomainError) -> Response:
    return Response(
        {"code": error.code, "detail": str(error)}, status=error.status_code
    )


def _domain_call(operation: Callable[[], Any]) -> Response | Any:
    try:
        return operation()
    except LearningDomainError as error:
        return _error(error)


def _paginate(
    request: Request, queryset: QuerySet[Any], serializer: type[Any], view: APIView
) -> Response:
    paginator = LearningPagination()
    page = paginator.paginate_queryset(queryset, request, view=view)
    return paginator.get_paginated_response(serializer(page, many=True).data)


def _ordered(queryset: QuerySet[Any], request: Request, allowed: dict[str, str]):
    requested = request.query_params.get("ordering")
    if not requested:
        return queryset.order_by(next(iter(allowed.values())))
    descending = requested.startswith("-")
    key = requested[1:] if descending else requested
    field = allowed.get(key)
    if field is None:
        return queryset.order_by(next(iter(allowed.values())))
    normalized_field = field.removeprefix("-")
    return queryset.order_by(f"-{normalized_field}" if descending else normalized_field)


class CohortListCreateView(APIView):
    @extend_schema(
        operation_id="learning_cohorts_list",
        parameters=[
            OpenApiParameter("course", uuid.UUID),
            OpenApiParameter("release_number", int),
            OpenApiParameter("status", str),
            OpenApiParameter("search", str),
            OpenApiParameter("ordering", str),
            OpenApiParameter("page", int),
            OpenApiParameter("page_size", int),
        ],
        responses={200: PaginatedCohortSerializer},
    )
    def get(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        queryset = CohortFilter(
            request.query_params,
            queryset=cohorts_visible_to_actor(request.user, organization).annotate(
                enrollment_count=Count("enrollments")
            ),
        ).qs
        queryset = _ordered(
            queryset, request, {"created_at": "-created_at", "name": "name"}
        )
        return _paginate(request, queryset, CohortReadSerializer, self)

    @extend_schema(
        operation_id="learning_cohorts_create",
        request=CohortCreateSerializer,
        responses={
            201: CohortReadSerializer,
            400: ErrorSerializer,
            403: ErrorSerializer,
        },
    )
    def post(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        serializer = CohortCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        course = get_object_or_404(
            Course.objects.select_related("organization"),
            organization=organization,
            slug=data["course_slug"],
        )
        release = get_object_or_404(
            CourseRelease.objects.select_related(
                "course__organization", "source_revision", "previous_release"
            ),
            course=course,
            number=data["release_number"],
        )
        result = _domain_call(
            lambda: create_cohort(
                actor=request.user,
                organization=organization,
                course=course,
                release=release,
                name=data["name"],
                slug=data.get("slug"),
                description=data.get("description", ""),
                access_starts_at=data.get("access_starts_at"),
                access_ends_at=data.get("access_ends_at"),
            )
        )
        if isinstance(result, Response):
            return result
        return Response(
            CohortReadSerializer(result).data, status=status.HTTP_201_CREATED
        )


class CohortDetailView(APIView):
    @extend_schema(
        operation_id="learning_cohorts_retrieve",
        responses={200: CohortReadSerializer, 404: ErrorSerializer},
    )
    def get(self, request: Request, slug: str, cohort_id: uuid.UUID) -> Response:
        organization = _organization(request, slug)
        cohort = cohort_visible_to_actor(request.user, organization, cohort_id)
        return Response(CohortReadSerializer(cohort).data)

    @extend_schema(
        operation_id="learning_cohorts_update",
        request=CohortUpdateSerializer,
        responses={200: CohortReadSerializer, 409: ErrorSerializer},
    )
    def patch(self, request: Request, slug: str, cohort_id: uuid.UUID) -> Response:
        organization = _organization(request, slug)
        cohort = cohort_visible_to_actor(request.user, organization, cohort_id)
        serializer = CohortUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = _domain_call(
            lambda: update_cohort(actor=request.user, cohort=cohort, **data)
        )
        if isinstance(result, Response):
            return result
        return Response(CohortReadSerializer(result).data)


class CohortArchiveView(APIView):
    @extend_schema(
        request=None, responses={200: CohortReadSerializer, 404: ErrorSerializer}
    )
    def post(self, request: Request, slug: str, cohort_id: uuid.UUID) -> Response:
        organization = _organization(request, slug)
        cohort = cohort_visible_to_actor(request.user, organization, cohort_id)
        result = _domain_call(lambda: archive_cohort(actor=request.user, cohort=cohort))
        if isinstance(result, Response):
            return result
        return Response(CohortReadSerializer(result).data)


class CohortEnrollmentView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter("page", int),
            OpenApiParameter("page_size", int),
        ],
        responses={200: PaginatedEnrollmentSerializer},
    )
    def get(self, request: Request, slug: str, cohort_id: uuid.UUID) -> Response:
        organization = _organization(request, slug)
        cohort = cohort_visible_to_actor(request.user, organization, cohort_id)
        queryset = enrollments_visible_to_actor(request.user, organization).filter(
            cohort=cohort
        )
        return _paginate(
            request, queryset.order_by("-created_at"), EnrollmentReadSerializer, self
        )

    @extend_schema(
        request=CohortEnrollmentBatchSerializer,
        responses={201: EnrollmentReadSerializer(many=True), 409: ErrorSerializer},
    )
    def post(self, request: Request, slug: str, cohort_id: uuid.UUID) -> Response:
        organization = _organization(request, slug)
        cohort = cohort_visible_to_actor(request.user, organization, cohort_id)
        serializer = CohortEnrollmentBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        memberships = list(
            Membership.objects.filter(
                organization=organization,
                id__in=serializer.validated_data["membership_ids"],
            )
        )
        if len(memberships) != len(set(serializer.validated_data["membership_ids"])):
            raise Http404
        result = _domain_call(
            lambda: enroll_cohort_members(
                actor=request.user, cohort=cohort, memberships=memberships
            )
        )
        if isinstance(result, Response):
            return result
        return Response(
            EnrollmentReadSerializer(result, many=True).data,
            status=status.HTTP_201_CREATED,
        )


class CohortProgressView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter("page", int),
            OpenApiParameter("page_size", int),
        ],
        responses={200: PaginatedCohortProgressSerializer},
    )
    def get(self, request: Request, slug: str, cohort_id: uuid.UUID) -> Response:
        organization = _organization(request, slug)
        summary = cohort_progress_summary(request.user, organization, cohort_id)
        rows = summary.pop("rows")
        average = summary.pop("average_basis_points") or 0
        page = LearningPagination()
        paginated = page.paginate_queryset(rows, request, view=self)
        enrollments = [row.release_assignment.enrollment for row in paginated]
        response = page.get_paginated_response(
            EnrollmentReadSerializer(enrollments, many=True).data
        )
        response.data["summary"] = {
            **summary,
            "average_percent": float(average) / 100,
        }
        return response


class EnrollmentListCreateView(APIView):
    @extend_schema(
        operation_id="learning_enrollments_list",
        parameters=[
            OpenApiParameter("course", uuid.UUID),
            OpenApiParameter("cohort", uuid.UUID),
            OpenApiParameter("status", str),
            OpenApiParameter("release_number", int),
            OpenApiParameter("progress_status", str),
            OpenApiParameter("search", str),
            OpenApiParameter("ordering", str),
            OpenApiParameter("page", int),
            OpenApiParameter("page_size", int),
        ],
        responses={200: PaginatedEnrollmentSerializer},
    )
    def get(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        queryset = EnrollmentFilter(
            request.query_params,
            queryset=enrollments_visible_to_actor(request.user, organization),
        ).qs
        queryset = _ordered(
            queryset,
            request,
            {
                "created_at": "-created_at",
                "last_activity_at": "current_release_assignment__progress__last_activity_at",
                "percent": "current_release_assignment__progress__percent_basis_points",
                "email": "membership__user__email",
            },
        )
        return _paginate(request, queryset, EnrollmentReadSerializer, self)

    @extend_schema(
        operation_id="learning_enrollments_create",
        request=EnrollmentCreateSerializer,
        responses={201: EnrollmentReadSerializer, 409: ErrorSerializer},
    )
    def post(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        serializer = EnrollmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        membership = get_object_or_404(
            Membership.objects.select_related("user"),
            organization=organization,
            pk=data["membership_id"],
        )
        course = get_object_or_404(
            Course.objects.select_related("organization"),
            organization=organization,
            slug=data["course_slug"],
        )
        cohort = (
            get_object_or_404(
                LearningCohort, organization=organization, pk=data["cohort_id"]
            )
            if data.get("cohort_id")
            else None
        )
        release = (
            get_object_or_404(
                CourseRelease.objects.select_related(
                    "course__organization", "source_revision", "previous_release"
                ),
                course=course,
                number=data["release_number"],
            )
            if data.get("release_number")
            else None
        )
        result = _domain_call(
            lambda: enroll_member(
                actor=request.user,
                organization=organization,
                course=course,
                membership=membership,
                cohort=cohort,
                release=release,
                access_starts_at=data.get("access_starts_at"),
                access_ends_at=data.get("access_ends_at"),
            )
        )
        if isinstance(result, Response):
            return result
        return Response(
            EnrollmentReadSerializer(result).data, status=status.HTTP_201_CREATED
        )


class EnrollmentDetailView(APIView):
    @extend_schema(
        operation_id="learning_enrollments_retrieve",
        responses={200: EnrollmentReadSerializer, 404: ErrorSerializer},
    )
    def get(self, request: Request, slug: str, enrollment_id: uuid.UUID) -> Response:
        organization = _organization(request, slug)
        enrollment = enrollment_visible_to_actor(
            request.user, organization, enrollment_id
        )
        return Response(EnrollmentReadSerializer(enrollment).data)


class EnrollmentProgressView(APIView):
    @extend_schema(responses={200: ProgressSerializer, 404: ErrorSerializer})
    def get(self, request: Request, slug: str, enrollment_id: uuid.UUID) -> Response:
        organization = _organization(request, slug)
        progress = progress_summary(request.user, organization, enrollment_id)
        return Response(progress_payload(progress))


class EnrollmentActionView(APIView):
    operation: Callable[..., CourseEnrollment]

    @extend_schema(
        request=EnrollmentLifecycleSerializer,
        responses={200: EnrollmentReadSerializer, 409: ErrorSerializer},
    )
    def post(self, request: Request, slug: str, enrollment_id: uuid.UUID) -> Response:
        organization = _organization(request, slug)
        enrollment = enrollment_visible_to_actor(
            request.user, organization, enrollment_id
        )
        serializer = EnrollmentLifecycleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _domain_call(
            lambda: self.operation(
                actor=request.user,
                enrollment=enrollment,
                expected_version=serializer.validated_data[
                    "expected_enrollment_version"
                ],
            )
        )
        if isinstance(result, Response):
            return result
        return Response(EnrollmentReadSerializer(result).data)


class SuspendEnrollmentView(EnrollmentActionView):
    operation = staticmethod(suspend_enrollment)


class ReactivateEnrollmentView(EnrollmentActionView):
    operation = staticmethod(reactivate_enrollment)


class RevokeEnrollmentView(EnrollmentActionView):
    operation = staticmethod(revoke_enrollment)


class UpgradeEnrollmentView(APIView):
    @extend_schema(
        request=ReleaseUpgradeSerializer,
        responses={200: EnrollmentReadSerializer, 409: ErrorSerializer},
    )
    def post(self, request: Request, slug: str, enrollment_id: uuid.UUID) -> Response:
        organization = _organization(request, slug)
        enrollment = enrollment_visible_to_actor(
            request.user, organization, enrollment_id
        )
        serializer = ReleaseUpgradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        release = get_object_or_404(
            CourseRelease.objects.select_related(
                "course__organization", "source_revision", "previous_release"
            ),
            course=enrollment.course,
            number=serializer.validated_data["target_release_number"],
        )
        result = _domain_call(
            lambda: upgrade_enrollment_release(
                actor=request.user,
                enrollment=enrollment,
                expected_enrollment_version=serializer.validated_data[
                    "expected_enrollment_version"
                ],
                target_release=release,
            )
        )
        if isinstance(result, Response):
            return result
        return Response(EnrollmentReadSerializer(result).data)


class MyLearningView(APIView):
    @extend_schema(responses={200: MyLearningSerializer(many=True)})
    def get(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        payload = [
            my_learning_payload(enrollment)
            for enrollment in my_active_enrollments(request.user, organization)
        ]
        rank = {"in_progress": 0, "not_started": 1, "completed": 2}
        payload.sort(
            key=lambda row: (
                rank[row["progress"]["status"]],
                row["course"]["title"].casefold(),
            )
        )
        return Response(payload)


class MyEnrollmentView(APIView):
    @extend_schema(responses={200: MyLearningSerializer, 404: ErrorSerializer})
    def get(self, request: Request, slug: str, enrollment_id: uuid.UUID) -> Response:
        organization = _organization(request, slug)
        enrollment = my_enrollment(request.user, organization, enrollment_id)
        return Response(my_learning_payload(enrollment))


class MyOutlineView(APIView):
    @extend_schema(responses={200: LearningOutlineSerializer, 404: ErrorSerializer})
    def get(self, request: Request, slug: str, enrollment_id: uuid.UUID) -> Response:
        organization = _organization(request, slug)
        enrollment = my_enrollment(request.user, organization, enrollment_id)
        from domain.learning.access import require_learning_access

        result = _domain_call(
            lambda: (
                require_learning_access(actor=request.user, enrollment=enrollment),
                learning_outline(enrollment),
            )[1]
        )
        return result if isinstance(result, Response) else Response(result)


class MyUnitView(APIView):
    @extend_schema(responses={200: LearningUnitSerializer, 404: ErrorSerializer})
    def get(
        self,
        request: Request,
        slug: str,
        enrollment_id: uuid.UUID,
        unit_id: uuid.UUID,
    ) -> Response:
        organization = _organization(request, slug)
        enrollment = my_enrollment(request.user, organization, enrollment_id)
        from domain.learning.access import require_learning_access

        result = _domain_call(
            lambda: (
                require_learning_access(actor=request.user, enrollment=enrollment),
                learning_unit(enrollment, unit_id),
            )[1]
        )
        return result if isinstance(result, Response) else Response(result)


class OpenUnitView(APIView):
    @extend_schema(request=None, responses={200: ProgressSerializer})
    def post(
        self,
        request: Request,
        slug: str,
        enrollment_id: uuid.UUID,
        unit_id: uuid.UUID,
    ) -> Response:
        organization = _organization(request, slug)
        enrollment = my_enrollment(request.user, organization, enrollment_id)
        result = _domain_call(
            lambda: open_unit(
                actor=request.user, enrollment=enrollment, unit_id=unit_id
            )
        )
        return (
            result
            if isinstance(result, Response)
            else Response(progress_payload(result))
        )


class CompleteUnitView(APIView):
    @extend_schema(
        request=CompleteUnitSerializer,
        responses={200: CompletionResultSerializer, 409: ErrorSerializer},
    )
    def post(
        self,
        request: Request,
        slug: str,
        enrollment_id: uuid.UUID,
        unit_id: uuid.UUID,
    ) -> Response:
        organization = _organization(request, slug)
        enrollment = my_enrollment(request.user, organization, enrollment_id)
        serializer = CompleteUnitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _domain_call(
            lambda: complete_unit(
                actor=request.user,
                enrollment=enrollment,
                unit_id=unit_id,
                expected_progress_version=serializer.validated_data[
                    "expected_progress_version"
                ],
            )
        )
        if isinstance(result, Response):
            return result
        progress, already_completed = result
        return Response(
            {
                "progress": progress_payload(progress),
                "already_completed": already_completed,
            }
        )


class ReopenUnitView(APIView):
    @extend_schema(
        request=CompleteUnitSerializer,
        responses={200: ProgressSerializer, 409: ErrorSerializer},
    )
    def post(
        self,
        request: Request,
        slug: str,
        enrollment_id: uuid.UUID,
        unit_id: uuid.UUID,
    ) -> Response:
        organization = _organization(request, slug)
        enrollment = my_enrollment(request.user, organization, enrollment_id)
        serializer = CompleteUnitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _domain_call(
            lambda: reopen_unit(
                actor=request.user,
                enrollment=enrollment,
                unit_id=unit_id,
                expected_progress_version=serializer.validated_data[
                    "expected_progress_version"
                ],
            )
        )
        return (
            result
            if isinstance(result, Response)
            else Response(progress_payload(result))
        )


class PositionView(APIView):
    throttle_classes = [PositionThrottle]

    @extend_schema(
        request=PositionSerializer,
        responses={200: ProgressSerializer, 400: ErrorSerializer},
    )
    def put(self, request: Request, slug: str, enrollment_id: uuid.UUID) -> Response:
        organization = _organization(request, slug)
        enrollment = my_enrollment(request.user, organization, enrollment_id)
        serializer = PositionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _domain_call(
            lambda: update_learning_position(
                actor=request.user,
                enrollment=enrollment,
                unit_id=serializer.validated_data["unit_id"],
                node_id=serializer.validated_data["node_id"],
            )
        )
        return (
            result
            if isinstance(result, Response)
            else Response(progress_payload(result))
        )
