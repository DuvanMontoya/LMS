class PublishingDomainError(Exception):
    """Error de dominio seguro traducible solamente en el borde HTTP."""


class PublicationAccessDenied(PublishingDomainError):
    pass


class PublicationConflict(PublishingDomainError):
    pass


class PublicationNotFound(PublishingDomainError):
    pass


class PublicationTransitionInvalid(PublishingDomainError):
    pass


class ReleaseNotFound(PublishingDomainError):
    pass


class ReleaseAlreadyExists(PublishingDomainError):
    pass


class ReleaseSourceNotApproved(PublishingDomainError):
    pass


class ReleaseSourceNotNewer(PublishingDomainError):
    pass


class ReleaseSnapshotInvalid(PublishingDomainError):
    pass


class ReleaseSnapshotTooLarge(PublishingDomainError):
    pass


class ReleaseChainInvalid(PublishingDomainError):
    pass


class ReleaseIntegrityFailed(PublishingDomainError):
    pass


class DraftAlreadyOpen(PublishingDomainError):
    pass


class DraftCreationInvalid(PublishingDomainError):
    pass


class WithdrawalNoteRequired(PublishingDomainError):
    pass
