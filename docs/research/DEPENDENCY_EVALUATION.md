# Dependency evaluation

| Candidate | Problem / native alternative | License / risk | Decision |
|---|---|---|---|
| Django, DRF, drf-spectacular | Web, validation, REST/OpenAPI; Django alone lacks DRF/schema generation. | BSD-style; schema generation must remain reviewed. | Approve. |
| Django[argon2] / argon2-cffi | Argon2id password hashing; Django default PBKDF2 is retained for verification. | MIT; memory-hard hashing has intentional test cost. | Approve, configured first. |
| django-stubs | Strict Pyright coverage of Django application code; runtime framework remains dynamically typed. | MIT; dev-only and exact 6.0.7. | Approve for this phase. |
| django-allauth[headless-spec] | Mature account, email codes, browser sessions and official OpenAPI; custom auth would recreate sensitive flows. | MIT; `headless` would add PyJWT for an excluded JWT capability, while browser sessions and the schema run without it. | Approve. |
| redis-py | Native Django `RedisCache` transport for allauth rate limits; Django has no Redis protocol implementation. | MIT-licensed dependency; Redis availability becomes authentication availability. | Approve for cache only; sessions remain PostgreSQL. |
| django-filter | Explicit list filtering; hand-written filters initially possible. | BSD; avoid exposing arbitrary fields. | Approve conditionally. |
| psycopg, django-storages[s3], Pillow | PostgreSQL driver, S3 adapter, safe image processing. | PostgreSQL/BSD; native wheels and image attack surface. | Approve. |
| Celery, redis-py, Redis 8.8.1 | durable async processing/cache coordination; Django 6 background tasks alone lacks chosen queue semantics. | Redis 8 tri-license and Windows worker limit. | Conditional approval; ADR 0012 and legal review before production. |
| transactional-email library/provider | Delivery provider integration. Django SMTP is sufficient interface now. | Provider lock-in and PII. | Defer until provider is selected; use Django email backend abstraction. |
| django-cors-headers | Cross-origin browser API. | Extra attack surface, unnecessary with same origin. | Reject initially. |
| django-csp | CSP headers. Django 6 has CSP framework. | Duplicate solution. | Reject. |
| Ruff, Pyright, pytest stack, pip-audit | Quality/security; stdlib lacks these controls. | Tool churn. | Installed in Phase 2; Pyright uses official npm distribution. |
| factory-boy, Hypothesis | Representative fixtures/property tests. | Tests can become opaque. | Approve where useful. |
| Sentry, OpenTelemetry | Error/tracing operations, absent natively. | Privacy/vendor/config risk. | Approve for observability phase, not scaffold. |
| TypeScript 7 / ESLint 10 | Latest compiler/linter candidates. | `eslint-config-next` installed peer ranges do not support them. | Reject for current scaffold; TS 6.0.2 and ESLint 9.39.5 under ADR 0011. |
| Tailwind | Tokenized responsive styling; plain CSS remains available. | Modern browser floor. | Installed. |
| Radix / shadcn | Accessible primitives / optional code generator. | UI churn and copied generated code. | Radix approve; shadcn defer. |
| TanStack Query, RHF, Zod | Client cache/forms/edge validation; React alone lacks ergonomic contracts. | Do not make client authoritative. | Approve. |
| openapi-fetch / openapi-typescript | One typed browser contract from official allauth OpenAPI; native fetch alone loses generated path/body checking. | MIT; allauth marks two code-flow bodies optional, so the encapsulated fallback is reviewed in ADR 0016. | Approve: `openapi-fetch 0.17.0`; `openapi-typescript 6.7.6` is selected over 7.x because the latter peers only with TypeScript 5 while the repository pins TS 6. |
| @hookform/resolvers / @axe-core/playwright | Bind Zod to React Hook Form and exercise browser accessibility. | MIT / MPL-2.0; axe is necessary but not sufficient for WCAG acceptance. | Approve. |
| Tiptap, MathLive, MathJax | Structured editing, math entry, rendering; native contenteditable/MathML alone insufficient for authoring UX. | Bundle/a11y/schema complexity. | Approve later, isolate. |
| CodeMirror / Monaco | Code editing. | Large bundle, no present requirement. | Defer; select CodeMirror if a real lightweight code-editor need appears. |
| @hey-api/openapi-ts | Typed client from single OpenAPI source. | Generated-code drift. | Approve after contract exists. |
| Vitest, Testing Library, Playwright, MSW | Unit/component/E2E/network tests. | Browser/runtime maintenance. | Approve. |
| Storybook | Visual review/catalogue. | Maintenance cost. | Defer until reusable design system exists. |
| lucide-react | Consistent icons; text labels remain essential. | Decorative icon misuse. | Conditional. |
| animation library | Motion. CSS handles simple motion. | Bundle and reduced-motion risk. | Reject initially. |
| MinIO, Mailpit | Local S3/SMTP emulation. | Image/support selection pending. | Defer to infrastructure phase. |
# Evaluación Prompt 7

Se rechazaron django-guardian, paquetes RBAC, Axios, JWT y bibliotecas de
diálogo: no resuelven una necesidad no cubierta y ampliarían la superficie de
autorización. No se instaló ninguna dependencia.

## Evaluación Prompt 8

`django-filter==26.1` (BSD) aporta FilterSets declarativos limitados a campos
explícitos. `django-treebeard==6.0.0` (Apache-2.0) aporta `MP_Node` sólo para
temas. Se rechazan MPTT, NetworkX, ltree experimental y una base de grafos:
no cubren una necesidad adicional y aumentarían la superficie operativa.
