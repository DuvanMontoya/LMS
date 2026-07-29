# ADR 0010: Initial Django app grouping

**Status:** Accepted — 2026-07-28.

The conceptual domain has nineteen named concerns, but the scaffold creates only five Django applications: `identity`, `catalog`, `content`, `learning`, and `assessments`. They are the smallest present boundaries with coherent early dependencies: identity/organization; taxonomy/curriculum/courses; content/authoring/media; enrolments/learning/progress; and assessments/attempts/grading. Search, notifications, analytics, audit, and integrations remain documented domain boundaries but are deferred until they have executable responsibilities. This avoids nineteen empty applications without collapsing domain rules into an all-purpose core.
