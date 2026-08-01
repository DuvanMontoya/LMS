# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
from __future__ import annotations

import re
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

Payload = Mapping[str, Any]
PayloadValidator = Callable[[Payload], None]
Consumer = Callable[["DomainEvent"], None]


@dataclass(frozen=True)
class EventDefinition:
    event_type: str
    schema_version: int
    validator: PayloadValidator
    retention_category: str
    allow_global: bool = False


@dataclass(frozen=True)
class ConsumerDefinition:
    name: str
    event_types: frozenset[str]
    handler: Consumer


_events: dict[str, EventDefinition] = {}
_consumers: dict[str, ConsumerDefinition] = {}
_EVENT_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){2}\.v([1-9][0-9]*)$")


def id_payload(*required: str, optional: tuple[str, ...] = ()) -> PayloadValidator:
    allowed = frozenset(required) | frozenset(optional)

    def validate(payload: Payload) -> None:
        keys = set(payload)
        if not set(required).issubset(keys) or not keys.issubset(allowed):
            raise ValueError("El payload no coincide con el schema del evento.")
        for field in required:
            if field.endswith("_id"):
                uuid.UUID(str(payload[field]))

    return validate


def register_event(definition: EventDefinition) -> None:
    match = _EVENT_RE.fullmatch(definition.event_type)
    if not match or int(match.group(2)) != definition.schema_version:
        raise RuntimeError(f"Event type inválido: {definition.event_type}")
    existing = _events.get(definition.event_type)
    if existing is not None and existing != definition:
        raise RuntimeError(f"Event type ya registrado: {definition.event_type}")
    _events[definition.event_type] = definition


def register_consumer(definition: ConsumerDefinition) -> None:
    unknown = definition.event_types - _events.keys()
    if unknown:
        raise RuntimeError(
            f"Eventos desconocidos para {definition.name}: {sorted(unknown)}"
        )
    existing = _consumers.get(definition.name)
    if existing is not None and existing != definition:
        raise RuntimeError(f"Consumer ya registrado: {definition.name}")
    _consumers[definition.name] = definition


def event_definition(event_type: str) -> EventDefinition:
    try:
        return _events[event_type]
    except KeyError as exc:
        raise ValueError("Event type no registrado.") from exc


def consumer_definition(name: str) -> ConsumerDefinition:
    try:
        return _consumers[name]
    except KeyError as exc:
        raise ValueError("Consumer no registrado.") from exc


def consumer_names_for_event(event_type: str) -> tuple[str, ...]:
    return tuple(
        sorted(
            name for name, item in _consumers.items() if event_type in item.event_types
        )
    )


def registered_events() -> Mapping[str, EventDefinition]:
    return MappingProxyType(_events)


def registered_consumers() -> Mapping[str, ConsumerDefinition]:
    return MappingProxyType(_consumers)


EVENT_TYPES = frozenset(
    {
        "publishing.course_release.published.v1",
        "publishing.course_publication.withdrawn.v1",
        "learning.enrollment.created.v1",
        "learning.enrollment.suspended.v1",
        "learning.enrollment.reactivated.v1",
        "learning.enrollment.revoked.v1",
        "learning.course_progress.completed.v1",
        "assessments.attempt.graded.v1",
        "assessments.attempt.pending_manual.v1",
        "assessments.regrade.completed.v1",
        "assets.asset_version.ready.v1",
        "assets.asset_version.rejected.v1",
        "assets.asset_version.failed.v1",
        "courses.revision.submitted.v1",
        "courses.revision.changes_requested.v1",
        "courses.revision.approved.v1",
        "assessments.question_revision.changes_requested.v1",
        "assessments.question_revision.approved.v1",
        "assessments.assessment_revision.changes_requested.v1",
        "assessments.assessment_revision.approved.v1",
    }
)

for _event_type in EVENT_TYPES:
    aggregate = _event_type.split(".")[1]
    register_event(
        EventDefinition(
            event_type=_event_type,
            schema_version=1,
            validator=id_payload(
                f"{aggregate}_id",
                optional=(
                    "course_id",
                    "release_id",
                    "membership_id",
                    "user_id",
                    "question_version_id",
                    "assessment_version_id",
                ),
            ),
            retention_category="academic",
        )
    )


from .models import DomainEvent  # noqa: E402
