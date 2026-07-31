"""Isolated browser-test settings; never point Playwright at the development DB."""

from __future__ import annotations

import os
from pathlib import Path

# pyright: reportConstantRedefinition=false
from .base import *  # noqa: F403

DEBUG = False
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
ASSET_S3_INTERNAL_ENDPOINT = os.environ.get(
    "ASSET_S3_INTERNAL_ENDPOINT", "http://127.0.0.1:4566"
)
ASSET_S3_PUBLIC_ENDPOINT = os.environ.get(
    "ASSET_S3_PUBLIC_ENDPOINT", "http://127.0.0.1:4566"
)
ASSET_S3_ACCESS_KEY_ID = "test"
ASSET_S3_SECRET_ACCESS_KEY = "test"
ASSET_S3_FORCE_PATH_STYLE = True
