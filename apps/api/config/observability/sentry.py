# pyright: reportUnknownMemberType=false, reportArgumentType=false
from __future__ import annotations

from typing import Any

import sentry_sdk
from django.conf import settings
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

from .logging import redact


def before_send(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any] | None:
    request = event.get("request")
    if isinstance(request, dict):
        request.pop("data", None)
        request.pop("cookies", None)
        request.pop("query_string", None)
        if isinstance(request.get("url"), str):
            request["url"] = request["url"].split("?", 1)[0]
        request["headers"] = redact(request.get("headers", {}))
    event.pop("breadcrumbs", None)
    return redact(event)


def before_breadcrumb(
    crumb: dict[str, Any], _hint: dict[str, Any]
) -> dict[str, Any] | None:
    return redact(crumb)


def initialize_sentry() -> None:
    dsn = getattr(settings, "SENTRY_DSN", "")
    if not dsn:
        return
    sentry_sdk.init(
        dsn=dsn,
        environment=settings.SENTRY_ENVIRONMENT,
        release=settings.SENTRY_RELEASE or None,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        send_default_pii=False,
        max_request_body_size="never",
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        before_send=before_send,
        before_breadcrumb=before_breadcrumb,
    )
