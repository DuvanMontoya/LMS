# ADR 0009: Background jobs

**Status:** Accepted with constraint — 2026-07-28.

Use Celery 5.6.3 with Redis coordination for non-request work, started after committed transactions and designed idempotently. Workers run in Linux containers because Celery does not support Windows. Django 6 CSP is used, so an extra CSP package is rejected. Redis 8 production use is conditional on legal acceptance of its tri-license.
