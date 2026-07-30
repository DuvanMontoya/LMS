from enum import StrEnum
from types import MappingProxyType

from .choices import RoleCode


class Capability(StrEnum):
    ORGANIZATION_VIEW = "organization.view"
    ORGANIZATION_UPDATE = "organization.update"
    MEMBERSHIP_VIEW = "membership.view"
    MEMBERSHIP_ADD = "membership.add"
    MEMBERSHIP_SUSPEND = "membership.suspend"
    MEMBERSHIP_REACTIVATE = "membership.reactivate"
    MEMBERSHIP_REVOKE = "membership.revoke"
    ROLE_VIEW = "role.view"
    ROLE_ASSIGN = "role.assign"
    ROLE_ASSIGN_OWNER = "role.assign_owner"
    MEMBERSHIP_EVENT_VIEW = "membership_event.view"
    CATALOG_VIEW = "catalog.view"
    CATALOG_MANAGE = "catalog.manage"
    CATALOG_MANAGE_PREREQUISITES = "catalog.manage_prerequisites"
    COURSE_AUTHORING_VIEW = "course.authoring.view"
    COURSE_AUTHORING_MANAGE = "course.authoring.manage"
    COURSE_AUTHORING_SUBMIT = "course.authoring.submit"
    COURSE_AUTHORING_REVIEW = "course.authoring.review"
    COURSE_AUTHORING_APPROVE = "course.authoring.approve"
    COURSE_APPROVED_VIEW = "course.approved.view"
    COURSE_RELEASE_PUBLISH = "course.release.publish"
    COURSE_RELEASE_WITHDRAW = "course.release.withdraw"
    COURSE_RELEASE_HISTORY_VIEW = "course.release.history.view"
    COURSE_RELEASE_CREATE_DRAFT = "course.release.create_draft"
    COURSE_PUBLISHED_VIEW = "course.published.view"
    LEARNING_COHORT_VIEW = "learning.cohort.view"
    LEARNING_COHORT_MANAGE = "learning.cohort.manage"
    LEARNING_ENROLLMENT_VIEW = "learning.enrollment.view"
    LEARNING_ENROLLMENT_MANAGE = "learning.enrollment.manage"
    LEARNING_PROGRESS_VIEW = "learning.progress.view"
    LEARNING_PROGRESS_MANAGE = "learning.progress.manage"
    ASSESSMENT_BANK_VIEW = "assessment.bank.view"
    ASSESSMENT_BANK_MANAGE = "assessment.bank.manage"
    ASSESSMENT_BANK_VERSION = "assessment.bank.version"
    ASSESSMENT_QUESTION_VIEW = "assessment.question.view"
    ASSESSMENT_QUESTION_MANAGE = "assessment.question.manage"
    ASSESSMENT_QUESTION_SUBMIT = "assessment.question.submit"
    ASSESSMENT_QUESTION_REVIEW = "assessment.question.review"
    ASSESSMENT_QUESTION_APPROVE = "assessment.question.approve"
    ASSESSMENT_AUTHORING_VIEW = "assessment.authoring.view"
    ASSESSMENT_AUTHORING_MANAGE = "assessment.authoring.manage"
    ASSESSMENT_AUTHORING_SUBMIT = "assessment.authoring.submit"
    ASSESSMENT_AUTHORING_REVIEW = "assessment.authoring.review"
    ASSESSMENT_AUTHORING_APPROVE = "assessment.authoring.approve"
    ASSESSMENT_DELIVERY_VIEW = "assessment.delivery.view"
    ASSESSMENT_DELIVERY_MANAGE = "assessment.delivery.manage"
    ASSESSMENT_GRADING_MANAGE = "assessment.grading.manage"
    ASSESSMENT_RESULTS_VIEW = "assessment.results.view"
    ASSESSMENT_ATTEMPT = "assessment.attempt"


