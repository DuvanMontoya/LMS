# Project status

## Phase

**Phase 12 — Matrículas y entrega del aprendizaje** está completada localmente
el 2026-07-30. `domain.learning` contiene cohortes, matrículas institucionales,
asignaciones históricas de releases, progreso determinista, continuidad de
lectura y eventos append-only. La entrega lee exclusivamente el snapshot
inmutable asignado y fue verificada con PostgreSQL 18.4, Redis 8.8.1 y Chromium
aislado, sin implementar evaluaciones ni certificados.

## Phase 12 — Matrículas y entrega del aprendizaje

- **Fecha y prompt:** 2026-07-30; Prompt 12 ejecutado de principio a fin. El
  Prompt 13 no fue ejecutado.
- **Git:** `HEAD` inicial y final
  `9d6a33d704ad94917ec80af1d5cf77b2bea6f287`; `origin/main` inicial y final en
  el mismo commit; rama `main`; remoto
  `https://github.com/DuvanMontoya/LMS.git`. No hubo cambios externos, commits,
  pushes, ramas ni reescrituras de historial por Codex.
- **Versiones:** Python 3.13.13, uv 0.11.19, Django 6.0.7, DRF 3.17.1,
  django-filter 26.1, drf-spectacular 0.30.0, psycopg 3.3.4, PostgreSQL 18.4,
  Redis 8.8.1, Node 24.18.0, pnpm 10.33.2, Next.js 16.2.12, React 19.2.8,
  TypeScript 6.0.2 y Playwright 1.62.0.
- **Dependencias:** no fue necesaria una dependencia nueva para el dominio. Se
  reutilizaron Django/DRF, django-filter, PostgreSQL, TanStack Query,
  React Hook Form, Zod, el cliente OpenAPI y axe. Las licencias y alternativas
  permanecen documentadas en `docs/research/DEPENDENCY_EVALUATION.md`.
- **ADR:** ADR 0022 fija la propiedad de `domain.learning`, el pinning explícito
  de releases, el progreso transaccional, la continuidad last-write-wins y los
  eventos append-only protegidos por PostgreSQL.
- **Capacidades:** se añadieron seis capacidades `learning.*`; owner/admin
  administran cohortes y matrículas, instructor consulta progreso, author y
  reviewer tienen sólo las lecturas institucionales previstas, y learner accede
  únicamente a su propia matrícula. Ser staff no omite políticas; el superuser
  conserva únicamente el bypass administrativo explícito.
- **Modelos:** `LearningCohort`, `CourseEnrollment`,
  `EnrollmentReleaseAssignment`, `CourseProgress`, `UnitProgress` y
  `LearningEvent`, todos con UUID, organización y relaciones explícitas.
- **Constraints e índices:** unicidad case-insensitive del slug de cohorte,
  máximo de una matrícula no revocada por membership/curso, un assignment
  vigente por matrícula, intervalos contiguos, un progreso por assignment y una
  fila por unidad; índices cubren organización, curso, estado, ventanas,
  membership y consultas cronológicas.
- **Triggers:** `learning.0002` rechaza `UPDATE` y `DELETE` de eventos;
  `learning.0003` impide cambiar el release de una cohorte con matrículas.
  Ambos migran desde una base PostgreSQL vacía.
- **Cohortes y matrículas:** creación, archivado lógico, ventanas opcionales,
  matrícula manual y por lote atómica, suspensión, reactivación, revocación
  terminal y reincorporación mediante una matrícula nueva.
- **Assignments, pinning y upgrades:** cada matrícula conserva un historial
  contiguo de assignments. Una publicación nueva nunca migra matrículas. El
  upgrade individual es explícito, cierra el assignment anterior, crea uno
  nuevo y no copia progreso; las matrículas de cohorte no admiten upgrade
  individual.
- **Progreso y completitud:** contadores fijados desde el snapshot, porcentaje
  en basis points, `expected_version`, locks de fila, apertura, completado
  idempotente, reapertura y transición exacta del curso completo/incompleto.
- **Continuidad:** unidad y nodo semántico se validan contra el snapshot; el
  navegador guarda con debounce de cinco segundos y `pagehide`, restaura hash,
  foco y movimiento reducido, y usa fallback seguro sin `localStorage`.
- **Eventos:** alta, suspensión, reactivación, revocación, assignment, upgrade,
  apertura, completado, reapertura y finalización quedan como hechos
  append-only; los movimientos frecuentes de posición no generan eventos.
- **Políticas y acceso:** membership activa, matrícula propia activa, ventana
  vigente, publicación no retirada, assignment vigente e integridad del release
  son requisitos acumulativos. `course.published.view` no sustituye matrícula.
- **API:** rutas versionadas bajo
  `/api/v1/organizations/{slug}/learning/`, con administración de cohortes,
  matrículas y progreso, y superficie propia `me`; filtros, orden, paginación,
  errores estables, 404 anti-IDOR, CSRF y throttle de posición.
- **OpenAPI:** schema sin warnings ni colisiones, cliente TypeScript regenerado
  y checks de drift de learning y plataforma aprobados.
- **Frontend y accesibilidad:** dashboard “Mi aprendizaje”, outline con
  progreso, lector snapshot-only, continuar, anterior/siguiente y pantallas
  institucionales de cohortes, matrículas y progreso. Se verificaron progreso
  nativo, captions, foco, teclado, contraste, axe WCAG 2.2 A/AA y 390 px sin
  overflow.
- **Demo y README:** `pnpm learning:demo` es idempotente, sólo funciona con
  `DEBUG=True`, no crea contraseñas y preserva la matrícula, el release y el
  progreso ya existentes. README documenta comando, cuentas, rutas y pinning.
