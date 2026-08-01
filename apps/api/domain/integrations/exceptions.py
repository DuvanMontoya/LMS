class IntegrationDomainError(Exception):
    """Stable error base that never carries provider payloads or secrets."""


class IntegrationAccessDenied(IntegrationDomainError):
    pass


class IntegrationRevisionConflict(IntegrationDomainError):
    pass


class IntegrationConfigurationIncomplete(IntegrationDomainError):
    pass


class IntegrationConnectionUnavailable(IntegrationDomainError):
    pass
