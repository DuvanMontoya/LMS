class LearningDomainError(Exception):
    code = "learning_invalid"
    status_code = 400


class CohortNotFound(LearningDomainError):
    code = "cohort_not_found"
    status_code = 404


class LearningPermissionDenied(LearningDomainError):
    code = "learning_permission_denied"
    status_code = 403


class CohortArchived(LearningDomainError):
    code = "cohort_archived"
    status_code = 409


class CohortReleaseImmutable(LearningDomainError):
    code = "cohort_release_immutable"
    status_code = 409


class AccessWindowInvalid(LearningDomainError):
    code = "cohort_access_window_invalid"


class EnrollmentNotFound(LearningDomainError):
    code = "enrollment_not_found"
    status_code = 404


class EnrollmentAlreadyExists(LearningDomainError):
    code = "enrollment_already_exists"
    status_code = 409


class EnrollmentTransitionInvalid(LearningDomainError):
    code = "enrollment_transition_invalid"
    status_code = 409


class EnrollmentConflict(LearningDomainError):
    code = "enrollment_conflict"
    status_code = 409


class EnrollmentCohortMismatch(LearningDomainError):
    code = "enrollment_cohort_mismatch"


class EnrollmentReleaseUpgradeInvalid(LearningDomainError):
    code = "enrollment_release_upgrade_invalid"
    status_code = 409


class LearningAccessDenied(LearningDomainError):
    code = "learning_access_denied"
    status_code = 403


class LearningAccessNotStarted(LearningAccessDenied):
    code = "learning_access_not_started"


class LearningAccessEnded(LearningAccessDenied):
    code = "learning_access_ended"


class LearningAccessSuspended(LearningAccessDenied):
    code = "learning_access_suspended"


class LearningAccessRevoked(LearningAccessDenied):
    code = "learning_access_revoked"


class LearningPublicationWithdrawn(LearningAccessDenied):
    code = "learning_publication_withdrawn"


class LearningReleaseInvalid(LearningAccessDenied):
    code = "learning_release_invalid"


class LearningUnitNotFound(LearningDomainError):
    code = "learning_unit_not_found"
    status_code = 404


class LearningAssetAccessDenied(LearningDomainError):
    code = "asset_access_denied"
    status_code = 403


class LearningAssetNotInRelease(LearningDomainError):
    code = "asset_access_not_in_release"
    status_code = 404


class LearningPositionInvalid(LearningDomainError):
    code = "learning_position_invalid"


class LearningProgressConflict(LearningDomainError):
    code = "learning_progress_conflict"
    status_code = 409


class LearningUnitNotCompleted(LearningDomainError):
    code = "learning_unit_not_completed"
    status_code = 409
