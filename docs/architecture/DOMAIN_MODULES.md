# Domain modules and boundaries

| Module / initial Django app grouping | Owns and public contract | Invariants and events | Allowed / prohibited dependencies; risk |
|---|---|---|---|
| `identity` | Implemented: User, password, groups, permissions, sessions and internal admin. Future: profile, roles and grants. | Custom user exists in `identity.0001`; email uniqueness is case-insensitive in PostgreSQL. | May serve all modules through policy contract; no academic ownership. Risk: role explosion. |
| `organizations` | Organización con ciclo `pending_activation/active/suspended/closed`, invitación inicial revocable, membresía, roles históricos y eventos. | La primera owner activa el tenant al aceptar; el operador global nunca recibe membresía implícita; el último owner activo no puede retirarse. | Depende sólo de identity; no posee cursos, matrículas ni reglas académicas. |
| `catalog` | Taxonomía y currículo institucional, incluidos objetivos, prerrequisitos y `SubjectTeachingResponsibility` fechada. | Slugs únicos por organización, grafos acíclicos y responsabilidad con cierre append-only; no se elimina físicamente ni concede roster. | Depende de organizations y su policy. Courses consume referencias y responsabilidad; catalog no posee delivery, notas ni intentos. |
| `courses` | Identidad y revisiones de curso, transiciones, módulos, unidades, `CourseActivity` ordenada, reglas de disponibilidad, política compuesta, esquema de calificación y `CourseTeachingException`. | Una secuencia contiene `lesson/live_class/assessment`; cada mutación exige versión y responsabilidad académica; la excepción es fechada y no concede grupo; aprobación no equivale a publicación. | Lee policy institucional y catálogo. Registros de extensión permiten bindings/readiness sin importar content, publishing, learning, scheduling o assessments. |
| `content` | Semantic documents, blocks, references, resource links | Validated document schema; no arbitrary executable markup. Emits `content_revised`. | Media and authoring; cannot publish itself. |
| `publishing` | Implemented: publication channel, immutable complete releases, integrity chain, withdrawal, draft cloning entry point and authenticated library. | Release/event rows are append-only and protected by PostgreSQL triggers; active points only to the newest release; reads use snapshots only. | Reads public courses/content/organization contracts. Courses and content never import publishing; no enrolment, progress, evaluation or delivery state. |
| `authoring` | Draft, review, publication, immutable snapshots/history | Published revision immutable; restoration creates a new revision. Emits `published`, `publication_retracted`. | Courses/content/assessments; cannot alter attempts. |
| `enrollments` | Enrolment, access window, status; future cohorts | Active access is evaluated at delivery time; historical enrolment facts retained. | Identity/courses/publication; no grading policy. |
| `learning` | `AcademicPeriod`, grupos académicos, grupos de curso release-pinned, roster/staff histórico, matrículas, `CourseGroupActivity`, progreso/evidencia append-only y continuidad. | Todo grupo nuevo cita periodo y release; cada actividad materializada coincide con snapshot/grupo; progreso compuesto separa completitud, nota, asistencia y dominio. | Puede leer organizations/courses/publishing; no importa scheduling/assessments ni posee score. Expone contratos acotados de asignación y proyección. |
| `scheduling` | Series/ocurrencias, sesiones LiveKit, asistencia, binding curricular de `live_class` y registro extensible de calendario. | PostgreSQL es autoridad; binding y política de asistencia son inmutables; webhooks idempotentes y segmentos append-only. | Lee organizations/courses y contratos públicos de learning. FullCalendar es UI; assessments registra providers sin importación inversa. |
| `assessments` | Bancos, versiones, deliveries group-scoped, assignments, intentos, scoring, regrading, gradebooks por grupo/periodo, analítica y binding curricular de `assessment`. | Snapshots público/grading separados; binding a versión aprobada inmutable; un intento en curso; grades/decisiones/eventos protegidos y calendario sin material de grading. | Lee policy, catálogo, publishing y contratos de learning. Registra readiness/snapshot/calendario; los dominios anteriores no lo importan. |
| `attempts` | Future extraction candidate, not a Django app in Phase 13. | Any extraction must preserve IDs, snapshots, events and transactions. | Must not be created without a new ADR and migration plan. |
| `grading` | Future advanced grading/gradebook boundary, not a Django app in Phase 13. | Regrading and projections must cite immutable inputs and preserve decisions. | Initial deterministic/manual grading remains in assessments under ADR 0023. |
| `progress` | Completion, mastery, progression projection | Derived records identify rules/version/input cutoff; historical results are not silently recomputed. | Learning/grading; no source-of-truth attempt data. |
| `media` | Blob metadata, derivative status, access policy | Metadata persists in DB; object key non-guessable; size/type verified. | Storage adapter only; no course ownership. |
| `search` | Permission-aware index/query projections | Never return unauthorized content; index rebuild is idempotent. | Reads published projections; no source mutations. |
| `notifications` | Preference, template, delivery/outbox | Delivery queued only after commit; preference applied before send. | Consumes events; no source ownership. |
| `analytics` | Append-only learning events and aggregates | Event schema versioned; aggregates reproducible from facts. | Consumes facts/events; never authoritatively grades. |
| `audit` | Sensitive action ledger | Append-only, actor/target/request correlation, retention policy. | Observes all via explicit contract; cannot become business event bus. |
| `integrations` | Future import/export/webhook adapters | Boundary validation and idempotency keys. | Depends on published service contracts only; no direct table access. |

Internal APIs are explicit Python services/selectors and namespaced REST endpoints, not imports of private models. A module may not import migrations, private querysets, UI serializers, or another module's tables directly.
# Identity boundary

