# ADR 0013: Local Compose and image locking

Date: 2026-07-28

## Decision

Use Docker Compose only for local PostgreSQL and Redis. `compose.yaml` declares the `lms` project, private bridge network, named volumes, health checks, and exact tags; `compose.lock.yaml` records the verified Linux amd64 image digests. Operational scripts always merge both files.

## Context

The API and web applications remain native Windows processes in this phase. PostgreSQL 18 changed its data-volume contract, so the named volume targets `/var/lib/postgresql`, not the legacy `/var/lib/postgresql/data`. No application, worker, object storage, mail sink, migration, or production deployment is included.

## Consequences

Image updates require `Pull` then the explicit `Lock` action and review of the changed digest. `Down` preserves named volumes; `Reset` requires `-ConfirmReset` and affects only resources labelled for the `lms` Compose project. The local stack is intentionally not a production topology.
