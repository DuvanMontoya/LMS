# pyright: reportConstantRedefinition=false

import os

from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
EMAIL_FILE_PATH = BASE_DIR / ".local" / "mail"  # noqa: F405

ASSET_S3_INTERNAL_ENDPOINT = os.environ.get(
    "ASSET_S3_INTERNAL_ENDPOINT", "http://127.0.0.1:4566"
)
ASSET_S3_PUBLIC_ENDPOINT = os.environ.get(
    "ASSET_S3_PUBLIC_ENDPOINT", "http://127.0.0.1:4566"
)
ASSET_S3_ACCESS_KEY_ID = os.environ.get("ASSET_S3_ACCESS_KEY_ID", "test")
ASSET_S3_SECRET_ACCESS_KEY = os.environ.get("ASSET_S3_SECRET_ACCESS_KEY", "test")
ASSET_S3_FORCE_PATH_STYLE = (
    os.environ.get("ASSET_S3_FORCE_PATH_STYLE", "true").lower() == "true"
)
