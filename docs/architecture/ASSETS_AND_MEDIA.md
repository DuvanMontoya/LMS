# Assets and media

## Frontera y modelo

`domain.assets` administra recursos privados; no estructura cursos, publica,
matricula ni evalúa. Content fija versiones, publishing captura el manifest y
learning autoriza la entrega del snapshot asignado.

```mermaid
erDiagram
  Asset ||--o{ AssetVersion : "has immutable"
  AssetVersion ||--o{ AssetVariant : "produces"
  AssetVersion ||--o{ AssetProcessingJob : "processed by"
  AssetVersion ||--o{ AssetEvent : "records"
  AssetVersion ||--o| AssetUploadSession : "uploaded through"
  AssetUploadSession ||--o{ AssetUploadPart : "records"
```

```mermaid
flowchart LR
  A["assets"] --> C["content"]
  A --> P["publishing"]
  A --> L["learning"]
  C --> P
  P --> L
```

## Upload y cuarentena

```mermaid
sequenceDiagram
  participant B as Browser
  participant API as Django API
  participant Q as S3 quarantine
  participant DB as PostgreSQL
  participant W as Media worker
  B->>API: initialize metadata + expected SHA-256
  API-->>B: presigned POST or multipart session
  B->>Q: bytes + checksum
  loop at most 3 concurrent parts
    B->>API: sign part
    B->>Q: PUT part + checksum
    B->>API: record ETag/checksum/size
  end
  B->>API: complete
  API->>Q: HeadObject and checksum validation
  API->>DB: durable job
  API-->>W: dispatch after commit
```

```mermaid
flowchart LR
  Q["Quarantine object"] --> AV["ClamAV scan"]
  AV -->|infected/error| R["Rejected or failed closed"]
  R --> D["Delete quarantine object"]
  AV -->|clean| M["MIME and format validation"]
  M --> T["Pillow / pypdf / FFmpeg / VTT / dataset"]
  T --> V["Immutable variants in private bucket"]
  V --> READY["Version READY and optional promotion"]
```

```mermaid
flowchart LR
  I["Image source"] --> O["EXIF transpose"]
  O --> L["pixel/animation limits"]
  L --> S["strip metadata"]
  S --> TH["thumbnail"]
  S --> MD["medium"]
  S --> LG["large"]
```

```mermaid
flowchart LR
  V["Video source"] --> FP["ffprobe allowlist and limits"]
  FP --> MP4["H.264 + AAC MP4"]
  FP --> POSTER["poster JPEG"]
  MP4 --> NOHLS["No HLS in phase 15"]
```

## Referencias, release y entrega

```mermaid
sequenceDiagram
  participant E as Editor
  participant C as Content
  participant A as Assets
  E->>C: save schema v2 with assetVersionId
  C->>A: validate org/kind/READY
  C->>C: append ContentAssetReference
```

```mermaid
flowchart LR
  CV["ContentVersion v2"] --> REF["fixed AssetVersion IDs"]
  REF --> MAN["release asset manifest"]
  MAN --> DIG["release digest"]
  DIG --> REL["immutable CourseRelease"]
```

```mermaid
sequenceDiagram
  participant L as Learner
  participant API as Learning API
  participant DB as PostgreSQL
  participant S3 as Private S3
  L->>API: assigned release unit
  API->>DB: validate effective enrollment + manifest
  API->>S3: presign allowed variants in batch
  API-->>L: descriptors without keys
  L->>S3: GET temporary URL
  L->>API: one batch refresh after expiry
```

```mermaid
flowchart LR
  AWS["Production: AWS S3 private buckets"] --> API["Django + Boto3"]
  LS["Local/CI: LocalStack S3 only"] --> API
  API --> PG["PostgreSQL authority"]
  API --> R["Redis broker"]
  R --> W["non-root media worker"]
  W --> C["ClamAV daemon"]
```

```mermaid
sequenceDiagram
  participant U1 as Request A
  participant U2 as Request B
  participant DB as PostgreSQL
  U1->>DB: lock Asset / expected lock_version
  U2->>DB: waits
  U1->>DB: promote and increment
  U2->>DB: conflict, no overwrite
```

```mermaid
flowchart TD
  F["Visible file input"] --> H["hash in browser"]
  H --> I["initialize"]
  I --> U{"simple or multipart"}
  U -->|simple| P["presigned POST + progress"]
  U -->|multipart| C["up to 3 PUTs + per-part checksum"]
  P --> X["complete and processing polling"]
  C --> X
  X --> R["READY detail or actionable error"]
```

## Operación

- `pnpm storage:init` aplica buckets, encryption, versioning, CORS y lifecycle.
- `pnpm media:build && pnpm media:up` levanta ClamAV y el worker reproducible.
- `pnpm assets:demo` crea siete assets propios y pasa por el pipeline real.
- `pnpm assets:smoke` comprueba storage, workers y EICAR generado en runtime.
- `reconcile_asset_storage` reporta faltantes/checksums; no repara de forma
  implícita.
- `expire_stale_upload_sessions` aborta sesiones vencidas de forma idempotente.

Los endpoints internos, credenciales y object keys nunca llegan al bundle. Las
URLs firmadas son descriptores temporales y no se persisten en documentos ni
releases.
