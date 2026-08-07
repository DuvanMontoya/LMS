# Repository structure

The repository is a pnpm/uv monorepo with a Django API, a Next.js web application and local Compose infrastructure. Production infrastructure remains external to the repository.

```text
/
├── apps/
│   ├── api/                         # uv-managed Django project and uv.lock
│   │   ├── config/                  # settings, ASGI/WSGI, root URLs, Celery wiring
│   │   ├── domain/                  # bounded Django apps; no catch-all core app
│   │   │   ├── */api/                # bounded-app transport modules
│   │   ├── tests/                   # cross-module integration/API tests
│   │   ├── templates/                # allauth, organization and notification mail
│   │   ├── manage.py pyproject.toml uv.lock
│   └── web/                         # pnpm-managed Next.js project
│       ├── src/app/                 # App Router and route groups
│       ├── src/components/          # feature components and UI primitives
│       ├── src/hooks/ src/lib/      # hooks, gateways and generated clients
│       ├── e2e/ public/             # browser suites and public assets
│       ├── openapi/                  # generated allauth browser snapshot
│       └── scripts/                  # deterministic generated-client script
├── infrastructure/                  # Local Compose policy and operations documentation
│   ├── README.md
│   └── local/.env.example            # Generated .env stays ignored
├── compose.yaml                      # Services, health checks and exact tags
├── compose.lock.yaml                 # Reviewed linux/amd64 image digests
├── docs/                            # architectural record and runbooks
├── scripts/                         # reviewed repo automation; never business logic
├── schemas/                         # shared semantic and publication contracts
├── .github/                         # CI, security and dependency-update workflows
├── package.json pnpm-workspace.yaml pnpm-lock.yaml
├── .node-version                    # exact Node declaration
├── AGENTS.md README.md SECURITY.md
```

## Zone contracts

`apps/api` owns schema and OpenAPI generation. `apps/web` will consume generated TypeScript kept inside its own `src/lib/api/generated`; it never hand-copies backend transport types. `scripts` contains the tested PowerShell runbooks. A `packages/` directory is intentionally absent: create a workspace package only after at least two real consumers need a stable, independently testable boundary.

### Backend internal convention

`config/settings/{base,local,test,production}.py` composes a small base without duplicated values. Environment values load from process variables; `.env` support is local-only and no secrets enter Git. `config/asgi.py` is the production async entrypoint and `wsgi.py` remains for compatible tooling. Domain apps expose `models`, `use_cases` where needed, `selectors` for complex reads, `api`, `permissions`, `tasks`, `events`, `tests`, and migrations only when that responsibility exists. `urls` are composed at module boundaries; models never depend on HTTP transport.

### Frontend internal convention

Route groups are `(auth)` and `(protected)`. Default components are Server Components. A `use client` boundary is the smallest interactive leaf (editor, form controller, browser-only accessibility affordance); client components receive serializable view data and call one feature gateway, never arbitrary URLs. Server requests forward the incoming cookie to same-origin Django; browser mutations use Django's CSRF contract. No token is copied into localStorage. API errors map centrally to a typed, accessible error model.

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

Prompt 10 implementa `apps/api/domain/content/` con modelos, validadores,
seguridad, servicios, selectores, policies, readiness, API, admin, migración,
bootstrap y pruebas. El contrato fuente es
`schemas/content/unit-document-v1.schema.json`. En Next, la ruta
`app/(protected)/organizaciones/[slug]/cursos/[courseSlug]/unidades/[unitId]/contenido`
compone `components/content/`; adaptadores, schema copiado, tipos generados y
validator viven en `src/lib/content/`. `scripts/generate-content-types.mjs` y
`copy-mathjax-assets.mjs` generan artefactos verificables. MathJax y MathLive en
`public/vendor/` son ignorados y regenerables; el worker de PDF.js se versiona
porque el lector lo sirve desde esa ruta.

`scripts/content.ps1` es el único runbook de la fase y los scripts raíz
`content:*` delegan en él. `apps/web/e2e/content.spec.ts` reutiliza el runner
aislado institucional; no existe una segunda aplicación, API, base o cliente
manual.

Prompt 11 agrega `apps/api/domain/publishing/`,
`schemas/publication/course-release-v1.schema.json`, rutas de publicación y
biblioteca, tipos en `src/lib/publishing/generated/`, E2E
`publication.spec.ts` y `scripts/publishing.ps1`. No crea otra aplicación,
base, autenticación o cliente.

Prompt 12 completa `apps/api/domain/learning/`, agrega tres migraciones, API y
management commands; en web agrega rutas `aprendizaje`/`aprender`,
`components/learning`, `lib/learning` y `learning.spec.ts`. Los contratos
generados permanecen en el único cliente `platform.ts`; no existe un segundo
backend, base, store o sistema de permisos.

Prompt 14 adapta la estructura real sin crear apps paralelas:

- `domain/assessments/math/`: AST, límites, constructores y equivalencia.
- `grading.py`, `jobs.py`, `regrading.py`, `gradebooks.py`, `analytics.py`:
  servicios cohesionados del mismo dominio.
- `tasks.py`, `queues.py`, `config/celery.py` y `Dockerfile.worker`: adaptador
  asíncrono.
- `schemas/assessment/`: MathJSON, response, scoring y grading revision.
- `evaluaciones/regrading`, `gradebooks`, `analitica`: rutas Next protegidas.
- `scripts/async.ps1`: ciclo de vida reproducible del worker.
- `apps/api/domain/assets/`: modelos, policies, uploads, storage, processing,
  delivery, API, comandos y pruebas de assets.
- `apps/api/Dockerfile.media-worker` e `infrastructure/media/`: build firmado
  de FFmpeg y worker privado no root.
- `apps/web/src/components/assets/`, `src/lib/assets/` y rutas `recursos/`:
  library, carga, detalle, picker y renderer.
- `scripts/storage.ps1`, `scripts/media.ps1`, `scripts/assets.ps1`: operación
  reproducible de Phase 15.
