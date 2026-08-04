# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

from domain.publishing.integrity import verify_release
from domain.publishing.models import CourseRelease
from domain.publishing.snapshots import (
    release_activity,
    release_outline,
    release_previous_next,
    release_unit,
)

from .exceptions import (
    LearningPositionInvalid,
    LearningReleaseInvalid,
    LearningUnitNotFound,
)


def verified_snapshot(release: CourseRelease) -> dict[str, Any]:
    if not verify_release(release).valid:
        raise LearningReleaseInvalid("El release asignado no superó la verificación.")
    snapshot = release.snapshot
    if not isinstance(snapshot, dict):
        raise LearningReleaseInvalid("El snapshot asignado es inválido.")
    return snapshot


def snapshot_outline(release: CourseRelease) -> list[dict[str, Any]]:
    return release_outline(verified_snapshot(release))


def snapshot_unit(release: CourseRelease, unit_id: uuid.UUID) -> dict[str, Any]:
    try:
        return release_unit(verified_snapshot(release), str(unit_id))
    except Exception as error:
        raise LearningUnitNotFound(
            "La unidad no existe en el release asignado."
        ) from error


def snapshot_activity(release: CourseRelease, activity_id: uuid.UUID) -> dict[str, Any]:
    try:
        return release_activity(verified_snapshot(release), str(activity_id))
    except Exception as error:
        raise LearningUnitNotFound(
            "La actividad no existe en el release asignado."
        ) from error


def snapshot_navigation(
    release: CourseRelease, unit_id: uuid.UUID
) -> dict[str, Any | None]:
    try:
        return release_previous_next(verified_snapshot(release), str(unit_id))
    except Exception as error:
        raise LearningUnitNotFound(
            "La unidad no existe en el release asignado."
        ) from error


def snapshot_unit_ids(release: CourseRelease) -> tuple[uuid.UUID, ...]:
    return tuple(
        uuid.UUID(unit["id"])
        for module in snapshot_outline(release)
        for unit in module["units"]
    )


def _nodes(document: object) -> Iterator[dict[str, Any]]:
    stack: list[object] = [document]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            yield current
            content = current.get("content")
            if isinstance(content, list):
                stack.extend(reversed(content))


def snapshot_node_ids(
    release: CourseRelease, unit_id: uuid.UUID
) -> frozenset[uuid.UUID]:
    unit = snapshot_unit(release, unit_id)
    delivery = unit.get("delivery")
    if not isinstance(delivery, dict) or delivery.get("kind") != "document":
        return frozenset()
    content = delivery.get("content")
    if not isinstance(content, dict):
        return frozenset()
    document = content.get("document")
    node_ids: set[uuid.UUID] = set()
    for node in _nodes(document):
        attrs = node.get("attrs")
        if isinstance(attrs, dict) and isinstance(attrs.get("nodeId"), str):
            node_ids.add(uuid.UUID(attrs["nodeId"]))
    return frozenset(node_ids)


def validate_snapshot_position(
    release: CourseRelease, unit_id: uuid.UUID, node_id: uuid.UUID | None
) -> None:
    snapshot_unit(release, unit_id)
    if node_id is not None and node_id not in snapshot_node_ids(release, unit_id):
        raise LearningPositionInvalid("El nodo no existe en la unidad asignada.")
