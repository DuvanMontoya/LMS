from uuid import uuid4

# pyright: reportConstantRedefinition=false
from .base import *  # noqa: F403

SECRET_KEY = "test-only-secret-key-not-for-production"
DEBUG = False
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
HEADLESS_SERVE_SPECIFICATION = True
# A separate native Redis namespace per pytest process prevents rate-limit keys
# from one focused command affecting another, without clearing local development
# cache data or issuing Redis-wide destructive commands.
CACHES["default"]["KEY_PREFIX"] = f"lms-auth-test-{uuid4().hex}"  # noqa: F405
ASSET_S3_INTERNAL_ENDPOINT = "http://127.0.0.1:4566"
ASSET_S3_PUBLIC_ENDPOINT = "http://127.0.0.1:4566"
ASSET_S3_ACCESS_KEY_ID = "test"
ASSET_S3_SECRET_ACCESS_KEY = "test"
ASSET_S3_FORCE_PATH_STYLE = True
