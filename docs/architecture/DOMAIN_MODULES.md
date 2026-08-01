# Domain modules and boundaries

| Module / initial Django app grouping | Owns and public contract | Invariants and events | Allowed / prohibited dependencies; risk |
|---|---|---|---|
| `identity` | Implemented: User, password, groups, permissions, sessions and internal admin. Future: profile, roles and grants. | Custom user exists in `identity.0001`; email uniqueness is case-insensitive in PostgreSQL. | May serve all modules through policy contract; no academic ownership. Risk: role explosion. |
| `organizations` | Implemented: organization, membership, historical role assignment and membership event API. | A UUID membership has at most one non-revoked row per user/organization; active owner cannot be last removed; role history is append/revoke. | Depends only on identity; cannot own courses, enrolments or academic rules. |
| `catalog` | Implemented: area, discipline, subject, materialized-path topic tree, reusable concept, learning objective, ordered concept associations and prerequisite edges. Future: competencies and learning paths. | UUID/slug uniqueness is scoped by organization; topic structural fields remain owned by Treebeard; both prerequisite graphs are acyclic; archived entities cannot receive new associations. | Depends on organizations and identity policy only. Courses may read its public services, but catalog never owns enrolment, delivery, grades or attempts. |
| `courses` | Implemented: stable Course identity, authoring revisions, append-only transitions, ordered modules/units and curriculum alignments. | At most one open revision; active positions are contiguous from 1; deferred uniqueness supports reorder; every mutation uses `expected_version`; approved structure is not publication. | Reads organization policy and catalog references; never owns taxonomy, semantic content, publication, enrolment, evaluations or grades. |
| `content` | Semantic documents, blocks, references, resource links | Validated document schema; no arbitrary executable markup. Emits `content_revised`. | Media and authoring; cannot publish itself. |
| `publishing` | Implemented: publication channel, immutable complete releases, integrity chain, withdrawal, draft cloning entry point and authenticated library. | Release/event rows are append-only and protected by PostgreSQL triggers; active points only to the newest release; reads use snapshots only. | Reads public courses/content/organization contracts. Courses and content never import publishing; no enrolment, progress, evaluation or delivery state. |
| `authoring` | Draft, review, publication, immutable snapshots/history | Published revision immutable; restoration creates a new revision. Emits `published`, `publication_retracted`. | Courses/content/assessments; cannot alter attempts. |
| `enrollments` | Enrolment, access window, status; future cohorts | Active access is evaluated at delivery time; historical enrolment facts retained. | Identity/courses/publication; no grading policy. |
| `learning` | Study session, bookmark, continuation | Learner state tied to delivered version. Emits `learning_event`. | Enrolments/publications; no score ownership. |
| `scheduling` | Series and bounded occurrences, academic calendar, live-session lifecycle, attendance segments and LiveKit webhook ledger. | PostgreSQL is authoritative; every live occurrence has one immutable room name; recurring sets are bounded; signed webhooks are idempotent and attendance is append-only by connection segment. | Reads organization policies, courses and the public effective-enrollment contract from learning. Existing academic domains never import scheduling. LiveKit and FullCalendar are adapters, not sources of truth. |
| `assessments` | Implemented: banks, question/assessment revisions and immutable versions, deliveries, assignments, attempts, responses, deterministic initial scoring and manual decisions. Future: pools, regrading, gradebook and analytics. | Public/grading snapshots are separate; one open revision and one in-progress attempt; final order is materialized; versions/items/decisions/events are trigger-protected. | Reads organization policy, catalog objectives, publishing releases and learning assignments. Reverse imports are prohibited. ADR 0023 intentionally groups the initial attempt/grading lifecycle here. |
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

`learning` posee `LearningCohort`, `CourseEnrollment`,
`EnrollmentReleaseAssignment`, `CourseProgress`, `UnitProgress`,
`LearningEvent`, políticas, servicios, selectores y API de delivery. Puede
importar organizations, courses y publishing para validar referencias y leer
snapshots; no importa content ni autoría viva. Publishing, courses y content no
importan learning. Véanse `LEARNING.md` y ADR 0022.

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

# Scheduling boundary

`domain.scheduling` posee series, ocurrencias acotadas, excepciones, sesiones
LiveKit, segmentos de asistencia y webhooks idempotentes. Puede referenciar
organizaciones/cursos y consultar matrícula efectiva mediante el contrato
público de learning; ningún dominio anterior lo importa. LiveKit sólo ejecuta
audio/video/pantalla y FullCalendar sólo representa y modifica mediante la API.
Véase ADR 0031.

### Assets

`domain.assets` posee assets lógicos, versiones/variantes, sesiones/partes,
jobs/eventos, S3, cuarentena, procesamiento y descriptors. No importa
`content`, `publishing` ni `learning`. Esos módulos pueden depender de sus
contratos estables: content materializa referencias, publishing manifiestos y
learning entrega release-pinned. `courses` continúa sin importar content/assets
y assessments permanece desacoplado.
