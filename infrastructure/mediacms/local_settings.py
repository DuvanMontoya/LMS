"""Private local MediaCMS policy; copied by the upstream container entrypoint."""

import os

FRONTEND_HOST = os.environ["FRONTEND_HOST"]
PORTAL_NAME = "LMS Media Studio"
PORTAL_DESCRIPTION = "Catálogo privado local para la autoría de vídeo de la LMS."
TIME_ZONE = "America/Bogota"
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# The portal is an author-operated catalogue, not a public video site.
PORTAL_WORKFLOW = "private"
GLOBAL_LOGIN_REQUIRED = True
REGISTER_ALLOWED = False
USERS_CAN_SELF_REGISTER = False
ACCOUNT_EMAIL_VERIFICATION = "none"
UPLOAD_MEDIA_ALLOWED = True
CAN_ADD_MEDIA = "all"
MEDIA_IS_REVIEWED = True
SHOW_ORIGINAL_MEDIA = False
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

# A local HTTP portal is deliberately not an LTI 1.3 launch target. The LMS
# may only add a launch binding after an HTTPS issuer, JWKS and client
# registration have been provisioned and verified.
USE_LTI = False

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
