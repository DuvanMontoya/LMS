# ADR 0008: Session authentication

**Status:** Accepted — 2026-07-28.

Use django-allauth headless capabilities with Django sessions, HttpOnly cookies, CSRF, same-origin reverse proxying and MFA-ready flows. Do not store persistent JWTs in browser storage. `django-cors-headers` is rejected initially because the chosen production topology has one origin.
