# Architecture

## Decision

Use a monorepo containing an independently built Next.js web application and a deployable Django modular monolith. Django exposes REST under `/api/v1`; an initial production reverse proxy presents a single HTTPS origin, forwarding `/api`, `/_allauth`, static media routes as configured, and web traffic to Next.js. PostgreSQL is the transactional system of record. Redis supports cache, rate-limit counters, and Celery coordination only. S3-compatible storage holds validated blobs, with metadata and permissions in PostgreSQL.

Operational endpoints `/health/live/` and `/health/ready/` remain outside `/api/v1` and OpenAPI. Liveness has no dependencies; readiness currently checks PostgreSQL only.

The architecture accepts the candidate stack with two constraints: (1) Celery workers run on Linux containers because Celery does not support Windows; (2) `django-csp` is rejected because Django 6.0 includes a CSP framework, reducing an unnecessary dependency.

## C4 context

```mermaid
flowchart LR
  student["Student / Teacher / Author / Reviewer / Administrator"] --> web["LMS Web application"]
  web --> api["LMS API: Django modular monolith"]
  mobile["Future mobile application"] -. versioned REST .-> api
  api --> db[("PostgreSQL academic system of record")]
  api --> object["S3-compatible object storage"]
  api --> redis[("Redis cache and task coordination")]
  worker["Celery worker"] --> redis
  worker --> db
  worker --> mail["Transactional email provider"]
```

## Containers

```mermaid
flowchart TB
  browser["Browser"] --> proxy["Reverse proxy / same HTTPS origin"]
  proxy --> next["apps/web: Next.js + rewrites same-origin"]
  proxy --> django["apps/api: Django ASGI/WSGI"]
  next -->|SSR cookie-only session requests| django
  django --> postgres[("PostgreSQL")]
  django --> redis[("Redis")]
  django --> s3["S3-compatible storage"]
  celery["Celery worker: same API codebase"] --> redis
  celery --> postgres
  celery --> s3
```

## Backend module map

```mermaid
flowchart LR
  identity --> organizations
  taxonomy --> curriculum
  curriculum --> courses
  courses --> content
  content --> authoring
  authoring --> enrollments
  enrollments --> learning
  assessments --> attempts
  attempts --> grading
  grading --> progress
  courses --> assessments
  media --> content
  audit -. observes .-> identity
  audit -. observes .-> authoring
  analytics -. consumes events .-> learning
  notifications -. consumes events .-> grading
  integrations -. adapters .-> courses
```

## Frontend module map

```mermaid
flowchart TB
  routes["App Router route groups"] --> features["Feature modules"]
  features --> api["Generated API client + typed gateway"]
  features --> academic["Academic components"]
  features --> ui["Design-system UI components"]
  features --> forms["Zod schemas + React Hook Form"]
  api --> backend["/api/v1"]
  academic --> ui
```

## Cross-cutting rules

- A Django application owns its models, migrations, selectors/use cases, API adapters, and tests. Dependencies point toward published internal contracts, not another app's private models or tables.
- Writes with real invariants use explicit application services and `transaction.atomic`; side effects use `transaction.on_commit` plus an outbox/task boundary. Trivial CRUD stays direct and readable.
- Reads may use focused selectors. There is no generic repository layer around the Django ORM and no business rule in signals.
- Controllers/serializers and React components are thin adapters. No frontend calculation is authoritative for grades, permissions, attempts, or publication.
- Internal asynchronous events are domain facts with an outbox record; they are not a premature event-sourcing system.

## Critical sequences

### Session authentication

```mermaid
sequenceDiagram
  participant B as Browser
  participant W as Next.js
  participant P as Same-origin proxy
  participant A as Django/allauth
  B->>W: sign-in form and CSRF context
  W->>P: POST /_allauth/... with credentials and CSRF token
  P->>A: forward HTTPS request
  A->>A: rate limit, authenticate, verify policy/MFA state
  A-->>B: Set-Cookie HttpOnly Secure session; response has no persistent JWT
  B->>W: navigate with session cookie
  W->>P: SSR request /api/v1/... forwarding cookie
  P->>A: authenticated API request + CSRF for unsafe methods
  A-->>W: authorized typed response
```

### Publication

```mermaid
sequenceDiagram
  participant Author
  participant API as Authoring service
  participant DB as PostgreSQL
  participant Worker as Celery
  Author->>API: submit draft revision for review
  API->>DB: validate and atomically move Draft -> InReview
  Author->>API: authorized publish
  API->>DB: freeze immutable publication and outbox event
  API-->>Author: publication identifier/version
  API->>Worker: after-commit projection/index task
  Worker->>DB: build derived, permission-aware projections
```

### Attempt and grading

```mermaid
sequenceDiagram
  participant Student
  participant Attempts
  participant DB as PostgreSQL
  participant Grading
  Student->>Attempts: begin assessment
  Attempts->>DB: verify enrolment/access and snapshot published version
  DB-->>Attempts: immutable delivered items
  Student->>Attempts: submit answers
  Attempts->>DB: atomically seal submission and outbox event
  Attempts->>Grading: after-commit grade request
  Grading->>DB: append score/feedback and gradebook projection
  DB-->>Student: versioned result/progress view
```

### Content versioning

```mermaid
flowchart LR
  logical["Logical content identity"] --> draft["Editable draft revision"]
  draft --> review["Reviewed revision"]
  review --> published["Immutable published version"]
  published --> delivery["Course/assessment delivery snapshot"]
  delivery --> attempt["Attempt / historical record"]
  published --> successor["New editable successor revision"]
  successor --> review
```

## Explicit rejections

Microservices, Kubernetes, GraphQL, full CQRS, event sourcing, an all-purpose `core` app, a generic ORM repository, browser-persisted JWTs, and CORS middleware for the same-origin production model are rejected initially. Reconsider only through evidence and an ADR.
# Arquitectura

La autorización institucional se resuelve en `organizations`: la identidad es
global, las membresías UUID delimitan cada organización y las capacidades se
calculan por roles activos en cada solicitud. Las mutaciones usan servicios
transaccionales; Next.js usa la URL como contexto y Django mantiene autoridad.
