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
# Currículo Prompt 8

La suite de `catalog` cubre modelos, servicios, API, Treebeard, CTE de ciclos y
dos escrituras concurrentes de prerrequisitos sobre PostgreSQL. Playwright usa
una base UUID, prefijo Redis y correo efímeros: prueba creación, edición visible
de área, disciplina, asignatura, tema, concepto y objetivo por owner/author,
reviewer/learner de solo lectura, URL cross-organization, asociaciones,
archivado, movimientos de temas y ciclos visibles. El revisor ejecuta además
una escritura `fetch` con su propia cookie/CSRF y debe recibir 403; el alumno
entra tras archivar y no puede ver el contenido. Axe WCAG 2.2 A/AA se ejecuta
en las rutas curriculares principales.

# Courses Prompt 9

La pirámide separa modelos/constraints, orden, workflow/readiness, políticas,
API y dos `TransactionTestCase` concurrentes sobre PostgreSQL real. La suite
global mantiene cobertura mínima de 75 %. Vitest cubre query keys y read-only.
Playwright usa base UUID, prefijo Redis y correo aislados: tres escenarios
recorren autoría completa con dos contextos para 409, edición, orden,
archivado/restauración, revisión inválida con foco e IDOR en curso, revisión,
módulo y unidad. Axe se ejecuta sin reglas deshabilitadas en las cinco rutas.

# Contenido Prompt 10

El corpus del schema se ejecuta en jsonschema y Ajv. Backend cubre modelos,
pre-scan/límites, nodos/marks, seguridad, derivación, digest/no-op, estados,
permisos, IDOR, mass assignment, query budgets, demo, API y readiness. Dos
`TransactionTestCase` reales cubren primera save y update concurrentes; las
pruebas de restauración confirman una versión nueva y la inmutabilidad histórica.

Vitest prueba drift/round-trip, renderer, toolbar, MathLive, MathJax Safe,
CodeMirror, tablas, dirty, atajos, conflictos y read-only. Playwright crea una
base PostgreSQL UUID, prefijo Redis y correo aislados, migra desde cero y recorre
autor → reviewer → owner → instructor → learner/usuario externo. Usa dos
contextos para 409, verifica JSON real, restore, readiness, API hostil, teclado,
axe A/AA y una lista de requests externas vacía. El `finally` elimina base,
prefijo, correo y procesos; no reutiliza servidores.

La cobertura global mantiene el gate 75 %. Para `domain.content` se inspecciona
además el reporte por archivo y se exige evidencia material de versiones,
concurrencia, seguridad y readiness; migraciones, artefactos generados y
bibliotecas se excluyen del juicio de lógica propia.

# Publicación Prompt 11

Pytest cubre schema, snapshot/límites, cadena/corrupción, publicación, retiro,
clonación, permisos, IDOR, API, inmutabilidad ORM/SQL y carreras reales. Vitest
cubre claves, etiquetas y schema inválido. Playwright crea PostgreSQL efímero,
publica, lee con dos contextos, valida axe, teclado y 390 px, retira, comprueba
404 y elimina base, Redis, correo y procesos.

Learning usa `TestCase` para constraints/servicios/API y
`TransactionTestCase` para complete, enrollment y upgrade concurrentes en
PostgreSQL real. Prueba triggers mediante SQL directo, independencia de
releases, ventanas, retiro, IDOR, mass assignment, lote atómico y drift.
Vitest valida progress/IDs semánticos. Playwright crea una base aislada, forma
cohorte/matrícula, completa 2/2, suspende/reactiva, ejecuta axe y 390 px y
confirma cleanup. ADR 0035 añade pruebas de sincronización idempotente,
versiones esperadas, bajas, traslado, herencia/excepción de ventana, privacidad
docente y los contratos assessments/scheduling antes de declarar cierre.

# Assessments Prompt 13

Jsonschema y Ajv compilan los cuatro contratos Draft 2020-12 y el drift de tipos
generados bloquea CI. Pytest cubre ocho tipos, Decimal, normalización, no partial
credit, workflows, digests, expected version, timers, release pinning, IDOR,
leakage, mass assignment y triggers. `TransactionTestCase` ejecuta dos starts
simultáneos y exige un solo intento.

Playwright usa base PostgreSQL UUID, prefijo Redis y correo efímeros, migra desde
cero, crea el fixture assessments, recorre autoría/entrega, ocho controles,
guardado explícito, 409, submit, grading manual, feedback, max attempts, IDOR,
HTML sin claves, axe y 390 px. El `finally` elimina sólo esos recursos.

# Assessments Prompt 14

La pirámide añade tests de schemas, scoring v2, partial credit, ataques
MathJSON, constructores/equivalencia SymPy, timeout, pools, migración/backfill,
append-only grades, manual preservation, regrading concurrente, gradebook,
analytics/suppression, API/IDOR/leakage y tareas idempotentes. Un smoke de
dominio y el E2E usan el worker Linux real con PostgreSQL y Redis efímeros.
Frontend cubre Compute Engine, MathLive, polling acotado, compositor de pools,
consolas, tablas, axe, teclado, escritorio y 390 px. Checks de drift, build,
auditorías y regresiones de fases previas siguen siendo obligatorios.

## Phase 15

Pytest separa gateway, uploads, multipart, checksums, formats, processing,
security/IDOR, delivery y concurrencia; content/publication/learning conservan
regresiones v1 y añaden contratos v2/pinning. `assets:smoke` usa LocalStack,
ClamAV y media worker reales y genera EICAR en runtime. Vitest cubre contratos y
componentes; Playwright Chromium prueba library/upload, teclado, axe y 390 px.
Migraciones/triggers se aplican en PostgreSQL limpio y CI limpia servicios con
`if: always()`.
