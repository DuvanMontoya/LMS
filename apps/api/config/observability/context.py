from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass

_FIELDS = (
    "request_id",
    "correlation_id",
    "causation_id",
    "event_id",
    "task_id",
    "trace_id",
    "span_id",
)
_context: dict[str, ContextVar[str | None]] = {
    field: ContextVar(f"lms_{field}", default=None) for field in _FIELDS
}


@dataclass(frozen=True)
class ContextTokens:
    values: dict[str, Token[str | None]]


def bind_context(**values: object) -> ContextTokens:
    tokens: dict[str, Token[str | None]] = {}
    for key, value in values.items():
        variable = _context.get(key)
        if variable is not None:
            tokens[key] = variable.set(str(value) if value is not None else None)
    return ContextTokens(tokens)


def reset_context(tokens: ContextTokens) -> None:
    for key, token in tokens.values.items():
        _context[key].reset(token)


def clear_context() -> None:
    for variable in _context.values():
        variable.set(None)


def current_context() -> dict[str, str]:
    return {
        key: value
        for key, variable in _context.items()
        if (value := variable.get()) is not None
    }
