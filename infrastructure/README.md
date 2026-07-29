# Local infrastructure

Compose starts only PostgreSQL and Redis for local development. Both host ports bind to loopback; PostgreSQL uses `5433` because the workstation's `5432` was already occupied during the initial preflight. Native Windows Django uses the same `POSTGRES_*` names from `infrastructure/local/.env` and connects to `127.0.0.1:5433`.

Run `pnpm infra:init`, then `pnpm infra:up`. The generated `.env` is ignored and its secrets are never printed. `pnpm infra:smoke` proves authentication, PostgreSQL/Django connectivity, persistence through restart, Redis authentication/persistence, cleanup, and Redis's non-root effective user. Use `pnpm infra:down` for a non-destructive stop; only `pnpm infra:reset` with its explicit confirmation removes the two project volumes.

`compose.yaml` holds exact immutable version tags and service policy. `compose.lock.yaml` overrides those images with the amd64 manifest digests resolved from Docker Official Images. All operational scripts load both files, so the effective services are digest pinned. `pnpm infra:lock` pulls the two approved tags and consciously refreshes only this lock file after review.

Redis 8.8.1 uses a single strong `requirepass` for this local, two-service setup. Compose interpolates that generated value only at runtime so no secret is stored in source control or printed by the runbook; the direct `redis-server` command preserves the official entrypoint's non-root privilege drop. This is intentionally simpler than production ACL users: no application service currently exists, the port is loopback-only, and all local commands authenticate. Revisit named ACL users, rotation, TLS, and network policy before a shared or production deployment.
