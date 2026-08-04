# Compatibility matrix

| Matrix | Result | Evidence / reproducible confirmation in Prompt 2 |
|---|---|---|
| Python 3.13.13 ↔ Django 6.0.7 | Compatible | Django official 6.0 matrix supports Python 3.13. Run `uv run python manage.py check`. |
| Django 6.0.7 ↔ DRF 3.17.1 | Compatible | DRF 3.17 release notes explicitly add Django 6.0. Run API smoke and tests. |
| Django 6.0.7 ↔ allauth 65.18.0 | Compatible | allauth 65.13.1 release notes declare Django 6 support. Run `manage.py check` with headless apps. |
| django-allauth 65.18.0 browser headless ↔ Django sessions/CSRF | Compatible | Official browser routes call `get_token()` and use Django's session strategy; test CSRF and cookie flow against PostgreSQL. |
| Django RedisCache ↔ redis-py 8.0.1 ↔ Redis 8.8.1 | Compatible | Django native Redis backend with Redis database 1 and a namespaced key prefix; integration test demonstrates allauth 429. |
| Django 6.0.7 ↔ Celery 5.6.3 | Compatible with Linux worker | Celery 5.6 supports Django >=2.2.28 and Python 3.13; Windows worker is unsupported. Run worker in Linux Compose. |
| Celery 5.6.3 ↔ redis-py 8.0.1 ↔ Redis 8.8.1 | Compatible by minimums, integration required | Celery minimum redis-py 4.5.2. Verify broker/result operations in Compose before enabling production use. |
| Django 6.0.7 ↔ PostgreSQL 18.4 ↔ psycopg 3.3.4 | Compatible | Django supports PostgreSQL and lists psycopg >=3.1.12 for Python 3.12+. Run migrations/integration tests. |
| Django 6.0.7[argon2] ↔ argon2-cffi 25.1.0 ↔ Python 3.13.13 | Compatible | Official Django extra resolved by uv; Argon2id is first configured hasher and tests verify hashes. |
| Django 6.0.7 ↔ django-stubs 6.0.7 ↔ Pyright | Compatible for application code | PyPI declares Django 6.0/Python 3.13 support; dynamic Django test-client internals remain runtime-tested with pytest. |
| Node 24.18.0 ↔ Next 16.2.12 ↔ React 19.2.8 | Compatible by documented floor | Next requires Node >=20.9; create app and run build/typecheck. |
| Next 16.2.12 ↔ TypeScript 7.0.2 | Incompatible in installed lint chain | `eslint-config-next` installs `typescript-eslint` peers `<6.1`; resolution failed. TypeScript 6.0.2 passes frozen install, lint, `tsc`, Vitest, Playwright and build; ADR 0011 records the fallback. |
| Next 16.2.12 ↔ security overrides | Validated with explicit debt | Root pins `postcss@8.5.18` and `sharp@0.35.3`; `pnpm audit --prod`, lint, typecheck and build pass. Revisit on every Next upgrade. |
| React 19.2.8 ↔ Tiptap/MathLive/MathJax | Deferred integration | Package metadata supports modern React but official explicit matrix is incomplete; prove with editor unit/e2e/a11y tests in Phase 13. |
| PostgreSQL 18.4 image ↔ local Compose ↔ Linux production | Compatible with mount adjustment | Official image changed PGDATA layout in 18. Mount `/var/lib/postgresql`, not legacy path. |
| Windows x64 ↔ local toolchain | Partially compatible | API/web toolchain present; psql/redis native absent; Docker services avoid this gap. Celery stays Linux. |
| Same-origin proxy ↔ Django sessions | Design-compatible | No CORS needed; validate secure cookies/CSRF behind proxy in Phase 7/29. |
| React 19.2.8 ↔ TanStack Query 5.101.4 ↔ RHF 7.83.0 ↔ Zod 4.4.3 | Compatible | npm registry peers accept React 19; strict TypeScript, unit and production build passed. |
| TypeScript 6.0.2 ↔ openapi-typescript | Compatible with 6.7.6 | Latest 7.13.0 declares TypeScript `^5.x`, so it is rejected rather than forcing a peer conflict. |
| S3-compatible storage ↔ django-storages/boto3 | Compatible, provider deferred | S3 adapter is approved; test against MinIO only after official image pin in Phase 3. |

“Compatible” never replaces the required technical proof: `check`, locked install, migrations, health checks, API tests, and browser session E2E are the acceptance evidence of later phases.
# Compatibilidad Prompt 7

No hubo dependencia nueva. La integración usa las versiones bloqueadas y
compatibles de Django/DRF/drf-spectacular y la pareja
openapi-typescript/openapi-fetch ya validada para TypeScript 6.

## Compatibilidad Prompt 8

| Matrix | Resultado | Evidencia |
|---|---|---|
| Django 6.0.7 ↔ django-filter 26.1 | Compatible | PyPI y checks Django. |
| Django 6.0.7 ↔ django-treebeard 6.0.0 | Compatible | Clasificadores Django 6/Python 3.13 y pruebas MP_Node. |
| PostgreSQL 18.4 ↔ CTE/locks | Compatible | Pruebas de grafos y concurrencia. |

