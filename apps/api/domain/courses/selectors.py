# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from django.db.models import Prefetch, QuerySet
from django.shortcuts import get_object_or_404

from domain.organizations.models import Organization

from .choices import AuthoringStatus, StructureStatus
from .extensions import enrich_outline
from .models import (
    Course,
    CourseModule,
    CourseRevision,
    CourseRevisionLearningObjective,
    CourseRevisionSubject,
    CourseRevisionTransition,
    CourseUnit,
    CourseUnitLearningObjective,
    CourseUnitTopic,
)
from .policies import (
    can_view_approved_course,
    can_view_course_authoring,
    can_view_revision,
)


def courses_visible_to_actor(
    actor: object, organization: Organization
) -> QuerySet[Course]:
    queryset = Course.objects.filter(organization=organization)
    if can_view_course_authoring(actor, organization):
        return queryset
    if can_view_approved_course(actor, organization):
        return queryset.filter(
            revisions__authoring_status=AuthoringStatus.APPROVED
        ).distinct()
    return queryset.none()


def course_visible_to_actor(
    actor: object, organization: Organization, slug: str
) -> Course:
    return get_object_or_404(
        courses_visible_to_actor(actor, organization).select_related("organization"),
        slug=slug,
    )


def revisions_visible_to_actor(
    actor: object, course: Course
) -> QuerySet[CourseRevision]:
    queryset = CourseRevision.objects.filter(course=course).select_related(
        "course__organization", "based_on_revision"
    )
    if can_view_course_authoring(actor, course.organization):
        return queryset
    if can_view_approved_course(actor, course.organization):
        return queryset.filter(authoring_status=AuthoringStatus.APPROVED)
    return queryset.none()


def revision_visible_to_actor(
    actor: object, course: Course, revision_id: str
) -> CourseRevision:
    revision = get_object_or_404(
        revisions_visible_to_actor(actor, course), pk=revision_id
    )
    if not can_view_revision(actor, revision):
        return get_object_or_404(CourseRevision.objects.none(), pk=revision_id)
    return revision


def revision_outline_queryset(course: Course) -> QuerySet[CourseRevision]:
    unit_queryset = (
        CourseUnit.objects.select_related("module")
        .prefetch_related(
            Prefetch(
                "topic_alignments",
                queryset=CourseUnitTopic.objects.select_related(
                    "topic__subject"
                ).order_by("position"),
            ),
            Prefetch(
                "objective_alignments",
                queryset=CourseUnitLearningObjective.objects.select_related(
                    "learning_objective__subject"
                ).order_by("position"),
            ),
        )
        .order_by("position", "created_at")
    )
    module_queryset = CourseModule.objects.prefetch_related(
        Prefetch("units", queryset=unit_queryset)
    ).order_by("position", "created_at")
    return (
        CourseRevision.objects.filter(course=course)
        .select_related("course__organization")
        .prefetch_related(
            Prefetch(
                "subject_alignments",
                queryset=CourseRevisionSubject.objects.select_related(
                    "subject__discipline__area"
                ).order_by("position"),
            ),
            Prefetch(
                "objective_alignments",
                queryset=CourseRevisionLearningObjective.objects.select_related(
                    "learning_objective__subject"
                ).order_by("position"),
            ),
            Prefetch("modules", queryset=module_queryset),
        )
    )


def course_outline(actor: object, course: Course, revision_id: str) -> CourseRevision:
    visible = revision_visible_to_actor(actor, course, revision_id)
    revision = get_object_or_404(revision_outline_queryset(course), pk=visible.pk)
    return enrich_outline(revision)


def course_review_history(
    actor: object, course: Course, revision_id: str
) -> QuerySet[CourseRevisionTransition]:
    revision = revision_visible_to_actor(actor, course, revision_id)
    return CourseRevisionTransition.objects.filter(revision=revision).select_related(
        "actor"
    )


def latest_visible_revision(actor: object, course: Course) -> CourseRevision | None:
    return revisions_visible_to_actor(actor, course).order_by("-number").first()


def active_outline_counts(revision: CourseRevision) -> dict[str, int]:
    return {
        "modules": revision.modules.filter(status=StructureStatus.ACTIVE).count(),
        "units": CourseUnit.objects.filter(
            module__revision=revision,
            module__status=StructureStatus.ACTIVE,
            status=StructureStatus.ACTIVE,
        ).count(),
    }
