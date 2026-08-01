from __future__ import annotations

from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from opentelemetry import trace

_FORBIDDEN = frozenset(
    {"body", "content", "email", "payload", "query", "response", "signed_url"}
)
P = ParamSpec("P")
R = TypeVar("R")


@contextmanager
def domain_span(
    name: str, attributes: Mapping[str, str | int | float | bool] | None = None
) -> Generator[Any]:
    safe = {
        key: value
        for key, value in (attributes or {}).items()
        if key.casefold() not in _FORBIDDEN
    }
    with trace.get_tracer("lms.domain").start_as_current_span(name) as span:
        for key, value in safe.items():
            span.set_attribute(key, value)
        yield span


def traced_domain_operation(name: str):
    def decorator(function: Callable[P, R]) -> Callable[P, R]:
        @wraps(function)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            with domain_span(name):
                return function(*args, **kwargs)

        return wrapped

    return decorator
