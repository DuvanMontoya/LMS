# Scaffolding commands for Prompt 2

**Do not run these in Phase 1.** They are PowerShell commands for the detected Windows x64 environment and are intentionally limited to reproducible monorepo/API/web scaffolding. They do not create domain features, Docker files, migrations, or infrastructure services.

Run from `C:\Users\Robert\Documents\GitHub\LMS`. Stop on any error (`$ErrorActionPreference = 'Stop'`); do not add `--force`. The official `create-next-app` flag syntax was verified in the official CLI reference; re-run its help before executing because a CLI can change.

## 1. Preflight and version freeze

```powershell
$ErrorActionPreference = 'Stop'
Set-Location 'C:\Users\Robert\Documents\GitHub\LMS'
Get-Date -Format o
py -3.13 --version
uv --version
node --version
pnpm --version
corepack --version
docker version --format '{{.Server.Version}}'
docker compose version
pnpm create next-app@16.2.12 --help
uv init --help
git status --short --branch
```

Expected: Python 3.13.13, uv 0.11.19, Node v24.18.0, pnpm 10.33.2, Docker/Compose available, official CLI help exits successfully. At the present empty non-Git directory, the last command will fail; if Git initialization has been authorized, run `git init -b main` first and record it. Do not silently continue after a mismatched runtime; update the stack ADR or install a project-local supported runtime by an approved means.

## 2. Initialize the workspace and Python project

```powershell
$ErrorActionPreference = 'Stop'
Set-Location 'C:\Users\Robert\Documents\GitHub\LMS'
New-Item -ItemType Directory -Path apps -ErrorAction Stop
pnpm init
uv init --bare --python 3.13.13 apps/api
Set-Location apps/api
uv python pin 3.13.13
uv add --bounds exact Django==6.0.7 djangorestframework==3.17.1 drf-spectacular==0.30.0 psycopg[binary]==3.3.4
uv add --group dev --bounds exact ruff==0.16.0 pytest==9.1.1 pytest-django==4.12.0 pytest-cov==7.0.0 pip-audit==2.10.1
uv lock
uv sync --locked
uv run django-admin startproject config .
New-Item -ItemType Directory -Path domain -ErrorAction Stop
foreach ($app in 'identity','catalog','content','learning','assessments') { uv run python manage.py startapp $app "domain/$app" }
uv run python manage.py check
```

Expected: `apps/api/pyproject.toml`, `.python-version`, `uv.lock`, Django `config`, and five official app skeletons only. The grouping is ADR 0010; it avoids nineteen empty apps. Do not add Celery, Redis, object storage, email, Sentry, or application models until their roadmap phase.

## 3. Initialize the Next.js application and pnpm workspace

```powershell
$ErrorActionPreference = 'Stop'
Set-Location 'C:\Users\Robert\Documents\GitHub\LMS'
pnpm create next-app@16.2.12 apps/web --ts --eslint --tailwind --app --src-dir --import-alias '@/*' --use-pnpm --disable-git --yes
pnpm --dir apps/web add --save-exact next@16.2.12 react@19.2.8 react-dom@19.2.8
pnpm --dir apps/web add --save-dev --save-exact typescript@6.0.2 eslint@9.39.5 prettier@3.9.6
pnpm install --lockfile-only
pnpm --dir apps/web exec next --version
pnpm --dir apps/web exec tsc --noEmit
pnpm --dir apps/web build
```

Expected: official Next.js App Router + TypeScript + Tailwind scaffold at `apps/web`, exact runtime pins in its manifest/lockfile, a passing typecheck and production build. TS 7 was tested but rejected under ADR 0011 because the installed Next ESLint chain does not support it.

## 4. Workspace metadata and health evidence

After the official generators complete, add only the documented workspace/configuration files needed for pnpm workspace orchestration and repository policy; use the generator output as the baseline. Confirm the exact syntax locally before editing it:

```powershell
$ErrorActionPreference = 'Stop'
Set-Location 'C:\Users\Robert\Documents\GitHub\LMS'
pnpm --help
uv lock --check --directory apps/api
uv run --directory apps/api python manage.py check
pnpm --dir apps/web lint
pnpm --dir apps/web exec tsc --noEmit
pnpm --dir apps/web build
git diff --check
git status --short
```

Expected: locked Python environment, clean Django checks, explicit web lint/type/build checks, whitespace-clean diff, and a status review. `git` commands are conditional on the authorized initialization in preflight.

## Later commands deliberately excluded

Docker Compose, PostgreSQL/Redis/MinIO/Mailpit images, Celery, S3, OpenAPI client generation, shadcn, Tiptap, MathLive, MathJax, Storybook, notification providers, and observability are later phases. Their inclusion now would violate the limited scaffolding objective.
