from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import quote, urlparse

BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "development-only-key-must-not-be-used-in-production"
)
DEBUG = False
ALLOWED_HOSTS: list[str] = []


def _required_origin(variable_name: str, default: str | None = None) -> str:
    """Return one canonical HTTP(S) origin without accepting URL components."""

    value = os.environ.get(variable_name, default)
    if not value:
        raise RuntimeError(f"{variable_name} is required.")
    parsed = urlparse(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError(f"{variable_name} must be an HTTP(S) origin without a path.")
    return value.rstrip("/")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "allauth",
    "allauth.account",
    "allauth.headless",
    "rest_framework",
    "drf_spectacular",
    "django_filters",
    "domain.identity",
    "domain.organizations",
    "domain.catalog",
    "domain.courses",
    "domain.content",
    "domain.publishing",
    "domain.learning",
    "domain.assessments",
    "domain.assets",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES: list[dict[str, object]] = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "lms"),
        "USER": os.environ.get("POSTGRES_USER", "lms"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": False,
        "OPTIONS": {
            "connect_timeout": int(os.environ.get("POSTGRES_CONNECT_TIMEOUT", "5"))
        },
    }
}

AUTH_USER_MODEL = "identity.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_USER_MODEL_EMAIL_FIELD = "email"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED = True
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_MAX_ATTEMPTS = 3
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_TIMEOUT = 900
ACCOUNT_EMAIL_VERIFICATION_SUPPORTS_RESEND = True
ACCOUNT_PASSWORD_RESET_BY_CODE_ENABLED = True
ACCOUNT_PASSWORD_RESET_BY_CODE_MAX_ATTEMPTS = 3
# django-allauth's supported, intentionally shorter default is three minutes.
ACCOUNT_PASSWORD_RESET_BY_CODE_TIMEOUT = 180
ACCOUNT_LOGIN_ON_PASSWORD_RESET = False
ACCOUNT_PREVENT_ENUMERATION = True
ACCOUNT_EMAIL_UNKNOWN_ACCOUNTS = True
ACCOUNT_SESSION_REMEMBER = False
ACCOUNT_LOGOUT_ON_GET = False
ACCOUNT_EMAIL_NOTIFICATIONS = True
ACCOUNT_PHONE_VERIFICATION_ENABLED = False

HEADLESS_ONLY = True
HEADLESS_CLIENTS = ("browser",)
HEADLESS_ADAPTER = "domain.identity.adapters.LMSHeadlessAdapter"
HEADLESS_SERVE_SPECIFICATION = True
# allauth sends the same neutral mail for unknown reset addresses.  In
# HEADLESS_ONLY mode it needs the future browser signup destination to build
# that mail; this setting does not create or serve a frontend route.
FRONTEND_ORIGIN = _required_origin("FRONTEND_ORIGIN", "http://127.0.0.1:3000")
HEADLESS_FRONTEND_URLS = {
    "account_signup": f"{FRONTEND_ORIGIN}/auth/registro",
    "account_reset_password": f"{FRONTEND_ORIGIN}/auth/restablecer-contrasena",
}
CSRF_TRUSTED_ORIGINS = [FRONTEND_ORIGIN]
_frontend_parsed = urlparse(FRONTEND_ORIGIN)
if _frontend_parsed.hostname in {"127.0.0.1", "localhost"}:
    _alt_host = "localhost" if _frontend_parsed.hostname == "127.0.0.1" else "127.0.0.1"
    _alt_netloc = (
        f"{_alt_host}:{_frontend_parsed.port}" if _frontend_parsed.port else _alt_host
    )
    _alt_origin = _frontend_parsed._replace(netloc=_alt_netloc).geturl().rstrip("/")
    if _alt_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_alt_origin)

# Direct browser uploads use the same exact local origins trusted by Django's
# CSRF boundary. Production keeps the explicitly configured frontend origin;
# development accepts only the localhost/loopback pair, never a wildcard.
ASSET_S3_ALLOWED_ORIGINS = tuple(CSRF_TRUSTED_ORIGINS)


ALLAUTH_TRUSTED_PROXY_COUNT = 0

_redis_host = os.environ.get("REDIS_HOST", "127.0.0.1")
_redis_port = os.environ.get("REDIS_PORT", "6379")
_redis_cache_db = os.environ.get("REDIS_CACHE_DB", "1")
_celery_broker_db = os.environ.get("CELERY_BROKER_DB", "2")
_redis_password = os.environ.get("REDIS_PASSWORD", "")
if not _redis_password:
    raise RuntimeError(
        "REDIS_PASSWORD is required; authentication rate limiting cannot fail open."
    )

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"redis://:{quote(_redis_password, safe='')}@{_redis_host}:{_redis_port}/{_redis_cache_db}",
        "TIMEOUT": 300,
        "KEY_PREFIX": "lms-auth",
        "OPTIONS": {
            "socket_connect_timeout": 1,
            "socket_timeout": 1,
            "retry_on_timeout": False,
        },
    }
}

