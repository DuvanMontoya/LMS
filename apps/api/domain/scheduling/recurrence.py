# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from itertools import islice
from typing import cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dateutil.rrule import rrulestr

from .exceptions import SchedulingInvalid

MAX_OCCURRENCES = 366
ALLOWED_FREQUENCIES = frozenset({"DAILY", "WEEKLY", "MONTHLY", "YEARLY"})


def validated_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise SchedulingInvalid("La zona horaria IANA no es válida.") from error


def materialized_windows(
    *,
    first_starts_at: datetime,
    duration_minutes: int,
    timezone_name: str,
    recurrence_rule: str,
) -> list[tuple[datetime, datetime]]:
    if first_starts_at.tzinfo is None:
        raise SchedulingInvalid("La fecha inicial debe incluir zona horaria.")
    zone = validated_timezone(timezone_name)
    local_start = first_starts_at.astimezone(zone)
    if not recurrence_rule.strip():
        local_end = local_start + timedelta(minutes=duration_minutes)
        return [(local_start.astimezone(UTC), local_end.astimezone(UTC))]

    normalized = recurrence_rule.strip().removeprefix("RRULE:").upper()
    try:
        parts = dict(item.split("=", 1) for item in normalized.split(";"))
    except ValueError as error:
        raise SchedulingInvalid("La RRULE contiene una parte inválida.") from error
    frequency = parts.get("FREQ")
    if frequency not in ALLOWED_FREQUENCIES:
        raise SchedulingInvalid(
            "La recurrencia académica sólo admite DAILY, WEEKLY, MONTHLY o YEARLY."
        )
    if ("COUNT" in parts) == ("UNTIL" in parts):
        raise SchedulingInvalid("La RRULE debe incluir exactamente COUNT o UNTIL.")
    if "COUNT" in parts:
        try:
            count = int(parts["COUNT"])
        except ValueError as error:
            raise SchedulingInvalid("COUNT no es válido.") from error
        if count < 1 or count > MAX_OCCURRENCES:
            raise SchedulingInvalid("COUNT debe estar entre 1 y 366.")
    try:
        parsed = rrulestr(normalized, dtstart=local_start)
        starts = list(islice(cast(Iterable[datetime], parsed), MAX_OCCURRENCES + 1))
    except (TypeError, ValueError, OverflowError) as error:
        raise SchedulingInvalid("La RRULE no es válida para DTSTART.") from error
    if not starts or len(starts) > MAX_OCCURRENCES:
        raise SchedulingInvalid("La recurrencia excede 366 ocurrencias.")
    windows: list[tuple[datetime, datetime]] = []
    seen: set[datetime] = set()
    for start in starts:
        aware = start if start.tzinfo else start.replace(tzinfo=zone)
        original = aware.astimezone(UTC)
        if original in seen:
            continue
        seen.add(original)
        local_end = aware.astimezone(zone) + timedelta(minutes=duration_minutes)
        windows.append((original, local_end.astimezone(UTC)))
    return windows


def rule_until(
    recurrence_rule: str, windows: list[tuple[datetime, datetime]]
) -> datetime | None:
    if re.search(r"(?:^|;)UNTIL=", recurrence_rule.upper()):
        return windows[-1][0]
    return None
