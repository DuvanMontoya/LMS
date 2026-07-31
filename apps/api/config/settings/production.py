# pyright: reportConstantRedefinition=false

import os

from .base import *  # noqa: F403

if not os.environ.get("DJANGO_SECRET_KEY"):
    raise RuntimeError("DJANGO_SECRET_KEY is required in production.")

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = False
ALLOWED_HOSTS = [
    host for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if host
]

if not ALLOWED_HOSTS:
    raise RuntimeError("DJANGO_ALLOWED_HOSTS is required in production.")

for setting_name in (
    "REDIS_HOST",
    "REDIS_PORT",
    "REDIS_PASSWORD",
    "REDIS_CACHE_DB",
    "EMAIL_HOST",
    "EMAIL_PORT",
    "EMAIL_HOST_USER",
    "EMAIL_HOST_PASSWORD",
    "FRONTEND_ORIGIN",
    "ASSET_S3_REGION",
    "ASSET_QUARANTINE_BUCKET",
    "ASSET_PRIVATE_BUCKET",
):
    if not os.environ.get(setting_name):
        raise RuntimeError(f"{setting_name} is required in production.")

if ASSET_S3_INTERNAL_ENDPOINT or ASSET_S3_PUBLIC_ENDPOINT:  # noqa: F405
    raise RuntimeError(
        "Production uses the AWS S3 endpoint; LocalStack endpoints are forbidden."
    )
if ASSET_S3_ACCESS_KEY_ID or ASSET_S3_SECRET_ACCESS_KEY:  # noqa: F405
    raise RuntimeError(
        "Production S3 credentials must come from the AWS credential chain."
    )

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
HEADLESS_SERVE_SPECIFICATION = False
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ["EMAIL_HOST"]
EMAIL_PORT = int(os.environ["EMAIL_PORT"])
EMAIL_HOST_USER = os.environ["EMAIL_HOST_USER"]
EMAIL_HOST_PASSWORD = os.environ["EMAIL_HOST_PASSWORD"]
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_USE_SSL = False
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "")
SERVER_EMAIL = os.environ.get("SERVER_EMAIL", DEFAULT_FROM_EMAIL)
DATABASES["default"]["CONN_MAX_AGE"] = int(  # noqa: F405
    os.environ.get("POSTGRES_CONN_MAX_AGE", "60")
)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True  # noqa: F405