if (
    not _redis_cache_db.isdecimal()
    or not _celery_broker_db.isdecimal()
    or _redis_cache_db == _celery_broker_db
):
    raise RuntimeError(
        "REDIS_CACHE_DB and CELERY_BROKER_DB must be distinct numeric databases."
    )

CELERY_BROKER_URL = (
    f"redis://:{quote(_redis_password, safe='')}@"
    f"{_redis_host}:{_redis_port}/{_celery_broker_db}"
)
CELERY_RESULT_BACKEND = None
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 100
CELERY_WORKER_ENABLE_REMOTE_CONTROL = (
    os.environ.get("CELERY_WORKER_REMOTE_CONTROL", "false").lower() == "true"
)
CELERY_TASK_SOFT_TIME_LIMIT = 30
CELERY_TASK_TIME_LIMIT = 45
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
ASSESSMENT_TASK_QUEUE_PREFIX = os.environ.get("ASSESSMENT_TASK_QUEUE_PREFIX", "")
if ASSESSMENT_TASK_QUEUE_PREFIX and not re.fullmatch(
    r"lms-e2e-[a-f0-9]{32}-", ASSESSMENT_TASK_QUEUE_PREFIX
):
    raise RuntimeError("ASSESSMENT_TASK_QUEUE_PREFIX is invalid.")
ASSESSMENT_TASK_COUNTDOWN_SECONDS = int(
    os.environ.get("ASSESSMENT_TASK_COUNTDOWN_SECONDS", "0")
)
if (
    ASSESSMENT_TASK_COUNTDOWN_SECONDS < 0
    or ASSESSMENT_TASK_COUNTDOWN_SECONDS > 5
    or (ASSESSMENT_TASK_COUNTDOWN_SECONDS and not ASSESSMENT_TASK_QUEUE_PREFIX)
):
    raise RuntimeError("ASSESSMENT_TASK_COUNTDOWN_SECONDS is invalid.")
CELERY_TASK_ROUTES = {
    "domain.assessments.tasks.grade_attempt_task": {
        "queue": f"{ASSESSMENT_TASK_QUEUE_PREFIX}grading"
    },
    "domain.assessments.tasks.process_regrade_job_task": {
        "queue": f"{ASSESSMENT_TASK_QUEUE_PREFIX}regrading"
    },
    "domain.assessments.tasks.refresh_analytics_task": {
        "queue": f"{ASSESSMENT_TASK_QUEUE_PREFIX}analytics"
    },
    "domain.assets.processing.tasks.process_asset_version_task": {"queue": "media"},
}
CELERY_IMPORTS = ("domain.assets.processing.tasks",)

ASSET_S3_REGION = os.environ.get("ASSET_S3_REGION", "us-east-1")
ASSET_S3_INTERNAL_ENDPOINT = os.environ.get("ASSET_S3_INTERNAL_ENDPOINT", "")
ASSET_S3_PUBLIC_ENDPOINT = os.environ.get("ASSET_S3_PUBLIC_ENDPOINT", "")
ASSET_S3_ACCESS_KEY_ID = os.environ.get("ASSET_S3_ACCESS_KEY_ID", "")
ASSET_S3_SECRET_ACCESS_KEY = os.environ.get("ASSET_S3_SECRET_ACCESS_KEY", "")
ASSET_S3_FORCE_PATH_STYLE = (
    os.environ.get("ASSET_S3_FORCE_PATH_STYLE", "false").lower() == "true"
)
ASSET_QUARANTINE_BUCKET = os.environ.get(
    "ASSET_QUARANTINE_BUCKET", "lms-assets-quarantine"
)
ASSET_PRIVATE_BUCKET = os.environ.get("ASSET_PRIVATE_BUCKET", "lms-assets-private")
ASSET_S3_SERVER_SIDE_ENCRYPTION = os.environ.get(
    "ASSET_S3_SERVER_SIDE_ENCRYPTION", "AES256"
)
ASSET_UPLOAD_URL_TTL_SECONDS = int(
    os.environ.get("ASSET_UPLOAD_URL_TTL_SECONDS", "900")
)
ASSET_DOWNLOAD_URL_TTL_SECONDS = int(
    os.environ.get("ASSET_DOWNLOAD_URL_TTL_SECONDS", "600")
)
ASSET_CLAMAV_HOST = os.environ.get("ASSET_CLAMAV_HOST", "127.0.0.1")
ASSET_CLAMAV_PORT = int(os.environ.get("ASSET_CLAMAV_PORT", "3310"))
ASSET_CLAMAV_TIMEOUT_SECONDS = int(os.environ.get("ASSET_CLAMAV_TIMEOUT_SECONDS", "30"))
ASSET_PIPELINE_NAME = "lms-media"
ASSET_PIPELINE_VERSION = "1"
ASSET_FFMPEG_PATH = os.environ.get("ASSET_FFMPEG_PATH", "ffmpeg")
ASSET_FFPROBE_PATH = os.environ.get("ASSET_FFPROBE_PATH", "ffprobe")

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

