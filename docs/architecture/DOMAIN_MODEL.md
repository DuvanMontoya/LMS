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
