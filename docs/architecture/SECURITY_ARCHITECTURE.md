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
404. Owner y administrator tienen capacidades explícitas; `is_staff` e
`is_superuser` no conceden capacidades institucionales sin una membresía activa
(ADR 0034).
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
capacidad insuficiente 403. `is_staff` e `is_superuser` no evitan políticas
institucionales. Serializers excluyen organización, actores,
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
asignables por request. Staff y superuser no evitan políticas institucionales
(ADR 0034).

## Frontera de publicación

La API deriva organización, curso, revisión, snapshot, digest, actores y
versiones; serializers no los aceptan por mass assignment. Lookups ajenos son
404. Releases/eventos tienen guardas de modelo y triggers. Biblioteca exige
sesión/capacidad, usa snapshot, envía `private, no-store` y no usa JWT ni
browser storage.

Learning exige identidad propia, membresía activa, matrícula efectiva, ventana
vigente, publicación activa y release íntegro. UUID conocidos de otra
organización/usuario producen 404. Mutaciones aceptan sólo allowlists y
expected versions; ningún body elige user, actor, organización, status,
assignment o contadores. Superuser administra explícitamente, pero no simula
una matrícula. Position usa CSRF, throttle y keepalive same-origin.

## Frontera de assessments

Cada lookup comienza por organización y capacidad; bank, question, assessment,
delivery, assignment, attempt, response y result ajenos devuelven 404. El
learner debe ser propietario del assignment de release efectivo. Los serializers
de intento exponen sólo `public_snapshot`, puntos, estado y valor guardado:
grading, feedback condicionado, seed y claves no forman parte del contrato.

Los bodies son allowlists, todo guardado usa `expected_version`, un intento
vencido no acepta respuestas y submit es definitivo. Versiones, AttemptItem,
ManualGradeDecision y AttemptEvent rechazan UPDATE/DELETE en PostgreSQL. No hay
DELETE físico, JWT, Web Storage, autosave, ejecución de código, symbolic grading
ni logging de respuestas/claves.

### Calificación avanzada

- MathJSON se valida por forma, operador, símbolo, función, tamaño, profundidad,
  entero y exponente antes de construir SymPy; no se parsea texto ni LaTeX.
- El proceso HTTP no ejecuta SymPy. El worker Linux no root recibe sólo IDs de
  job, usa JSON, soft/hard limits y no publica puertos.
- Grading payload, expected MathJSON, respuestas y seeds no viajan en tareas,
  logs, OpenAPI learner, SSR ni browser storage.
- Jobs y grades usan locks/idempotency en PostgreSQL; revisiones, grade versions,
  item grades y snapshots analíticos son append-only.
- Policies de organización aplican anti-IDOR y separan regrading, gradebook y
  analytics; staff no omite permisos.
- Timeout/inconclusive nunca se convierte en respuesta incorrecta.

## Threat model de assets

- Entrada: nombre, MIME, extensión, bytes, checksums, metadata multimedia y VTT
  son no confiables. Allowlist + magic bytes/ffprobe/parser + límites previenen
  spoofing, parser bombs, decompression bombs y contenido activo.
- Malware: quarantine no es firmable; ClamAV falla cerrado, registra evidencia
  mínima y elimina objetos infectados. Staff/superuser no tienen bypass.
- Storage: block-public-access, encryption, versioning, CORS exacto, lifecycle,
  keys UUID y credenciales sólo servidor. ETag no autentica contenido.
- API: capabilities por organización, selectors anti-IDOR, serializers cerrados,
  rate limits y ausencia de DELETE/upload remoto evitan mass assignment, SSRF y
  borrado histórico.
- Procesamiento: subprocess argv sin shell, timeouts, FFmpeg sin red, worker no
  root/read-only y temporales limpiados reducen RCE, exfiltración y agotamiento.
- Entrega: matrícula + release + unidad se validan antes de URLs temporales;
  descriptors no exponen buckets/keys y sólo permiten variantes necesarias.
