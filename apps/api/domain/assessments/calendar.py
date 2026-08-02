# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from django.db.models import Q

from domain.organizations.models import Organization

from .choices import AssignmentStatus, DeliveryStatus
from .models import AssessmentDelivery
from .selectors import deliveries_for, learner_assignments

CALENDAR_NAMESPACE = uuid.UUID("cb79f70c-4adb-48eb-b260-3ad5004c4ad1")


def _event(
    *,
    delivery: AssessmentDelivery,
    boundary: str,
    at: datetime,
    actor_assignment_id: uuid.UUID | None,
) -> dict[str, Any]:
    release = delivery.course_release
    group_activity = delivery.course_group_activity
    event_id = uuid.uuid5(CALENDAR_NAMESPACE, f"{delivery.id}:{boundary}")
    is_open = boundary == "opens"
    href = (
        f"/organizaciones/{delivery.organization.slug}/evaluaciones/"
        f"mis-entregas/{actor_assignment_id}"
        if actor_assignment_id
        else (
            f"/organizaciones/{delivery.organization.slug}/evaluaciones/"
            f"entregas/{delivery.id}"
        )
    )
    return {
        "id": event_id,
        "groupId": delivery.id,
        "title": f"{'Abre' if is_open else 'Cierra'}: {delivery.name}",
        "start": at,
        "end": at + timedelta(minutes=1),
        "allDay": False,
        "editable": False,
        "startEditable": False,
        "durationEditable": False,
        "extendedProps": {
            "courseId": str(release.course_id) if release else None,
            "courseSlug": release.course.slug if release else None,
            "courseName": release.title if release else delivery.name,
            "courseGroupId": (
                str(group_activity.course_group_id) if group_activity else None
            ),
            "courseGroupName": (
                group_activity.course_group.name if group_activity else None
            ),
            "courseGroupActivityId": (
                str(group_activity.id) if group_activity else None
            ),
            "activityRequired": bool(group_activity and group_activity.required),
            "countsTowardProgress": bool(group_activity and group_activity.required),
            "attendanceThresholdMinutes": None,
            "eventType": f"assessment_{boundary}",
            "occurrenceStatus": delivery.status,
            "sessionId": None,
            "liveStatus": None,
            "hostName": "",
            "description": delivery.assessment_version.title,
            "recurring": False,
            "occurrenceVersion": delivery.lock_version,
            "canJoin": False,
            "canStart": False,
            "canModerate": False,
            "canShareScreen": False,
            "canEdit": False,
            "canDelete": False,
            "href": href,
        },
    }


def assessment_calendar_events(
    actor: object,
    organization: Organization,
    starts_at: datetime,
    ends_at: datetime,
    course_id: uuid.UUID | None,
) -> list[dict[str, Any]]:
    learner_rows = learner_assignments(actor=actor, organization=organization).filter(
        status=AssignmentStatus.ACTIVE
    )
    assignment_by_delivery = {
        row.delivery_id: row.id
        for row in learner_rows.select_related(
            "delivery__course_release__course",
            "delivery__course_group_activity__course_group",
        )
    }
    visible_ids = set(
        deliveries_for(organization, actor=actor).values_list("id", flat=True)
    ) | set(assignment_by_delivery)
    queryset = (
        AssessmentDelivery.objects.filter(
            id__in=visible_ids,
            status=DeliveryStatus.ACTIVE,
        )
        .filter(
            Q(opens_at__gte=starts_at, opens_at__lt=ends_at)
            | Q(closes_at__gte=starts_at, closes_at__lt=ends_at)
        )
        .select_related(
            "organization",
            "assessment_version",
            "course_release__course",
            "course_group_activity__course_group",
        )
    )
    if course_id is not None:
        queryset = queryset.filter(course_release__course_id=course_id)
    events: list[dict[str, Any]] = []
    for delivery in queryset:
        assignment_id = assignment_by_delivery.get(delivery.id)
        if delivery.opens_at and starts_at <= delivery.opens_at < ends_at:
            events.append(
                _event(
                    delivery=delivery,
                    boundary="opens",
                    at=delivery.opens_at,
                    actor_assignment_id=assignment_id,
                )
            )
        if delivery.closes_at and starts_at <= delivery.closes_at < ends_at:
            events.append(
                _event(
                    delivery=delivery,
                    boundary="closes",
                    at=delivery.closes_at,
                    actor_assignment_id=assignment_id,
                )
            )
    return events
