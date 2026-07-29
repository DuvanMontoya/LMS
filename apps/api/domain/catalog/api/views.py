# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportCallIssue=false, reportOptionalMemberAccess=false, reportOptionalSubscript=false, reportIndexIssue=false, reportGeneralTypeIssues=false
from __future__ import annotations

from typing import TypeVar, cast

from django.db.models import Model, QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from domain.catalog.exceptions import CatalogDomainError, PrerequisiteCycle
from domain.catalog.filters import (
    AreaFilter,
    ConceptFilter,
    DisciplineFilter,
    LearningObjectiveFilter,
    SubjectFilter,
)
from domain.catalog.models import (
    AcademicArea,
    CatalogStatus,
    Concept,
    ConceptPrerequisite,
    Discipline,
    LearningObjective,
    LearningObjectiveConcept,
    Subject,
    SubjectPrerequisite,
    Topic,
    TopicConcept,
)
from domain.catalog.policies import can_manage_catalog, can_view_catalog
from domain.catalog.selectors import (
    areas_visible_to,
    concepts_visible_to,
    disciplines_visible_to,
    learning_objectives_visible_to,
    subjects_visible_to,
    topics_visible_to,
)
from domain.catalog.services import (
    archive_area,
    archive_concept,
    archive_discipline,
    archive_learning_objective,
    archive_subject,
    archive_topic_subtree,
    create_area,
    create_child_topic,
    create_concept,
    create_discipline,
    create_learning_objective,
    create_root_topic,
    create_subject,
    move_topic,
    replace_concept_prerequisites,
    replace_learning_objective_concepts,
    replace_subject_prerequisites,
    replace_topic_concepts,
    restore_entity,
    update_entity,
)
from domain.organizations.models import Organization
from domain.organizations.selectors import organization_visible_to

from .serializers import (
    AreaSerializer,
    ConceptAssociationEntrySerializer,
    ConceptSerializer,
    CreateAreaSerializer,
    CreateConceptSerializer,
    CreateDisciplineSerializer,
    CreateObjectiveSerializer,
    CreateSubjectSerializer,
    CreateTopicSerializer,
    DisciplineSerializer,
    MoveTopicSerializer,
    ObjectiveSerializer,
    PrerequisiteGraphEntrySerializer,
    ReplaceConceptAssociationsSerializer,
    ReplaceSubjectPrerequisitesSerializer,
    SubjectSerializer,
    TopicSerializer,
    UpdateAreaSerializer,
    UpdateConceptSerializer,
    UpdateNamedEntitySerializer,
    UpdateObjectiveSerializer,
    UpdateTopicSerializer,
)

CatalogModel = TypeVar("CatalogModel", bound=Model)


def _organization(request: Request, slug: str) -> Organization:
    return organization_visible_to(request.user, slug)


def _visible(request: Request, organization: Organization):
    if not can_view_catalog(request.user, organization):
        raise PermissionDenied("catalog_permission_denied")
    return (
        [CatalogStatus.ACTIVE, CatalogStatus.ARCHIVED]
        if can_manage_catalog(request.user, organization)
        else [CatalogStatus.ACTIVE]
    )


