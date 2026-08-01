# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
from __future__ import annotations

import time
from typing import Any

from celery import signals
from opentelemetry import context, propagate, trace
from opentelemetry.trace import SpanKind, Status, StatusCode

from .metrics import celery_task_duration, celery_tasks, safe_attributes
from .sentry import initialize_sentry
from .telemetry import initialize_telemetry

_tracer = trace.get_tracer("lms.celery")


@signals.worker_process_init.connect
def initialize_worker_observability(**_: Any) -> None:
    initialize_sentry()
    initialize_telemetry()


@signals.before_task_publish.connect
def inject_trace_headers(headers: dict[str, Any] | None = None, **_: Any) -> None:
    if headers is not None:
        propagate.inject(headers)


@signals.task_prerun.connect
def start_task_span(task: Any = None, task_id: str | None = None, **_: Any) -> None:
    if task is None:
        return
    parent = propagate.extract(getattr(task.request, "headers", None) or {})
    span = _tracer.start_span(
        f"celery {task.name}", context=parent, kind=SpanKind.CONSUMER
    )
    token = context.attach(trace.set_span_in_context(span, parent))
    task.request._otel_span = span
    task.request._otel_token = token
    task.request._otel_started = time.perf_counter()
    span.set_attribute("messaging.system", "celery")
    span.set_attribute("messaging.operation.type", "process")
    if task_id:
        span.set_attribute("messaging.message.id", task_id)


def _finish_task(task: Any, outcome: str, error: BaseException | None = None) -> None:
    if task is None:
        return
    if getattr(task.request, "_otel_finished", False):
        return
    task.request._otel_finished = True
    span = getattr(task.request, "_otel_span", None)
    token = getattr(task.request, "_otel_token", None)
    started = getattr(task.request, "_otel_started", None)
    attributes = safe_attributes(
        {"task_name": str(getattr(task, "name", "unknown"))[:120], "outcome": outcome}
    )
    celery_tasks.add(1, attributes)
    if started is not None:
        celery_task_duration.record(time.perf_counter() - started, attributes)
    if span is not None:
        if error is not None:
            span.record_exception(error)
            span.set_status(Status(StatusCode.ERROR))
        else:
            span.set_status(Status(StatusCode.OK))
        span.end()
    if token is not None:
        context.detach(token)


@signals.task_postrun.connect
def finish_task_span(task: Any = None, state: str | None = None, **_: Any) -> None:
    _finish_task(task, "completed" if state == "SUCCESS" else "failed")


@signals.task_failure.connect
def fail_task_span(
    task: Any = None, exception: BaseException | None = None, **_: Any
) -> None:
    _finish_task(task, "failed", exception)
