"""Isolated browser-test settings; never point Playwright at the development DB."""

from __future__ import annotations

import base64
import os
from pathlib import Path

# pyright: reportConstantRedefinition=false
from .base import *  # noqa: F403

DEBUG = False
DEBUG_PROPAGATE_EXCEPTIONS = True
ALLOWED_HOSTS = ["127.0.0.1"]
HEADLESS_SERVE_SPECIFICATION = True

_mail_path = Path(os.environ.get("E2E_MAIL_PATH", ""))
_allowed_mail_root = BASE_DIR / ".local" / "e2e-mail"  # noqa: F405
if not _mail_path or _mail_path.resolve() != _allowed_mail_root.resolve():
    raise RuntimeError("E2E_MAIL_PATH must be apps/api/.local/e2e-mail.")

_redis_prefix = os.environ.get("E2E_REDIS_PREFIX", "")
if not _redis_prefix.startswith("lms-e2e-"):
    raise RuntimeError("E2E_REDIS_PREFIX must use the lms-e2e- namespace.")

EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
EMAIL_FILE_PATH = _mail_path
CACHES["default"]["KEY_PREFIX"] = _redis_prefix  # noqa: F405
CELERY_TASK_ROUTES = {**CELERY_TASK_ROUTES}  # noqa: F405
CELERY_TASK_ROUTES.update(
    {
        "domain.integrations.tasks.run_integration_health_check": {
            "queue": f"{_redis_prefix}-integrations"
        },
        "domain.events.tasks.dispatch_domain_event": {
            "queue": f"{_redis_prefix}-events"
        },
        "domain.events.tasks.process_event_replay": {
            "queue": f"{_redis_prefix}-events"
        },
        "domain.discovery.tasks.process_search_index_job": {
            "queue": f"{_redis_prefix}-discovery"
        },
        "domain.notifications.tasks.send_email_delivery": {
            "queue": f"{_redis_prefix}-notifications"
        },
    }
)
ASSET_S3_INTERNAL_ENDPOINT = os.environ.get(
    "ASSET_S3_INTERNAL_ENDPOINT", "http://127.0.0.1:4566"
)
ASSET_S3_PUBLIC_ENDPOINT = os.environ.get(
    "ASSET_S3_PUBLIC_ENDPOINT", "http://127.0.0.1:4566"
)
ASSET_S3_ACCESS_KEY_ID = "test"
ASSET_S3_SECRET_ACCESS_KEY = "test"
ASSET_S3_FORCE_PATH_STYLE = True

# Contract stubs are served by this isolated Django instance only.  They are
# never available under development or production settings, and no external
# provider credential is used in browser evidence.
_e2e_api_origin = f"http://127.0.0.1:{os.environ['E2E_API_PORT']}"
_e2e_stub_origin = f"{_e2e_api_origin}/_e2e/integrations"
INTEGRATIONS_MASTER_KEYS = "e2e-integration-key:" + base64.b64encode(b"e" * 32).decode(
    "ascii"
)
INTEGRATIONS_ACTIVE_KEY_ID = "e2e-integration-key"
INTEGRATIONS_OPENAI_MODELS_URL = f"{_e2e_stub_origin}/openai/v1/models"
INTEGRATIONS_GEMINI_MODELS_URL = f"{_e2e_stub_origin}/gemini/v1beta/models"
INTEGRATIONS_DEEPSEEK_MODELS_URL = f"{_e2e_stub_origin}/deepseek/models"
INTEGRATIONS_GOOGLE_API_BASE_URL = f"{_e2e_stub_origin}/google"
GOOGLE_OAUTH_CLIENT_ID = "e2e-google-client"
GOOGLE_OAUTH_CLIENT_SECRET = "e2e-google-secret"
GOOGLE_OAUTH_AUTHORIZE_URL = f"{_e2e_stub_origin}/google/authorize"
GOOGLE_OAUTH_TOKEN_URL = f"{_e2e_stub_origin}/google/token"
GOOGLE_OAUTH_REDIRECT_URI = f"{FRONTEND_ORIGIN}/api/v1/integrations/google/callback/"  # noqa: F405