- **Pruebas:** 18 pruebas learning y 144 pruebas backend pasan; cobertura total
  backend 81.92%. Pasan Ruff, Pyright, ESLint, Prettier, TypeScript, 40 pruebas
  Vitest, Next build, checks de producción, migraciones desde cero, OpenAPI,
  drift, auditorías y los E2E de learning y publishing.
- **Navegador:** Chromium integrado inspeccionó dashboard del estudiante,
  outline/lector, restauración, administración de cohortes y progreso en
  escritorio y 390 px. El E2E aislado repitió el recorrido con axe, teclado,
  dos contextos concurrentes y limpieza final.
- **CI:** instala dependencias bloqueadas, arranca PostgreSQL/Redis, verifica
  migraciones, schema/cliente, límites modulares, pruebas, concurrencia,
  seguridad, build y Chromium, con cleanup incondicional.
- **Auditorías:** `pip-audit` y `pnpm audit --prod` no reportan
  vulnerabilidades conocidas. `uv lock --check`, `uv sync --locked` y
  `pnpm install --frozen-lockfile` pasan.
- **Riesgos y deuda:** Redis conserva su decisión de licencia/operación para
  producción; el throttle de DRF no es un control antiabuso absoluto; el punto
  de lectura usa deliberadamente last-write-wins; los overrides heredados de
  `postcss`/`sharp` se revisarán con Next.js. No hay bloqueo esencial ni cambio
  irreversible adicional al pinning registrado en ADR 0022.
- **Trabajo no realizado:** evaluaciones, bancos de preguntas, intentos,
  calificación, certificados, Celery, ejecución de código y LMS externo quedan
  fuera del alcance.
- **Siguiente paso:** **Prompt 13 — Banco de preguntas y evaluaciones: tipos de pregunta, bancos versionados, composición de evaluaciones, intentos, respuestas y calificación inicial.**

## Auditoría UI/UX posterior a Phase 12 — 2026-07-30

- Se recorrieron en Chromium integrado las rutas protegidas con instancias
  reales disponibles para owner y learner, tanto a 1280 px como a 390 px. El
  build enumeró y compiló además todo el árbol App Router. Las pantallas
  revisadas mantienen un único `main`, no presentan overflow horizontal y
  conservan navegación, permisos y datos reales.
- El shell dejó de anidar landmarks `main`. “Mi aprendizaje” ya no queda activo
  en las rutas administrativas y “Entrega del aprendizaje” permanece activo
  tanto en cohortes como en matrículas, incluidos sus detalles. El drawer móvil
  conserva todas las opciones autorizadas, scroll interno, cierre por
  navegación y separación correcta entre owner y learner.
- Cohortes y matrículas adoptaron el espaciado y superficies del sistema
  académico. Se añadieron búsqueda, filtros, paginación, estados vacíos,
  etiquetas de estado y fechas en español, progreso compacto, métricas y
  tarjetas adaptables. Los formularios ya no exigen UUID, slug de curso ni
  número de release manuales: usan membresías, cursos, releases y cohortes
  autorizados obtenidos de la API.
- Archivar, suspender, reactivar, revocar y actualizar release requieren
  diálogos descriptivos; el botón final nombra la acción concreta. Una
  matrícula revocada vuelve a estar disponible para reincorporación mediante
  una matrícula nueva, sin alterar su historial.
- La auditoría detectó un defecto funcional en `_ordered`: solicitar
  `ordering=-created_at` producía `--created_at` y rompía el listado de
  matrículas. La normalización quedó corregida y una regresión API cubre orden
  ascendente y descendente en cohortes y matrículas.
- El lector solicitaba el worker local de accesibilidad de MathJax, pero la
  copia reproducible no lo incluía y respondía 404. `speech-worker.js` forma
  ahora parte de los assets verificados por `prebuild`; el servidor local
  responde 200 con el archivo completo.
- Evidencia final: `pnpm check`, `pnpm web:test` (40/40), `pnpm web:build`,
  `pnpm learning:check`, `pnpm learning:test` (18/18), `pnpm api:test`
  (144/144; 81.92 %) y `pnpm learning:e2e` (1/1 con axe, 390 px, concurrencia y
  cleanup) pasan. El recorrido manual comprobó el lector anclado al nodo de
  continuidad, sin recursos externos ni overflow.
- Deuda residual no bloqueante: los selectores administrativos cargan hasta 100
  cursos, cohortes y membresías por formulario. Antes de operar organizaciones
  mayores se debe sustituir ese límite por búsqueda remota paginada y
  virtualización accesible; no se introdujo una dependencia sólo para anticipar
  esa escala.

## Delivered scaffold

- El checkout actual está en `main`, sigue `origin/main` y conserva su historial
  previo. La precondición del Prompt 9 que afirmaba “sin remote/sin commit” no
  coincidía con el estado autoritativo del repositorio. Mientras la validación
  seguía activa, a las 14:05 del 2026-07-29, `HEAD` y `origin/main` avanzaron
  externamente de `475c129` a `ee40ffd`; Codex no ejecutó `commit` ni `push`, no
  creó una rama y no reescribió ese movimiento. Los ajustes del cierre hostil
  permanecen preservados como cambios locales sobre ese commit.
- Root pnpm workspace with Node 24.18.0 and pnpm 10.33.2 pinned in `.node-version` and `package.json`.
- `apps/api`: uv project pinned to Python 3.13.13, Django 6.0.7, DRF 3.17.1, drf-spectacular 0.30.0, psycopg 3.3.4; `uv.lock` present.
- Five official Django app skeletons: `identity`, `catalog`, `content`, `learning`, `assessments`; ADR 0010 records their intentional grouping.
- Environment settings package (`base`, `development`, `test`, `production`) with PostgreSQL-only configuration, safe production checks and `.env.example` placeholders.
- `apps/web`: Next 16.2.12, React 19.2.8, Tailwind 4.3.3, TypeScript 6.0.2, ESLint 9.39.5, Prettier, Vitest, Testing Library and Playwright Chromium; root `pnpm-lock.yaml` present.
- Root scripts and PowerShell `preflight`, `bootstrap`, and `check` runbooks; Linux CI workflow created.

