from __future__ import annotations


class ContentDomainError(Exception):
    code = "content_error"

    def __init__(self, message: str, *, path: str = "content") -> None:
        super().__init__(message)
        self.message = message
        self.path = path


class ContentAccessDenied(ContentDomainError):
    code = "content_permission_denied"


class ContentNotEditable(ContentDomainError):
    code = "content_not_editable"


class ContentNotApplicable(ContentDomainError):
    code = "content_not_applicable"


class ContentDeliveryInvalid(ContentDomainError):
    code = "content_delivery_invalid"


class ContentDocumentConflict(ContentDomainError):
    code = "content_conflict"

    def __init__(
        self, message: str, *, current_version: int, path: str = "document_version"
    ) -> None:
        super().__init__(message, path=path)
        self.current_version = current_version


class ContentSchemaUnsupported(ContentDomainError):
    code = "content_schema_unsupported"


class ContentSchemaInvalid(ContentDomainError):
    code = "content_schema_invalid"


class ContentTooLarge(ContentDomainError):
    code = "content_too_large"


class ContentTooDeep(ContentDomainError):
    code = "content_too_deep"


class ContentNodeLimitExceeded(ContentDomainError):
    code = "content_node_limit_exceeded"


class ContentDuplicateNodeId(ContentDomainError):
    code = "content_duplicate_node_id"


class ContentUnsafeLink(ContentDomainError):
    code = "content_unsafe_link"


class ContentUnsafeMath(ContentDomainError):
    code = "content_unsafe_math"


class ContentInvalidCodeLanguage(ContentDomainError):
    code = "content_invalid_code_language"


class ContentVersionNotFound(ContentDomainError):
    code = "content_version_not_found"


class ContentRestoreInvalid(ContentDomainError):
    code = "content_restore_invalid"


class ContentDigestMismatch(ContentDomainError):
    code = "content_digest_mismatch"
