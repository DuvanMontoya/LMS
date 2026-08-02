# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from collections.abc import Callable
from types import MappingProxyType
from typing import Any

from .choices import ActivityType
from .models import CourseActivity

ActivitySnapshotProvider = Callable[[CourseActivity], dict[str, Any]]
ActivityCloneProvider = Callable[[CourseActivity, CourseActivity, Any], None]

_SNAPSHOT_PROVIDERS: dict[str, ActivitySnapshotProvider] = {}
_CLONE_PROVIDERS: dict[str, ActivityCloneProvider] = {}


def register_activity_provider(
    activity_type: ActivityType,
    *,
    snapshot: ActivitySnapshotProvider,
    clone: ActivityCloneProvider,
) -> None:
    key = str(activity_type)
    if key == ActivityType.LESSON.value:
        raise ValueError("La lección usa el contrato interno de CourseUnit.")
    if key in _SNAPSHOT_PROVIDERS or key in _CLONE_PROVIDERS:
        raise ValueError(f"El provider de actividad '{key}' ya existe.")
    _SNAPSHOT_PROVIDERS[key] = snapshot
    _CLONE_PROVIDERS[key] = clone


def registered_activity_providers():
    return MappingProxyType(_SNAPSHOT_PROVIDERS)


def activity_binding_snapshot(activity: CourseActivity) -> dict[str, Any]:
    if activity.activity_type == ActivityType.LESSON:
        if activity.lesson_unit_id is None:
            raise ValueError("La lección no tiene unidad vinculada.")
        return {"provider": "content", "unit_id": str(activity.lesson_unit_id)}
    provider = _SNAPSHOT_PROVIDERS.get(activity.activity_type)
    if provider is None:
        raise ValueError(
            f"No existe provider para la actividad '{activity.activity_type}'."
        )
    return provider(activity)


def clone_activity_binding(
    *, source: CourseActivity, target: CourseActivity, actor: Any
) -> None:
    if source.activity_type == ActivityType.LESSON:
        return
    provider = _CLONE_PROVIDERS.get(source.activity_type)
    if provider is None:
        raise ValueError(
            f"No existe provider de clonación para '{source.activity_type}'."
        )
    provider(source, target, actor)
