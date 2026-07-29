# ADR 0011: TypeScript 6 compatibility fallback

**Status:** Accepted — 2026-07-28.

TypeScript 7.0.2 and ESLint 10.8.0 were tested against Next 16.2.12. The installed `eslint-config-next` chain includes `typescript-eslint` peers constrained to TypeScript `<6.1` and plugins constrained to ESLint 9. TypeScript 6.0.2 and ESLint 9.39.5 are therefore selected. They pass frozen install, ESLint, Prettier, `tsc`, Vitest, Playwright and Next build. Re-evaluate TypeScript 7 only after the Next lint chain declares support; no parallel TypeScript installation is introduced.