## Compatibilidad Prompt 9

| Combinación | Resultado | Evidencia 2026-07-29 |
|---|---|---|
| Django 6.0.7 ↔ PostgreSQL 18.4 constraints diferibles | Compatible | `sqlmigrate courses 0001`, migración limpia y reorder concurrente real. |
| DRF 3.17.1 ↔ django-filter 26.1 | Compatible | filtros posteriores a visibilidad y paginación probados por API. |
| drf-spectacular 0.30.0 ↔ OpenAPI 3.0.3 | Compatible | schema sin warnings y cliente sincronizado. |
| Next 16.2.12 ↔ React 19.2.8 ↔ TanStack Query 5.101.4 | Compatible | lint, tipos, Vitest, build y Chromium. |
| Playwright 1.58.2 ↔ Chromium ↔ axe 4.12.1 | Compatible | cinco rutas, 390 px, teclado, dos contextos y cero violaciones A/AA. |

## Compatibilidad Prompt 10

| Combinación | Resultado | Evidencia 2026-07-29 |
| --- | --- | --- |
| Python 3.13.13 ↔ jsonschema 4.26.0 ↔ Draft 2020-12 | Compatible | meta-schema, corpus válido/inválido y suite backend sobre el schema canónico. |
| Django 6.0.7 ↔ PostgreSQL 18.4 JSONB/locks | Compatible | migración real, checks/constraints y pruebas `TransactionTestCase` de primera save y update concurrentes. |
| Tiptap 3.29.2 ↔ React 19.2.8 ↔ Next 16.2.12 | Compatible | SSR con `immediatelyRender: false`, unit tests, round-trip, build y Chromium real. |
| Ajv 8.20.0 ↔ JSON Schema Draft 2020-12 | Compatible | `Ajv2020`, formatos propios estrictos y el mismo corpus frontend/backend. |
| MathLive 0.110.0 ↔ MathJax 4.1.3 | Compatible | edición LaTeX, bundles/fuentes locales, safe extension, unit tests y axe. |
| CodeMirror 6 modular ↔ React 19 | Compatible | lifecycle estable sin remount por tecla, lenguajes enumerados y salida de teclado probada. |
| json-schema-to-typescript 15.0.4 ↔ TypeScript 6.0.2 | Compatible | generación determinista, typecheck y drift check sin escritura. |
| Tiptap/MathJax/CodeMirror ↔ CSP futura | Compatible por diseño | no CDN, eval, ejecución de código ni HTML persistido; la política CSP de producción sigue diferida. |

La compatibilidad observada no elimina la obligación de repetir frozen install,
schema drift, lint, tipos, pruebas, build y Playwright al cambiar cualquier pin.

## Compatibilidad Prompt 11

| Combinación | Resultado | Evidencia 2026-07-30 |
| --- | --- | --- |
| Django 6.0.7 ↔ PostgreSQL 18.4 JSONB/triggers/locks | Compatible | Migración limpia y pruebas ORM/SQL/concurrencia. |
| jsonschema 4.26.0 ↔ Ajv 8.20.0 ↔ Draft 2020-12 | Compatible | Corpus release y drift de tipos. |
| DRF 3.17.1 ↔ drf-spectacular 0.30.0 | Compatible | OpenAPI válido sin warnings y cliente generado. |
| Next 16.2.12 ↔ React 19.2.8 ↔ TanStack Query 5.101.4 | Compatible | Tipos, Vitest, build y lectura no-store. |
| Playwright 1.58.2 ↔ Chromium ↔ axe 4.12.1 | Compatible | Publish/reader/withdraw, teclado, axe y 390 px. |

## Learning — verificación 2026-07-30

| Integración exacta | Estado | Evidencia |
| --- | --- | --- |
| Django 6.0.7 ↔ PostgreSQL 18.4 locks/partial constraints/triggers | Compatible | Migración limpia, SQL directo y tres carreras. |
| DRF 3.17.1 ↔ drf-spectacular 0.30.0 ↔ django-filter 26.1 | Compatible | OpenAPI sin warnings, filtros/paginación y cliente sin drift. |
| Next 16.2.12 ↔ React 19.2.8 ↔ Query 5.101.4 ↔ RHF 7.83.0 ↔ Zod 4.4.3 | Compatible | TypeScript, ESLint, Vitest, Server/Client boundaries y build. |
| Playwright 1.62.0 ↔ Chromium ↔ axe 4.12.1 | Compatible | Learning E2E, 390 px y WCAG A/AA sin violaciones. |

## Advanced assessments — verificación 2026-07-30

