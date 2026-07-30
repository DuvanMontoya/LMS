# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
from __future__ import annotations

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from domain.courses.models import Course
from domain.organizations.models import Organization

from .choices import PublicationStatus
from .models import CoursePublication, CoursePublicationEvent, CourseRelease
from .policies import can_view_history, can_view_published


def organization_course(organization: Organization, course_slug: str) -> Course:
    return get_object_or_404(
        Course.objects.select_related("organization"),
        organization=organization,
        slug=course_slug,
    )


def publication_for_history(
    actor: object, organization: Organization, course_slug: str
) -> CoursePublication:
    if not can_view_history(actor, organization):
        return get_object_or_404(CoursePublication.objects.none())
    return get_object_or_404(
        CoursePublication.objects.select_related(
            "course", "current_release", "withdrawn_by"
        ),
        course__organization=organization,
        course__slug=course_slug,
    )


def releases_for_history(
    actor: object, publication: CoursePublication
) -> QuerySet[CourseRelease]:
    if not can_view_history(actor, publication.course.organization):
        return CourseRelease.objects.none()
    return CourseRelease.objects.filter(course=publication.course).select_related(
        "source_revision", "previous_release", "created_by"
    )


def release_for_history(
    actor: object, publication: CoursePublication, release_number: int
) -> CourseRelease:
    return get_object_or_404(
        releases_for_history(actor, publication), number=release_number
    )


def publication_events(
    actor: object, publication: CoursePublication
) -> QuerySet[CoursePublicationEvent]:
    if not can_view_history(actor, publication.course.organization):
        return CoursePublicationEvent.objects.none()
    return CoursePublicationEvent.objects.filter(
        publication=publication
    ).select_related("release", "revision", "actor")


def active_library_publications(
    actor: object, organization: Organization
) -> QuerySet[CoursePublication]:
    if not can_view_published(actor, organization):
        return CoursePublication.objects.none()
    return CoursePublication.objects.filter(
        course__organization=organization,
        status=PublicationStatus.ACTIVE,
    ).select_related("course", "current_release")


def active_library_publication(
    actor: object, organization: Organization, course_slug: str
) -> CoursePublication:
    return get_object_or_404(
        active_library_publications(actor, organization), course__slug=course_slug
    )