## Delivered local infrastructure

- `compose.yaml` declares only PostgreSQL 18.4 and Redis 8.8.1, a private bridge network, loopback ports, health checks and named volumes; `compose.lock.yaml` fixes their verified Linux amd64 digests.
- `infrastructure/local/.env` is generated with cryptographically random local secrets and ignored. The selected PostgreSQL host port is `5433` because a non-LMS PostgreSQL process already owned `5432`; Redis uses free port `6379`.
- `scripts/infrastructure.ps1` provides explicit init, validation, pull/lock, lifecycle, restart, smoke and confirmation-gated reset operations. The smoke proves PostgreSQL SCRAM failures/success, UTF-8, UTC, checksums, Django connectivity and restart persistence; it also proves Redis authentication, AOF persistence, cleanup and non-root service operation.
- ADR 0012 records the Redis 8.8.1 upgrade and tri-license condition; ADR 0013 records the Compose/digest model. CI runs the disposable Linux Compose smoke and always cleans its project resources.

## Delivered Django foundation

- Pre-migration audit found no application tables, no `django_migrations` and no prior migrations. `identity.0001_initial` was generated by Django 6.0.7, its SQL inspected, then all built-in and identity migrations were applied without fake operations.
- `identity.User` extends `AbstractUser`, has UUID primary key, removes `username`, uses normalized required email as `USERNAME_FIELD`, and protects exact plus `Lower(email)` uniqueness in PostgreSQL. ADR 0014 records this irreversible choice.
- `Django[argon2]` resolved `argon2-cffi 25.1.0`; Argon2id is first in `PASSWORD_HASHERS`. DRF defaults to SessionAuthentication/IsAuthenticated/JSON. Redis remains unrelated to Django.
- Internal forms/admin work without username. No persistent superuser, authentication endpoint, allauth, profile, role, academic model or SQLite database was created.
- `/health/live/` and `/health/ready/` are outside OpenAPI; real checks passed for 200, HEAD and controlled PostgreSQL 503/restore. Pytest PostgreSQL suite: 21 passed, 89.82% coverage; Ruff and Pyright passed.
- `scripts/django.ps1`, package commands and CI now cover checks, plans, migration, health, PostgreSQL tests and a clean ephemeral migration database. The documentation path cited as `0013-compose-image-locking.md` in the prompt was corrected to the actual decision `0013-local-compose-and-image-locking.md`.

## Delivered headless authentication

- `django-allauth[headless-spec] 65.18.0` and `redis 8.0.1` are exact direct dependencies. `PyYAML` is the only allauth extra dependency. The distribution's browser-session headless module works without the `headless` optional extra, which would install `PyJWT[crypto]` for excluded JWT capability; no `django-redis`, REST-auth wrapper, JWT library, social extra, MFA or app client is installed.
- `allauth`, `allauth.account` and `allauth.headless` are configured with the official account middleware and both official authentication backends. `identity.User` and its immutable `identity.0001` remain unchanged; allauth migrations `account.0001` through `account.0009` applied normally and no social table exists.
- The public contract is `/_allauth/browser/v1/`; `/accounts/` retains only allauth internals while `HEADLESS_ONLY=True` removes headed login/signup. Browser authentication uses PostgreSQL-backed Django sessions and real CSRF. Session cookies are HttpOnly/SameSite=Lax and production enables Secure; no access, refresh or `X-Session-Token` is issued. `LMS_FRONTEND_URL` supplies only future signup/reset links required for neutral allauth mail; it does not create a Next.js UI.
- Registration is email/password only, normalized by the existing user model and manager. Mandatory allauth email codes allow three attempts, expire after 900 seconds and support resend. Password-reset codes allow three attempts and the official 180-second timeout; reset does not authenticate the account. Development mail is written under ignored `apps/api/.local/mail`; tests use locmem. Spanish plaintext/HTML templates contain no password, UUID, tracker or remote asset.
- Redis logical database 1 is explicitly reserved for Django `RedisCache` keys prefixed `lms-auth`; it provides allauth rate limits and never stores sessions, users or custom codes. There is no LocMem/Dummy fallback. `/health/ready/` now checks PostgreSQL and the public cache API without revealing which dependency failed; liveness remains dependency-free.
- `domain.identity.adapters.LMSHeadlessAdapter` provides the official OpenAPI-aware minimal user payload: UUID string, email, display and `has_usable_password`. `scripts/auth.ps1` and root `auth:*` commands validate configuration, official routes/specification, migrations, functional/security/email/rate tests, safe smoke and scoped development-mail cleanup. CI starts the project Compose PostgreSQL and Redis pair before authentication checks.

## Delivered Next.js browser authentication integration

