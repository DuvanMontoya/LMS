# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from domain.catalog.models import Subject, SubjectTeachingResponsibility
from domain.organizations.capabilities import Capability
from domain.organizations.choices import RoleCode
from domain.organizations.models import Organization
from domain.organizations.policies import (
    active_membership,
    active_roles,
    has_capability,
)

from .choices import AuthoringStatus
from .models import Course, CourseRevision, CourseTeachingException


def has_course_academic_responsibility(
    actor: object,
    organization: Organization,
    *,
    course: Course | None = None,
    subjects: list[Subject] | None = None,
) -> bool:
    membership = active_membership(actor, organization)  # type: ignore[arg-type]
    roles = active_roles(membership)
    if {RoleCode.OWNER, RoleCode.ADMINISTRATOR} & roles:
        return True
    if membership is None:
        return False
    today = timezone.localdate()
    active_responsibilities = SubjectTeachingResponsibility.objects.filter(
        membership=membership,
        starts_on__lte=today,
        ended_at__isnull=True,
    ).filter(Q(ends_on__isnull=True) | Q(ends_on__gte=today))
    if subjects is not None:
        subject_ids = {subject.id for subject in subjects}
        responsible_ids = set(
            active_responsibilities.filter(subject_id__in=subject_ids).values_list(
                "subject_id", flat=True
            )
        )
        return bool(subject_ids) and responsible_ids == subject_ids
    if course is None:
        return False
    has_exception = (
        CourseTeachingException.objects.filter(
            course=course,
            membership=membership,
            starts_on__lte=today,
            ended_at__isnull=True,
        )
        .filter(Q(ends_on__isnull=True) | Q(ends_on__gte=today))
        .exists()
    )
    if has_exception:
        return True
    return active_responsibilities.filter(
        subject__course_revision_alignments__revision__course=course
    ).exists()


def can_view_course_authoring(actor: object, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.COURSE_AUTHORING_VIEW)  # type: ignore[arg-type]


def can_view_approved_course(actor: object, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.COURSE_APPROVED_VIEW)  # type: ignore[arg-type]


def can_manage_course(actor: object, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.COURSE_AUTHORING_MANAGE)  # type: ignore[arg-type]


def can_submit_revision(actor: object, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.COURSE_AUTHORING_SUBMIT)  # type: ignore[arg-type]


def can_review_revision(actor: object, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.COURSE_AUTHORING_REVIEW)  # type: ignore[arg-type]


def can_approve_revision(actor: object, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.COURSE_AUTHORING_APPROVE)  # type: ignore[arg-type]


def can_view_revision(actor: object, revision: CourseRevision) -> bool:
    organization = revision.course.organization
    if revision.authoring_status == AuthoringStatus.APPROVED:
        return can_view_course_authoring(
            actor, organization
        ) or can_view_approved_course(actor, organization)
    return can_view_course_authoring(actor, organization)


def can_view_course(actor: object, course: Course) -> bool:
    organization = course.organization
    if can_view_course_authoring(actor, organization):
        return True
    return (
        can_view_approved_course(actor, organization)
        and course.revisions.filter(authoring_status=AuthoringStatus.APPROVED).exists()
    )
