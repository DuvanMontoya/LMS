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


_ALL_CAPABILITIES = frozenset(Capability)
_MEMBER_READ_CAPABILITIES = frozenset(
    {
        Capability.ORGANIZATION_VIEW,
    }
)

ROLE_CAPABILITIES = MappingProxyType(
    {
        RoleCode.OWNER: _ALL_CAPABILITIES,
        RoleCode.ADMINISTRATOR: _ALL_CAPABILITIES
        - frozenset({Capability.ROLE_ASSIGN_OWNER}),
        RoleCode.AUTHOR: _MEMBER_READ_CAPABILITIES,
        RoleCode.REVIEWER: _MEMBER_READ_CAPABILITIES,
        RoleCode.INSTRUCTOR: _MEMBER_READ_CAPABILITIES,
        RoleCode.LEARNER: _MEMBER_READ_CAPABILITIES,
    }
)


def capabilities_for_roles(roles: set[RoleCode]) -> frozenset[Capability]:
    capabilities: set[Capability] = set()
    for role in roles:
        capabilities.update(ROLE_CAPABILITIES[role])
    return frozenset(capabilities)
