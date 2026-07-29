# Repository structure

Phase 3 adds only the local Compose infrastructure required for PostgreSQL and Redis. Application and production-infrastructure directories remain absent rather than empty.

```text
/
├── apps/
│   ├── api/                         # uv-managed Django project and uv.lock
│   │   ├── config/                  # settings, ASGI/WSGI, root URLs, Celery wiring
│   │   ├── domain/                  # bounded Django apps; no catch-all core app
│   │   │   ├── identity/ catalog/ content/ learning/ assessments/
│   │   ├── api/                     # version routing and transport composition only
│   │   ├── tests/                   # cross-module integration/API tests
│   │   ├── templates/ mail/ locale/ fixtures/
│   │   ├── manage.py pyproject.toml uv.lock
│   └── web/                         # pnpm-managed Next.js project
│       ├── src/app/                 # App Router and route groups
│       ├── src/features/            # domain UI modules
│       ├── src/components/ui/       # visual primitives; no business policy
│       ├── src/components/academic/ # semantic/math/editor renderers
│       ├── src/lib/api/             # generated client and gateway
│       ├── src/lib/validation/ src/hooks/ src/styles/
│       ├── tests/ e2e/ mocks/ public/
│       ├── openapi/                  # generated allauth browser snapshot
│       └── scripts/                  # deterministic generated-client script
│       └── package.json pnpm-lock.yaml
├── infrastructure/                  # Local Compose policy and operations documentation
│   ├── README.md
│   └── local/.env.example            # Generated .env stays ignored
├── compose.yaml                      # Services, health checks and exact tags
├── compose.lock.yaml                 # Reviewed linux/amd64 image digests
├── docs/                            # architectural record and runbooks
├── scripts/                         # reviewed repo automation; never business logic
├── tests/                           # black-box contract suites only, if later justified
├── .github/                         # CI, security and dependency-update workflows
├── package.json pnpm-workspace.yaml # workspace orchestration only
├── .tool-versions                   # exact Node, pnpm and Python declaration
├── AGENTS.md README.md
```

## Zone contracts

`apps/api` owns schema and OpenAPI generation. `apps/web` will consume generated TypeScript kept inside its own `src/lib/api/generated`; it never hand-copies backend transport types. `scripts` contains the tested PowerShell runbooks. A `packages/` directory is intentionally absent: create a workspace package only after at least two real consumers need a stable, independently testable boundary.

### Backend internal convention

`config/settings/{base,local,test,production}.py` composes a small base without duplicated values. Environment values load from process variables; `.env` support is local-only and no secrets enter Git. `config/asgi.py` is the production async entrypoint and `wsgi.py` remains for compatible tooling. Domain apps expose `models`, `use_cases` where needed, `selectors` for complex reads, `api`, `permissions`, `tasks`, `events`, `tests`, and migrations only when that responsibility exists. `urls` are composed at module boundaries; models never depend on HTTP transport.

### Frontend internal convention

Route groups are `(public)`, `(auth)`, `(learner)`, `(teaching)`, `(authoring)`, and `(admin)`. Default components are Server Components. A `use client` boundary is the smallest interactive leaf (editor, form controller, browser-only accessibility affordance); client components receive serializable view data and call one feature gateway, never arbitrary URLs. Server requests forward the incoming cookie to same-origin Django; browser mutations use Django's CSRF contract. No token is copied into localStorage. API errors map centrally to a typed, accessible error model.

TanStack Query is reserved for client-owned, invalidatable remote state. React state remains local unless several distant clients require it. Forms pair a feature Zod schema with React Hook Form; backend remains authoritative. Tiptap documents use a validated semantic schema, MathLive is isolated to input widgets, and MathJax rendering is server-safe/lazy where necessary.
# Estructura del repositorio

`apps/api/domain/organizations` contiene modelos, capacidades, políticas,
servicios, selectores, API, admin y comando de bootstrap. `apps/web/openapi`
y `src/lib/api/generated/platform.ts` son artefactos generados del OpenAPI de
plataforma; `src/app/(protected)/organizaciones` es la superficie institucional.
Prompt 8 incorpora `domain/catalog` con API, filtros, servicios, grafos,
políticas, migración y pruebas, además de las rutas curriculares bajo la
organización y componentes/hooks `catalog` en Next.js. No se creó otra app.

Prompt 9 incorpora `apps/api/domain/courses/` como aplicación Django generada
por `startapp`, con modelos, servicios, políticas, selectores, readiness, API,
migración, bootstrap y pruebas. Next agrega
`app/(protected)/organizaciones/[slug]/cursos/`, `components/courses/`,
`lib/courses/` y su E2E. `scripts/courses.ps1` orquesta las validaciones sin
infraestructura paralela.
