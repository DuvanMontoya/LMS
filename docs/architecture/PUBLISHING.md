# Publicación inmutable

Documento operativo de la fase 11, decidido por ADR 0021. `publishing` es el
único propietario de la proyección publicable de un curso. Una revisión
`approved` sigue siendo autoría; sólo un `CourseRelease` con snapshot validado
es material de biblioteca.

## Modelo, snapshot y cadena

```mermaid
erDiagram
  COURSE ||--|| COURSE_PUBLICATION : channel
  COURSE_PUBLICATION ||--o{ COURSE_RELEASE : history
  COURSE_RELEASE o|--|| COURSE_RELEASE : previous
  COURSE_PUBLICATION ||--o{ COURSE_PUBLICATION_EVENT : records
```

```mermaid
flowchart LR
  revision["Approved revision"] --> structure["Ordered modules and units"]
  catalog["Catalog labels"] --> snapshot["Complete release snapshot"]
  content["Current semantic documents"] --> snapshot
  snapshot --> schema["Draft 2020-12 validation"]
  schema --> release["Immutable JSONB"]
```

```mermaid
flowchart LR
  r1["Release 1 digest"] --> r2["Release 2: previous digest + snapshot"]
  r2 --> r3["Release 3: previous digest + snapshot"]
  r3 --> verify["verify_release_chain"]
```

El JSON excluye usuarios, permisos, secretos, HTML, aprendizaje, matrículas y
datos vivos. Se canonicaliza con JSON UTF-8, claves ordenadas y separadores
compactos. Los límites se validan antes de insertar. La biblioteca nunca
recompone el curso desde autoría.

## Transacciones y fronteras

```mermaid
sequenceDiagram
  actor Owner
  participant Service
  participant DB as PostgreSQL
  Owner->>Service: publish(revision, expected lock)
  Service->>DB: BEGIN + row locks
  Service->>Service: readiness + snapshot + schema + digest
  Service->>DB: INSERT release/event; update channel
  Service->>DB: COMMIT
```

```mermaid
sequenceDiagram
  actor Owner
  participant Service
  participant DB as PostgreSQL
  Owner->>Service: withdraw(note, expected lock)
  Service->>DB: BEGIN + lock publication
  Service->>DB: status withdrawn + append event
  Service->>DB: COMMIT
```

```mermaid
sequenceDiagram
  actor Author
  participant Publishing
  participant Courses
  participant Content
  Author->>Publishing: create draft from release
  Publishing->>Courses: clone approved structure
  Publishing->>Content: clone snapshot documents
  Content-->>Publishing: version 1, same digests
```

```mermaid
flowchart LR
  write["UPDATE or DELETE"] --> trigger["PostgreSQL trigger"]
  trigger --> reject["raise integrity exception"]
  insert["INSERT"] --> allow["append only"]
```

```mermaid
sequenceDiagram
  actor Learner
  participant Next
  participant API
  participant Snapshot
  Learner->>Next: library route
  Next->>API: session cookie, no-store
  API->>Snapshot: active publication only
  Snapshot-->>Next: outline or semantic unit
```

```mermaid
flowchart LR
  snapshot["CourseRelease.snapshot"] --> list["Library list"]
  snapshot --> outline["Course outline"]
  snapshot --> unit["Semantic reader"]
  live["Live authoring tables"] -. "never queried" .-> unit
```

```mermaid
flowchart TB
  library["/biblioteca"] --> course["/biblioteca/[courseSlug]"]
  course --> unit["/biblioteca/[courseSlug]/unidades/[unitId]"]
  workspace["/cursos/[courseSlug]"] --> publication["/publicacion"]
  publication --> history["/publicaciones/[releaseNumber]"]
```

```mermaid
flowchart LR
  role["Organization role"] --> policy["Publishing policy"]
  policy --> publish["publish / withdraw / history / clone"]
  policy --> read["published course read"]
  url["Scoped organization URL"] --> policy
```

```mermaid
sequenceDiagram
  participant A as Request A
  participant DB as Locked publication
  participant B as Request B
  A->>DB: select_for_update
  B->>DB: waits
  A->>DB: insert contiguous release and commit
  DB-->>B: refreshed lock_version
  B-->>B: idempotent result or 409
```

## Operación y garantías

Los triggers `publishing_prevent_course_release_mutation` y
`publishing_prevent_publication_event_mutation` protegen UPDATE/DELETE aun
fuera del ORM. `verify_course_releases` recalcula schema, digest, enlace previo
y cadena sin escribir. El retiro exige nota, conserva releases y eventos y no
restaura una versión anterior. Sólo un release nuevo vuelve a estado activo.

Las respuestas de biblioteca usan `Cache-Control: private, no-store`. Las rutas
exigen sesión y capacidad institucional; una referencia cruzada devuelve 404.
No existe DELETE, restore, body de snapshot, JWT, almacenamiento browser,
matrícula, progreso ni evaluación.
