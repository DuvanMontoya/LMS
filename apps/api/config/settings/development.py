# pyright: reportConstantRedefinition=false

import os

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
