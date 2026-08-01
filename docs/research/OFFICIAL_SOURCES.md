# Official sources and research record

Consulted 2026-07-28. Only official project documentation, official registries, Docker Official Images, and standards are authority for this phase.

| Topic | Official source | Evidence used |
|---|---|---|
| Django release/support and Python matrix | https://www.djangoproject.com/download/ ; https://docs.djangoproject.com/en/6.0/faq/install/ | 6.0 stable series; Python 3.12–3.14; PostgreSQL recommendation. |
| Django identity, passwords and settings | https://docs.djangoproject.com/en/6.0/topics/auth/customizing/ ; https://docs.djangoproject.com/en/6.0/topics/auth/passwords/ ; https://docs.djangoproject.com/en/6.0/ref/settings/ | Custom user must be first app migration; `AbstractUser` supports `UserAdmin`; Argon2id setup and connection/cookie settings. |
| DRF policies | https://www.django-rest-framework.org/api-guide/settings/ | Session authentication, `IsAuthenticated`, JSON renderer and unsafe defaults avoided. |
| Argon2 and Django typing | https://pypi.org/project/argon2-cffi/ ; https://pypi.org/project/django-stubs/ | argon2-cffi 25.1.0 supports Python 3.13; django-stubs 6.0.7 matches Django 6.0. |
| Django 6 release | https://docs.djangoproject.com/en/6.0/releases/6.0/ | Python minimum 3.12 and dependency minimums. |
| DRF | https://www.django-rest-framework.org/community/release-notes/ | DRF 3.17 Django 6 support. |
| allauth | https://docs.allauth.org/en/latest/release-notes/recent.html ; https://docs.allauth.org/en/latest/headless/ ; https://docs.allauth.org/en/latest/headless/openapi.html ; https://pypi.org/project/django-allauth/ | Consulted 2026-07-29: Django 6 support, browser session strategy, CSRF bootstrap, official OpenAPI and published extra metadata. `headless` requires `PyJWT[crypto]`; local resolution proves browser session routes and schema operate with `headless-spec` alone. |
| redis-py | https://pypi.org/project/redis/ | Consulted 2026-07-29: redis-py 8.0.1 stable, Python >=3.10. |
| Celery | https://docs.celeryq.dev/en/stable/history/whatsnew-5.6.html ; https://docs.celeryq.dev/en/stable/getting-started/introduction.html | Python/Redis support and Windows unsupported constraint. |
| Node | https://nodejs.org/en/about/previous-releases | Node 24 LTS status and production LTS guidance. |
| Next.js | https://nextjs.org/docs/app/getting-started/installation ; https://nextjs.org/docs/app/api-reference/cli/create-next-app | Node/TS requirement and official CLI flags. |
| Next.js rewrites, Proxy and cookies | https://nextjs.org/docs/app/api-reference/config/next-config-js/rewrites ; https://nextjs.org/docs/app/api-reference/file-conventions/proxy ; https://nextjs.org/docs/app/api-reference/functions/cookies | Consulted 2026-07-29: explicit rewrites, `proxy.ts` convention and dynamic cookie access. |
| Frontend auth client | https://tanstack.com/query/latest/docs/framework/react/reference/QueryClientProvider ; https://react-hook-form.com/docs ; https://zod.dev ; https://openapi-ts.dev ; https://playwright.dev/docs/intro ; https://github.com/dequelabs/axe-core-npm | Consulted 2026-07-29: provider ownership, form validation boundary, generated OpenAPI types and browser accessibility testing. |
| Tailwind | https://tailwindcss.com/docs/installation/framework-guides/nextjs ; https://tailwindcss.com/docs/compatibility | Next setup and modern-browser caveat. |
| uv | https://docs.astral.sh/uv/concepts/projects/sync/ ; https://docs.astral.sh/uv/reference/cli/ | lock/sync semantics and CLI. |
| PostgreSQL | https://www.postgresql.org/support/versioning/ ; https://www.postgresql.org/docs/current/release-18.html | 18.4 support/current-minor policy and 18 changes. |
| PostgreSQL container and initdb | https://hub.docker.com/_/postgres ; https://www.postgresql.org/docs/current/app-initdb.html | `postgres:18.4-trixie`, Linux amd64 digest lock, PostgreSQL 18 `/var/lib/postgresql` mount, SCRAM host auth, UTF-8 and checksums. |
| Redis container and license | https://hub.docker.com/_/redis ; https://redis.io/legal/licenses/ | `redis:8.8.1-trixie`, Linux amd64 digest lock, non-root official entrypoint behavior, `/data` persistence and Redis 8 RSALv2/SSPLv1/AGPLv3 tri-license. |
| Packages and JS versions | https://pypi.org/ ; https://registry.npmjs.org/ | Exact published versions and release timestamps, queried read-only. |
| Dependency security | https://github.com/advisories/GHSA-6g55-p6wh-862q ; https://github.com/advisories/GHSA-f88m-g3jw-g9cj | Patched PostCSS and sharp versions used by explicit temporary overrides. |
| Security/accessibility standards | https://www.w3.org/TR/WCAG22/ ; https://www.rfc-editor.org/rfc/rfc9110 | WCAG 2.2 AA target and HTTP semantics. |

