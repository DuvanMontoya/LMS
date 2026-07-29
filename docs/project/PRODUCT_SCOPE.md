# Product scope

## Product intent

LMS is a single-organization academic platform for deep study. The primary users are students, teachers, academic authors, reviewers, and administrators. It prioritizes structured knowledge, rigorous assessments, and durable academic records over marketplace or marketing features.

## In scope by progressive delivery

Identity and role/object permissions; taxonomy and curriculum; course and semantic content authoring; immutable publication versions; enrolment and study continuity; question banks, assessment attempts and grading; progress; media; search; notifications; academic analytics; audit; import/export adapters; Spanish-first internationalization and WCAG 2.2 AA.

## Explicitly out of scope for the initial foundation

- Adapting Moodle, Open edX, WordPress, Canvas, or another LMS.
- Native mobile application; it will consume the same versioned API later.
- Marketplace, payments, subscriptions, advertising, or multi-vendor commerce.
- Microservices, Kubernetes, GraphQL, event sourcing, or ceremonial full CQRS.
- Full multi-tenancy. Organization ownership is modeled as an optional future boundary, not enforced in V1.

## Non-negotiable product properties

- Published academic material and delivered assessment versions are immutable.
- PostgreSQL, not Redis or browser state, is the source of truth for academic records.
- A student never has historical attempts or grades silently reinterpreted by a later edit.
- Accessibility, auditability, privacy, security, and internationalization are acceptance criteria rather than polish work.
