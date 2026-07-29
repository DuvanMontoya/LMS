# ADR 0014: Custom email user model

Date: 2026-07-29

## Decision

`identity.User` is the project user model from its first migration. It extends `AbstractUser`, replaces `username` with required email authentication, uses a UUID primary key and is selected through `AUTH_USER_MODEL = "identity.User"`.

Email is trimmed and normalized to lowercase in the typed manager. PostgreSQL retains both Django's exact `unique=True` constraint and a `UniqueConstraint(Lower("email"))`: the first gives Django-level uniqueness metadata and efficient exact lookup, while the second is the authority for case-insensitive uniqueness under concurrent writes.

## Consequences

Future model relations use `settings.AUTH_USER_MODEL`; runtime lookup uses `get_user_model()`. No profile, role, academic identity, public authentication endpoint or persistent superuser is introduced. This migration is intentionally irreversible without a data migration and schema plan.
