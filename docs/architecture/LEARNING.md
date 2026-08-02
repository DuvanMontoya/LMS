# Entrega del aprendizaje

Documento normativo de `domain.learning`, conforme a ADR 0022 y ADR 0035. La
publicación crea una versión legible; la matrícula concede delivery sobre una
versión fija. Un grupo académico es un padrón institucional y un grupo de curso
es la oferta concreta de curso/release.

## Modelo y ownership

```mermaid
erDiagram
  AcademicGroup ||--o{ AcademicGroupMember : mantiene
  AcademicGroup ||--o{ LearningCohort : alimenta_opcionalmente
  LearningCohort ||--o{ CohortStaffAssignment : asigna_docentes
  LearningCohort ||--o{ EnrollmentCohortAssignment : agrupa_históricamente
  CourseEnrollment ||--o{ EnrollmentCohortAssignment : cambia_de_grupo
  LearningCohort }o--|| CourseRelease : fija
  CourseEnrollment }o--|| Membership : vincula
  CourseEnrollment }o--|| Course : cursa
```

```mermaid
erDiagram
  CourseEnrollment ||--|{ EnrollmentReleaseAssignment : historial
  EnrollmentReleaseAssignment }o--|| CourseRelease : fija
  EnrollmentReleaseAssignment o|--o| EnrollmentReleaseAssignment : anterior
```

```mermaid
erDiagram
  EnrollmentReleaseAssignment ||--|| CourseProgress : mide
  CourseProgress ||--o{ LearningEvent : audita
  EnrollmentReleaseAssignment ||--o{ LearningEvent : contextualiza
```

```mermaid
erDiagram
  CourseProgress ||--o{ UnitProgress : agrega
  UnitProgress {
    uuid unit_id
    uuid last_node_id
    string status
  }
```

## Transacciones

```mermaid
sequenceDiagram
  actor Admin
  participant Service
  participant PostgreSQL
  Admin->>Service: preview/confirm roster o matrícula individual
  Service->>PostgreSQL: BEGIN + lock roster/grupo/matrícula/publicación
  Service->>PostgreSQL: enrollment + assignment + progress + events
  PostgreSQL-->>Service: constraints válidas
  Service-->>Admin: COMMIT enrollment
```

```mermaid
sequenceDiagram
  actor Admin
  participant Learning
  participant Publishing
  Admin->>Learning: upgrade(target, expected_version)
  Learning->>Learning: lock enrollment y validar individual
  Learning->>Publishing: verificar release posterior
  Learning->>Learning: cerrar assignment anterior
  Learning->>Learning: crear assignment y progreso vacío
  Learning-->>Admin: nueva versión de enrollment
```

```mermaid
sequenceDiagram
  actor Student
  participant API
  participant Progress
  Student->>API: complete(unit, expected_progress_version)
  API->>Progress: lock + validar snapshot
  Progress->>Progress: upsert UnitProgress completed
  Progress->>Progress: recalcular contadores y versión
  Progress-->>Student: 200 o 409
```

```mermaid
stateDiagram-v2
  [*] --> not_started
  not_started --> in_progress: open/complete
  in_progress --> completed: todas las unidades
  completed --> in_progress: reopen unit
```

## Continuidad y acceso

```mermaid
flowchart TD
  A["Resume solicitado"] --> B{"last unit pertenece al snapshot"}
  B -- sí --> C{"last node pertenece a la unidad"}
  C -- sí --> D["unit URL + #node-UUID"]
  C -- no --> E["unit URL"]
  B -- no --> F["primera unidad incompleta"]
  F --> G["primera unidad u outline"]
```

```mermaid
flowchart TD
  A["Solicitud de estudiante"] --> B{"identidad propia y membership active"}
  B -- no --> X["denegar"]
  B -- sí --> C{"enrollment active y ventana vigente"}
  C -- no --> X
  C -- sí --> D{"publication active"}
  D -- no --> X
  D -- sí --> E{"assignment activo y release íntegro"}
  E -- no --> X
  E -- sí --> Y["snapshot asignado"]
```

```mermaid
sequenceDiagram
  participant Browser
  participant Next as Next Server Component
  participant API
  participant Snapshot
  Browser->>Next: GET ruta protegida
  Next->>API: cookies + no-store
  API->>API: policy + enrollment scope
  API->>Snapshot: verify + read assigned release
  Snapshot-->>Browser: outline/unit tipado
```

```mermaid
flowchart LR
  A["/aprendizaje"] --> B["Mi aprendizaje"]
  B --> C["/aprender/course"]
  C --> D["/aprender/course/unidades/unit"]
  E["/aprendizaje/grupos-academicos"] --> F["padrón y ofertas vinculadas"]
  G["/aprendizaje/grupos-curso"] --> H["asistente, roster, docentes y progreso"]
  I["/aprendizaje/matriculas"] --> J["individuales, excepciones y lifecycle"]
```

## Concurrencia e inmutabilidad

```mermaid
sequenceDiagram
  participant Tab1
  participant PostgreSQL
  participant Tab2
  Tab1->>PostgreSQL: lock progress v4
  Tab2->>PostgreSQL: espera lock progress v4
  PostgreSQL-->>Tab1: COMMIT v5
  PostgreSQL-->>Tab2: row v5
  Tab2-->>Tab2: expected 4 != 5
  Tab2-->>PostgreSQL: ROLLBACK 409
```

```mermaid
flowchart TD
  I["INSERT LearningEvent"] --> P["permitir"]
  U["UPDATE LearningEvent"] --> T["BEFORE trigger"]
  D["DELETE LearningEvent"] --> T
  T --> R["RAISE integrity_constraint_violation"]
```

## Reglas operativas

- `active`, `suspended` y `revoked` son estados explícitos; revocación es
  terminal y reincorporación crea otra matrícula.
- Un grupo de curso archivado impide altas nuevas sin revocar matrículas
  existentes. La ruta y modelo `LearningCohort` se preservan como compatibilidad
  v1, pero no son el término principal de la UI.
- Una matrícula tiene una asignación histórica de grupo de curso. Un traslado
  dentro del mismo curso y release conserva su progreso; cambiar release usa
  upgrade explícito.
- Las ventanas se heredan desde la política del grupo de curso o se marcan como
  excepción individual. Cambiar la política ajusta sólo herencias, nunca una
  excepción ni un hecho histórico.
- Sólo learners activos de un padrón académico se sincronizan. Una baja suspende
  el acceso que nació de sincronización y deja toda evidencia conservada.
- El total de unidades se fija desde el release; el porcentaje usa 0–10 000
  basis points. No hay floats persistidos.
- Ausencia de `UnitProgress` significa `not_started`.
- `open` es idempotente para el evento; `complete` devuelve
  `already_completed`; `reopen` revierte completitud y puede reabrir el curso.
- La posición usa `IntersectionObserver`, debounce de cinco segundos y flush
  `keepalive` en navegación/pagehide. No usa Web Storage ni eventos masivos.
- El dashboard puede mostrar estado suspendido/finalizado/retirado, pero sólo
  `available` abre contenido.
- No existe DELETE en API ni borrado físico de historial.
