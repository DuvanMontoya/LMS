# Conceptual domain model

## Aggregates and immutability

`identity.User` is the only implemented identity aggregate: UUID primary key, email authentication and Django permission/session compatibility. `Course`, `ContentDocument`, `Question`, and `Assessment` remain future logical identities with editable revisions; no profile, role or academic relation exists in the current schema.

```mermaid
erDiagram
  USER ||--|| PROFILE : has
  USER }o--o{ ROLE : receives
  AREA ||--o{ SUBJECT : contains
  SUBJECT ||--o{ CONCEPT : defines
  CONCEPT }o--o{ CONCEPT : prerequisite
  COURSE ||--o{ COURSE_REVISION : revises
  COURSE_REVISION ||--o{ MODULE : contains
  MODULE ||--o{ UNIT : contains
  UNIT ||--o{ CONTENT_DOCUMENT : references
  CONTENT_DOCUMENT ||--o{ CONTENT_REVISION : revises
  COURSE_REVISION ||--o{ COURSE_PUBLICATION : publishes
  USER ||--o{ ENROLLMENT : has
  COURSE_PUBLICATION ||--o{ ENROLLMENT : grants_access_to
  QUESTION ||--o{ QUESTION_VERSION : publishes
  ASSESSMENT ||--o{ ASSESSMENT_VERSION : publishes
  ASSESSMENT_VERSION ||--o{ QUESTION_VERSION : snapshots
  ENROLLMENT ||--o{ ATTEMPT : starts
  ATTEMPT ||--o{ DELIVERED_ITEM : contains
  DELIVERED_ITEM ||--o{ RESPONSE : records
  RESPONSE ||--o{ GRADE : receives
  ENROLLMENT ||--o{ PROGRESS : projects
  MEDIA_RESOURCE }o--o{ CONTENT_REVISION : embedded_in
  USER ||--o{ AUDIT_RECORD : acts
```

## State transitions

```mermaid
stateDiagram-v2
  [*] --> Draft
  Draft --> InReview: submit
  InReview --> Draft: request_changes
  InReview --> Published: publish immutable version
  Published --> Superseded: publish successor
  Published --> Withdrawn: explicit withdrawal
  Superseded --> [*]
  Withdrawn --> [*]
```

The attempt lifecycle is `not_started → in_progress → submitted → grading → graded`, with `expired` and `voided` only through authorized, audited transitions. A response is append-only after submission; any correction is a separately identified adjudication. Enrolment states include `pending`, `active`, `suspended`, `completed`, `expired`, and `withdrawn`.

## Required end-to-end flow

```mermaid
sequenceDiagram
  participant A as Author
  participant P as Publication service
  participant S as Student
  participant T as Attempt service
  participant G as Grading service
  participant R as Progress projection
  A->>P: draft -> review -> publish
  P-->>P: freeze course/content/question versions
  S->>T: access enrolment and delivered publication
  T-->>T: create immutable attempt snapshot
  S->>T: submit response
  T->>G: committed submission event
  G->>R: audited grade fact
  R-->>S: progress derived from versioned facts
```

Never retroactively recalculate a delivered question, submitted response, awarded grade, or historical progress without creating a separately versioned/corrected record and preserving provenance.
# Foundational identity

`identity.User` is the only identity model in the first schema. It has UUID `id`, required case-insensitively unique `email`, password/authentication fields, names, flags, groups and permissions. Academic roles, profile data and enrolment belong to later bounded modules.

`account.EmailAddress` is an allauth-owned supporting record, not a second user
model: it tracks the primary/verified email used by mandatory verification and
must remain coherent with `identity.User.email`. No profile, role or academic
relation is introduced by authentication.
# Modelo de dominio

```mermaid
erDiagram
  User ||--o{ Membership : participa
  Organization ||--o{ Membership : contiene
  Membership ||--o{ MembershipRoleAssignment : tiene_historial
  Membership ||--o{ MembershipEvent : registra
```

`Membership` tiene UUID y una única fila no revocada por usuario/organización.
Las asignaciones de rol y eventos son históricos; no existen roles globales en
`User`.
# Modelo curricular de Prompt 8