def _catalog_error(error: CatalogDomainError) -> Response:
    if isinstance(error, PrerequisiteCycle):
        return Response(
            {
                "code": "prerequisite_cycle",
                "detail": "La relación produciría un ciclo de prerrequisitos.",
            },
            status=status.HTTP_409_CONFLICT,
        )
    return Response(
        {
            "code": "catalog_operation_rejected",
            "detail": "La operación curricular no es válida.",
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


class CatalogFilteredListView(APIView):
    """Applies declared filters only after the organization visibility boundary."""

    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = None
    ordering_fields: tuple[str, ...] = ()
    ordering: tuple[str, ...] = ()

    def filter_catalog_queryset(
        self, request: Request, queryset: QuerySet[CatalogModel]
    ) -> QuerySet[CatalogModel]:
        for backend in self.filter_backends:
            queryset = cast(
                QuerySet[CatalogModel],
                backend().filter_queryset(cast(HttpRequest, request), queryset, self),
            )
        return queryset


class AreaListView(CatalogFilteredListView):
    queryset = AcademicArea.objects.none()
    filterset_class = AreaFilter
    ordering_fields = ("name", "slug")
    ordering = ("name",)

    @extend_schema(
        parameters=[
            OpenApiParameter("status", str, OpenApiParameter.QUERY),
            OpenApiParameter("search", str, OpenApiParameter.QUERY),
            OpenApiParameter("ordering", str, OpenApiParameter.QUERY),
        ],
        responses={200: AreaSerializer(many=True)},
    )
    def get(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        rows = self.filter_catalog_queryset(
            request, areas_visible_to(organization, _visible(request, organization))
        )
        return Response(AreaSerializer(rows, many=True).data)

    @extend_schema(request=CreateAreaSerializer, responses={201: AreaSerializer})
    def post(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        if not can_manage_catalog(request.user, organization):
            raise PermissionDenied("catalog_permission_denied")
        serializer = CreateAreaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entity = create_area(
            actor=request.user, organization=organization, **serializer.validated_data
        )
        return Response(AreaSerializer(entity).data, status=status.HTTP_201_CREATED)


class AreaDetailView(APIView):
    def _area(self, request: Request, slug: str, area_id: str) -> AcademicArea:
        organization = _organization(request, slug)
        _visible(request, organization)
        return get_object_or_404(AcademicArea, pk=area_id, organization=organization)

    @extend_schema(responses={200: AreaSerializer})
    def get(self, request: Request, slug: str, area_id: str) -> Response:
        return Response(AreaSerializer(self._area(request, slug, area_id)).data)

    @extend_schema(request=UpdateAreaSerializer, responses={200: AreaSerializer})
    def patch(self, request: Request, slug: str, area_id: str) -> Response:
        organization = _organization(request, slug)
        if not can_manage_catalog(request.user, organization):
            raise PermissionDenied("catalog_permission_denied")
        serializer = UpdateAreaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        area = get_object_or_404(AcademicArea, pk=area_id, organization=organization)
        updated = update_entity(
            actor=request.user,
            organization=organization,
            entity=area,
            **serializer.validated_data,
        )
        return Response(AreaSerializer(updated).data)


class AreaActionView(APIView):
    action = ""

    @extend_schema(request=None, responses={200: AreaSerializer})
    def post(self, request: Request, slug: str, area_id: str) -> Response:
        organization = _organization(request, slug)
        if not can_manage_catalog(request.user, organization):
            raise PermissionDenied("catalog_permission_denied")
        area = get_object_or_404(AcademicArea, pk=area_id, organization=organization)
        try:
            entity = (
                archive_area(actor=request.user, organization=organization, area=area)
                if self.action == "archive"
                else restore_entity(
                    actor=request.user, organization=organization, entity=area
                )
            )
        except CatalogDomainError as error:
            return _catalog_error(error)
        return Response(AreaSerializer(entity).data)


class ArchiveAreaView(AreaActionView):
    action = "archive"


class RestoreAreaView(AreaActionView):
    action = "restore"


class DisciplineListView(CatalogFilteredListView):
    queryset = Discipline.objects.none()
    filterset_class = DisciplineFilter
    ordering_fields = ("name", "slug")
    ordering = ("name",)

    @extend_schema(
        parameters=[
            OpenApiParameter("area", str, OpenApiParameter.QUERY),
            OpenApiParameter("status", str, OpenApiParameter.QUERY),
            OpenApiParameter("search", str, OpenApiParameter.QUERY),
            OpenApiParameter("ordering", str, OpenApiParameter.QUERY),
        ],
        responses={200: DisciplineSerializer(many=True)},
    )
    def get(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        rows = self.filter_catalog_queryset(
            request,
            disciplines_visible_to(organization, _visible(request, organization)),
        )
        return Response(DisciplineSerializer(rows, many=True).data)

    @extend_schema(
        request=CreateDisciplineSerializer, responses={201: DisciplineSerializer}
    )
    def post(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        if not can_manage_catalog(request.user, organization):
            raise PermissionDenied("catalog_permission_denied")
        serializer = CreateDisciplineSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        area = get_object_or_404(
            AcademicArea,
            pk=serializer.validated_data.pop("area_id"),
            organization=organization,
        )
        entity = create_discipline(
            actor=request.user,
            organization=organization,
            area=area,
            **serializer.validated_data,
        )
        return Response(
            DisciplineSerializer(entity).data, status=status.HTTP_201_CREATED
        )


class DisciplineDetailView(APIView):
    def _discipline(
        self, request: Request, slug: str, discipline_id: str
    ) -> Discipline:
        organization = _organization(request, slug)
        _visible(request, organization)
        return get_object_or_404(
            Discipline.objects.select_related("area"),
            pk=discipline_id,
            area__organization=organization,
        )

    @extend_schema(responses={200: DisciplineSerializer})
    def get(self, request: Request, slug: str, discipline_id: str) -> Response:
        return Response(
            DisciplineSerializer(self._discipline(request, slug, discipline_id)).data
        )

    @extend_schema(
        request=UpdateNamedEntitySerializer, responses={200: DisciplineSerializer}
    )
    def patch(self, request: Request, slug: str, discipline_id: str) -> Response:
        organization = _organization(request, slug)
        if not can_manage_catalog(request.user, organization):
            raise PermissionDenied("catalog_permission_denied")
        serializer = UpdateNamedEntitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entity = self._discipline(request, slug, discipline_id)
        updated = update_entity(
            actor=request.user,
            organization=organization,
            entity=entity,
            **serializer.validated_data,
        )
        return Response(DisciplineSerializer(updated).data)


class DisciplineActionView(APIView):
    action = ""

    @extend_schema(request=None, responses={200: DisciplineSerializer})
    def post(self, request: Request, slug: str, discipline_id: str) -> Response:
        organization = _organization(request, slug)
        if not can_manage_catalog(request.user, organization):
            raise PermissionDenied("catalog_permission_denied")
        entity = get_object_or_404(
            Discipline.objects.select_related("area"),
            pk=discipline_id,
            area__organization=organization,
        )
        try:
            result = (
                archive_discipline(
                    actor=request.user, organization=organization, discipline=entity
                )
                if self.action == "archive"
                else restore_entity(
                    actor=request.user, organization=organization, entity=entity
                )
            )
        except CatalogDomainError as error:
            return _catalog_error(error)
        return Response(DisciplineSerializer(result).data)


class ArchiveDisciplineView(DisciplineActionView):
    action = "archive"


class RestoreDisciplineView(DisciplineActionView):
    action = "restore"


class SubjectListView(CatalogFilteredListView):
    queryset = Subject.objects.none()
    filterset_class = SubjectFilter
    ordering_fields = ("name", "slug")
    ordering = ("name",)

    @extend_schema(
        parameters=[
            OpenApiParameter("area", str, OpenApiParameter.QUERY),
            OpenApiParameter("discipline", str, OpenApiParameter.QUERY),
            OpenApiParameter("status", str, OpenApiParameter.QUERY),
            OpenApiParameter("search", str, OpenApiParameter.QUERY),
            OpenApiParameter("ordering", str, OpenApiParameter.QUERY),
        ],
        responses={200: SubjectSerializer(many=True)},
    )
    def get(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        rows = self.filter_catalog_queryset(
            request, subjects_visible_to(organization, _visible(request, organization))
        )
        return Response(SubjectSerializer(rows, many=True).data)

    @extend_schema(request=CreateSubjectSerializer, responses={201: SubjectSerializer})
    def post(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        if not can_manage_catalog(request.user, organization):
            raise PermissionDenied("catalog_permission_denied")
        serializer = CreateSubjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        discipline = get_object_or_404(
            Discipline.objects.select_related("area"),
            pk=serializer.validated_data.pop("discipline_id"),
            area__organization=organization,
        )
        entity = create_subject(
            actor=request.user,
            organization=organization,
            discipline=discipline,
            **serializer.validated_data,
        )
        return Response(SubjectSerializer(entity).data, status=status.HTTP_201_CREATED)


class SubjectDetailView(APIView):
    def _subject(self, request: Request, slug: str, subject_id: str) -> Subject:
        organization = _organization(request, slug)
        _visible(request, organization)
        return get_object_or_404(
            Subject.objects.select_related("discipline__area"),
            pk=subject_id,
            discipline__area__organization=organization,
        )

    @extend_schema(responses={200: SubjectSerializer})
    def get(self, request: Request, slug: str, subject_id: str) -> Response:
        return Response(
            SubjectSerializer(self._subject(request, slug, subject_id)).data
        )

    @extend_schema(
        request=UpdateNamedEntitySerializer, responses={200: SubjectSerializer}
    )
    def patch(self, request: Request, slug: str, subject_id: str) -> Response:
        organization = _organization(request, slug)
        if not can_manage_catalog(request.user, organization):
            raise PermissionDenied("catalog_permission_denied")
        serializer = UpdateNamedEntitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entity = self._subject(request, slug, subject_id)
        updated = update_entity(
            actor=request.user,
            organization=organization,
            entity=entity,
            **serializer.validated_data,
        )
        return Response(SubjectSerializer(updated).data)


class SubjectActionView(APIView):
    action = ""

    @extend_schema(request=None, responses={200: SubjectSerializer})
    def post(self, request: Request, slug: str, subject_id: str) -> Response:
        organization = _organization(request, slug)
        if not can_manage_catalog(request.user, organization):
            raise PermissionDenied("catalog_permission_denied")
        entity = get_object_or_404(
            Subject.objects.select_related("discipline__area"),
            pk=subject_id,
            discipline__area__organization=organization,
        )
        try:
            result = (
                archive_subject(
                    actor=request.user, organization=organization, subject=entity
                )
                if self.action == "archive"
                else restore_entity(
                    actor=request.user, organization=organization, entity=entity
                )
            )
        except CatalogDomainError as error:
            return _catalog_error(error)
        return Response(SubjectSerializer(result).data)


class ArchiveSubjectView(SubjectActionView):
    action = "archive"


class RestoreSubjectView(SubjectActionView):
    action = "restore"


class SubjectPrerequisiteView(APIView):
    @extend_schema(responses={200: ReplaceSubjectPrerequisitesSerializer})
    def get(self, request: Request, slug: str, subject_id: str) -> Response:
        organization = _organization(request, slug)
        _visible(request, organization)
        subject = get_object_or_404(
            Subject, pk=subject_id, discipline__area__organization=organization
        )
        payload = [
            {
                "prerequisite_id": str(link.prerequisite_id),
                "kind": link.kind,
                "rationale": link.rationale,
            }
            for link in subject.prerequisite_links.select_related(
                "prerequisite"
            ).order_by("prerequisite__name")
        ]
        return Response({"prerequisites": payload})

    @extend_schema(
        request=ReplaceSubjectPrerequisitesSerializer,
        responses={200: ReplaceSubjectPrerequisitesSerializer},
    )
    def put(self, request: Request, slug: str, subject_id: str) -> Response:
        organization = _organization(request, slug)
        serializer = ReplaceSubjectPrerequisitesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subject = get_object_or_404(
            Subject, pk=subject_id, discipline__area__organization=organization
        )
        rows = serializer.validated_data["prerequisites"]
        ids = [row["prerequisite_id"] for row in rows]
        prerequisites = {
            str(item.id): item
            for item in Subject.objects.filter(
                pk__in=ids,
                discipline__area__organization=organization,
            )
        }
        if len(prerequisites) != len(ids):
            return Response(
                {
                    "code": "cross_organization_relation",
                    "detail": "Relación institucional no válida.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            replace_subject_prerequisites(
                actor=request.user,
                organization=organization,
                target=subject,
                prerequisites=[
                    (
                        prerequisites[str(row["prerequisite_id"])],
                        row["kind"],
                        row.get("rationale", ""),
                    )
                    for row in rows
                ],
            )
        except CatalogDomainError as error:
            return _catalog_error(error)
        return Response(serializer.data)


class SubjectPrerequisiteListView(APIView):
    """Return all visible subject edges in one organization-scoped query."""

    @extend_schema(responses={200: PrerequisiteGraphEntrySerializer(many=True)})
    def get(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        visible_statuses = _visible(request, organization)
        rows = (
            SubjectPrerequisite.objects.filter(
                subject__discipline__area__organization=organization,
                subject__status__in=visible_statuses,
                prerequisite__status__in=visible_statuses,
            )
            .select_related("subject", "prerequisite")
            .order_by("subject__name", "prerequisite__name")
        )
        return Response(
            [
                {
                    "entity_id": str(link.subject_id),
                    "prerequisite_id": str(link.prerequisite_id),
                    "kind": link.kind,
                    "rationale": link.rationale,
                }
                for link in rows
            ]
        )


class ConceptPrerequisiteView(APIView):
    @extend_schema(responses={200: ReplaceSubjectPrerequisitesSerializer})
    def get(self, request: Request, slug: str, concept_id: str) -> Response:
        organization = _organization(request, slug)
        _visible(request, organization)
        concept = get_object_or_404(Concept, pk=concept_id, organization=organization)
        return Response(
            {
                "prerequisites": [
                    {
                        "prerequisite_id": str(link.prerequisite_id),
                        "kind": link.kind,
                        "rationale": link.rationale,
                    }
                    for link in concept.prerequisite_links.select_related(
                        "prerequisite"
                    ).order_by("prerequisite__name")
                ]
            }
        )

    @extend_schema(
        request=ReplaceSubjectPrerequisitesSerializer,
        responses={200: ReplaceSubjectPrerequisitesSerializer},
    )
    def put(self, request: Request, slug: str, concept_id: str) -> Response:
        organization = _organization(request, slug)
        serializer = ReplaceSubjectPrerequisitesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        concept = get_object_or_404(Concept, pk=concept_id, organization=organization)
        rows = serializer.validated_data["prerequisites"]
        ids = [row["prerequisite_id"] for row in rows]
        prerequisites = {
            str(item.id): item
            for item in Concept.objects.filter(pk__in=ids, organization=organization)
        }
        if len(prerequisites) != len(ids):
            return Response(
                {
                    "code": "cross_organization_relation",
                    "detail": "Relación institucional no válida.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            replace_concept_prerequisites(
                actor=request.user,
                organization=organization,
                target=concept,
                prerequisites=[
                    (
                        prerequisites[str(row["prerequisite_id"])],
                        row["kind"],
                        row.get("rationale", ""),
                    )
                    for row in rows
                ],
            )
        except CatalogDomainError as error:
            return _catalog_error(error)
        return Response(serializer.data)


class ConceptPrerequisiteListView(APIView):
    """Return all visible concept edges in one organization-scoped query."""

    @extend_schema(responses={200: PrerequisiteGraphEntrySerializer(many=True)})
    def get(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        visible_statuses = _visible(request, organization)
        rows = (
            ConceptPrerequisite.objects.filter(
                concept__organization=organization,
                concept__status__in=visible_statuses,
                prerequisite__status__in=visible_statuses,
            )
            .select_related("concept", "prerequisite")
            .order_by("concept__name", "prerequisite__name")
        )
        return Response(
            [
                {
                    "entity_id": str(link.concept_id),
                    "prerequisite_id": str(link.prerequisite_id),
                    "kind": link.kind,
                    "rationale": link.rationale,
                }
                for link in rows
            ]
        )


class TopicConceptAssociationView(APIView):
    @extend_schema(responses={200: ReplaceConceptAssociationsSerializer})
    def get(self, request: Request, slug: str, topic_id: str) -> Response:
        organization = _organization(request, slug)
        _visible(request, organization)
        topic = get_object_or_404(
            Topic, pk=topic_id, subject__discipline__area__organization=organization
        )
        return Response(
            {
                "concept_ids": [
                    str(link.concept_id)
                    for link in topic.concept_links.order_by("position")
                ]
            }
        )

    @extend_schema(
        request=ReplaceConceptAssociationsSerializer,
        responses={200: ReplaceConceptAssociationsSerializer},
    )
    def put(self, request: Request, slug: str, topic_id: str) -> Response:
        organization = _organization(request, slug)
        serializer = ReplaceConceptAssociationsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        topic = get_object_or_404(
            Topic, pk=topic_id, subject__discipline__area__organization=organization
        )
        ids = serializer.validated_data["concept_ids"]
        indexed = {
            str(item.id): item
            for item in Concept.objects.filter(pk__in=ids, organization=organization)
        }
        if len(indexed) != len(ids):
            return Response(
                {
                    "code": "cross_organization_relation",
                    "detail": "Relación institucional no válida.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            replace_topic_concepts(
                actor=request.user,
                organization=organization,
                topic=topic,
                concepts=[indexed[str(item)] for item in ids],
            )
        except CatalogDomainError as error:
            return _catalog_error(error)
        return Response({"concept_ids": [str(item) for item in ids]})


class TopicConceptAssociationListView(APIView):
    @extend_schema(
        responses={200: ConceptAssociationEntrySerializer(many=True)},
        description="Return visible topic-to-concept associations in one organization-scoped query.",
    )
    def get(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        visible = _visible(request, organization)
        rows = (
            TopicConcept.objects.filter(
                topic__subject__discipline__area__organization=organization,
                topic__status__in=visible,
                concept__status__in=visible,
            )
            .select_related("topic", "concept")
            .order_by("topic_id", "position")
        )
        grouped: dict[str, list[str]] = {}
        for link in rows:
            grouped.setdefault(str(link.topic_id), []).append(str(link.concept_id))
        return Response(
            [
                {"entity_id": entity_id, "concept_ids": concept_ids}
                for entity_id, concept_ids in grouped.items()
            ]
        )


class ObjectiveConceptAssociationView(APIView):
    @extend_schema(responses={200: ReplaceConceptAssociationsSerializer})
    def get(self, request: Request, slug: str, objective_id: str) -> Response:
        organization = _organization(request, slug)
        _visible(request, organization)
        objective = get_object_or_404(
            LearningObjective,
            pk=objective_id,
            subject__discipline__area__organization=organization,
        )
        return Response(
            {
                "concept_ids": [
                    str(link.concept_id)
                    for link in objective.concept_links.order_by("position")
                ]
            }
        )

    @extend_schema(
        request=ReplaceConceptAssociationsSerializer,
        responses={200: ReplaceConceptAssociationsSerializer},
    )
    def put(self, request: Request, slug: str, objective_id: str) -> Response:
        organization = _organization(request, slug)
        serializer = ReplaceConceptAssociationsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        objective = get_object_or_404(
            LearningObjective,
            pk=objective_id,
            subject__discipline__area__organization=organization,
        )
        ids = serializer.validated_data["concept_ids"]
        indexed = {
            str(item.id): item
            for item in Concept.objects.filter(pk__in=ids, organization=organization)
        }
        if len(indexed) != len(ids):
            return Response(
                {
                    "code": "cross_organization_relation",
                    "detail": "Relación institucional no válida.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            replace_learning_objective_concepts(
                actor=request.user,
                organization=organization,
                objective=objective,
                concepts=[indexed[str(item)] for item in ids],
            )
        except CatalogDomainError as error:
            return _catalog_error(error)
        return Response({"concept_ids": [str(item) for item in ids]})


class ObjectiveConceptAssociationListView(APIView):
    @extend_schema(
        responses={200: ConceptAssociationEntrySerializer(many=True)},
        description="Return visible objective-to-concept associations in one organization-scoped query.",
    )
    def get(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        visible = _visible(request, organization)
        rows = (
            LearningObjectiveConcept.objects.filter(
                learning_objective__subject__discipline__area__organization=organization,
                learning_objective__status__in=visible,
                concept__status__in=visible,
            )
            .select_related("learning_objective", "concept")
            .order_by("learning_objective_id", "position")
        )
        grouped: dict[str, list[str]] = {}
        for link in rows:
            grouped.setdefault(str(link.learning_objective_id), []).append(
                str(link.concept_id)
            )
        return Response(
            [
                {"entity_id": entity_id, "concept_ids": concept_ids}
                for entity_id, concept_ids in grouped.items()
            ]
        )


class TopicDetailView(APIView):
    def _topic(self, request: Request, slug: str, topic_id: str) -> Topic:
        organization = _organization(request, slug)
        _visible(request, organization)
        return get_object_or_404(
            Topic.objects.select_related("subject__discipline__area"),
            pk=topic_id,
            subject__discipline__area__organization=organization,
        )

    @extend_schema(responses={200: TopicSerializer})
    def get(self, request: Request, slug: str, topic_id: str) -> Response:
        return Response(TopicSerializer(self._topic(request, slug, topic_id)).data)

    @extend_schema(request=UpdateTopicSerializer, responses={200: TopicSerializer})
    def patch(self, request: Request, slug: str, topic_id: str) -> Response:
        organization = _organization(request, slug)
        if not can_manage_catalog(request.user, organization):
            raise PermissionDenied("catalog_permission_denied")
        serializer = UpdateTopicSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entity = self._topic(request, slug, topic_id)
        updated = update_entity(
            actor=request.user,
            organization=organization,
            entity=entity,
            **serializer.validated_data,
        )
        return Response(TopicSerializer(updated).data)


class TopicMoveView(APIView):
    @extend_schema(request=MoveTopicSerializer, responses={200: TopicSerializer})
    def post(self, request: Request, slug: str, topic_id: str) -> Response:
        organization = _organization(request, slug)
        if not can_manage_catalog(request.user, organization):
            raise PermissionDenied("catalog_permission_denied")
        serializer = MoveTopicSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        topic = get_object_or_404(
            Topic, pk=topic_id, subject__discipline__area__organization=organization
        )
        target = get_object_or_404(
            Topic,
            pk=serializer.validated_data["target_id"],
            subject__discipline__area__organization=organization,
        )
        try:
            moved = move_topic(
                actor=request.user,
                organization=organization,
                topic=topic,
                target=target,
                pos=serializer.validated_data["position"],
            )
        except CatalogDomainError as error:
            return _catalog_error(error)
        return Response(TopicSerializer(moved).data)


class TopicActionView(APIView):
    action = ""

    @extend_schema(request=None, responses={200: TopicSerializer})
    def post(self, request: Request, slug: str, topic_id: str) -> Response:
        organization = _organization(request, slug)
        if not can_manage_catalog(request.user, organization):
            raise PermissionDenied("catalog_permission_denied")
        topic = get_object_or_404(
            Topic.objects.select_related("subject__discipline__area"),
            pk=topic_id,
            subject__discipline__area__organization=organization,
        )
        try:
            result = (
                archive_topic_subtree(
                    actor=request.user, organization=organization, topic=topic
                )
                if self.action == "archive"
                else restore_entity(
                    actor=request.user, organization=organization, entity=topic
                )
            )
        except CatalogDomainError as error:
            return _catalog_error(error)
        return Response(TopicSerializer(result).data)


class ArchiveTopicView(TopicActionView):
    action = "archive"


class RestoreTopicView(TopicActionView):
    action = "restore"


class TopicListView(APIView):
    @extend_schema(responses={200: TopicSerializer(many=True)})
    def get(self, request: Request, slug: str, subject_id: str) -> Response:
        organization = _organization(request, slug)
        visible = _visible(request, organization)
        subject = get_object_or_404(
            Subject, pk=subject_id, discipline__area__organization=organization
        )
        rows = list(topics_visible_to(subject, visible))
        items = {
            row.path: {**TopicSerializer(row).data, "children": []} for row in rows
        }
        roots = []
        for row in rows:
            item = items[row.path]
            parent = items.get(row.path[: -Topic.steplen])
            if parent:
                parent["children"].append(item)
            else:
                roots.append(item)
        return Response(roots)

    @extend_schema(request=CreateTopicSerializer, responses={201: TopicSerializer})
    def post(self, request: Request, slug: str, subject_id: str) -> Response:
        organization = _organization(request, slug)
        if not can_manage_catalog(request.user, organization):
            raise PermissionDenied("catalog_permission_denied")
        subject = get_object_or_404(
            Subject, pk=subject_id, discipline__area__organization=organization
        )
        serializer = CreateTopicSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        parent_id = serializer.validated_data.pop("parent_id", None)
        entity = (
            create_child_topic(
                actor=request.user,
                organization=organization,
                parent=get_object_or_404(Topic, pk=parent_id, subject=subject),
                **serializer.validated_data,
            )
            if parent_id
            else create_root_topic(
                actor=request.user,
                organization=organization,
                subject=subject,
                **serializer.validated_data,
            )
        )
        return Response(TopicSerializer(entity).data, status=status.HTTP_201_CREATED)


class ConceptListView(CatalogFilteredListView):
    queryset = Concept.objects.none()
    filterset_class = ConceptFilter
    ordering_fields = ("name", "slug")
    ordering = ("name",)

    @extend_schema(
        parameters=[
            OpenApiParameter("status", str, OpenApiParameter.QUERY),
            OpenApiParameter("search", str, OpenApiParameter.QUERY),
            OpenApiParameter("ordering", str, OpenApiParameter.QUERY),
        ],
        responses={200: ConceptSerializer(many=True)},
    )
    def get(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        rows = self.filter_catalog_queryset(
            request, concepts_visible_to(organization, _visible(request, organization))
        )
        return Response(ConceptSerializer(rows, many=True).data)

    @extend_schema(request=CreateConceptSerializer, responses={201: ConceptSerializer})
    def post(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        if not can_manage_catalog(request.user, organization):
            raise PermissionDenied("catalog_permission_denied")
        serializer = CreateConceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entity = create_concept(
            actor=request.user, organization=organization, **serializer.validated_data
        )
        return Response(ConceptSerializer(entity).data, status=status.HTTP_201_CREATED)


class ConceptDetailView(APIView):
    @extend_schema(responses={200: ConceptSerializer})
    def get(self, request: Request, slug: str, concept_id: str) -> Response:
        organization = _organization(request, slug)
        _visible(request, organization)
        concept = get_object_or_404(Concept, pk=concept_id, organization=organization)
        return Response(ConceptSerializer(concept).data)

    @extend_schema(request=UpdateConceptSerializer, responses={200: ConceptSerializer})
    def patch(self, request: Request, slug: str, concept_id: str) -> Response:
        organization = _organization(request, slug)
        if not can_manage_catalog(request.user, organization):
            raise PermissionDenied("catalog_permission_denied")
        serializer = UpdateConceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        concept = get_object_or_404(Concept, pk=concept_id, organization=organization)
        updated = update_entity(
            actor=request.user,
            organization=organization,
            entity=concept,
            **serializer.validated_data,
        )
        return Response(ConceptSerializer(updated).data)


class ConceptActionView(APIView):
    action = ""

    @extend_schema(request=None, responses={200: ConceptSerializer})
    def post(self, request: Request, slug: str, concept_id: str) -> Response:
        organization = _organization(request, slug)
        if not can_manage_catalog(request.user, organization):
            raise PermissionDenied("catalog_permission_denied")
        concept = get_object_or_404(Concept, pk=concept_id, organization=organization)
        try:
            entity = (
                archive_concept(
                    actor=request.user, organization=organization, concept=concept
                )
                if self.action == "archive"
                else restore_entity(
                    actor=request.user, organization=organization, entity=concept
                )
            )
        except CatalogDomainError as error:
            return _catalog_error(error)
        return Response(ConceptSerializer(entity).data)


class ArchiveConceptView(ConceptActionView):
    action = "archive"


class RestoreConceptView(ConceptActionView):
    action = "restore"


class ObjectiveListView(CatalogFilteredListView):
    queryset = LearningObjective.objects.none()
    filterset_class = LearningObjectiveFilter
    ordering_fields = ("code", "cognitive_level")
    ordering = ("code",)

    @extend_schema(
        parameters=[
            OpenApiParameter("subject", str, OpenApiParameter.QUERY),
            OpenApiParameter("status", str, OpenApiParameter.QUERY),
            OpenApiParameter("cognitive_level", str, OpenApiParameter.QUERY),
            OpenApiParameter("search", str, OpenApiParameter.QUERY),
            OpenApiParameter("ordering", str, OpenApiParameter.QUERY),
        ],
        responses={200: ObjectiveSerializer(many=True)},
    )
    def get(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        rows = self.filter_catalog_queryset(
            request,
            learning_objectives_visible_to(
                organization, _visible(request, organization)
            ),
        )
        return Response(ObjectiveSerializer(rows, many=True).data)

    @extend_schema(
        request=CreateObjectiveSerializer, responses={201: ObjectiveSerializer}
    )
    def post(self, request: Request, slug: str) -> Response:
        organization = _organization(request, slug)
        if not can_manage_catalog(request.user, organization):
            raise PermissionDenied("catalog_permission_denied")
        serializer = CreateObjectiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subject = get_object_or_404(
            Subject,
            pk=serializer.validated_data.pop("subject_id"),
            discipline__area__organization=organization,
        )
        entity = create_learning_objective(
            actor=request.user,
            organization=organization,
            subject=subject,
            **serializer.validated_data,
        )
        return Response(
            ObjectiveSerializer(entity).data, status=status.HTTP_201_CREATED
        )


class ObjectiveDetailView(APIView):
    def _objective(
        self, request: Request, slug: str, objective_id: str
    ) -> LearningObjective:
        organization = _organization(request, slug)
        _visible(request, organization)
        return get_object_or_404(
            LearningObjective.objects.select_related("subject__discipline__area"),
            pk=objective_id,
            subject__discipline__area__organization=organization,
        )

    @extend_schema(responses={200: ObjectiveSerializer})
    def get(self, request: Request, slug: str, objective_id: str) -> Response:
        return Response(
            ObjectiveSerializer(self._objective(request, slug, objective_id)).data
        )

    @extend_schema(
        request=UpdateObjectiveSerializer, responses={200: ObjectiveSerializer}
    )
    def patch(self, request: Request, slug: str, objective_id: str) -> Response:
        organization = _organization(request, slug)
        if not can_manage_catalog(request.user, organization):
            raise PermissionDenied("catalog_permission_denied")
        serializer = UpdateObjectiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entity = self._objective(request, slug, objective_id)
        updated = update_entity(
            actor=request.user,
            organization=organization,
            entity=entity,
            **serializer.validated_data,
        )
        return Response(ObjectiveSerializer(updated).data)


class ObjectiveActionView(APIView):
    action = ""

    @extend_schema(request=None, responses={200: ObjectiveSerializer})
    def post(self, request: Request, slug: str, objective_id: str) -> Response:
        organization = _organization(request, slug)
        if not can_manage_catalog(request.user, organization):
            raise PermissionDenied("catalog_permission_denied")
        objective = get_object_or_404(
            LearningObjective.objects.select_related("subject__discipline__area"),
            pk=objective_id,
            subject__discipline__area__organization=organization,
        )
        try:
            result = (
                archive_learning_objective(
                    actor=request.user, organization=organization, objective=objective
                )
                if self.action == "archive"
                else restore_entity(
                    actor=request.user, organization=organization, entity=objective
                )
            )
        except CatalogDomainError as error:
            return _catalog_error(error)
        return Response(ObjectiveSerializer(result).data)


class ArchiveObjectiveView(ObjectiveActionView):
    action = "archive"


class RestoreObjectiveView(ObjectiveActionView):
    action = "restore"