- `apps/web` now presents Spanish routes for login, registration, email verification, password recovery/reset and the minimal protected `/estudiar` area. Django remains the owner of every cookie, session, CSRF decision and account flow; Next does not create auth cookies or store tokens.
- `next.config.ts` validates the server-only `DJANGO_INTERNAL_ORIGIN` and rewrites only `/_allauth`, `/api/v1` and `/health`. `FRONTEND_ORIGIN` defaults to canonical `http://127.0.0.1:3000` while `CSRF_TRUSTED_ORIGINS` dynamically accepts loopback alternatives (`http://localhost:3000` and `http://127.0.0.1:3000`) to prevent 403 CSRF rejection during browser dev sessions; no CORS or `/admin` rewrite exists.
- The generated `openapi/allauth.openapi.json` (12 browser paths) and `src/lib/api/generated/allauth.ts` are produced from the real allauth endpoint by `scripts/generate-allauth-client.mjs`. `auth:web:client:generate` writes them atomically and `auth:web:client:check` verifies drift without modification.
- `openapi-fetch 0.17.0`, TanStack Query 5.101.4, React Hook Form 7.83.0, resolvers 5.5.7, Zod 4.4.3, `server-only` 0.0.1 and axe Playwright 4.12.1 are exact dependencies. `openapi-typescript 6.7.6` is the latest stable line compatible with the repository TypeScript 6 policy; 7.13.0 was rejected for its TypeScript 5-only peer.
- Browser CSRF bootstraps through official allauth config, uses only same-origin credentials and appends `X-CSRFToken` for unsafe methods. Query keys and no-retry auth mutations are centralized. `proxy.ts` is optimistic only; the protected server layout checks Django with forwarded Cookie and `no-store`.
- ADR 0016 records the same-origin, generated-contract and server-authoritative decisions. `config.settings.e2e` accepts only a UUID-named PostgreSQL database, an `lms-e2e-` Redis prefix and the ignored `apps/api/.local/e2e-mail` directory. The runner creates, migrates and drops that database, clears only its Redis keys, mail and `.local/e2e-results`, and refuses occupied ports 3000/8000 on Windows.
- The Playwright configuration starts Django and Next directly at `127.0.0.1:8000` and `127.0.0.1:3000` with `reuseExistingServer: false`, one Chromium worker, no trace/video/screenshot, and no browser storage of sessions or codes. It covers registration, mandatory email-code verification, logout/login, password reset, protected-route return, open-redirect rejection, CSRF rejection, keyboard focus order and axe WCAG 2.2 A/AA checks. The 13-test unit/component suite, all five browser cases, lint, strict typecheck, generated-client drift check, backend checks and production Next build pass.

## Compatibility correction

TypeScript 7.0.2 and ESLint 10.8.0 were installed temporarily and rejected after real peer-resolution evidence from `eslint-config-next`/`typescript-eslint`. The working selection is TypeScript 6.0.2 and ESLint 9.39.5 (ADR 0011). No parallel compiler was retained.

## Security result

`pip-audit` reported no known Python vulnerabilities. `pnpm audit --prod` initially identified one moderate and three high vulnerabilities inherited through Next's PostCSS/sharp dependencies. Root overrides pin `postcss@8.5.18` and `sharp@0.35.3`; the audit then reported no known vulnerabilities. pnpm still reports optional WASM peer warnings and intentionally blocks `unrs-resolver` lifecycle scripts; lint, tests and build pass without approving them. Reassess both on every Next upgrade.

## Validation evidence

- El 2026-07-29 se consultaron las guías oficiales de Next.js sobre `rewrites` y preservación de la barra final, y de openapi-fetch sobre serialización JSON. El BFF conserva ahora las rutas API con barra final antes de reenviarlas a Django, y el adaptador CSRF conserva `Content-Type` del `Request` generado antes de añadir `X-CSRFToken`.
- La matriz aislada `pnpm organizations:e2e` ejecutó 9 escenarios Chromium: autenticación existente, owner (alta, suspensión, reactivación, revocación y reincorporación), administrador sin controles sobre owners, aislamiento entre organizaciones y axe WCAG A/AA institucional. Pasó después de corregir la navegación post-login, el reenvío con barra final, los encabezados JSON y la actualización de la tabla de membresías.
- El navegador integrado cargó visualmente el login local y el entorno de demostración quedó disponible en `127.0.0.1:3000`/`127.0.0.1:8000`. Las cuentas demo reproducibles se generan sólo con `DEBUG=True` mediante `pnpm organizations:demo`; el README documenta su uso y las credenciales.
- La validación de la superficie de currículo sigue abierta, pero su corte actual está probado: `pnpm catalog:test` pasó 66 pruebas Python con 79.75% de cobertura, `pnpm web:typecheck` y `pnpm web:lint` pasaron, y `pnpm catalog:visual` ejecutó 14 escenarios Chromium aislados. Entre ellos están la jerarquía curricular, creación visual de disciplina, asignatura, tema, objetivo y concepto, reducción y reubicación visible de un tema, rechazo visible de ciclos de prerrequisitos, asociaciones ordenadas tema/objetivo–concepto y axe WCAG 2.2 A/AA; la base temporal, Redis y correo temporal se eliminaron al finalizar.
- El 2026-07-29 se completaron las rutas REST de detalle, actualización, archivado/restauración y movimiento para disciplinas, asignaturas, temas y objetivos. `Topic.objects.move()` sustituye el método de instancia deprecado por Treebeard 6. La interfaz permite crear un tema hijo y la prueba Chromium aislada verificó el flujo; queda pendiente completar la edición visible de todas las entidades y las listas completas de prerrequisitos antes de cerrar la fase.
- El 2026-07-29 la página de prerrequisitos pasó a listas accesibles para asignaturas y conceptos: muestra relaciones entrantes y salientes, permite varias aristas con tipo y justificación, y excluye entidades archivadas. Chromium verificó la creación y el rechazo del ciclo de conceptos; la repetición completa posterior pasó 14/14.
- La validación de cierre local pasó: `pnpm check`, `pnpm test` (50 pruebas Python, cobertura 80.92%; 16 pruebas Vitest), `pnpm organizations:test` (14), políticas (4), concurrencia (1), contrato OpenAPI sin drift y `pnpm web:build`.
- Django `check`: exit 0; `check --deploy` in development: exit 0 with five expected deployment warnings.
- Production-like `check --deploy`: exit 0 with a long non-secret placeholder key and `lms.invalid` host.
- Ruff lint/format, Pyright strict, pytest (36 tests, 91.95% coverage), ESLint, Prettier, `tsc`, Vitest (13 tests), Next build, production same-origin proxy smoke, isolated Playwright Chromium (5 tests) and isolated axe WCAG 2.2 A/AA (1 tagged test) have passed individually.
- `pnpm install --frozen-lockfile` and `uv sync --locked` pass. PostgreSQL 18.4
  and Redis 8.8.1 Docker Official Images are available through local Compose
  only, locked by Linux amd64 digest, loopback-published, authenticated and
  persistence-smoke-tested. No SQLite database, application container, Celery,
  S3 o cambio de remote fue creado por Codex; tampoco ejecutó `commit` ni
  `push`. El avance externo de Git observado durante la validación queda
  registrado en “Delivered scaffold”.

