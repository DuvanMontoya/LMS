class CatalogDomainError(Exception):
    """A safe, typed domain error mapped only at the HTTP boundary."""


class CatalogAccessDenied(CatalogDomainError):
    pass


class CatalogEntityNotFound(CatalogDomainError):
    pass


class CatalogEntityArchived(CatalogDomainError):
    pass


class ReservedSlug(CatalogDomainError):
    pass


class ImmutableSlug(CatalogDomainError):
    pass


class CrossOrganizationRelation(CatalogDomainError):
    pass


class ActiveChildrenExist(CatalogDomainError):
    pass


class ActiveDependenciesExist(CatalogDomainError):
    pass


class InvalidTopicMove(CatalogDomainError):
    pass


class TopicDepthExceeded(CatalogDomainError):
    pass


class TreeIntegrityViolation(CatalogDomainError):
    pass


class DuplicateAssociation(CatalogDomainError):
    pass


class InvalidAssociationOrder(CatalogDomainError):
    pass


class PrerequisiteCycle(CatalogDomainError):
    pass


class PrerequisiteSelfReference(CatalogDomainError):
    pass


class PrerequisiteTargetArchived(CatalogDomainError):
    pass
