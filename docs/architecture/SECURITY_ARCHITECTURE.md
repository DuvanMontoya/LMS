# Security architecture

## Baseline

- Create the custom Django user model in the first migration. Use Django's supported modern password hasher configuration, secure password reset/email verification flows, django-allauth MFA/usersessions capabilities, and session invalidation on sensitive changes.
- Browser authentication is Django session + `HttpOnly`, `Secure` (production), `SameSite` cookies, CSRF middleware/tokens, HTTPS, same origin and a reverse proxy. `django-cors-headers` is not approved initially.
- Apply RBAC plus object policies at the service/API boundary; privileged operations are authorization-checked, rate-limited and audit-recorded. Django Admin is internal-only.
- Validate every input server-side. Use ORM/parameterized database access; encode output; restrict rich content to a vetted semantic schema; configure Django 6 CSP and security headers.
- Uploads use allowlisted media types, magic-byte/content inspection where viable, size/count limits, generated safe keys, malware scanning before availability, private buckets by default, and short-lived signed access.
- Secrets exist only in environment/secret stores. `.env.example` names variables but has no real values. Logs/traces never include passwords, cookies, tokens, PII-rich answers, or unredacted submissions.
- Local PostgreSQL and Redis bind exclusively to `127.0.0.1`, require generated passwords, and use a private Compose bridge network. PostgreSQL initializes host connections with SCRAM and checksums; Redis uses local `requirepass`, AOF, and the official non-root entrypoint. This is not a substitute for production TLS, ACL users, rotation, or network policy.
- Passwords use Django's official Argon2id hasher first, while retained built-in hashers verify legacy values. Session cookies are HttpOnly/SameSite=Lax, production marks session and CSRF cookies secure, and DRF is SessionAuthentication plus IsAuthenticated by default.
- Public authentication uses only the official allauth browser headless surface. Mandatory email verification and password recovery use allauth one-time codes; browser requests remain subject to Django CSRF. Redis database 1 is only the `lms-auth` cache namespace for allauth rate limits, never a session store or user/code store. Redis failure is not allowed to fall back to local cache.
- Browser traffic remains same-origin at Next.js. Only explicit rewrite surfaces reach Django; the internal Django origin is server-only, CSRF remains readable to same-origin JavaScript, and neither session nor code is persisted in browser storage.
- Authentication and protected responses send `Cache-Control: no-store`, `Referrer-Policy: same-origin`, `X-Content-Type-Options: nosniff` and a restrictive permissions policy. `/admin/` is deliberately not rewritten. Development and E2E routing bind to `127.0.0.1`; production origin and reverse-proxy trust remain explicit deployment work.

## Operational controls

Encrypted backups and tested restore procedures cover PostgreSQL and object storage; retention/deletion policies distinguish operational logs, audit records, academic records, and media. Dependencies use lockfiles, vulnerability checks, release review, and SBOM export. CI has secret scanning, permission-minimal credentials, protected branches, review of migrations and OpenAPI diffs.

## Threat decisions

The primary risks are account takeover, authorization bypass, CSRF/XSS in authoring, malicious uploads, grading/attempt tampering, data leakage via search/analytics, background-task replay, secret exposure, and destructive migrations. Threat modeling precedes each public or sensitive module. Celery tasks are idempotent, receive stable identifiers not trusted payloads, re-check authorization/business state, and are queued only after transaction commit.