## Remaining risk / debt

- Security overrides for `postcss` and `sharp` are necessary compatibility debt until Next updates its own dependency pins.
- pnpm's optional WASM peer/build-script warnings are not hidden; they are non-blocking only because the checked toolchain passes without executing those scripts.
- `identity.0001` y el modelo de usuario permanecen inmutables. Cualquier cambio
  futuro exige ADR, plan de migración y evidencia PostgreSQL real.
- Redis 8 remains conditional for production pending a legal license choice and a production design for ACL users, rotation, TLS and network policy.
- django-allauth 65.18.0 exports phone patterns even when `ACCOUNT_PHONE_VERIFICATION_ENABLED=False`. `domain.identity.headless_urls` filters only those exported URL leaves before Django includes them; tests prove they are 404 and absent from generated OpenAPI. Reassess the shim on every allauth upgrade.
- The browser-only deployment intentionally omits allauth's optional `headless` extra because it installs `PyJWT[crypto]`; the installed distribution still provides, and tests prove, the supported browser-session headless routes and official OpenAPI schema through `headless-spec`. Re-evaluate this narrow dependency decision on every allauth upgrade.
- A production SMTP provider, a real reverse-proxy trust chain, administrative network restriction, social login, MFA and user-session inventory are intentionally deferred.
- The Windows production-smoke wrapper still needs process-tree cleanup before it can be CI evidence: `pnpm.cmd` can leave child Node processes after a wrapper stop. The isolated Playwright runner avoids that path by using direct Node server launchers and force-stopping only processes bound to its prechecked local ports.

## Next exact step

**Prompt 11 — Publicación inmutable: snapshots completos del curso, versiones publicadas, validación, retiro y experiencia de lectura.**

## Prompt 8 latest evidence

El 2026-07-29 `pnpm catalog:e2e` pasó 20/20 en Chromium aislado. Incluyó
creación y edición visible de área, disciplina, asignatura, tema, concepto y
objetivo por owner/author; reviewer, instructor y learner de solo lectura;
`POST` directo del revisor con cookie/CSRF que devolvió 403; URL
cross-organization, árbol, asociaciones, ciclos, archivado y restauración de
un concepto sólo después de retirar sus asociaciones y aristas, archivado
oculto al learner y axe WCAG 2.2 A/AA en las cinco rutas curriculares. La base
PostgreSQL, prefijo Redis y correo efímeros se limpiaron en `finally`.

El mismo día, `pnpm catalog:test` pasó 69 pruebas Python con 81.23% de cobertura,
`pnpm check`, `pnpm catalog:schema`, `pnpm catalog:client:check` y
`pnpm web:build` pasaron sin warnings. Las listas agrupadas `topic-concepts`, `objective-concepts`,
`subject-prerequisites` y `concept-prerequisites` permiten que las pantallas
curriculares eviten una carga N+1. La comprobación manual Chromium con las
cuentas demo verificó login, redirección y el currículo de
`organizacion-demo` con conteos, filtros y jerarquía visibles.

La revisión final añadió selectores explícitos de visibilidad por organización
y estado para áreas, disciplinas, asignaturas, temas, conceptos y objetivos.
Las vistas de lista aplican `DjangoFilterBackend` y ordenamiento permitido sólo
después de esa frontera; el esquema OpenAPI declara `search`, `status`,
relaciones y `ordering`, y el cliente generado quedó sincronizado. El reemplazo
de prerrequisitos conserva las aristas no modificadas, bloquea la organización y
el grafo antes de validar ciclos y sólo inserta, actualiza o retira el diff.
Una regresión `TransactionTestCase` adicional ejecuta dos escrituras Treebeard
simultáneas sobre la misma asignatura y confirma dos nodos válidos y
`find_problems()` vacío tras la serialización por bloqueo.

## Prompt 9 latest evidence

El 2026-07-29 se creó `domain.courses` con el generador oficial de Django y una
única migración inicial inspeccionada y aplicada en PostgreSQL 18.4. El dominio
mantiene `Course`, revisiones de autoría, historial de transiciones append-only,
módulos y unidades ordenados, y alineaciones explícitas con asignaturas, temas y
objetivos de `domain.catalog`. No se alteró `identity.0001`, no se copiaron roles
a `User`, `Group` ni almacenamiento del navegador, y una revisión aprobada no
se modela como publicación.

Se añadieron seis capacidades a la matriz central de organizaciones y todas las
decisiones de autorización atraviesan policies/services. Las escrituras usan
`transaction.atomic()`, `select_for_update()` y `expected_version`; los
conflictos devuelven un `409 revision_conflict` estable y conservan la edición
del usuario en la interfaz. La base protege slug reservado, unicidad por
organización, cardinalidad de asignatura principal, posiciones válidas y únicas,
transiciones inmutables y ausencia de borrado físico en la API. Dos
transacciones PostgreSQL reales probaron que una actualización concurrente se
guarda y la otra falla, y que la reordenación conserva una secuencia íntegra.