| Integración exacta | Estado | Evidencia |
| --- | --- | --- |
| Python 3.13.13 ↔ SymPy 1.14.0 | Compatible | PyPI, imports, constructores y suite matemática. |
| Python 3.13.13 ↔ Celery 5.6.3 | Compatible en Linux | Worker Compose prefork real; Windows permanece excluido. |
| Celery 5.6.3 ↔ redis-py 6.4.0 ↔ Redis 8.8.1 | Compatible | Broker DB 2, JSON, health y domain smoke. |
| Django 6.0.7 ↔ Celery 5.6.3 | Compatible | Config oficial, `on_commit` y tasks idempotentes. |
| Django 6.0.7 ↔ PostgreSQL 18.4 | Compatible | Migraciones/triggers, locks, corr y percentiles reales. |
| Compute Engine 0.99.0 ↔ TypeScript 6.0.2 ↔ Node 24 | Compatible | Frozen install, types, Vitest, Next build y Chromium. |
| MathLive 0.110.0 ↔ React 19.2.8 | Compatible | Editor/response reales, teclado y axe. |
| Scoring schemas ↔ jsonschema 4.26.0 ↔ Ajv 8.20.0 | Compatible | Corpus, generación y drift checks. |

Compute Engine es adaptador de entrada, no autoridad de nota; SymPy sólo corre
en el worker. La compatibilidad exige repetir build/worker/E2E ante cualquier
cambio de pin.

## Phase 15

| Combinación | Resultado | Evidencia |
| --- | --- | --- |
| Python 3.13.13 + Django 6.0.7 + boto3 1.43.61 | Compatible | classifiers PyPI, lock y gateway/smoke S3 |
| Python 3.13.13 + Pillow 12.3.0 | Compatible | classifiers, import y pipeline imagen |
| Python 3.13.13 + pypdf 6.14.2 | Compatible | classifiers, import y pipeline PDF |
| Celery 5.6.3 + Redis 8.8.1 + Django 6 | Compatible | worker real, ping y jobs media |
| FFmpeg 8.1.2 + Debian trixie + libx264 | Compatible GPL | build firmado, ffprobe/transcodes reales |
| ClamAV 1.5.3 + media worker | Compatible | PING, clean demo y EICAR rechazado |
| LocalStack 4.14.0 + S3 API | Compatible sólo local | buckets/checksums/presign/lifecycle smoke |
| django-storages 1.14.6 + Django 6/Python 3.13 | Rechazado | classifiers oficiales insuficientes |
| MinIO community | Rechazado | repositorio archivado; AWS S3 es contrato |

La compatibilidad requiere repetir build, smoke real, migración y Chromium al
cambiar cualquier pin. LocalStack 4.14.0 no es recomendación productiva.

## Academic scheduling and live classes — 2026-07-31

| Combinación | Resultado previo a instalación | Evidencia requerida al cierre |
| --- | --- | --- |
| Python 3.13.13 + `livekit-api 1.2.0` | Compatible por `Requires-Python >=3.9` | import, tokens/grants, webhook firmado y gateway mock/real si hay credenciales |
| Django 6.0.7 + SDK asíncrono LiveKit | Compatible mediante bridge explícito, sin `asyncio.run()` | concurrencia, cierre de cliente, errores remotos e idempotencia |
| Python 3.13.13 + `python-dateutil 2.9.0.post0` | Compatible por metadata PyPI | corpus RRULE, DST, COUNT/UNTIL, excepciones y límites |
| React 19.2.8 + LiveKit components 2.9.23 + client 2.21.0 | Peers compatibles (`react >=18`, client `^2.20.1`) | TypeScript, Vitest, build, cleanup/reconexión y Chromium |
| React 19.2.8 + FullCalendar React 7.0.2 | Peer oficial `^17 || ^18 || ^19`; SSR soportado | import v7, SSR/build, rango visible, interacción y axe |
| FullCalendar 7.0.2 + temporal-polyfill 1.0.2 | Peer `^1.0.1` satisfecho | frozen install y build sin paquetes v6/Premium |

La metadata compatible no sustituye `uv sync --locked`, `pnpm install
--frozen-lockfile`, migración PostgreSQL, suites, build ni navegador real.

## Renderizado de lecciones fuente — 2026-08-04

| Combinación | Resultado | Evidencia requerida |
| --- | --- | --- |
| React 19.2.8 + `react-markdown 10.1.0` | Compatible por peer `react >=18` | TypeScript, Vitest y Next build |
| `react-markdown 10.1.0` + `remark-gfm 4.0.1` + `remark-math 6.0.0` | Compatible en unified/remark | tablas/listas, delimitadores matemáticos y HTML crudo omitido |
| `remark-math 6.0.0` + MathJax 4.1.3 local | Compatible mediante adaptador React explícito | matemática inline/bloque y ausencia de CDN |
| `.tex` UTF-8 + parser de lectura acotado + MathJax 4.1.3 | Compatible sin compilación | corpus real, límites y aviso visible para TikZ no representado |

La compatibilidad no significa soporte general de todos los paquetes TeX. La
fuente original permanece descargable y cualquier entorno no interpretado debe
quedar visible como limitación, nunca desaparecer silenciosamente.