No blog, tutorial, forum, AI output, or third-party comparison was used as version authority.

## Prompt 7 consultation — 2026-07-29

| Topic | Official source | Evidence used |
|---|---|---|
| Django transactions and locking | https://docs.djangoproject.com/en/6.0/topics/db/transactions/ ; https://docs.djangoproject.com/en/6.0/ref/models/querysets/#select-for-update | `atomic`, PostgreSQL row locks and `TransactionTestCase` for the last-owner invariant. |
| Django constraints and indexes | https://docs.djangoproject.com/en/6.0/ref/models/constraints/ ; https://docs.djangoproject.com/en/6.0/ref/models/indexes/ | Conditional uniqueness, check constraints and query-led index design. |
| DRF authorization | https://www.django-rest-framework.org/api-guide/permissions/ | Global session authentication and thin permission boundary; policies remain framework-independent. |
| drf-spectacular | https://drf-spectacular.readthedocs.io/en/latest/ ; https://drf-spectacular.readthedocs.io/en/latest/faq.html | Explicit request/response metadata, enum overrides and `spectacular --validate --fail-on-warn`. |

## Prompt 8 consultation — 2026-07-29

| Topic | Official source | Evidence used |
|---|---|---|
| django-filter 26.1 | https://pypi.org/project/django-filter/ | Stable CalVer release; declarative, explicit FilterSets only. |
| django-treebeard 6.0.0 | https://pypi.org/project/django-treebeard/ ; https://django-treebeard.readthedocs.io/ | Django 6/Python 3.13 support and `MP_Node` materialized path for Topic. |
| Django transactions | https://docs.djangoproject.com/en/6.0/topics/db/transactions/ ; https://docs.djangoproject.com/en/6.0/ref/models/querysets/#select-for-update | `atomic` plus PostgreSQL row locks for tree and graph writes. |
| PostgreSQL recursive CTE | https://www.postgresql.org/docs/current/sql-select.html | Recursive `WITH` and `CYCLE` semantics; implementation remains parameterized. |

## Prompt 9 consultation — 2026-07-29

| Topic | Official source | Evidence used |
|---|---|---|
| Django constraints | https://docs.djangoproject.com/en/6.0/ref/models/constraints/ | Conditional uniqueness, expression uniqueness, deferred unique constraints and validation behavior. |
| Django transactions and row locking | https://docs.djangoproject.com/en/6.0/topics/db/transactions/ ; https://docs.djangoproject.com/en/6.0/ref/models/querysets/#select-for-update | Short `atomic` service boundaries and row locks around revision/version/order writes. |
| PostgreSQL constraints | https://www.postgresql.org/docs/18/ddl-constraints.html ; https://www.postgresql.org/docs/18/sql-createtable.html | `DEFERRABLE INITIALLY DEFERRED`, partial unique indexes and null behavior used by ordered active rows. |
| DRF filtering and pagination | https://www.django-rest-framework.org/api-guide/filtering/ ; https://www.django-rest-framework.org/api-guide/pagination/ | Explicit `django-filter` fields, allowlisted ordering and bounded page size. |
| drf-spectacular | https://drf-spectacular.readthedocs.io/en/latest/customization.html ; https://drf-spectacular.readthedocs.io/en/latest/client_generation.html | Explicit operation/field schema annotations and fail-on-warning client generation. |
| Next.js Server Components | https://nextjs.org/docs/app/getting-started/server-and-client-components ; https://nextjs.org/docs/app/api-reference/functions/fetch | Server-side authorization boundary and `cache: no-store`. |
| TanStack Query invalidation | https://tanstack.com/query/latest/docs/framework/react/guides/query-invalidation | Scoped invalidation after course mutations; global retries remain disabled. |
| Playwright keyboard and accessibility | https://playwright.dev/docs/input ; https://playwright.dev/docs/accessibility-testing | Real Chromium keyboard controls, responsive checks and axe integration. |

