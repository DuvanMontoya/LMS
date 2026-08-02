# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportArgumentType=false
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

from domain.learning.contracts import (
    actor_has_course_group_staff_scope,
    effective_course_enrollment,
    effective_course_group_enrollment,
    effective_enrollments_for_actor,
)
from domain.organizations.capabilities import Capability
from domain.organizations.models import Membership, Organization
from domain.organizations.policies import active_membership, has_capability

from .choices import AttendanceRole
from .models import AcademicEventSeries, LiveSession


@dataclass(frozen=True)
class LiveAccess:
    role: AttendanceRole
    can_publish: bool
    can_share_screen: bool
    can_moderate: bool


def can_view_schedule(actor: object, organization: Organization) -> bool:
    membership = active_membership(actor, organization)  # type: ignore[arg-type]
    return (
        has_capability(  # type: ignore[arg-type]
            actor, organization, Capability.SCHEDULING_VIEW
        )
        or effective_enrollments_for_actor(
            actor=actor, organization=organization
        ).exists()
        or bool(
            membership
            and membership.scheduled_event_participations.filter(
                series__status="active"
            ).exists()
        )
    )


def can_create_schedule(actor: object, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.SCHEDULING_CREATE)  # type: ignore[arg-type]


def can_manage_schedule(actor: object, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.SCHEDULING_MANAGE)  # type: ignore[arg-type]


def actor_membership(actor: object, organization: Organization) -> Membership | None:
    return active_membership(actor, organization)  # type: ignore[arg-type]


def can_edit_series(actor: object, series: AcademicEventSeries) -> bool:
    membership = actor_membership(actor, series.organization)
    return can_manage_schedule(actor, series.organization) or bool(
        membership
        and membership.id == series.host_membership_id
        and can_create_schedule(actor, series.organization)
    )


def live_access(
    *, actor: object, session: LiveSession, at: datetime | None = None
) -> LiveAccess | None:
    organization = session.occurrence.series.organization
    membership = actor_membership(actor, organization)
    if (
        membership
        and membership.id == session.occurrence.series.host_membership_id
        and has_capability(actor, organization, Capability.LIVE_SESSION_HOST)  # type: ignore[arg-type]
        and (
            session.occurrence.series.course_group_id is None
            or actor_has_course_group_staff_scope(
                actor=actor, course_group=session.occurrence.series.course_group
            )
        )
    ):
        return LiveAccess(
            role=AttendanceRole.HOST,
            can_publish=True,
            can_share_screen=True,
            can_moderate=has_capability(
                actor,
                organization,
                Capability.LIVE_SESSION_MODERATE,  # type: ignore[arg-type]
            ),
        )
    if can_manage_schedule(actor, organization):
        return LiveAccess(
            role=AttendanceRole.ADMINISTRATOR,
            can_publish=True,
            can_share_screen=True,
            can_moderate=True,
        )
    series = session.occurrence.series
    if series.course_group_id:
        enrollment = effective_course_group_enrollment(
            actor=actor,
            organization=organization,
            course_group=series.course_group,
            at=at or timezone.now(),
        )
        if enrollment is None:
            return None
    elif series.course_id:
        enrollment = effective_course_enrollment(
            actor=actor,
            organization=organization,
            course=series.course,
            at=at or timezone.now(),
        )
        if enrollment is None:
            return None
    elif (
        membership is None
        or not series.participants.filter(membership=membership).exists()
    ):
        return None
    return LiveAccess(
        role=AttendanceRole.STUDENT,
        can_publish=True,
        can_share_screen=False,
        can_moderate=False,
    )
