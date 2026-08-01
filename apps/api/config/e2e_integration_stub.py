"""Isolated provider-contract stub used exclusively by the Playwright settings."""

from __future__ import annotations

from urllib.parse import urlencode, urlparse

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST


def _authorized(request: HttpRequest) -> bool:
    return request.headers.get("Authorization") == "Bearer e2e-access-token"


@require_GET
def models(
    request: HttpRequest, provider: str, version: str | None = None
) -> JsonResponse:
    del version
    if provider == "gemini":
        if request.headers.get("x-goog-api-key") != "e2e-gemini-key":
            return JsonResponse({"error": "unauthorized"}, status=401)
        return JsonResponse(
            {
                "models": [
                    {"name": "models/gemini-2.5-pro"},
                    {"name": "models/gemini-2.5-flash"},
                ]
            }
        )
    if provider == "openai":
        expected = "Bearer e2e-openai-key"
        payload = {"data": [{"id": "gpt-5-e2e"}, {"id": "gpt-5-mini-e2e"}]}
    elif provider == "deepseek":
        expected = "Bearer e2e-deepseek-key"
        payload = {"data": [{"id": "deepseek-chat-e2e"}]}
    else:
        return JsonResponse({"detail": "Not found."}, status=404)
    if request.headers.get("Authorization") != expected:
        return JsonResponse({"error": "unauthorized"}, status=401)
    return JsonResponse(payload)


@require_GET
def google_authorize(request: HttpRequest) -> HttpResponse:
    redirect_uri = request.GET.get("redirect_uri", "")
    state = request.GET.get("state", "")
    parsed = urlparse(redirect_uri)
    expected = urlparse(str(settings.GOOGLE_OAUTH_REDIRECT_URI))
    if (
        not state
        or request.GET.get("code_challenge_method") != "S256"
        or parsed.scheme != expected.scheme
        or parsed.netloc != expected.netloc
        or parsed.path != expected.path
    ):
        return JsonResponse({"error": "invalid_authorization_request"}, status=400)
    return HttpResponseRedirect(
        f"{redirect_uri}?{urlencode({'code': 'e2e-google-code', 'state': state})}"
    )


@csrf_exempt
@require_POST
def google_token(request: HttpRequest) -> JsonResponse:
    if (
        request.POST.get("code") != "e2e-google-code"
        or not request.POST.get("code_verifier")
        or request.POST.get("client_id") != "e2e-google-client"
        or request.POST.get("client_secret") != "e2e-google-secret"
    ):
        return JsonResponse({"error": "invalid_grant"}, status=400)
    return JsonResponse(
        {
            "access_token": "e2e-access-token",
            "refresh_token": "e2e-refresh-token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
    )


@csrf_exempt
def google_resource(request: HttpRequest, resource: str) -> JsonResponse:
    if not _authorized(request):
        return JsonResponse({"error": "unauthorized"}, status=401)
    if resource == "calendar/v3/users/me/calendarList":
        return JsonResponse({"items": [{"id": "primary"}]})
    if resource == "drive/v3/files":
        return JsonResponse({"files": [{"id": "e2e-drive-file"}]})
    if resource == "youtube/v3/channels":
        return JsonResponse({"items": [{"id": "e2e-channel"}]})
    if resource == "meet/v2/spaces" and request.method == "POST":
        return JsonResponse(
            {
                "name": "spaces/e2e-meeting",
                "meetingUri": "https://meet.google.test/e2e-meeting",
                "meetingCode": "e2e-meeting",
            }
        )
    return JsonResponse({"detail": "Not found."}, status=404)