## Prompt 10 consultation — 2026-07-29

| Tema | Fuente oficial | Evidencia aplicada |
| --- | --- | --- |
| JSON Schema 2020-12 | https://json-schema.org/draft/2020-12/json-schema-core.html ; https://json-schema.org/draft/2020-12/json-schema-validation.html | Dialecto, vocabularios, `$schema`, validación estructural y ausencia de refs remotos. |
| Python jsonschema | https://python-jsonschema.readthedocs.io/en/stable/validate/ ; https://pypi.org/project/jsonschema/ | `Draft202012Validator.check_schema`, validación por instancia y versión estable 4.26.0. |
| Ajv | https://ajv.js.org/json-schema.html ; https://www.npmjs.com/package/ajv | Instancia 2020 para Draft 2020-12 y pin 8.20.0. |
| Tiptap React y schema | https://tiptap.dev/docs/editor/getting-started/install/react ; https://tiptap.dev/docs/editor/core-concepts/schema ; https://tiptap.dev/docs/editor/extensions/functionality/unique-id | SSR con render inmediato desactivado, nodos/marks declarativos y IDs estables. |
| Tiptap static renderer y content checking | https://tiptap.dev/docs/editor/api/utilities/static-renderer ; https://tiptap.dev/docs/editor/core-concepts/schema#content-checking | Representación React desde JSON y rechazo de contenido no conforme. |
| MathLive | https://mathlive.io/mathfield/guides/integration/ ; https://mathlive.io/mathfield/api/ | Campo matemático web, valor LaTeX, accesibilidad y directorio local de fuentes. |
| MathJax local y Safe | https://docs.mathjax.org/en/latest/web/start.html ; https://docs.mathjax.org/en/latest/options/safe.html ; https://docs.mathjax.org/en/latest/web/components/combined.html | Componentes locales, configuración `ui/safe`, allowlists y paquetes TeX explícitos. |
| CodeMirror 6 | https://codemirror.net/docs/ref/ ; https://codemirror.net/examples/tab/ | Estado/vista/extensiones, keymaps y escape de Tab para no crear trampa de teclado. |
| Django transacciones | https://docs.djangoproject.com/en/6.0/topics/db/transactions/ ; https://docs.djangoproject.com/en/6.0/ref/models/querysets/#select-for-update | Transacción corta y locks reales para primera creación, updates y restauración concurrentes. |
| PostgreSQL JSON y constraints | https://www.postgresql.org/docs/18/datatype-json.html ; https://www.postgresql.org/docs/18/ddl-constraints.html | `jsonb`, unicidad, checks e índices del historial. |
| WCAG 2.2 | https://www.w3.org/TR/WCAG22/ | Objetivo A/AA, teclado, foco, nombres accesibles, tablas y contenido matemático. |
| Registros | https://pypi.org/project/jsonschema/ ; https://registry.npmjs.org/ | Versiones estables, metadatos, licencias y peer dependencies consultados antes del lock. |

No se usaron CDN, tutoriales ni blogs como autoridad. Cada bundle matemático se
copia desde la dependencia bloqueada y el check de assets falla si falta.

## Sistema visual institucional — consulta 2026-07-29

| Tema | Fuente oficial | Evidencia usada |
|---|---|---|
| shadcn/ui para Next.js | https://ui.shadcn.com/docs/installation/next | Configuración sobre proyecto existente, alias `@/*` y generación local de componentes. |
| Sidebar shadcn/ui | https://ui.shadcn.com/docs/components/radix/sidebar | Composición `SidebarProvider`, sidebar colapsable, grupos, trigger y superficie móvil. |
| Tailwind v4 | https://ui.shadcn.com/docs/changelog/2025-02-tailwind-v4 | Variables CSS, tokens y compatibilidad del generador con Tailwind 4. |
| Accesibilidad Radix | https://www.radix-ui.com/primitives/docs/overview/accessibility | Gestión de foco, teclado y atributos ARIA en diálogos, menús y overlays. |
| Versiones y licencias | https://registry.npmjs.org/ | `shadcn 4.16.0`, `radix-ui 1.6.7`, `lucide-react 1.27.0` y utilidades visuales, con peers y licencias comprobados mediante `pnpm view`. |