El contrato `/api/v1/organizations/{organization_slug}/courses/` cubre listado,
detalle, revisión, outline, readiness, metadatos, alineaciones, estructura,
archivado/restauración y flujo draft → in_review → changes_requested/approved.
Los `404` no revelan cursos, revisiones, módulos ni unidades de otra
organización. El esquema drf-spectacular se generó sin warnings y el cliente
TypeScript quedó sincronizado; el frontend consume únicamente esos tipos
generados y mantiene las decisiones de autorización en el servidor.
Como todas las vistas PATCH validan serializers explícitos sin `partial=True`,
drf-spectacular usa `COMPONENT_SPLIT_PATCH=False`: `expected_version` permanece
obligatorio también en el schema y el tipo TypeScript, no sólo en runtime.

Las cinco rutas Next.js —lista, creación, workspace, estructura y revisión—
fueron inspeccionadas en el navegador integrado con la cuenta owner de
demostración. A 1280 px mostraron los encabezados y controles esperados; a
390 px las cinco tuvieron `scrollWidth == clientWidth`. El editor de estructura
mostró los tres módulos y ocho unidades del curso de demostración sin
desbordamiento, y la consola no registró errores.

`pnpm courses:e2e` pasó 3/3 escenarios Chromium aislados: flujo completo
author/reviewer/owner, dos contextos con conflicto optimista visible y valores
preservados, edición y reordenación de módulos/unidades, alineaciones, archivo y
restauración por teclado, readiness, solicitud de cambios con foco en el
faltante, corrección, reenvío, aprobación, solo lectura por rol, visibilidad del
instructor, ocultamiento al learner, axe WCAG 2.2 A/AA, viewport de 390 px e
IDOR multinivel. La base PostgreSQL temporal, el prefijo Redis y el correo
temporal se eliminaron en `finally`.

`pnpm courses:demo` es idempotente y sólo funciona con `DEBUG=True`. Mantiene
los identificadores del curso `introduccion-calculo-diferencial`, su revisión
draft, tres módulos, ocho unidades y sus alineaciones; una prueba impide su uso
en configuración no development. La deuda intencional restante es mover una
unidad entre módulos, que no forma parte del contrato del Prompt 9. Contenido
semántico, publicación, enrolment, evaluación y delivery permanecen fuera de
este dominio y de esta fase.

El cierre hostil añadió regresiones directas para mass assignment,
`expected_version` ausente, slug inmutable, inmutabilidad de `in_review` y
`approved`, módulo sin unidad, unidad sin objetivo, referencias de catálogo
archivadas, relaciones entre organizaciones, objetivos no alineados y una
regresión N+1 que mantiene constante el número de consultas del outline al
cuadruplicar módulos y unidades. La suite de Courses pasó 17/17 con 79.03% de
cobertura aislada (`models` 88%, `services` 82%, `readiness` 78%, `policies`
75%, serializers 97%); la suite global pasó 86 pruebas Python con 80.46% y 18
pruebas Vitest. La ejecución
Chromium global pasó 23/23 escenarios y limpió su base, Redis y correo. Ruff,
Pyright (0 errores), ESLint, Prettier, TypeScript, Next build, OpenAPI sin
warnings, drift checks, `pip-audit` y `pnpm audit --prod` quedaron verdes.

## Acceso local persistente y experiencia institucional — 2026-07-29

- `bootstrap_local_access` crea o reconcilia únicamente en desarrollo la cuenta
  local solicitada y un espacio institucional real. Recibe la contraseña por la
  variable efímera `LMS_LOCAL_ACCESS_PASSWORD`, no la imprime, no la escribe en
  Git y evita recalcular el hash si ya coincide. `--exclusive` revoca otras
  membresías mediante el servicio de organizaciones sin borrar datos ni
  historial. La cuenta local quedó como owner de
  `espacio-academico-rmontoyac`; no necesita ejecutar los bootstraps demo.
- `pnpm dev:start`, `dev:status`, `dev:logs`, `dev:restart` y `dev:stop`
  administran Django y Next en procesos ocultos identificados, con estado y logs
  bajo `.local/dev` ignorado. PostgreSQL y Redis permanecen administrados por
  Compose. El objetivo operativo es que una revisión o tarea no detenga el
  entorno que el propietario está probando.
- El frontend adoptó una única base visual generada con shadcn/ui y Radix:
  blanco, grises fríos y azul sólo como énfasis. El sidebar es claro,
  colapsable y móvil; su estado activo usa una marca discreta y no bloques de
  color. El encabezado global dejó de duplicar el título de cada página.
- Currículo usa explorador jerárquico con inspector; cursos usa catálogo en
  filas y workspace; miembros usa directorio y diálogos; organizaciones e
  inicio académico usan listas de trabajo. La creación de áreas, disciplinas,
  asignaturas, conceptos, objetivos y temas ocurre en diálogos contextuales.
  Los formularios de curso, alineación, revisión y metadatos se compactaron con
  divisores, controles consistentes y acciones breves.
- El login reproduce la composición visual autorizada de
  `DuvanMontoya/Frontera-Matematica`: campo geométrico de investigación,
  ecuaciones, tipografía editorial y panel translúcido. Sólo se adaptó la
  identidad textual; formularios, CSRF, errores, recuperación, verificación y
  sesión siguen usando allauth/Django reales.
- `shadcn` se usó como generador fijado en `4.16.0` y se retiró del runtime con
  `eject`. Permanecen sólo componentes consumidos; se eliminaron componentes,
  `next-themes` y `sonner` sin consumidores. Las nuevas dependencias directas
  están fijadas exactamente y su evaluación/licencia está en
  `docs/research/DEPENDENCY_EVALUATION.md`.
