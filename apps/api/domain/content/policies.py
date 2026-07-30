# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
from __future__ import annotations

from domain.courses.choices import EDITABLE_AUTHORING_STATUSES
from domain.courses.models import CourseRevision
from domain.courses.policies import can_manage_course, can_view_revision


def can_view_unit_content(actor: object, revision: CourseRevision) -> bool:
    return can_view_revision(actor, revision)


def can_edit_unit_content(actor: object, revision: CourseRevision) -> bool:
    return (
        can_manage_course(actor, revision.course.organization)
        and revision.authoring_status in EDITABLE_AUTHORING_STATUSES
    )
