# pyright: reportUnknownMemberType=false, reportUnusedImport=false
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("lms")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Register manual stable instrumentation; beta auto-instrumentations are excluded.
from config.observability import celery as _observability_celery  # noqa: E402, F401
