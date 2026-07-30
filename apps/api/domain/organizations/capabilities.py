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


_ALL_CAPABILITIES = frozenset(Capability)
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
    }
)

ROLE_CAPABILITIES = MappingProxyType(
    {
        RoleCode.OWNER: _ALL_CAPABILITIES,
        RoleCode.ADMINISTRATOR: _ALL_CAPABILITIES
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
            }
        ),
        RoleCode.INSTRUCTOR: _MEMBER_READ_CAPABILITIES
        | frozenset(
            {
                Capability.CATALOG_VIEW,
                Capability.COURSE_APPROVED_VIEW,
                Capability.COURSE_PUBLISHED_VIEW,
            }
        ),
        RoleCode.LEARNER: _MEMBER_READ_CAPABILITIES
        | frozenset({Capability.CATALOG_VIEW, Capability.COURSE_PUBLISHED_VIEW}),
    }
)


def capabilities_for_roles(roles: set[RoleCode]) -> frozenset[Capability]:
    capabilities: set[Capability] = set()
    for role in roles:
        capabilities.update(ROLE_CAPABILITIES[role])
    return frozenset(capabilities)
