class OrganizationDomainError(Exception):
    """Base error kept independent from HTTP adapters."""


class OrganizationAccessDenied(OrganizationDomainError):
    pass


class MembershipNotActive(OrganizationDomainError):
    pass


class InvalidMembershipTransition(OrganizationDomainError):
    pass


class LastOwnerViolation(OrganizationDomainError):
    pass


class RoleAssignmentDenied(OrganizationDomainError):
    pass


class RoleAlreadyAssigned(OrganizationDomainError):
    pass


class RoleNotAssigned(OrganizationDomainError):
    pass


class MemberAlreadyExists(OrganizationDomainError):
    pass


class VerifiedUserRequired(OrganizationDomainError):
    pass


class InitialOwnerUnavailable(OrganizationDomainError):
    pass


class RevisionConflict(OrganizationDomainError):
    pass


class InvitationUnavailable(OrganizationDomainError):
    pass


class InvitationAlreadyExists(OrganizationDomainError):
    pass


class JoinRequestUnavailable(OrganizationDomainError):
    pass


class JoinRequestAlreadyExists(OrganizationDomainError):
    pass


class ManagedAccountsDisabled(OrganizationDomainError):
    pass