La referencia visual privada del login fue leída directamente desde
`DuvanMontoya/Frontera-Matematica` mediante el acceso GitHub autorizado, no
mediante una copia pública o un contenido inventado. Se reutilizó su composición
visual; la autenticación continúa siendo el contrato allauth del LMS.

## Prompt 11 consultation — 2026-07-30

| Tema | Fuente oficial | Evidencia aplicada |
| --- | --- | --- |
| Django transactions/locks | https://docs.djangoproject.com/en/6.0/topics/db/transactions/ ; https://docs.djangoproject.com/en/6.0/ref/models/querysets/#select-for-update | `atomic`, locks `of=("self",)` y carreras PostgreSQL. |
| Django migrations/admin | https://docs.djangoproject.com/en/6.0/ref/migration-operations/#runsql ; https://docs.djangoproject.com/en/6.0/ref/contrib/admin/ | `RunSQL` para triggers y admin read-only. |
| PostgreSQL 18 triggers/JSON | https://www.postgresql.org/docs/18/sql-createtrigger.html ; https://www.postgresql.org/docs/18/datatype-json.html | Bloqueo UPDATE/DELETE y snapshot JSONB. |
| JSON Schema 2020-12 | https://json-schema.org/draft/2020-12/json-schema-core.html ; https://json-schema.org/draft/2020-12/json-schema-validation.html | Contrato estricto local sin refs remotos. |
| jsonschema/Ajv | https://python-jsonschema.readthedocs.io/en/stable/validate/ ; https://ajv.js.org/json-schema.html | Mismo dialecto backend/frontend. |
| DRF/drf-spectacular | https://www.django-rest-framework.org/api-guide/serializers/ ; https://drf-spectacular.readthedocs.io/en/latest/customization.html | Serializers cerrados y OpenAPI sin warnings. |
| Next/React | https://nextjs.org/docs/app/api-reference/functions/fetch ; https://react.dev/reference/rsc/server-components | Server Components y `no-store`. |
| TanStack Query | https://tanstack.com/query/latest/docs/framework/react/guides/query-invalidation | Invalidación acotada, sin optimistic/retry. |
| Playwright/axe | https://playwright.dev/docs/accessibility-testing ; https://playwright.dev/docs/input | Chromium, teclado, axe y 390 px. |

Versiones/avisos se contrastaron en PyPI, npm Registry y repositorios oficiales.
No se usaron blogs, tutoriales o respuestas de terceros.

## Prompt 14 consultation — 2026-07-30

| Tema | Fuente oficial | Evidencia aplicada |
| --- | --- | --- |
| SymPy 1.14 | https://docs.sympy.org/latest/modules/core.html ; https://pypi.org/project/sympy/1.14.0/ | Constructores explícitos, álgebra exacta y soporte Python 3.13; sin parsers de texto. |
| Celery 5.6 | https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html ; https://docs.celeryq.dev/en/stable/userguide/workers.html | Integración Django, dispatch after commit, prefork, prefetch y time limits. |
| Celery security/config | https://docs.celeryq.dev/en/stable/userguide/configuration.html | JSON-only, result backend deshabilitado, UTC y broker Redis. |
| Redis | https://redis.io/docs/latest/develop/interact/pubsub/ ; https://redis.io/docs/latest/develop/clients/redis-py/ | Broker efímero; PostgreSQL conserva el estado durable. |
| MathJSON/Compute Engine | https://mathjson.org/ ; https://cortexjs.io/compute-engine/ | AST estructurado, parse UX LaTeX y serialización MathJSON. |
| MathLive | https://mathlive.io/mathfield/ | Entrada, teclado físico/virtual y eventos del math-field. |
| Django locks/commit | https://docs.djangoproject.com/en/6.0/ref/models/querysets/#select-for-update ; https://docs.djangoproject.com/en/6.0/topics/db/transactions/ | Locks, `on_commit`, transacciones y prueba del outer join nullable. |
| PostgreSQL aggregates | https://www.postgresql.org/docs/18/functions-aggregate.html | `avg`, `corr` y percentiles sin pandas/SciPy. |
| DRF/OpenAPI | https://www.django-rest-framework.org/api-guide/serializers/ ; https://drf-spectacular.readthedocs.io/en/latest/customization.html | Inputs cerrados, responses y jobs 202. |
| JSON Schema/Ajv | https://json-schema.org/draft/2020-12/ ; https://ajv.js.org/json-schema.html | Schemas locales estrictos y drift backend/frontend. |
| Next/React | https://nextjs.org/docs/app ; https://react.dev/reference/react/useEffect | Server/Client boundaries y polling con cleanup. |
| Playwright/axe | https://playwright.dev/docs/accessibility-testing ; https://playwright.dev/docs/test-assertions | E2E Chromium, teclado, axe y 390 px. |