- El micro-pulido final se realizó sobre las rutas reales con la cuenta local:
  inicio, organizaciones, resumen, currículo, asignatura, conceptos, objetivos,
  prerrequisitos, cursos, creación y miembros. Se compactaron encabezados,
  espacios, estados vacíos y formularios; las acciones de temas, conceptos,
  objetivos, membresías, historial y conflictos usan controles y diálogos
  coherentes, sin `window.confirm`. El editor semántico conserva su lógica y
  schema, pero adoptó los mismos tokens, superficies y estados del resto de la
  plataforma.
- Un Chromium aislado a 390 px recorrió once rutas autenticadas y confirmó
  `scrollWidth == clientWidth` en todas. La revisión visual detectó y corrigió
  el estrechamiento del inspector curricular móvil y la superposición de la
  acción del formulario de curso. Axe con WCAG 2 A/AA y 2.2 AA quedó sin
  violaciones en login y los flujos representativos de inicio, resumen,
  currículo, asignatura, prerrequisitos, creación de curso y miembros; también
  se corrigieron los dos contrastes detectados en avatar y acción destructiva.
- Después del último cambio pasaron Prettier, ESLint, TypeScript, las 27 pruebas
  Vitest y `next build` 16.2.12 con todas las rutas. La suite API global ya había
  pasado 113 pruebas con 82.69% de cobertura, `check` y verificación de
  migraciones. La sesión real quedó abierta y `pnpm dev:status` confirma Django
  en `127.0.0.1:8000` y Next en `127.0.0.1:3000`.

## Corrección de navegación, membresías y editor semántico — 2026-07-30

- En contextos con una sola organización, `/organizaciones` redirige al resumen
  institucional y el sidebar presenta la organización como identidad estática,
  no como una acción que vuelve a abrir la misma pantalla. El resumen enlaza
  `Inicio` con `/estudiar`; el selector y la ruta de cambio se conservan sólo
  cuando existen varias organizaciones.
- El alta de miembros mantiene el contrato vigente: sólo incorpora cuentas
  registradas, activas y verificadas, sin inventar invitaciones ni un segundo
  sistema de identidad. La interfaz explica ese requisito, permite copiar la
  ruta real de registro, busca por correo y muestra el detalle seguro devuelto
  por la API. Se verificó el flujo completo en el navegador con una identidad
  temporal verificada y rol learner; la membresía, sus eventos, asignaciones,
  correo y usuario temporales se eliminaron inmediatamente después.
- El error de guardado del contenido provenía de la extensión de enlace de
  Tiptap: serializaba atributos HTML (`target`, `rel` y `class`) que el contrato
  canónico prohíbe. `CanonicalLink` conserva en JSON únicamente `href` y el
  `title` opcional; los atributos de seguridad se agregan sólo al renderizar.
  Los errores de schema ahora se deduplican y se presentan en español. El
  documento real con enlaces se guardó sin cambio semántico y la API confirmó
  que no creó una versión duplicada.
- Currículo, estructura de cursos, miembros y contenido recibieron un
  micro-pulido coherente con el sistema visual existente: menos texto técnico,
  jerarquía más compacta, estados y alertas consistentes, módulos y unidades
  escaneables, alineaciones agrupadas y barra de autoría adaptable. No se
  cambiaron rutas, arquitectura ni reglas de negocio.
- La revisión en el navegador integrado cubrió resumen, miembros, currículo,
  estructura y contenido en escritorio y a 390 px; las cinco rutas tuvieron
  `scrollWidth == clientWidth`. También se verificaron la redirección de
  `/organizaciones`, el alta y limpieza real de un miembro, el error controlado
  para un correo inexistente y el guardado del documento que antes fallaba.
- Pasaron Prettier, ESLint, TypeScript, las 31 pruebas Vitest, el build de
  Next.js 16.2.12 y las 24 pruebas de `domain.content`. Docker Desktop tuvo que
  reactivarse porque PostgreSQL no respondía en el primer intento; PostgreSQL y
  Redis quedaron saludables y la suite integrada pasó completa al repetirla.

## Prompt 11 — Publicación inmutable empresarial — 2026-07-30

- Git inicial: `main`, HEAD y `origin/main`
  `1272d5d35e4e05fb6f4799341bee64b0221b03b3`, worktree limpio. Git final
  conserva los mismos HEAD/remoto y sólo cambios locales de esta fase. Codex no
  ejecutó commit, push, add, reset, rebase, merge ni clean. Los servidores del
  usuario en 3000/8000 fueron preservados; E2E usó puertos y `.next` efímeros.
- ADR 0021 asigna a `domain.publishing` el canal mutable, releases/eventos
  append-only, snapshot completo, cadena SHA-256, retiro, clonación y biblioteca
  snapshot-only. Courses/content no importan publishing y publican sólo
  contratos estables de clonación.
- No hubo dependencia nueva. Se revalidaron Django 6.0.7, PostgreSQL 18.4,
  DRF 3.17.1, drf-spectacular 0.30.0, jsonschema 4.26.0, Ajv 8.20.0, Next
  16.2.12, React 19.2.8, TanStack 5.101.4 y Playwright/axe bloqueados.
- Capacidades nuevas: `course.release.publish`, `withdraw`, `history.view`,
  `create_draft` y `course.published.view`, evaluadas sólo por policies de
  organizaciones. Owner/administrator administran releases; learner lee.
- `CoursePublication`, `CourseRelease` y `CoursePublicationEvent` usan UUID,
  constraints/índices, lock version, current/previous pointers, métricas y
  eventos. `publishing.0002` instala triggers PostgreSQL que rechazan
  UPDATE/DELETE en releases y eventos; ORM y SQL directo están probados.
- `course-release-v1.schema.json` es Draft 2020-12, estricto y local. Snapshot
  determinista incluye curso, subject/objetivos, módulos/unidades/topics y
  documento semántico vigente; excluye HTML, secretos, actores, permisos,
  matrículas/progreso/evaluaciones. Límites, schema, canonicalización y digest
  se validan antes del INSERT.
