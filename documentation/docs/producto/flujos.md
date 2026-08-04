# Flujos académicos

## Autoría, publicación y entrega

```mermaid
stateDiagram-v2
  [*] --> draft
  draft --> in_review: autor envía
  in_review --> changes_requested: revisor solicita cambios
  changes_requested --> draft: autor corrige
  in_review --> approved: revisor aprueba
  approved --> release: administrador publica snapshot
  release --> active: publicación activa
  active --> withdrawn: retiro con nota
```

El estado de la revisión pertenece a `domain.courses`. La publicación pertenece a `domain.publishing` y no modifica la revisión ni las versiones de contenido. Una matrícula conserva el release asignado aunque se publique otro.

## Sesión y autorización

```mermaid
sequenceDiagram
  participant B as Navegador
  participant W as Next.js
  participant A as Django
  participant P as Política de dominio
  participant DB as PostgreSQL
  B->>W: Ruta protegida
  W->>A: Solicitud same-origin con cookie de sesión
  A->>P: Comprueba membresía, capacidad y alcance
  P->>DB: Consulta datos institucionales
  DB-->>P: Estado autorizado o ausente
  P-->>A: Decisión
  A-->>W: JSON o 403/404
  W-->>B: Superficie permitida o error seguro
```

La sesión es de Django y las mutaciones protegidas usan CSRF. No se persisten JWT, roles, capacidades ni sesiones en `localStorage`, `sessionStorage` o IndexedDB.

## Ciclo de un recurso académico

```mermaid
flowchart LR
  init[Inicio de carga con checksum] --> quarantine[Objeto privado en cuarentena]
  quarantine --> scan[Antivirus y validación de formato]
  scan -->|aprobado| processing[Variantes y metadatos]
  scan -->|rechazado| rejected[Rechazado]
  processing --> ready[AssetVersion READY]
  ready --> pinned[Contenido o release fija la versión]
  pinned --> descriptor[Descriptor temporal autorizado]
```

Un `AssetVersion` `READY` es inmutable. Los bytes y sus variantes siguen siendo privados; el estudiante recibe un descriptor temporal sólo si una matrícula efectiva autoriza el release.
