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
| Radix / shadcn | Primitivas accesibles y código UI propio generado para una interfaz institucional coherente. | Churn visual y riesgo de conservar componentes copiados sin uso. | Aprobado: Radix en runtime; shadcn sólo como generador fijado y retirado del runtime tras `eject`. |
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

## Evaluación Prompt 9

No se añadió ninguna dependencia. Django/PostgreSQL cubren transacciones,
locking, constraints diferibles y posiciones; DRF/django-filter/drf-spectacular
cubren el contrato; el cliente existente cubre caché, formularios, same-origin y
Chromium. Se rechazaron bibliotecas de ordering, admin sortable, historial,
máquinas de estados, grafos y drag-and-drop porque duplicarían invariantes
pequeñas y explícitas. Sus licencias no cambian la decisión: no existe un
problema técnico que justifique añadir propietario, actualización ni alternativa
de retirada.

## Evaluación Prompt 10

`jsonschema==4.26.0` resuelve validación portable Draft 2020-12 en el servidor;
se seleccionó sobre validadores manuales como fuente exclusiva porque los
validadores semánticos sólo complementan el contrato. Tiptap 3.29.2 y sus
extensiones oficiales resuelven ProseMirror, schema, React y render estático sin
crear un editor paralelo. Ajv 8.20.0 y json-schema-to-typescript 15.0.4 mantienen
el navegador derivado del mismo archivo.

MathLive 0.110.0 se limita a entrada LaTeX y MathJax 4.1.3 a representación local
segura; no se aceptó KaTeX, CDN, SVG/MathML almacenado ni HTML TeX. CodeMirror 6
se instaló sólo para edición inert de Python, JavaScript/TypeScript, JSON, SQL y
texto; Monaco fue rechazado por tamaño y complejidad, y no existe runtime de
ejecución. Todas las dependencias tienen pin exacto y licencias permisivas
registradas; axe conserva MPL-2.0 ya aceptada.

El equipo de contenido es owner de actualización y retirada. Si se elimina una
biblioteca UI, el JSON Schema, las versiones y el API sobreviven: los adaptadores
son reemplazables. Los riesgos aceptados son bundle, fuentes locales, churn de
extensiones y warnings transitivos WASI/lifecycle; se controlan con asset drift,
auditorías, unit tests, Next build, Chromium, axe y requests externas bloqueadas.
Se rechazaron collaboration/CRDT, autosave, IndexedDB, upload/media, ejecución,
plantillas HTML y un segundo schema frontend por no pertenecer a esta fase.

## Evaluación del sistema visual institucional — 2026-07-29

Se ejecutó el generador oficial `shadcn 4.16.0` con el estilo `radix-nova` sobre
el proyecto Next existente. El resultado usa `radix-ui 1.6.7` (MIT), compatible
por peer con React 19, `lucide-react 1.27.0` (ISC),
`class-variance-authority 0.7.1` (Apache-2.0), `clsx 2.1.1`,
`tailwind-merge 3.6.0` y `tw-animate-css 1.4.0` (MIT), todos con versión exacta.
El equipo frontend es propietario de su actualización.

`shadcn` no permanece como dependencia de runtime: `eject` integró su hoja
Tailwind en `globals.css` y retiró el paquete. Se conservaron solamente las
primitivas usadas por la plataforma; se eliminaron checkbox, empty, field,
pagination, select, table, tabs y button-group generados pero no consumidos.
También se retiraron `next-themes` y `sonner` porque ninguna ruta los usaba.

El problema resuelto es consistente y acotado: sidebar responsive, diálogos,
alertas, formularios, breadcrumbs, tooltips y controles accesibles sin crear
otro sistema de navegación o autorización. La alternativa de retirada es
mantener las firmas locales de `components/ui` y sustituir internamente cada
primitiva por HTML/React accesible. El dominio, los contratos OpenAPI, las
políticas y los datos no dependen de estas piezas visuales.

Los warnings peer opcionales de `@napi-rs/wasm-runtime` heredados por Vite y el
resolver de ESLint permanecen visibles y no se suprimieron. No pertenecen a las
dependencias UI añadidas; se aceptan únicamente mientras instalación congelada,
lint, tests y build funcionen sin autorizar scripts bloqueados.

## Evaluación Prompt 11

No se añadió ni actualizó dependencia. JSONB, locks, constraints, triggers,
SHA-256 y canonicalización se resuelven con PostgreSQL, Django y biblioteca
estándar. jsonschema/Ajv/tipos, DRF/OpenAPI, TanStack, renderer y Playwright ya
tenían problema, owner, licencia y alternativa documentados. Se rechazaron
event sourcing externo, blockchain, cache de publicación, sanitizer adicional
y storage porque aumentarían superficie sin resolver un requisito. Después del
primer release, hechos y triggers son retención irreversible por diseño.