- `publish_approved_revision` bloquea filas en `atomic`, exige aprobación,
  readiness/contenido, valida snapshot, numera contiguamente, encadena digest,
  inserta evento y actualiza el canal. Es idempotente para la misma revisión y
  seguro ante carreras. Retiro exige nota, conserva current release y sólo un
  release nuevo reactiva.
- `create_draft_from_release` clona estructura con UUID nuevos y documentos v1
  con digest conservado, sin historial previo; open draft y conflictos hacen
  rollback. Los servicios públicos viven en courses/content.
- API `/api/v1` cubre estado, publish, withdraw, releases, verify, create-draft
  y biblioteca list/detail/outline/unit. No hay DELETE ni snapshot entrante.
  IDOR devuelve 404, permisos 403, payload/version inválidos 400/409 y respuestas
  de lectura son `private, no-store`.
- OpenAPI fue generado/validado sin warnings y `platform.ts` quedó sincronizado.
  El schema genera tipos/validator Ajv de forma atómica; drift checks no escriben.
- Next agrega publicación, historial, retiro/draft confirmados y biblioteca con
  lector semántico, anterior/siguiente, MathJax local, código inert, tablas y
  bloques pedagógicos. Server Components usan no-store y TanStack desactiva
  retry/optimistic updates. No usa JWT, localStorage, sessionStorage o IndexedDB.
- Demo `introduccion-calculo-diferencial` fue publicado idempotentemente con
  servicios reales y verificado. `bootstrap_demo_publication` rechaza
  production. README y doce diagramas documentan uso, seguridad y operación.
- Chromium aislado recorrió release 1, historial, biblioteca, dos unidades,
  clonación, aprobación, release 2, independencia del snapshot, teclado, 390 px,
  axe y retiro. La revisión detectó/fijó estructura `<dl>`,
  conflicto de puertos/lock `.next` y cambio de identidad en un mismo contexto.
  E2E terminó 1/1 verde en 1.1 min y eliminó base, Redis, correo y procesos.
- Pytest publishing cubre schema, servicios, API y dos carreras; la suite
  integrada cubre release 2, reactivación, clonación, corrupción, triggers,
  roles e IDOR. Ruff, Pyright, cobertura ≥75 %, ESLint, Prettier, TypeScript,
  Vitest, Next build, auditorías y regresiones auth/organizations/catalog/
  courses/content forman el cierre obligatorio. La suite global cerró 126/126
  con 81,94 % de cobertura y Vitest 34/34.
- CI instala locks, levanta PostgreSQL/Redis, migra desde cero, valida triggers,
  schema/tipos/OpenAPI/drift, ejecuta suites/concurrencia, calidad, build,
  Chromium/axe y cleanup `always()`. No publica artefactos sensibles.
- Riesgo residual: la cadena detecta corrupción pero no es firma externa; la
  seguridad depende de control de acceso PostgreSQL y backups. Decisión
  irreversible: releases/eventos productivos no se corrigen in-place. Deuda:
  ampliar Playwright con visual regression estable; no bloquea contratos.
- Matriz completa: `docs/project/PHASE_11_ACCEPTANCE.md` (158 PASS).
- Trabajo no realizado: matrícula, progreso, evaluación, cache público,
  restauración de publication, media, búsqueda y Prompt 12.

## Remediación de navegación del frontend — 2026-07-30

- Se auditó el shell protegido y la matriz real de rutas antes de modificar la
  interfaz. El sidebar conservó su única implementación y ahora separa
  plataforma, institución, gestión académica, curso actual y administración.
- Currículo expone estructura curricular, conceptos, objetivos y
  prerrequisitos. Cursos expone listado y creación sólo con
  `course.authoring.manage`; dentro de un curso aparecen resumen, estructura,
  revisión y, únicamente con `course.release.history.view`, publicación.
  Biblioteca y miembros continúan filtrados por sus capacidades existentes.
- Las rutas dinámicas se derivan del `pathname` institucional ya autorizado; no
  se agregó estado, endpoint, ruta, permiso, capa de navegación ni regla de
  negocio paralela. Las unidades mantienen activa la sección Estructura y los
  releases la sección Publicación sin declarar como actual una URL distinta.
- El drawer móvil cierra al seleccionar enlaces principales o anidados y la
  navegación actual usa `aria-current="page"` sólo para coincidencias exactas.
  El modo colapsado conserva iconos y tooltips del componente existente.
- La revisión en el navegador integrado recorrió 15 pantallas reales en
  escritorio sin errores ni overflow: inicio, resumen institucional, las cuatro
  superficies de currículo, listado y creación de curso, resumen, estructura,
  revisión, publicación, biblioteca, contenido de unidad y miembros. En 390 px
  se verificaron el drawer, la ruta activa, el cierre tras navegar, Biblioteca,
  Publicación y `scrollWidth <= clientWidth`.
- Pasaron Prettier, ESLint, TypeScript, las 37 pruebas Vitest —incluidas tres
  nuevas sobre el contexto dinámico del curso— y el build de producción de
  Next.js 16.2.12. El backend persistente, iniciado con `--noreload` antes de
  Phase 11, entregaba capacidades antiguas; tras reiniciarlo, el contexto real
  de owner/administrator expuso Biblioteca y Publicación como establecen las
  policies, sin modificar datos ni permisos.
- La suite E2E aislada de publicación pasó 1/1 en Chromium: permisos de
  navegación para owner y learner, publicación de dos releases, historial,
  detalle inmutable, Biblioteca, lector de curso y unidades, 390 px, axe,
  clonación, retiro, 404 posterior y limpieza de base/Redis/correo/procesos.

Siguiente paso:

> **Prompt 12 — Matrículas y entrega del aprendizaje: acceso por curso, cohortes, progreso, continuidad, completitud y experiencia del estudiante.**
