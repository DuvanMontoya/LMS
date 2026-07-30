# ADR 0020 — Semantic unit documents and schema-versioned academic editor

- Estado: Accepted
- Fecha: 2026-07-29
- Decisores: arquitectura LMS
- Alcance: `domain.content` y el editor académico de unidades

## Contexto

Una `CourseUnit` necesita contenido académico rico sin convertir HTML, SVG ni
MathML en fuente de verdad. El contrato debe ser portable entre Django y Next.js,
resistir documentos patológicos y cargas activas, conservar todo cambio aceptado
y participar en la preparación de una revisión sin trasladar la estructura del
curso fuera de `domain.courses`. Esta fase no publica, matricula, evalúa ni
ejecuta código.

## Decisión

`domain.content` es propietario de un documento semántico JSON por `CourseUnit`.
El contrato canónico es
`schemas/content/unit-document-v1.schema.json`, JSON Schema Draft 2020-12, sin
referencias remotas. `schema_version` es explícito; una evolución incompatible
creará otro schema y una migración de documentos deliberada. El backend valida
con `jsonschema` y validadores semánticos; el frontend valida la misma copia con
Ajv y deriva sus tipos mediante `json-schema-to-typescript`. El check de drift no
modifica el checkout.

Los nodos almacenan intención —párrafos, headings, listas, citas, bloques
pedagógicos, fórmulas, código y tablas—, nunca presentación ejecutable. Cada nodo
de bloque tiene un UUID estable y el backend exige unicidad global. Los enlaces
aceptan únicamente esquemas seguros. LaTeX se limita y filtra antes de renderizar.
El código sólo se edita y representa como texto.

Tiptap/ProseMirror 3 configura `immediatelyRender: false`, comprobación de
contenido y extensiones semánticas propias. MathLive edita LaTeX; MathJax local
con `ui/safe`, paquetes explícitos y sin `texhtml` lo representa. CodeMirror 6
edita bloques de lenguajes enumerados. La lectura y el preview usan el mismo
renderer estático tipado, sin `dangerouslySetInnerHTML` propio.

`UnitContentDocument` es `OneToOne` con `CourseUnit` y señala su versión vigente.
`UnitContentVersion` es append-only, tiene número monotónico único, JSONB,
texto/métricas derivados y digest SHA-256 de JSON canónico. Guardar requiere
`expected_document_version`. La transacción bloquea revisión, unidad y documento;
un digest idéntico es no-op, uno distinto crea la siguiente versión. Restaurar
crea otra versión: nunca altera ni elimina la histórica.

No hay autosave, almacenamiento del navegador ni colaboración en tiempo real. El
guardado es explícito y `Ctrl/Cmd+S` comparte la misma acción. Un 409 conserva el
documento local y presenta el estado del servidor. `beforeunload` protege cambios
no guardados.

`domain.courses` ofrece registries genéricos de readiness y enriquecimiento del
outline; `domain.content` se registra al cargar su aplicación. Así, `courses` no
importa `content`. Una revisión sólo puede enviarse cuando todas sus unidades
activas tienen contenido significativo y válido. Aprobar sigue siendo una
transición de autoría, no publicación.

## Relaciones

```mermaid
erDiagram
    COURSE_UNIT ||--o| UNIT_CONTENT_DOCUMENT : owns
    UNIT_CONTENT_DOCUMENT ||--o{ UNIT_CONTENT_VERSION : records
    UNIT_CONTENT_DOCUMENT ||--o| UNIT_CONTENT_VERSION : current
    USER ||--o{ UNIT_CONTENT_VERSION : creates
```

## Transacción de guardado

```mermaid
sequenceDiagram
    participant UI as Editor
    participant API as Content API
    participant DB as PostgreSQL
    UI->>API: PUT JSON + expected_document_version
    API->>DB: BEGIN; lock revision and unit
    API->>DB: lock or create document safely
    API->>API: pre-scan, schema, semantic and security validation
    API->>API: canonical JSON, text, metrics and SHA-256
    alt digest unchanged
        API->>DB: COMMIT without version
    else changed
        API->>DB: INSERT immutable version; UPDATE current pointer
        API->>DB: COMMIT
    end
    API-->>UI: current document representation
```

## Guardados concurrentes

```mermaid
sequenceDiagram
    participant A
    participant B
    participant API
    participant DB
    A->>API: PUT expected v1
    B->>API: PUT expected v1
    API->>DB: serialize with row locks
    API-->>A: 200 v2
    API-->>B: 409 server v2
    Note over B: local JSON remains intact
```