The `identity` module owns the custom user, manager, internal admin forms and admin registration. Other modules must reference `settings.AUTH_USER_MODEL` in model fields and `get_user_model()` at runtime; they must not import `identity.User` directly.

# Catalog boundary

`catalog` deliberately groups the taxonomy and curriculum scope implemented in
Prompt 8. It owns the database tables and application services for all its
writes; `organizations` supplies only membership/capability policy. API views
may call catalog services but no other module may write catalog tables directly.
The two prerequisite graphs are independent: subjects express subject sequence,
and concepts express conceptual dependency. Neither graph implies a course,
publication or learner progression.

`SubjectTeachingResponsibility` expresa alcance académico fechado sobre una
asignatura. Sólo owner/administrator la crea o cierra; una persona elegible
consulta únicamente las propias. No concede acceso a grupos, estudiantes,
asistencia, intentos ni notas.

# Courses boundary

`courses` owns every write to course identity, revisions, transitions, modules,
units and their alignments. Transport code supplies actor and URL-scoped
organization, then calls application services. Catalog references remain owned
by `catalog`; courses validates their organization and status but never mutates
them. Semantic documents and publication snapshots remain outside this module.

# Content boundary

`content` es propietario exclusivo del documento semántico asociado a
`CourseUnit`, sus versiones append-only, validación, canonicalización, texto,
métricas, digest, API y renderer frontend. Puede importar el modelo público de
unidad y las políticas institucionales; `courses` no importa `content`.
`courses.readiness` y `courses.extensions` exponen registries estables y
agnósticos: `ContentConfig.ready()` registra providers sin consultar la base.

`CourseActivity` es el orden curricular canónico y `CourseUnit` conserva el
contrato semántico de una actividad `lesson`. Los bindings de clases y
evaluaciones se registran mediante extensiones estables. Toda escritura de
servicio vuelve a comprobar responsabilidad por asignatura o una
`CourseTeachingException` activa, incluso si se omite el selector HTTP.

Sólo servicios de `content` escriben sus tablas y siempre lo hacen dentro de una
transacción que bloquea la revisión y la unidad propietarias. El módulo no posee
curso, revisión, módulo, rol, catálogo, publicación, matrícula, evaluación,
archivo ni delivery. Un documento aprobado continúa siendo autoría privada
hasta que `publishing` produzca un snapshot completo.

# Publishing boundary

`publishing` posee `CoursePublication`, `CourseRelease`,
`CoursePublicationEvent`, schema, cadena, servicios, políticas, API y
biblioteca. Los contratos de clonación crean UUID nuevos y documentos v1 sin
importarlo. Un retiro cambia el canal y agrega evento, no el release. Véanse
`PUBLISHING.md` y ADR 0021.

`learning` posee `AcademicGroup`, `LearningCohort` (nombre técnico compatible
para grupo de curso), `CohortStaffAssignment`, `CourseEnrollment`,
`EnrollmentCohortAssignment`, `EnrollmentReleaseAssignment`, progreso, hechos
de roster y delivery. Puede importar organizations, courses y publishing para
validar referencias y leer snapshots; no importa content ni autoría viva.
Publishing, courses y content no importan learning. Assessments consume el
grupo efectivo como snapshot y scheduling usa su contrato público, sin invertir
la dependencia. Véanse `LEARNING.md`, ADR 0022 y ADR 0035.

ADR 0036/0037 amplían esta frontera: `AcademicPeriod` gobierna cada grupo nuevo,
`CourseGroupActivity` materializa el release v3 y `ActivityProgress` conserva
evidencia y eventos append-only. `CourseProgress` es una proyección compuesta;
ningún delivery operativo modifica el snapshot publicado.

# Assessments boundary

`assessments` posee el corte completo de Phase 13: banco, autoría, versiones,
entrega, intento, respuesta y grading inicial. Puede validar referencias de
organizations/catalog/publishing/learning, pero esos módulos no lo importan.
El navegador recibe sólo snapshots públicos. Véanse `ASSESSMENTS.md` y ADR
0023.

Prompt 14 amplía esta misma frontera con políticas de scoring, MathJSON seguro,
pools, jobs, grade versions, regrading, gradebook y analítica. Celery sólo llama
servicios de assessments; no introduce un dominio ni persistencia alterna.
Redis no contiene grades. `courses`, `content`, `publishing` y `learning`
continúan sin importar assessments; el gradebook no modifica `CourseProgress`.

El gradebook nuevo se identifica por grupo de curso y release, por lo que el
periodo se deriva del mismo grupo. `AssessmentActivityBinding` enlaza una única
versión aprobada y el provider de calendario proyecta sólo apertura/cierre y
deep link autorizados, nunca seed, respuesta esperada o payload de grading.

# Scheduling boundary

`domain.scheduling` posee series de curso o independientes, audiencias
explícitas de sesiones independientes, ocurrencias acotadas, excepciones,
sesiones LiveKit, segmentos de asistencia y webhooks idempotentes. Puede
referenciar organizaciones/cursos y usar contratos públicos de learning para
matrícula y requisitos de progreso; learning no importa scheduling. LiveKit
sólo ejecuta audio/video/pantalla y FullCalendar representa mediante la API.
Véanse ADR 0031 y ADR 0032.

`LiveClassActivityBinding` fija la política de asistencia de autoría y cada
ocurrencia curricular cita `CourseGroupActivity`. El registro de providers de
calendario evita que scheduling importe dominios operativos.

### Assets

`domain.assets` posee assets lógicos, versiones/variantes, sesiones/partes,
jobs/eventos, S3, cuarentena, procesamiento y descriptors. No importa
`content`, `publishing` ni `learning`. Esos módulos pueden depender de sus
contratos estables: content materializa referencias, publishing manifiestos y
learning entrega release-pinned. `courses` continúa sin importar content/assets
y assessments permanece desacoplado.
