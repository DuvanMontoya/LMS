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
