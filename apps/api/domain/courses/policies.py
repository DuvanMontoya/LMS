# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from domain.organizations.capabilities import Capability
from domain.organizations.models import Organization
from domain.organizations.policies import has_capability

from .choices import AuthoringStatus
from .models import Course, CourseRevision


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
