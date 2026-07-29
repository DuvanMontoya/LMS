# ADR 0005: PostgreSQL source of truth

**Status:** Accepted — 2026-07-28.

PostgreSQL 18.4 owns durable identity, academic content, versions, enrolments, attempts, grades, progress, and audit records. Redis is transient cache/coordination only; JSONB is limited to truly variable structures. This protects reconstructible academic history and transactional invariants.
