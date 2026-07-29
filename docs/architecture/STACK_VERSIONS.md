# Stack versions

Consulted 2026-07-28. “Latest” means the latest stable release available at that time, excluding pre-releases; package release dates are verified against the official PyPI/npm registry. Exact pins are deliberately refreshed in Prompt 2 before the first lockfile is created.

| Category | Technology | Latest stable / selected | Support and compatibility checked | Release date | Decision / update policy |
|---|---|---|---|---|---|
| Runtime | Python | 3.13.13 / **3.13.13** | Django 6 supports 3.12–3.14; local `py` provides it. | installed local | Approve now; pin `.python-version`/`.tool-versions`, update patches monthly. |
| Backend | Django | 6.0.7 / **6.0.7** | Supported stable series; Python >=3.12; PostgreSQL supported. 5.2.15 is the supported LTS but not selected because 6.0 is current stable and compatible. | 2026-07-07 | Approve; security patch review monthly. |
| Backend security | argon2-cffi | absent / **25.1.0** | Official Django `argon2` extra; Python 3.13 supported. | 2026-07-29 | Approve for Argon2id password storage. |
| Development typing | django-stubs | absent / **6.0.7** | PyPI declares Django 6.0 and Python 3.13 support; dev-only typing support. | 2026-07-29 | Approve; Pyright excludes dynamic test-client internals, not identity runtime code. |
| Backend | DRF | 3.17.1 / **3.17.1** | Official 3.17 adds Django 6 support; Python >=3.10. | 2026-03-24 | Approve. |
| Backend | django-allauth[headless-spec] | 65.18.0 / **65.18.0** | The distribution includes the browser-session headless surface; `headless-spec` supplies the official OpenAPI dependency without the JWT-only optional extra. | 2026-07-29 | Approve; reevaluate phone-route suppression when upstream supports it. |
| Backend | drf-spectacular | 0.30.0 / **0.30.0** | Python >=3.8; verify schema integration after scaffold. | 2026-07-06 | Approve. |
| Backend | django-filter | 25.2 / **25.2** | Python >=3.10; limited, explicit filtering only. | 2025-01-? | Approve conditionally; re-verify exact metadata in Prompt 2. |
| Backend | psycopg binary extra | 3.3.4 / **3.3.4** | Django 6 notes require >=3.1.12; Python >=3.10. | 2026-05-01 | Approve; production build policy in Phase 29. |
| Async | Celery[redis] | 5.6.3 / **5.6.3** | Python 3.13 and Redis transport documented; unsupported on Windows, use Linux worker. | 2026-03-26 | Approve with Linux-only worker constraint. |
| Async | redis-py | 8.0.1 / **8.0.1** | Python >=3.10; Celery 5.6 minimum is 4.5.2. | 2026-06-23 | Approve as transitive/direct only if cache client needed. |
| Storage | django-storages[s3] | 1.14.6 / **1.14.6** | Python >=3.7; S3 adapter only. | 2025-04-02 | Approve. |
| Storage | boto3 | 1.43.58 / **1.43.58** | Python >=3.10; S3 protocol client. | 2026-07-28 | Approve via django-storages extra; do not duplicate clients. |
| Media | Pillow | 12.3.0 / **12.3.0** | Django 6 lists >=10.1 for Python 3.12. | 2026-07-01 | Approve for image validation/transforms. |
| Quality | Ruff | 0.16.0 / **0.16.0** | Python >=3.7. | 2026-07-23 | Approve as sole Python formatter/linter. |
| Quality | Pyright | 1.1.411 / **1.1.411** | Installed from the official npm distribution, pointing explicitly to `apps/api/.venv`. | 2026-06-25 | Sole primary checker. |
| Quality | pytest / pytest-django / pytest-cov | 9.1.1 / 4.12.0 / 7.0.0 | **same**; Python >=3.10. | 2026-06-19 / 2026-02-14 / 2025-09-09 | Installed in Phase 2. |
| Quality | factory-boy / Hypothesis | 3.3.3 / 6.163.0 | **3.3.3 / 6.163.0**; Python compatible. | 2025-02-03 / 2026-07-28 | Approve; Hypothesis specifically for state/graders. |
| Security/obs | pip-audit / Sentry SDK / OpenTelemetry API | 2.10.1 / 2.66.1 / 1.44.0 | **same**; Python compatible. | 2026-06-10 / 07-22 / 07-16 | Approve respectively for audit, later error telemetry, later traces. |
| Runtime | Node.js | 24.18.0 LTS / **24.18.0** | LTS; Next requires Node >=20.9. | 2026-06-23 | Approve; only LTS patch upgrades. |
| Tool | pnpm | 10.33.2 / **10.33.2** | Local version; corepack available. | installed local | Approve; pin `packageManager`. |
| Frontend | Next.js / React / React DOM | 16.2.12 / 19.2.8 / 19.2.8 | **same**; Next App Router and TS >=5.1 supported; Node 24 compatible. | 2026-07-25 / 07-21 | Approve. |
| Frontend | TypeScript / Tailwind | 7.0.2 / 4.3.3 | **6.0.2 / 4.3.3**; Next requires >=5.1; Tailwind v4 modern-browser caveat. | 2026-07-08 / 07-16 | TS 7 rejected: `eslint-config-next` transitives require `<6.1`; ADR 0011. |
| Frontend | ESLint / Prettier | 10.8.0 / 3.9.6 | **9.39.5 / 3.9.6** | 2026-07-24 / 07-21 | ESLint 10 rejected: Next plugins declare support only through 9. |
| Frontend | Radix / shadcn | 1.1.23 / CLI deferred | **Radix 1.1.23**; shadcn is generator, not a runtime framework. | 2026-07-24 | Radix approve; shadcn defer until design-system need. |
| Frontend | TanStack Query / React Hook Form / Zod | 5.101.4 / 7.83.0 / 4.4.3 | **same**; TypeScript-first client state/forms validation. | 2026-07-21 / 07-25 / 05-04 | Approve. |
| Frontend auth | openapi-fetch / openapi-typescript / resolvers / axe Playwright | 0.17.0 / 7.13.0 / 5.5.7 / 4.12.1 | **0.17.0 / 6.7.6 / 5.5.7 / 4.12.1**; 7.x generator peers only with TypeScript 5, while 6.7.6 has no incompatible peer. | consulted 2026-07-29 | Approve exact pins; reevaluate 7.x when it supports TypeScript 6. |
| Academic | Tiptap / MathLive / MathJax | 3.29.2 / 0.110.0 / 4.1.3 | **same**; keep editor/rendering isolated and test accessibility. | 2026-07-28 / 06-09 / 07-03 | Approve for later authoring phase, not installed in scaffold. |
| API/testing | Vitest / Testing Library / Playwright | 4.1.10 / 16.3.2 / 1.62.0 | **same**; jsdom 30.0.0 and jest-dom 7.0.0 support real smoke tests. | 2026-07-06 / 01-19 / 07-24 | Installed in Phase 2; OpenAPI client and MSW remain deferred. |
| UX | Storybook / lucide-react | 10.5.5 / 1.27.0 | **same**; Storybook is deferred; Lucide only if design needs icons. | 2026-07-27 / 07-25 | Defer / conditional. |
| Data | PostgreSQL | 18.4 / **18.4** | Supported through 2030; Docker Official Image `postgres:18.4-trixie`, Linux amd64 digest locked in `compose.lock.yaml`. | 2026-07-28 official image revalidated | Approve; current minor and digest review required. |
| Cache | Redis server | 8.8.1 / **8.8.1** | Docker Official Image `redis:8.8.1-trixie`, Linux amd64 digest locked in `compose.lock.yaml`; Redis 8 tri-license. | 2026-07-28 official image and license revalidated | Conditional: explicit legal choice before production. |
| Local infra | Docker / Compose | 29.4.1 / 5.1.3 local | Windows x64 present; production target Linux. | installed local | Approve local tooling; no global change. |

The registry snapshot did not establish an authoritative `django-filter` day for 25.2, so that field is intentionally marked for recheck rather than invented.

Phase 2 applies root `pnpm.overrides` for `postcss@8.5.18` and `sharp@0.35.3` to remediate advisories inherited by Next 16.2.12. Remove those compatibility overrides once Next absorbs the fixes.
