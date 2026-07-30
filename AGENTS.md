# LMS repository rules

## Current phase

Phase 10 is complete locally: preserve `identity.0001`; any user-model change requires an ADR, migration plan and real PostgreSQL evidence. Organization roles belong only to `domain.organizations`, must be checked through policies/services, and may not be copied to `User`, `Group`, browser storage or generic admin forms. `domain.catalog` owns organization-scoped taxonomy and curriculum only. `domain.courses` owns course identity, authoring revisions, transitions, ordered modules/units and their catalog alignments; an approved revision is not a publication. `domain.content` attaches one schema-versioned semantic JSON document and append-only versions to `CourseUnit`; it must not own course structure or introduce publication, enrolment, evaluation, code execution or delivery behavior. `domain.courses` must not import `domain.content`; optional readiness and outline behavior is registered through the stable extension registries.

## Persistent engineering rules

- Consult official documentation, release notes, registries, and standards before selecting versions, commands, or capabilities. Record the source and consultation date.
- Use exact, supported stable versions; never use preview channels or floating tags in reproducible commands.
- Prefer official generators and CLIs over hand-written boilerplate. Run their `--help` before relying on changed syntax.
- Preserve the modular-monolith boundaries in `docs/architecture/DOMAIN_MODULES.md`; add an ADR before changing a material architectural decision.
- Do not add a dependency without a documented problem, compatibility check, license assessment, owner, and removal alternative.
- Treat peer-dependency warnings, blocked lifecycle scripts, and dependency-audit findings as evidence to resolve or document; never suppress them with unsafe package-manager flags.
- Never commit secrets, credentials, production data, generated local state, or real personal data. Use documented environment-variable names and examples only.
- Do not overwrite or remove unrelated work. Inspect Git status before edits and preserve existing contracts.
- Keep application rules out of transport controllers, React components, unmanaged signals, and generic repository wrappers.
- Run the validations required by the active phase. Do not claim that a behavior works without proportionate evidence.
- Update `docs/project/STATUS.md` whenever phase status, a decision, a verification, a risk, or the next exact step changes.

## Documentation conventions

Technical identifiers, package names, folders, modules, and ADR titles are English. Explanatory documentation is Spanish. Mermaid diagrams must reflect a decision recorded in an ADR or architecture document.
