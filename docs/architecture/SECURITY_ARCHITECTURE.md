# Security architecture

## Baseline

- Create the custom Django user model in the first migration. Use Django's supported modern password hasher configuration, secure password reset/email verification flows, django-allauth MFA/usersessions capabilities, and session invalidation on sensitive changes.
- Browser authentication is Django session + `HttpOnly`, `Secure` (production), `SameSite` cookies, CSRF middleware/tokens, HTTPS, same origin and a reverse proxy. `django-cors-headers` is not approved initially.
- Apply RBAC plus object policies at the service/API boundary; privileged operations are authorization-checked, rate-limited and audit-recorded. Django Admin is internal-only.
- Validate every input server-side. Use ORM/parameterized database access; encode output; restrict rich content to a vetted semantic schema; configure Django 6 CSP and security headers.
- Uploads use allowlisted media types, magic-byte/content inspection where viable, size/count limits, generated safe keys, malware scanning before availability, private buckets by default, and short-lived signed access.
- Secrets exist only in environment/secret stores. `.env.example` names variables but has no real values. Logs/traces never include passwords, cookies, tokens, PII-rich answers, or unredacted submissions.
- Local PostgreSQL and Redis bind exclusively to `127.0.0.1`, require generated passwords, and use a private Compose bridge network. PostgreSQL initializes host connections with SCRAM and checksums; Redis uses local `requirepass`, AOF, and the official non-root entrypoint. This is not a substitute for production TLS, ACL users, rotation, or network policy.
- Passwords use Django's official Argon2id hasher first, while retained built-in hashers verify legacy values. Session cookies are HttpOnly/SameSite=Lax, production marks session and CSRF cookies secure, and DRF is SessionAuthentication plus IsAuthenticated by default.
- Public authentication uses only the official allauth browser headless surface. Mandatory email verification and password recovery use allauth one-time codes; browser requests remain subject to Django CSRF. Redis database 1 is only the `lms-auth` cache namespace for allauth rate limits, never a session store or user/code store. Redis failure is not allowed to fall back to local cache.
- Browser traffic remains same-origin at Next.js. Only explicit rewrite surfaces reach Django; the internal Django origin is server-only, CSRF remains readable to same-origin JavaScript, and neither session nor code is persisted in browser storage.
- Authentication and protected responses send `Cache-Control: no-store`, `Referrer-Policy: same-origin`, `X-Content-Type-Options: nosniff` and a restrictive permissions policy. `/admin/` is deliberately not rewritten. Development and E2E routing bind to `127.0.0.1`; production origin and reverse-proxy trust remain explicit deployment work.

## Operational controls

Encrypted backups and tested restore procedures cover PostgreSQL and object storage; retention/deletion policies distinguish operational logs, audit records, academic records, and media. Dependencies use lockfiles, vulnerability checks, release review, and SBOM export. CI has secret scanning, permission-minimal credentials, protected branches, review of migrations and OpenAPI diffs.

## Threat decisions

The primary risks are account takeover, authorization bypass, CSRF/XSS in authoring, malicious uploads, grading/attempt tampering, data leakage via search/analytics, background-task replay, secret exposure, and destructive migrations. Threat modeling precedes each public or sensitive module. Celery tasks are idempotent, receive stable identifiers not trusted payloads, re-check authorization/business state, and are queued only after transaction commit.
# Seguridad

La API usa sesión Django y CSRF. Los selectores filtran por membresía activa
antes de buscar por slug/UUID, por lo que un recurso de otra organización es
404. Owner y administrator tienen capacidades explícitas; sólo un superuser
activo tiene bypass y `is_staff` no concede capacidades.
# Currículo acotado por organización

Las rutas de catálogo contienen el slug de organización y resuelven la entidad
por esa frontera; un UUID ajeno produce 404. `catalog.view` sólo recibe activos,
mientras `catalog.manage` puede incluir archivados y `catalog.manage_prerequisites`
controla los dos grafos. Serializers no aceptan organización, actores, estado ni
internos Treebeard; servicios aplican transacciones, políticas y transiciones.

No hay JWT, almacenamiento local de sesión, `AllowAny`, `csrf_exempt`, DELETE
curricular ni relaciones entre organizaciones.

## Frontera de Courses

Los selectores comienzan por organización y curso visibles; después limitan
revisión, módulo y unidad al padre autorizado. UUID ajenos responden 404 y una
capacidad insuficiente 403. `is_staff` no evita políticas; sólo el superuser
activo tiene bypass explícito. Serializers excluyen organización, actores,
estado, posición y `lock_version`. Cada mutación exige `expected_version`,
bloquea la revisión y rechaza una versión obsoleta con 409. Ni permisos,
estructura ni borradores se almacenan en cookies, Redis, `localStorage` o
`sessionStorage`; la sesión conserva sólo identidad Django.

## Frontera de contenido semántico

El body se limita por bytes antes de decodificar en profundidad. Después pasan
pre-scan iterativo, meta-schema Draft 2020-12, validadores semánticos, unicidad
UUID, protocolos de links y denylist/allowlist LaTeX. Sólo JSON canónico
aceptado llega a JSONB. No se persisten HTML, SVG ni MathML; paste/drop de
archivos se rechaza y el renderer propio no usa `dangerouslySetInnerHTML`.

MathJax y fuentes MathLive se sirven localmente. La configuración carga
`ui/safe`, paquetes base/ams explícitos y excluye `texhtml` y `require`
arbitrario. SVG generado queda fuera del árbol accesible duplicado y su
contenedor matemático tiene nombre. CodeMirror jamás evalúa el texto. Links
renderizados mantienen protocolo permitido y atributos seguros.

La consulta siempre resuelve organización → curso → revisión → unidad; un UUID
ajeno es 404. Capacidad insuficiente es 403, versión obsoleta 409 y payload
inválido 400. Campos derivados, actores, número, digest, unidad y estado no son
asignables por request. Staff no evita policies; sólo superuser activo tiene
bypass explícito.
