# ADR 0001: Modular monolith

**Status:** Accepted — 2026-07-28.

Use one deployable Django codebase and a Celery worker that shares it, divided by documented domain boundaries. This keeps transactional academic invariants and delivery simple while retaining separable modules. Microservices are rejected until measured independent scaling, deployment, and ownership needs exceed this model.
