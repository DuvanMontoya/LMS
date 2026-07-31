class AssetDomainError(Exception):
    code = "asset_error"


class AssetAccessDenied(AssetDomainError):
    code = "asset_access_denied"


class AssetNotFound(AssetDomainError):
    code = "asset_not_found"


class AssetConflict(AssetDomainError):
    code = "asset_conflict"


class AssetUploadInvalid(AssetDomainError):
    code = "upload_invalid"


class AssetUploadExpired(AssetDomainError):
    code = "upload_expired"


class AssetUploadRateLimited(AssetDomainError):
    code = "upload_rate_limited"


class AssetStorageError(AssetDomainError):
    code = "storage_error"


class AssetProcessingError(AssetDomainError):
    code = "processing_error"


class AssetMalwareDetected(AssetProcessingError):
    code = "malware_detected"


class AssetFormatInvalid(AssetProcessingError):
    code = "format_invalid"


class AssetChecksumMismatch(AssetProcessingError):
    code = "checksum_mismatch"
