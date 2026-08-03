# pyright: reportUnknownVariableType=false
from __future__ import annotations

import logging
from typing import Any

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def json_api_exception_handler(
    exception: Exception, context: dict[str, Any]
) -> Response:
    """Keep unexpected API failures observable without leaking Django HTML."""

    handled = exception_handler(exception, context)
    if handled is not None:
        return handled

    request = context.get("request")
    request_id = getattr(request, "request_id", None)
    logger.error(
        "Unhandled API exception",
        exc_info=(type(exception), exception, exception.__traceback__),
    )
    payload: dict[str, str] = {
        "code": "internal_error",
        "detail": "No fue posible completar la operación.",
    }
    if request_id is not None:
        payload["request_id"] = str(request_id)
    return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
