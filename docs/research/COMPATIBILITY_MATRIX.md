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