PyPI, npm Registry, repositorios oficiales y avisos de seguridad confirmaron
pins estables no prerelease. No se usaron blogs, Stack Overflow ni parsers de
terceros como autoridad.

## Revalidación de learning — 2026-07-30

| Autoridad oficial | Fuente | Aplicación |
| --- | --- | --- |
| Django 6.0 | https://docs.djangoproject.com/en/6.0/ref/models/querysets/#select-for-update | Locks con `of=("self",)` y `TransactionTestCase`; no lock sobre outer join nullable. |
| PostgreSQL 18 | https://www.postgresql.org/docs/18/plpgsql-trigger.html | Triggers row-level que abortan UPDATE/DELETE. |
| DRF | https://www.django-rest-framework.org/api-guide/throttling/ | Throttle scoped de posición; no es control de concurrencia. |
| drf-spectacular | https://drf-spectacular.readthedocs.io/en/latest/customization.html | Serializers y operation IDs explícitos, schema sin warnings. |
| django-filter 26.1 | https://django-filter.readthedocs.io/en/stable/guide/rest_framework.html | FilterSet DRF con campos allowlisted. |
| Next 16 | `node_modules/next/dist/docs/01-app/01-getting-started/05-server-and-client-components.md` | Pages Server Components; browser APIs en Client Components. |
| React 19 | https://react.dev/reference/react/useEffect ; https://react.dev/reference/react/useRef | Observer/timers en effect; refs fuera del render. |
| TanStack Query 5 | https://tanstack.com/query/latest/docs/framework/react/guides/mutations | Mutaciones sin retry e invalidación tras éxito. |
| React Hook Form | https://react-hook-form.com/docs/useform | Formularios con schema y errores accesibles. |
| Zod 4 | https://zod.dev/basics | Validación de UUID, fechas y payloads antes de mutar. |
| Playwright | https://playwright.dev/docs/accessibility-testing | E2E visible, locators por rol y axe A/AA. |
| MDN | https://developer.mozilla.org/docs/Web/API/Intersection_Observer_API ; https://developer.mozilla.org/docs/Web/API/Window/pagehide_event ; https://developer.mozilla.org/docs/Web/API/Request/keepalive | Posición visible, debounce y flush de navegación. |

## Prompt 15 consultation — 2026-07-31

