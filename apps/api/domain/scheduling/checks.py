from typing import Any

from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security)
def livekit_configuration_check(
    app_configs: object | None, **kwargs: Any
) -> list[Error]:
    del app_configs, kwargs
    errors: list[Error] = []
    if not settings.LIVEKIT_ENABLED:
        return errors
    missing = [
        name
        for name in ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET")
        if not getattr(settings, name, "")
    ]
    if missing:
        errors.append(
            Error(
                "LiveKit está habilitado sin configuración completa.",
                hint=f"Configura: {', '.join(missing)}.",
                id="scheduling.E001",
            )
        )
    if not 60 <= settings.LIVEKIT_TOKEN_TTL_SECONDS <= 3600:
        errors.append(
            Error(
                "LIVEKIT_TOKEN_TTL_SECONDS debe estar entre 60 y 3600.",
                id="scheduling.E002",
            )
        )
    if settings.LIVEKIT_URL and not settings.LIVEKIT_URL.startswith(
        ("ws://", "wss://", "http://", "https://")
    ):
        errors.append(
            Error(
                "LIVEKIT_URL debe usar ws, wss, http o https.",
                id="scheduling.E003",
            )
        )
    return errors
