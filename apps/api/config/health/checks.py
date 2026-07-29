from __future__ import annotations

from django.core.cache import cache
from django.db import DatabaseError, connection


def is_database_ready() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return False
    return True


def is_cache_ready() -> bool:
    try:
        cache.get("health:readiness")
    except Exception:  # Redis backend errors must make readiness unavailable.
        return False
    return True