```mermaid
erDiagram
  Organization ||--o{ AcademicArea : scopes
  AcademicArea ||--o{ Discipline : contains
  Discipline ||--o{ Subject : contains
  Subject ||--o{ Topic : owns
  Organization ||--o{ Concept : owns
  Subject ||--o{ LearningObjective : owns
  Topic ||--o{ TopicConcept : orders
  Concept ||--o{ TopicConcept : appears_in
  LearningObjective ||--o{ LearningObjectiveConcept : orders
  Concept ||--o{ LearningObjectiveConcept : supports
  Subject ||--o{ SubjectPrerequisite : requires
  SubjectPrerequisite }o--|| Subject : prerequisite
  Concept ||--o{ ConceptPrerequisite : requires
  ConceptPrerequisite }o--|| Concept : prerequisite
```

`Topic` hereda `MP_Node`: `path`, `depth` y `numchild` son internos y no se
exponen por REST. Los prerrequisitos son dos DAG separados; una CTE recursiva
parametrizada rechaza ciclos y la fila de organización se bloquea antes de
reemplazar aristas. No hay `GenericForeignKey`, eliminación física ni cursos.

# Modelo de Courses (Prompt 9)

Los siguientes diagramas formalizan ADR 0019.

## 1. Course–Revision

```mermaid
erDiagram
  Organization ||--o{ Course : owns
  Course ||--o{ CourseRevision : versions
  CourseRevision o|--o{ CourseRevision : based_on
  CourseRevision ||--o{ CourseRevisionTransition : records
```

## 2. Revision–Module–Unit

```mermaid
erDiagram
  CourseRevision ||--o{ CourseModule : contains
  CourseModule ||--o{ CourseUnit : contains
```

## 3. Revision workflow

```mermaid
stateDiagram-v2
  draft --> in_review
  changes_requested --> in_review
  in_review --> changes_requested
  in_review --> approved
```

## 4. Optimistic concurrency

```mermaid
sequenceDiagram
  ClientA->>API: expected_version 7
  API->>DB: SELECT FOR UPDATE
  API->>DB: write and lock_version 8
  ClientB->>API: expected_version 7
  API->>DB: SELECT FOR UPDATE
  API-->>ClientB: 409 revision_conflict
```

## 5. Module reorder transaction

```mermaid
sequenceDiagram
  API->>DB: lock CourseRevision
  API->>DB: compare expected_version
  API->>DB: lock active CourseModule rows
  API->>DB: update every position
  API->>DB: increment lock_version and COMMIT
```

## 6. Unit reorder transaction

```mermaid
sequenceDiagram
  API->>DB: lock CourseRevision
  API->>DB: compare expected_version
  API->>DB: lock CourseModule and active CourseUnit rows
  API->>DB: update every position
  API->>DB: increment lock_version and COMMIT
```

## 7. Course–Subject

```mermaid
erDiagram
  CourseRevision ||--|{ CourseRevisionSubject : aligns
  Subject ||--o{ CourseRevisionSubject : referenced_by
```

## 8. Course–LearningObjective

```mermaid
erDiagram
  CourseRevision ||--o{ CourseRevisionLearningObjective : aligns
  LearningObjective ||--o{ CourseRevisionLearningObjective : referenced_by
```

## 9. Unit–Topic

```mermaid
erDiagram
  CourseUnit ||--o{ CourseUnitTopic : aligns
  Topic ||--o{ CourseUnitTopic : referenced_by
```

## 10. Unit–LearningObjective

```mermaid
erDiagram
  CourseUnit ||--o{ CourseUnitLearningObjective : aligns
  LearningObjective ||--o{ CourseUnitLearningObjective : referenced_by
```

## 11. Organization isolation

```mermaid
flowchart LR
  request["actor + organization slug"] --> membership["active membership"]
  membership --> capability["course capability"]
  capability --> course["Course.organization"]
  course --> descendants["revision, module, unit"]
  mismatch["foreign UUID"] --> hidden["404"]
```

## 12. Frontend course routes

```mermaid
flowchart TD
  list["/organizaciones/[slug]/cursos"] --> create["/nuevo"]
  list --> workspace["/[courseSlug]"]
  workspace --> structure["/[courseSlug]/estructura"]
  workspace --> review["/[courseSlug]/revision"]
```