_ALL_CAPABILITIES = frozenset(Capability)
_ALL_ADMIN_CAPABILITIES = _ALL_CAPABILITIES - frozenset({Capability.ASSESSMENT_ATTEMPT})
_MEMBER_READ_CAPABILITIES = frozenset(
    {
        Capability.ORGANIZATION_VIEW,
    }
)
_CATALOG_MANAGER_CAPABILITIES = frozenset(
    {
        Capability.CATALOG_VIEW,
        Capability.CATALOG_MANAGE,
        Capability.CATALOG_MANAGE_PREREQUISITES,
    }
)
_COURSE_AUTHOR_CAPABILITIES = frozenset(
    {
        Capability.COURSE_AUTHORING_VIEW,
        Capability.COURSE_AUTHORING_MANAGE,
        Capability.COURSE_AUTHORING_SUBMIT,
        Capability.COURSE_APPROVED_VIEW,
        Capability.COURSE_RELEASE_HISTORY_VIEW,
        Capability.COURSE_RELEASE_CREATE_DRAFT,
        Capability.COURSE_PUBLISHED_VIEW,
        Capability.LEARNING_COHORT_VIEW,
        Capability.LEARNING_ENROLLMENT_VIEW,
        Capability.LEARNING_PROGRESS_VIEW,
        Capability.ASSESSMENT_BANK_VIEW,
        Capability.ASSESSMENT_BANK_MANAGE,
        Capability.ASSESSMENT_BANK_VERSION,
        Capability.ASSESSMENT_QUESTION_VIEW,
        Capability.ASSESSMENT_QUESTION_MANAGE,
        Capability.ASSESSMENT_QUESTION_SUBMIT,
        Capability.ASSESSMENT_AUTHORING_VIEW,
        Capability.ASSESSMENT_AUTHORING_MANAGE,
        Capability.ASSESSMENT_AUTHORING_SUBMIT,
        Capability.ASSESSMENT_DELIVERY_VIEW,
        Capability.ASSESSMENT_RESULTS_VIEW,
    }
)

ROLE_CAPABILITIES = MappingProxyType(
    {
        RoleCode.OWNER: _ALL_ADMIN_CAPABILITIES,
        RoleCode.ADMINISTRATOR: _ALL_ADMIN_CAPABILITIES
        - frozenset({Capability.ROLE_ASSIGN_OWNER}),
        RoleCode.AUTHOR: _MEMBER_READ_CAPABILITIES
        | _CATALOG_MANAGER_CAPABILITIES
        | _COURSE_AUTHOR_CAPABILITIES,
        RoleCode.REVIEWER: _MEMBER_READ_CAPABILITIES
        | frozenset(
            {
                Capability.CATALOG_VIEW,
                Capability.COURSE_AUTHORING_VIEW,
                Capability.COURSE_AUTHORING_REVIEW,
                Capability.COURSE_APPROVED_VIEW,
                Capability.COURSE_RELEASE_HISTORY_VIEW,
                Capability.COURSE_PUBLISHED_VIEW,
                Capability.LEARNING_PROGRESS_VIEW,
                Capability.ASSESSMENT_BANK_VIEW,
                Capability.ASSESSMENT_QUESTION_VIEW,
                Capability.ASSESSMENT_QUESTION_REVIEW,
                Capability.ASSESSMENT_AUTHORING_VIEW,
                Capability.ASSESSMENT_AUTHORING_REVIEW,
                Capability.ASSESSMENT_DELIVERY_VIEW,
                Capability.ASSESSMENT_RESULTS_VIEW,
            }
        ),
        RoleCode.INSTRUCTOR: _MEMBER_READ_CAPABILITIES
        | frozenset(
            {
                Capability.CATALOG_VIEW,
                Capability.COURSE_APPROVED_VIEW,
                Capability.COURSE_PUBLISHED_VIEW,
                Capability.LEARNING_COHORT_VIEW,
                Capability.LEARNING_ENROLLMENT_VIEW,
                Capability.LEARNING_PROGRESS_VIEW,
                Capability.ASSESSMENT_BANK_VIEW,
                Capability.ASSESSMENT_QUESTION_VIEW,
                Capability.ASSESSMENT_AUTHORING_VIEW,
                Capability.ASSESSMENT_DELIVERY_VIEW,
                Capability.ASSESSMENT_DELIVERY_MANAGE,
                Capability.ASSESSMENT_GRADING_MANAGE,
                Capability.ASSESSMENT_RESULTS_VIEW,
            }
        ),
        RoleCode.LEARNER: _MEMBER_READ_CAPABILITIES
        | frozenset({Capability.ASSESSMENT_ATTEMPT}),
    }
)


def capabilities_for_roles(roles: set[RoleCode]) -> frozenset[Capability]:
    capabilities: set[Capability] = set()
    for role in roles:
        capabilities.update(ROLE_CAPABILITIES[role])
    return frozenset(capabilities)