| Tema | Fuente oficial | Evidencia aplicada |
| --- | --- | --- |
| AWS S3 uploads/checksums | https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html ; https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity-upload.html ; https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html | Presigned upload, checksum SHA-256 y flujo multipart; ETag no es digest autoritativo. |
| AWS S3 controls | https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html ; https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html ; https://docs.aws.amazon.com/AmazonS3/latest/userguide/intro-lifecycle-rules.html | Block public access, versioning, lifecycle y abort multipart. |
| Boto3 1.43.61 | https://boto3.amazonaws.com/v1/documentation/api/latest/index.html ; https://pypi.org/project/boto3/1.43.61/ | Cliente S3 directo, Python 3.13 y Apache-2.0. |
| Pillow 12.3.0 | https://pillow.readthedocs.io/en/stable/releasenotes/12.3.0.html ; https://pypi.org/project/pillow/12.3.0/ | Verificación, EXIF transpose, límites/decompression bombs y MIT-CMU. |
| pypdf 6.14.2 | https://pypdf.readthedocs.io/en/stable/ ; https://pypi.org/project/pypdf/6.14.2/ | PDF/pages/encryption y BSD-3-Clause. |
| FFmpeg 8.1.2 | https://ffmpeg.org/download.html ; https://ffmpeg.org/releases/ ; https://ffmpeg.org/legal.html | Tarball estable, firma PGP `FCF986EA15E6E293A5644F10B4322F04D67658D8`, ffprobe y obligaciones GPL/libx264. |
| ClamAV 1.5.3 | https://docs.clamav.net/manual/Installing/Docker.html ; https://docs.clamav.net/manual/Usage/Scanning.html | Imagen oficial, daemon/INSTREAM y fail closed. |
| LocalStack | https://docs.localstack.cloud/aws/services/s3/ ; https://github.com/localstack/localstack/releases/tag/v4.14.0 | Emulación S3 local fijada; versiones recientes con autenticación/licencia no se adoptaron. |
| Celery 5.6.3 | https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html ; https://docs.celeryq.dev/en/stable/userguide/tasks.html | Dispatch after commit, acks late, retries e idempotencia. |
| WebVTT | https://www.w3.org/TR/webvtt1/ | Gramática, cues y asociación `<track>`. |
| WCAG 2.2 / HTML media | https://www.w3.org/TR/WCAG22/ ; https://html.spec.whatwg.org/multipage/media.html | Alt/decorative, transcript, captions, progreso y controles nativos. |

PyPI, repositorios oficiales, registries e imágenes publicadas confirmaron pins
y licencias. `django-storages` 1.14.6 fue rechazado por no declarar Django 6 ni
Python 3.13; MinIO fue rechazado tras el archivado de su repositorio comunitario.

## Prompt 16 consultation — 2026-07-31

| Tema | Fuente oficial | Evidencia aplicada |
| --- | --- | --- |
| PostgreSQL FTS y trigram | https://www.postgresql.org/docs/18/textsearch.html ; https://www.postgresql.org/docs/18/pgtrgm.html | `websearch_to_tsquery`, ranking, headline, GIN y trigram acotado. |
| Django PostgreSQL search | https://docs.djangoproject.com/en/6.0/ref/contrib/postgres/search/ ; https://docs.djangoproject.com/en/6.0/ref/contrib/postgres/operations/ | `SearchVectorField`, `SearchRank`, `SearchHeadline` y `TrigramExtension`. |
| Django transacciones | https://docs.djangoproject.com/en/6.0/topics/db/transactions/ | `transaction.on_commit` y tests de commit/rollback. |
| Celery 5.6.3 | https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html ; https://docs.celeryq.dev/en/stable/userguide/tasks.html | `delay_on_commit`, task IDs, retry y workers idempotentes. |
| OpenTelemetry Python/OTLP | https://opentelemetry.io/docs/languages/python/ ; https://opentelemetry.io/docs/languages/python/exporters/ | Traces/metrics estables, logs development, OTLP y batching. |
| Collector 0.157.0 | https://opentelemetry.io/docs/collector/ ; https://github.com/open-telemetry/opentelemetry-collector-releases/releases/tag/v0.157.0 | Contrib por filelog, pipelines y release estable. |
| Sentry Python/Next | https://docs.sentry.io/platforms/python/ ; https://docs.sentry.io/platforms/javascript/guides/nextjs/ | Scrubbing, `before_send`, PII off y setup manual sin Replay. |
| Prometheus | https://prometheus.io/docs/practices/naming/ ; https://prometheus.io/docs/practices/instrumentation/ | Nombres, labels acotados y cardinalidad. |
| Grafana/Loki/Jaeger | https://grafana.com/docs/grafana/latest/administration/provisioning/ ; https://grafana.com/docs/loki/latest/send-data/otel/ ; https://www.jaegertracing.io/docs/2.20/ | Provisioning, OTLP logs y Jaeger v2 OTLP. |
| Registros | https://pypi.org/ ; https://registry.npmjs.org/ | Pins: sentry-sdk 2.66.1, structlog 26.1.0, OTel 1.44.0 y @sentry/nextjs 10.69.0. Las instrumentaciones `0.65b0` se rechazaron. |
| Imágenes oficiales | Docker Hub y releases oficiales | Collector 0.157.0, Prometheus 3.13.2, Jaeger 2.20.0, Loki 3.7.4 y Grafana 13.1.1, todos con digest linux/amd64 verificado. |

No se usaron blogs, tutoriales, previews ni tags flotantes como autoridad.
