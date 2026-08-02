from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from domain.organizations.models import Organization

CalendarProvider = Callable[
    [object, Organization, datetime, datetime, UUID | None], list[dict[str, Any]]
]

_providers: dict[str, CalendarProvider] = {}


def register_calendar_provider(name: str, provider: CalendarProvider) -> None:
    existing = _providers.get(name)
    if existing is not None and existing is not provider:
        raise RuntimeError(f"calendar_provider_conflict:{name}")
    _providers[name] = provider


def external_calendar_events(
    *,
    actor: object,
    organization: Organization,
    starts_at: datetime,
    ends_at: datetime,
    course_id: UUID | None,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for name in sorted(_providers):
        events.extend(
            _providers[name](actor, organization, starts_at, ends_at, course_id)
        )
    return events
