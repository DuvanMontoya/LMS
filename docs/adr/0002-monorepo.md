# ADR 0002: Monorepo

**Status:** Accepted — 2026-07-28.

Keep `apps/api` and `apps/web` in one Git repository with independent uv/pnpm lockfiles. This supports coordinated API contracts and one architecture record without pretending the runtimes are one package. Shared workspace packages are deferred until two consumers prove a stable boundary.
