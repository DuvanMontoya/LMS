# ADR 0003: Django backend

**Status:** Accepted — 2026-07-28.

Use Django 6.0.7, DRF 3.17.1, Python 3.13.13, PostgreSQL and psycopg. Django supplies mature admin/ORM/security facilities; DRF exposes the versioned API. A custom user model is mandatory in the first migration. No generic repository layer is used.
