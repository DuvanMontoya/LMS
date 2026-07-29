# Testing and quality strategy

## Initial CI blockers (from Phases 2–3)

Formatting, linting, strict type checking, unit tests, Django system/deployment checks appropriate to environment, `makemigrations --check`, migration-plan review, OpenAPI/client drift check once introduced, dependency audit, lockfile integrity, secret scan, and `git diff --check` block CI. Next.js 16 lint is explicit because `next build` no longer runs it.

The infrastructure CI job additionally generates disposable local secrets, validates the merged Compose and digest lock, starts the two services, runs PostgreSQL/Django and Redis authentication/persistence smokes twice with a restart between them, and always removes only the `lms` Compose resources and volumes.

Identity tests use Django's PostgreSQL test database for UUID, database constraints, manager, forms and internal admin behavior. Health tests prove zero SQL for liveness, one PostgreSQL query for readiness and a safe mocked connection-failure path. A separate PowerShell operation creates, migrates and drops a uniquely named ephemeral PostgreSQL database.

Headless authentication tests use PostgreSQL, real Redis with a fresh random test key prefix per pytest process, locmem email and `Client(enforce_csrf_checks=True)`. They exercise CSRF bootstrap, generic failed login/enumeration responses, mass-assignment rejection, signup, mandatory code verification (expiry, reuse, attempts and resend), session rotation/logout, password reset (expiry, reuse, attempts, old-session invalidation and no automatic login), Argon2id and a Redis-backed 429 rate limit without persisting test accounts in the local development database or clearing local cache keys.

## Progressive controls

| Area | Required evidence |
|---|---|
| Backend | Ruff format/lint, Pyright strict incremental baseline, pytest unit/integration/API suites, pytest-django transaction tests, factories, Hypothesis for graders/state transitions, coverage trend, migration checks, `check --deploy` in production-like settings, `pip-audit`. |
| Frontend | Prettier, ESLint, strict TypeScript, Vitest, Testing Library, axe-based accessibility assertions, Playwright critical journeys at desktop and mobile widths, MSW contract failures, bundle analysis only when budget/regression warrants it. |
| Contracts | OpenAPI schema validation, generated-client reproducibility and API authorization/error tests. No manually duplicated DTOs. |
| Data | Fixtures are small, anonymized and module-owned; factories own test creation. Restore and migration rehearsals use disposable data. |
| Release | Protected main, conventional commits, reviewed PRs, dependency-update PRs, artifact provenance, production smoke, rollback and restore evidence. |

Accessibility acceptance includes keyboard-only flow, visible focus, names/roles/states, reduced motion, contrast, and meaningful math alternatives. Passing automation is necessary but never the whole accessibility claim.

Authentication integration additionally checks deterministic OpenAPI drift, typed client compilation, CSRF cookie parsing, return-path rejection, Spanish error mapping, generated paths and a production proxy smoke. Browser journeys use an isolated UUID-named PostgreSQL database, random `lms-e2e-` Redis key prefix and ignored file-mail directory. The runner migrates and drops the database, deletes only that prefix and its local mail/results paths in `finally`; it never aims Playwright at the development database. Playwright starts direct Django and Next servers on loopback, refuses server reuse, runs Chromium serially, and retains no trace, video, screenshot or email-code artifact after success. The CI workflow installs Chromium explicitly and runs the complete journey suite, including the tagged axe WCAG 2.2 A/AA scan.
# Estrategia de pruebas

Organizations se prueba sobre PostgreSQL con restricciones, matriz
rol-capacidad, servicios, API y una carrera `TransactionTestCase` que intenta
revocar dos owners en paralelo. El schema y el cliente TypeScript se verifican
contra drift en CI.
