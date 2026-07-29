# ADR 0012: Redis version and license

Date: 2026-07-28

## Decision

Use Docker Official Image `redis:8.8.1-trixie`, locked for Linux amd64 in `compose.lock.yaml`, for local infrastructure. It replaces the previously recorded 8.4.4 because the official registry now publishes 8.8.1 as the current stable patch line. Redis 8 is tri-licensed under RSALv2, SSPLv1, or AGPLv3; local development use is accepted only with a mandatory legal decision before production use.

## Context

Redis remains coordination/cache infrastructure and never the academic system of record. Docker's official image drops privileges to the `redis` user by default; the Compose configuration neither overrides the user nor enables `SKIP_DROP_PRIVS`. The local service uses a generated strong password, loopback publishing, AOF persistence, and one `requirepass` instead of ACL users.

## Consequences

The image and its license must be reviewed whenever the digest is updated. Before production or multi-user environments, select and document the license option with counsel, introduce named ACL users and rotation, and add TLS/network controls. A replacement is feasible because application code has not yet adopted a Redis client.
