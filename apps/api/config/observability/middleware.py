from __future__ import annotations

import time
import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from opentelemetry import propagate, trace
from opentelemetry.trace import SpanKind, Status, StatusCode

from .context import bind_context, reset_context
from .metrics import http_request_duration, http_requests, safe_attributes
from .sentry import initialize_sentry
from .telemetry import initialize_telemetry


class RequestIdMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        initialize_sentry()
        initialize_telemetry()
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        try:
            request_id = uuid.UUID(request.headers.get("X-Request-ID", ""))
        except (ValueError, AttributeError):
            request_id = uuid.uuid4()
        request.request_id = request_id  # type: ignore[attr-defined]
        tokens = bind_context(request_id=request_id, correlation_id=request_id)
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = str(request_id)
            return response
        finally:
            reset_context(tokens)


class OpenTelemetryRequestMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        initialize_sentry()
        initialize_telemetry()
        self.get_response = get_response
        self.tracer = trace.get_tracer("lms.http")

    def __call__(self, request: HttpRequest) -> HttpResponse:
        started = time.perf_counter()
        carrier = {key: value for key, value in request.headers.items()}
        context = propagate.extract(carrier)
        with self.tracer.start_as_current_span(
            "HTTP request", context=context, kind=SpanKind.SERVER
        ) as span:
            span.set_attribute("http.request.method", request.method or "UNKNOWN")
            response: HttpResponse | None = None
            try:
                response = self.get_response(request)
            except Exception:
                span.set_status(Status(StatusCode.ERROR))
                raise
            finally:
                route = getattr(getattr(request, "resolver_match", None), "route", None)
                route_template = f"/{route}" if route else "unresolved"
                status_code = response.status_code if response is not None else 500
                attributes = safe_attributes(
                    {
                        "route": route_template[:200],
                        "method": request.method or "UNKNOWN",
                        "status_class": f"{status_code // 100}xx",
                    }
                )
                http_requests.add(1, attributes)
                http_request_duration.record(time.perf_counter() - started, attributes)
                if route:
                    span.update_name(f"{request.method} {route_template}")
                    span.set_attribute("http.route", route_template)
                span.set_attribute("http.response.status_code", status_code)
                span.set_status(
                    Status(StatusCode.ERROR if status_code >= 500 else StatusCode.OK)
                )
            assert response is not None
            return response
