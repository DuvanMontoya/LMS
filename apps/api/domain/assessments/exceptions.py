from __future__ import annotations


class AssessmentDomainError(Exception):
    code = "assessment_error"
    status_code = 400

    def __init__(self, message: str, *, path: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.path = path


class AssessmentConflict(AssessmentDomainError):
    code = "revision_conflict"
    status_code = 409


class AssessmentForbidden(AssessmentDomainError):
    code = "assessment_forbidden"
    status_code = 403


class AssessmentNotFound(AssessmentDomainError):
    code = "assessment_not_found"
    status_code = 404


class AssessmentInvalid(AssessmentDomainError):
    code = "assessment_invalid"


class AssessmentNotReady(AssessmentDomainError):
    code = "assessment_not_ready"


class AttemptUnavailable(AssessmentDomainError):
    code = "attempt_unavailable"
    status_code = 409


class AttemptExpired(AssessmentDomainError):
    code = "attempt_expired"
    status_code = 409
