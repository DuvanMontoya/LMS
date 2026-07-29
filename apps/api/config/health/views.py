from __future__ import annotations

from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed, JsonResponse

from .checks import is_cache_ready, is_database_ready


def _response(status: str, status_code: int) -> JsonResponse:
    response = JsonResponse({"status": status}, status=status_code)
    response["Cache-Control"] = "no-store"
    return response


def _method_not_allowed() -> HttpResponse:
    response = HttpResponseNotAllowed(["GET", "HEAD"])
    response["Cache-Control"] = "no-store"
    return response


def live(request: HttpRequest) -> HttpResponse:
    if str(request.method) not in {"GET", "HEAD"}:
        return _method_not_allowed()
    return _response("ok", 200)


def ready(request: HttpRequest) -> HttpResponse:
    if str(request.method) not in {"GET", "HEAD"}:
        return _method_not_allowed()
    if is_database_ready() and is_cache_ready():
        return _response("ok", 200)
    return _response("unavailable", 503)
