# Domain modules and boundaries

| Module / initial Django app grouping | Owns and public contract | Invariants and events | Allowed / prohibited dependencies; risk |
|---|---|---|---|
| `identity` | Implemented: User, password, groups, permissions, sessions and internal admin. Future: profile, roles and grants. | Custom user exists in `identity.0001`; email uniqueness is case-insensitive in PostgreSQL. | May serve all modules through policy contract; no academic ownership. Risk: role explosion. |
| `organizations` | Implemented: organization, membership, historical role assignment and membership event API. | A UUID membership has at most one non-revoked row per user/organization; active owner cannot be last removed; role history is append/revoke. | Depends only on identity; cannot own courses, enrolments or academic rules. |
| `catalog` | Implemented: area, discipline, subject, materialized-path topic tree, reusable concept, learning objective, ordered concept associations and prerequisite edges. Future: competencies and learning paths. | UUID/slug uniqueness is scoped by organization; topic structural fields remain owned by Treebeard; both prerequisite graphs are acyclic; archived entities cannot receive new associations. | Depends on organizations and identity policy only. Courses may read its public services, but catalog never owns enrolment, delivery, grades or attempts. |
| `courses` | Logical course, structure, owners, lifecycle | One ordered structure per revision; logical identity differs from publication. | Taxonomy/curriculum/identity; never grades. |
| `content` | Semantic documents, blocks, references, resource links | Validated document schema; no arbitrary executable markup. Emits `content_revised`. | Media and authoring; cannot publish itself. |
| `authoring` | Draft, review, publication, immutable snapshots/history | Published revision immutable; restoration creates a new revision. Emits `published`, `publication_retracted`. | Courses/content/assessments; cannot alter attempts. |
| `enrollments` | Enrolment, access window, status; future cohorts | Active access is evaluated at delivery time; historical enrolment facts retained. | Identity/courses/publication; no grading policy. |
| `learning` | Study session, bookmark, continuation | Learner state tied to delivered version. Emits `learning_event`. | Enrolments/publications; no score ownership. |
| `assessments` | Question bank, question/evaluation revisions, rubrics, hints | Evaluation and question publications reference immutable revisions. | Content/authoring/courses; cannot own attempt lifecycle. |
| `attempts` | Attempt, delivered item, answer, timer/integrity state | One attempt transition at a time; submitted answer cannot be overwritten. Emits `attempt_submitted`. | Enrolments/published assessments; no grade calculation implementation. |
| `grading` | Score, manual review, controlled regrade, gradebook projection | Grade records cite response and grading policy/version; regrade is append/controlled. | Attempts/assessments; cannot mutate answer. |
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
