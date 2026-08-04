# pyright: reportConstantRedefinition=false

import os
from pathlib import Path

from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "host.docker.internal"]
EMAIL_DELIVERY_MODE = os.environ.get("EMAIL_DELIVERY_MODE", "file").strip().lower()
if EMAIL_DELIVERY_MODE == "smtp":
    for setting_name in (
        "EMAIL_HOST",
        "EMAIL_PORT",
        "EMAIL_HOST_USER",
        "EMAIL_HOST_PASSWORD",
        "DEFAULT_FROM_EMAIL",
    ):
        if not os.environ.get(setting_name):
            raise RuntimeError(
                f"{setting_name} is required when EMAIL_DELIVERY_MODE=smtp."
            )
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ["EMAIL_HOST"]
    EMAIL_PORT = int(os.environ["EMAIL_PORT"])
    EMAIL_HOST_USER = os.environ["EMAIL_HOST_USER"]
    EMAIL_HOST_PASSWORD = os.environ["EMAIL_HOST_PASSWORD"]
    EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
    EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "false").lower() == "true"
    if EMAIL_USE_TLS and EMAIL_USE_SSL:
        raise RuntimeError("EMAIL_USE_TLS and EMAIL_USE_SSL cannot both be true.")
    DEFAULT_FROM_EMAIL = os.environ["DEFAULT_FROM_EMAIL"]
    SERVER_EMAIL = os.environ.get("SERVER_EMAIL", DEFAULT_FROM_EMAIL)
    EMAIL_MESSAGE_ID_DOMAIN = os.environ.get("EMAIL_MESSAGE_ID_DOMAIN", "papyros.pro")
else:
    if EMAIL_DELIVERY_MODE != "file":
        raise RuntimeError("EMAIL_DELIVERY_MODE must be either file or smtp.")
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

# Loopback LTI exists only for the local review surface.  ``mediacms:up``
# generates this ignored key once, so a local MediaCMS registration survives
# Django restarts without placing a credential in Git or in browser storage.
MEDIACMS_LTI_ENABLED = os.environ.get("MEDIACMS_LTI_ENABLED", "true").lower() == "true"
MEDIACMS_LTI_TOOL_ORIGIN = os.environ.get(
    "MEDIACMS_LTI_TOOL_ORIGIN", "http://localhost:8091"
).rstrip("/")
LMS_LTI_ISSUER = os.environ.get("LMS_LTI_ISSUER", "http://localhost:3000").rstrip("/")
LMS_LTI_CLIENT_ID = os.environ.get("LMS_LTI_CLIENT_ID", "lms-local-mediacms")
LMS_LTI_DEPLOYMENT_ID = os.environ.get("LMS_LTI_DEPLOYMENT_ID", "lms-local-mediacms-v1")
LMS_LTI_KEY_ID = os.environ.get("LMS_LTI_KEY_ID", "lms-local-mediacms-v1")
_LOCAL_LTI_KEY_PATH = Path(
    os.environ.get(
        "LMS_LTI_LOCAL_KEY_PATH",
        BASE_DIR.parents[1] / ".local" / "mediacms" / "lms-lti-private-key.pem",  # noqa: F405
    )
)
LMS_LTI_PRIVATE_KEY_PEM = os.environ.get("LMS_LTI_PRIVATE_KEY_PEM", "")
if not LMS_LTI_PRIVATE_KEY_PEM and _LOCAL_LTI_KEY_PATH.is_file():
    LMS_LTI_PRIVATE_KEY_PEM = _LOCAL_LTI_KEY_PATH.read_text(encoding="utf-8")
LMS_LTI_MEDIA_ACCESS_AUDIENCE = os.environ.get(
    "LMS_LTI_MEDIA_ACCESS_AUDIENCE", "mediacms-lti-media-access"
)
LMS_LTI_MEDIA_ACCESS_VALIDATION_URL = os.environ.get(
    "LMS_LTI_MEDIA_ACCESS_VALIDATION_URL",
    "http://localhost:3000/api/v1/lti/media-access/",
).rstrip("/")
LMS_LTI_MEDIA_ACCESS_TTL_SECONDS = int(
    os.environ.get("LMS_LTI_MEDIA_ACCESS_TTL_SECONDS", "28800")
)
