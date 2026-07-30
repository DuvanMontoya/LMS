from __future__ import annotations

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from domain.courses.models import CourseRevision, CourseUnit

from .models import UnitContentDocument, UnitContentVersion
from .policies import can_view_unit_content


def content_visible_to_actor(
    actor: object, revision: CourseRevision
) -> QuerySet[UnitContentDocument]:
    if not can_view_unit_content(actor, revision):
        return UnitContentDocument.objects.none()
    return UnitContentDocument.objects.filter(
        unit__module__revision=revision
    ).select_related(
        "unit__module__revision__course__organization",
        "current_version",
        "created_by",
        "updated_by",
    )


def scoped_unit(revision: CourseRevision, unit_id: str) -> CourseUnit:
    return get_object_or_404(
        CourseUnit.objects.select_related("module__revision__course__organization"),
        pk=unit_id,
        module__revision=revision,
    )


def current_unit_content(
    actor: object, revision: CourseRevision, unit: CourseUnit
) -> UnitContentDocument | None:
    return (
        content_visible_to_actor(actor, revision)
        .filter(unit=unit)
        .select_related("current_version")
        .first()
    )


def unit_content_versions(
    actor: object, revision: CourseRevision, unit: CourseUnit
) -> QuerySet[UnitContentVersion]:
    document = current_unit_content(actor, revision, unit)
    if document is None:
        return UnitContentVersion.objects.none()
    return (
        UnitContentVersion.objects.filter(document=document)
        .select_related("created_by")
        .defer("content", "plain_text")
        .order_by("-number")
    )


def unit_content_version(
    actor: object,
    revision: CourseRevision,
    unit: CourseUnit,
    version_number: int,
) -> UnitContentVersion:
    document = current_unit_content(actor, revision, unit)
    return get_object_or_404(
        UnitContentVersion.objects.select_related("created_by", "document"),
        document=document,
        number=version_number,
    )
