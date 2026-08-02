# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from domain.organizations.choices import MembershipStatus
from domain.publishing.choices import PublicationStatus

from .choices import AccessState, EnrollmentStatus
from .exceptions import (
    LearningAccessDenied,
    LearningAccessEnded,
    LearningAccessNotStarted,
    LearningAccessRevoked,
    LearningAccessSuspended,
    LearningPublicationWithdrawn,
    LearningReleaseInvalid,
)
from .models import CourseEnrollment, EnrollmentReleaseAssignment
from .policies import can_access_enrollment_learning
from .snapshots import verified_snapshot


@dataclass(frozen=True)
class LearningAccess:
    enrollment: CourseEnrollment
    assignment: EnrollmentReleaseAssignment
    state: AccessState


def access_state(
    enrollment: CourseEnrollment, *, at: datetime | None = None
) -> AccessState:
    now = at or timezone.now()
    if enrollment.status == EnrollmentStatus.REVOKED:
        return AccessState.REVOKED
    if enrollment.status == EnrollmentStatus.SUSPENDED:
        return AccessState.SUSPENDED
    if enrollment.membership.status != MembershipStatus.ACTIVE:
        return AccessState.MEMBERSHIP_INACTIVE
    access_starts_at, access_ends_at = enrollment.effective_access_window()
    if access_starts_at and now < access_starts_at:
        return AccessState.NOT_STARTED
    if access_ends_at and now >= access_ends_at:
        return AccessState.ENDED
    try:
        publication = enrollment.course.publication
    except ObjectDoesNotExist:
        publication = None
    if publication is None or publication.status != PublicationStatus.ACTIVE:
        return AccessState.PUBLICATION_WITHDRAWN
    assignment = enrollment.current_release_assignment
    if assignment is None or assignment.ended_at is not None:
        return AccessState.RELEASE_INVALID
    try:
        verified_snapshot(assignment.release)
    except LearningReleaseInvalid:
        return AccessState.RELEASE_INVALID
    return AccessState.AVAILABLE


def require_learning_access(
    *, actor: object, enrollment: CourseEnrollment
) -> LearningAccess:
    if not can_access_enrollment_learning(actor, enrollment):  # type: ignore[arg-type]
        raise LearningAccessDenied("La matrícula no pertenece al usuario.")
    state = access_state(enrollment)
    errors = {
        AccessState.NOT_STARTED: LearningAccessNotStarted,
        AccessState.ENDED: LearningAccessEnded,
        AccessState.SUSPENDED: LearningAccessSuspended,
        AccessState.REVOKED: LearningAccessRevoked,
        AccessState.PUBLICATION_WITHDRAWN: LearningPublicationWithdrawn,
        AccessState.MEMBERSHIP_INACTIVE: LearningAccessDenied,
        AccessState.RELEASE_INVALID: LearningReleaseInvalid,
    }
    error = errors.get(state)
    if error:
        raise error("La matrícula no tiene acceso efectivo.")
    assignment = enrollment.current_release_assignment
    if assignment is None:
        raise LearningReleaseInvalid("La matrícula no tiene release asignado.")
    return LearningAccess(enrollment=enrollment, assignment=assignment, state=state)
