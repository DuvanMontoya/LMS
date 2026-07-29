# Deployment architecture

## Local development

```mermaid
flowchart LR
  dev["Windows developer: browser, uv API, pnpm web"] --> compose["Docker Compose"]
  compose --> pg["postgres:18.4-trixie, digest locked"]
  compose --> redis["redis:8.8.1-trixie, digest locked"]
```

Native Windows runs the web/API development process. PostgreSQL and Redis are the only Compose services in this phase, both bind only to loopback and use named volumes. `compose.lock.yaml` pins Linux amd64 manifests; PostgreSQL 18 stores its cluster under the `/var/lib/postgresql` volume. Celery, object storage, mail emulation, and a reverse proxy remain out of scope.

The application exposes non-versioned `/health/live/` and `/health/ready/` for orchestration. Liveness has no dependency. Readiness checks PostgreSQL and the public Django cache API backed by Redis, because Redis now enforces authentication rate limits; neither endpoint reveals the failed dependency.

## Initial production

```mermaid
flowchart TB
  internet["HTTPS clients"] --> proxy["Managed/load-balancer reverse proxy"]
  proxy --> web["Next.js web Linux container"]
  proxy --> api["Django API Linux container /api"]
  api --> pg["Managed or self-managed PostgreSQL"]
  api --> redis["Redis service"]
  api --> storage["S3-compatible object storage"]
  worker["Celery Linux container"] --> redis
  worker --> pg
  worker --> storage
```

No Kubernetes is introduced. Containers are separately deployable but not microservices: API and worker share one versioned backend image/codebase. Health checks, non-root images, migration-before-rollout, rolling deployment, encrypted backups, restoring tests, observability, and a rollback runbook are required before production. The reverse proxy terminates TLS and preserves the scheme/host headers necessary for secure Django cookies.
# Despliegue

El OpenAPI de plataforma se publica sólo en desarrollo/test; no se añade Swagger
ni Redoc. El frontend reescribe `/api/v1` al origen Django interno y el cliente
server-only reenvía exclusivamente la cookie de sesión con `no-store`.

Prompt 8 no añade servicios: PostgreSQL conserva árbol, asociaciones, grafos y
archivado; Redis continúa reservado para cache y límites de autenticación. No
se almacenan currículo, capacidades ni sesiones en el navegador o Redis.
