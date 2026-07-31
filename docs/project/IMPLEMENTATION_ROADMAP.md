# Implementation roadmap

Each phase requires its predecessor's acceptance criteria, a scoped pull request, and an update to `STATUS.md`. “Commands” refers to the phase-specific runbook, not commands executed in Phase 1.

| # | Objective and dependencies | Expected change and validation | Do not do yet / risk |
|---|---|---|---|
| 1 | Audit and architecture. None. | This documentation; sources and ADR review. | No scaffold or dependencies. |
| 2 | Reproducible monorepo scaffold. **Completed 2026-07-28.** | Official CLIs, lockfiles, Django/Next scaffolds, quality checks, unit/E2E smoke and CI. | No domain feature or Docker service. |
| 3 | Local infrastructure. **Completed 2026-07-28.** | Compose PostgreSQL and Redis only, digest lock, health checks, authenticated persistence smoke and CI cleanup. | No application services, migrations, object/mail emulators, worker or production deploy. |
| 4 | Django configuration. **Completed 2026-07-29.** | Custom UUID/email user in first migration, Argon2id, internal admin, closed DRF policy, PostgreSQL readiness and reproducible migrations. | No public authentication or business domain. |
| 5 | Next.js configuration. Requires 2. | App shell, design tokens, lint/test harness, server/client boundary rules. | No academic feature. |
| 6 | OpenAPI contract and client. Requires 4–5. | Versioned schema, generated client, drift check. | No duplicated DTOs. |
| 7 | Identity and authentication. **Backend and browser integration completed 2026-07-29 (Prompt 6).** | allauth browser session flows, CSRF, mandatory email-code verification, password reset, Redis rate limits, same-origin OpenAPI client and isolated Chromium/axe evidence. | No localStorage JWT, app client, social login or MFA. |
| 8 | Authorization. Requires 7. **Completed 2026-07-29 (Prompt 7).** | Organization-scoped RBAC, historical memberships/roles/events, transactional policies, generated platform client and protected institutional routes. | No broad admin bypass, courses, invitations or taxonomy. |
| 9 | Taxonomy and curriculum. Requires 8. **Completed 2026-07-29 (Prompt 8).** | Areas, subjects, concepts, prerequisites, learning objectives. | No course editor. |
| 10 | Courses and structure. Requires 9. **Completed 2026-07-29 (Prompt 9).** | Logical courses, revisions, explicit review workflow, ordered modules/units and curriculum alignments. | No semantic content or publication snapshots. |
| 11 | Semantic content and academic editor. Requires 10. **Completed 2026-07-29 (Prompt 10).** | Schema-versioned JSON documents, append-only content versions, Tiptap/MathLive/MathJax/CodeMirror, static rendering, readiness, isolated Chromium and axe. | No unrestricted HTML, files, code execution or publication. |
| 12 | Immutable publication. Requires 10–11. **Completed locally 2026-07-30 (Prompt 11).** | Full-course immutable snapshots, SHA-256 chain, PostgreSQL triggers, withdrawal, draft cloning, authenticated snapshot-only library and reader. | No retroactive edits, draft leakage, enrolment, progress or evaluation. |
| 13 | Advanced academic editor. Requires 11–12. | Only later capabilities justified by publication and user evidence. | No arbitrary plugin ecosystem, collaboration or hidden autosave by default. |
| 14 | Enrolments. Requires 8, 10, 12. | Access dates/status and future cohorts. | No billing. |
| 15 | Study experience. Requires 12, 14. | Delivery, bookmarks, study sessions, continuity. | No native app. |
| 16 | Question bank. Requires 8, 11–12. | Versioned question types, hints and rubrics. | No grades on mutable questions. |
| 17 | Assessments. Requires 16. | Assessment composition/rules and publication. | No attempts before snapshots. |
| 18 | Attempts and responses. Requires 14, 17. | Delivery snapshots, timing and integrity transitions. | No analytics as source of truth. |
| 19 | Grading. Requires 18. | Automatic/manual grading and controlled regrade; property tests. | No silent score overwrite. |
| 20 | Progress. Requires 15, 19. | Completion/mastery rules and projections. | No destructive recomputation. |
| 21 | Media. Requires 11. | S3 storage, validation, lifecycle and signed access. | No unbounded uploads. |
| 22 | Search. Requires 8, 11, 12. | Permission-filtered index/search. | No information leakage. |
| 23 | Notifications. Requires 7, 14, 19. | Preferences/templates, outbox tasks, delivery tests. | No direct task before commit. |
| 24 | Analytics. Requires 18–20. | Event model and reproducible aggregates. | No mutable grade history. |
| 25 | Observability. Requires 3–6. | Structured logs, tracing, error reporting, alert runbook. | No sensitive payload collection. |
| 26 | Security hardening. Requires core flows. | Threat-model review, headers, rate limits, backup/restore drills. | No “security by obscurity”. |
| 27 | Performance. Requires representative data. | Query/bundle/load budgets and measured improvements. | No speculative caching. |
| 28 | Accessibility. Requires core UI. | WCAG 2.2 AA manual + automated evidence. | No visual-only acceptance. |
| 29 | Deployment. Requires 25–28. | Linux images, reverse proxy, migration/rollback and restore runbooks. | No Kubernetes by default. |
| 30 | Final documentation. Requires all. | Operations, API, ADR, data-retention and handoff review. | No undocumented release. |

Every implementation phase must specify its own commands, tests, acceptance criteria, risks, and deferred work in its delivery notes. Phase 2 is deliberately limited to scaffolding.

## Phase 12 completada — learning delivery

Se cerró la entrega transaccional con cohortes, matrículas fijadas a releases,
historial de asignaciones, progreso, continuidad, API/frontends institucional y
del estudiante, migraciones/triggers, demo y E2E. ADR 0022 y
`docs/architecture/LEARNING.md` fijan la frontera. Evaluaciones, certificados,
enrollment approval, publication y delivery asíncrono permanecen para fases
posteriores.

## Phase 13 completada — assessments inicial

El 2026-07-30 se cerró el banco de preguntas, ocho tipos, workflows y versiones
inmutables, composición, deliveries fijadas a assignments de learning,
intentos/respuestas, scoring Decimal all-or-none, grading manual append-only,
API, frontend, demo, migraciones/triggers y E2E. ADR 0023 reemplaza para este
corte la separación futura de las filas 16–19: sigue siendo un monolito modular
en `domain.assessments`; una extracción exige ADR y migración. Partial credit,
expresiones matemáticas, pools, regrading, gradebook, indicadores e import/export
QTI permanecen posteriores.

## Phase 14 completada — advanced grading and analytics

`domain.assessments` incorpora scoring v2, crédito parcial, MathJSON/SymPy
allowlisted, pools persistidos, grading y regrading durable con Celery,
versiones append-only de grade, gradebook por release y snapshots analíticos.
Las migraciones `0006`–`0008`, ADR 0024, OpenAPI, tipos generados, worker Linux,
demo y Chromium mantienen las fronteras de Phase 13. El siguiente alcance es
Prompt 15; media, archivos, S3, ejecución de código, QTI e IRT siguen excluidos.