## Restauración

```mermaid
flowchart LR
    V1["Version 1"] --> V2["Version 2"]
    V2 --> V3["Version 3"]
    V1 -. "restore payload" .-> V4["Version 4, current"]
```

## Validación del schema

```mermaid
flowchart TD
    R["Raw JSON body"] --> P["Byte, depth and node pre-scan"]
    P --> S["Draft 2020-12 validation"]
    S --> V["Semantic, UUID, link and LaTeX validators"]
    V --> C["Canonicalize and derive metrics"]
    C --> D["Persist immutable version"]
```

## Schema del editor

```mermaid
graph TD
    Doc --> Basic["Paragraph, heading, lists, blockquote"]
    Doc --> Pedagogy["Definition, theorem, example, note, warning, exercise"]
    Doc --> Math["Inline and display math"]
    Doc --> Code["Code block"]
    Doc --> Table["Captioned table with headers"]
    Basic --> Marks["Bold, italic, strike, code and safe link"]
```

## Renderizado

```mermaid
flowchart LR
    JSON["Validated semantic JSON"] --> SR["Typed static renderer"]
    SR --> HTML["React elements"]
    SR --> MJ["Local MathJax safe typesetting"]
    SR --> PRE["Inert code text"]
    SR --> AT["Accessible tables and links"]
```

## Edición matemática

```mermaid
sequenceDiagram
    participant U as Author
    participant ML as MathLive field
    participant T as Tiptap node
    participant MJ as MathJax local
    U->>ML: edit LaTeX
    ML->>T: normalized LaTeX attribute
    T->>MJ: validated formula
    MJ-->>U: accessible visual representation
```

## Extensión de readiness

```mermaid
flowchart LR
    C["courses readiness service"] --> R["Provider registry"]
    Content["content AppConfig"] --> R
    R --> Missing["missing or empty issues"]
    R --> Ready["ready when every active unit is meaningful"]
```

## Rutas frontend

```mermaid
flowchart TD
    Structure["/estructura"] --> Editor["/unidades/{unitId}/contenido"]
    Editor --> Preview["Preview panel"]
    Editor --> History["Version history"]
    Review["Review panel"] --> Readiness["Content readiness issues"]
```

## Frontera de seguridad

```mermaid
flowchart LR
    Browser --> BFF["Next same-origin proxy"]
    BFF --> Auth["Django session and CSRF"]
    Auth --> Policy["Organization and revision policy"]
    Policy --> Validator["Bounded semantic validator"]
    Validator --> DB["PostgreSQL JSONB"]
    DB --> Renderer["Static renderer"]
    Renderer --> Browser
    Renderer -. "no remote fetch, eval or stored HTML" .-> Denied["Denied"]
```

## Generación de schema y tipos

```mermaid
flowchart LR
    Canon["Canonical JSON Schema"] --> Validate["Meta-schema validation"]
    Validate --> Generate["json-schema-to-typescript"]
    Validate --> Copy["Frontend schema copy"]
    Generate --> TS["Generated TypeScript"]
    Copy --> Ajv["Ajv validator"]
    Temp["--check temporary output"] --> Compare["Byte comparison / drift failure"]
    Canon --> Temp
```

## Consecuencias

La representación es auditable, determinista y segura por construcción; se evita
un segundo contrato frontend y se preserva la historia completa. El coste es
mantener migraciones explícitas del schema, extensiones Tiptap propias y assets
locales de matemática. Los documentos tienen límites estrictos: 1 MiB
serializado, 5.000 nodos, profundidad 32, 300.000 caracteres, 1.000 bloques
superiores, tablas de 100 × 20, código de 50.000 caracteres y fórmulas acotadas.

## Alternativas rechazadas

- HTML/Markdown como fuente de verdad: mezcla semántica y presentación, aumenta
  el espacio XSS y dificulta evolución estructural.
- Guardado destructivo o sobrescritura de versiones: pierde trazabilidad.
- Autosave o almacenamiento local: introduce estados ocultos y conflictos fuera
  del contrato transaccional.
- KaTeX, CDN o ejecución de código: contradicen el renderer decidido y el límite
  de seguridad de esta fase.
- Importar `content` desde `courses`: crea inversión/ciclo de dependencias.
- Publicar la revisión aprobada: pertenece a una fase posterior con snapshots
  inmutables completos.
