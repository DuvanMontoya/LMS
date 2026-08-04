"""Private local MediaCMS policy; copied by the upstream container entrypoint."""

import os

FRONTEND_HOST = os.environ["FRONTEND_HOST"]
PORTAL_NAME = "LMS Media Studio"
PORTAL_DESCRIPTION = "Catálogo privado local para la autoría de vídeo de la LMS."
TIME_ZONE = "America/Bogota"
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
# MediaCMS shares a browser profile with the LMS during local authoring. Its
# session cookie stays private. The upstream uploader deliberately reads the
# standard Django `csrftoken` cookie, so that name cannot be changed here.
SESSION_COOKIE_NAME = "mediacms_sessionid"
CSRF_TRUSTED_ORIGINS = ["http://127.0.0.1:8091", "http://localhost:8091"]

# The portal is an author-operated catalogue, not a public video site.
PORTAL_WORKFLOW = "private"
GLOBAL_LOGIN_REQUIRED = True
# Nginx calls this one protected endpoint internally to authorize media files.
# It must answer 403 for an anonymous request rather than redirecting to login.
ROOT_URLCONF = "mediacms_local_urls"
REGISTER_ALLOWED = False
USERS_CAN_SELF_REGISTER = False
ACCOUNT_EMAIL_VERIFICATION = "none"
UPLOAD_MEDIA_ALLOWED = True
CAN_ADD_MEDIA = "all"
MEDIA_IS_REVIEWED = True
# The built-in MediaCMS video page expects an original-media URL whenever
# downloads are enabled. Nginx still authorizes every original/encoded/HLS
# request through MediaCMS, so this remains private while avoiding a React
# null-URL crash in MediaCMS 8.1.3.
SHOW_ORIGINAL_MEDIA = True
CAN_SHARE_MEDIA = False
CAN_LIKE_MEDIA = False
CAN_DISLIKE_MEDIA = False
CAN_COMMENT = "advancedUser"
CAN_REPORT_MEDIA = False
ALLOW_ANONYMOUS_ACTIONS = []
GENERATE_SITEMAP = False
INCLUDE_LISTING_NUMBERS = False
LOAD_FROM_CDN = False
ALLOW_CUSTOM_MEDIA_URLS = False
ALLOW_MEDIA_REPLACEMENT = False

# The local integration intentionally uses ``localhost`` for both the LMS and
# MediaCMS so browser secure-cookie rules match the upstream LTI implementation.
# It is developer-only: production is blocked by the LMS settings unless HTTPS,
# a persistent signing key, and real platform registration are configured.
USE_RBAC = True
USE_LTI = True
# This is a server-to-server, bearer-only validation gate.  It runs for every
# protected source, encoded file or HLS segment and intentionally has no
# positive cache: an enrollment suspension, revocation or release upgrade must
# take effect on the next request.  Docker's documented host gateway reaches
# the local LMS without publishing another port.
LMS_MEDIA_ACCESS_VALIDATION_URL = os.environ.get(
    "LMS_MEDIA_ACCESS_VALIDATION_URL",
    "http://host.docker.internal:8010/api/v1/lti/media-access/",
)
LMS_MEDIA_ACCESS_VALIDATION_TIMEOUT_SECONDS = float(
    os.environ.get("LMS_MEDIA_ACCESS_VALIDATION_TIMEOUT_SECONDS", "2")
)
LMS_MEDIA_ACCESS_SESSION_TTL_SECONDS = int(
    os.environ.get("LMS_MEDIA_ACCESS_SESSION_TTL_SECONDS", "28800")
)

REDIS_LOCATION = (
    "redis://:"
    + os.environ["MEDIACMS_REDIS_PASSWORD"]
    + "@redis:6379/1"
)
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_LOCATION,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}
BROKER_URL = REDIS_LOCATION
CELERY_RESULT_BACKEND = REDIS_LOCATION

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["POSTGRES_NAME"],
        "HOST": os.environ["POSTGRES_HOST"],
        "PORT": os.environ["POSTGRES_PORT"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "OPTIONS": {
            "pool": {
                "min_size": 2,
                "max_size": 8,
                "timeout": 10,
                "max_lifetime": 30 * 60,
                "max_idle": 10 * 60,
            }
        },
    }
}