DEFAULT_FROM_EMAIL = "Plataforma académica <no-reply@lms.invalid>"
SERVER_EMAIL = DEFAULT_FROM_EMAIL
EMAIL_SUBJECT_PREFIX = "[Plataforma académica] "

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S%z",
}
SPECTACULAR_SETTINGS = {
    "TITLE": "LMS Platform API",
    "VERSION": "0.2.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # Every PATCH view validates an explicit serializer without partial=True.
    # Preserve required fields such as expected_version in the generated client.
    "COMPONENT_SPLIT_PATCH": False,
    "ENUM_NAME_OVERRIDES": {
        "OrganizationRole": "domain.organizations.choices.RoleCode",
        "OrganizationMembershipStatus": "domain.organizations.choices.MembershipStatus",
        "CourseLifecycleStatus": "domain.courses.choices.CourseStatus",
        "CourseAuthoringStatus": "domain.courses.choices.AuthoringStatus",
        "CourseSubjectAlignmentType": "domain.courses.choices.SubjectAlignmentType",
        "PublicationLifecycleStatus": "domain.publishing.choices.PublicationStatus",
        "PublicationEventType": "domain.publishing.choices.PublicationEventType",
        "LearningAssignmentReason": "domain.learning.choices.AssignmentReason",
        "LearningProgressStatus": "domain.learning.choices.ProgressStatus",
        "LearningUnitProgressStatus": "domain.learning.choices.UnitProgressStatus",
        "LearningEventType": "domain.learning.choices.LearningEventType",
        "LearningAccessState": "domain.learning.choices.AccessState",
        "AssessmentAuthoringStatus": "domain.assessments.choices.AuthoringStatus",
        "AssessmentQuestionType": "domain.assessments.choices.QuestionType",
        "AssessmentFeedbackMode": "domain.assessments.choices.FeedbackMode",
        "AssessmentDeliveryStatus": "domain.assessments.choices.DeliveryStatus",
        "AssessmentAssignmentStatus": "domain.assessments.choices.AssignmentStatus",
        "AssessmentAttemptStatus": "domain.assessments.choices.AttemptStatus",
        "AssessmentResponseStatus": "domain.assessments.choices.ResponseStatus",
        "AssessmentAttemptEventType": "domain.assessments.choices.AttemptEventType",
        "AssessmentPoolSelectionStrategy": "domain.assessments.choices.PoolSelectionStrategy",
        "AssessmentGradingRevisionSource": "domain.assessments.choices.GradingRevisionSource",
        "AssessmentGradeSource": "domain.assessments.choices.GradeSource",
        "AssessmentGradingStatus": "domain.assessments.choices.GradingStatus",
        "AssessmentJobStatus": "domain.assessments.choices.JobStatus",
        "AssessmentRegradeAttemptStatus": "domain.assessments.choices.RegradeAttemptStatus",
        "AssessmentGradebookStatus": "domain.assessments.choices.GradebookStatus",
        "AssessmentGradebookColumnStatus": "domain.assessments.choices.GradebookColumnStatus",
        "AssessmentAttemptAggregation": "domain.assessments.choices.AttemptAggregation",
        "AssessmentGradebookEntryStatus": "domain.assessments.choices.GradebookEntryStatus",
        "AssessmentGradebookSummaryStatus": "domain.assessments.choices.GradebookSummaryStatus",
        "CatalogPrerequisiteKind": "domain.catalog.models.PrerequisiteKind",
        "AssetKind": "domain.assets.choices.AssetKind",
        "AssetVersionStatus": "domain.assets.choices.AssetVersionStatus",
        "AssetUploadMethod": "domain.assets.choices.UploadMethod",
        "AssetUploadStatus": "domain.assets.choices.UploadStatus",
        "AssetProcessingJobStatus": "domain.assets.choices.ProcessingJobStatus",
        "AssetVariantRole": "domain.assets.choices.VariantRole",
    },
}
