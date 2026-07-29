$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repositoryRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repositoryRoot

function Invoke-VersionCheck([string]$Label, [scriptblock]$Command) {
    Write-Host "== $Label =="
    & $Command
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Invoke-VersionCheck 'Git' { git --version }
Invoke-VersionCheck 'Python' { py -3.13 --version }
Invoke-VersionCheck 'uv' { uv --version }
Invoke-VersionCheck 'Node.js' { node --version }
Invoke-VersionCheck 'pnpm' { pnpm --version }
Invoke-VersionCheck 'Docker' { docker --version }
Invoke-VersionCheck 'Docker Compose' { docker compose version }
Invoke-VersionCheck 'Installed Python interpreters' { uv python list }

if ((git branch --show-current) -ne 'main') { throw 'Expected Git branch main.' }
if (git remote) { throw 'No Git remote is permitted during scaffolding.' }
if (-not (Test-Path 'apps/api/uv.lock')) { throw 'Missing apps/api/uv.lock.' }
if (-not (Test-Path 'pnpm-lock.yaml')) { throw 'Missing pnpm-lock.yaml.' }
if (-not (Test-Path 'compose.yaml')) { throw 'Missing compose.yaml.' }
if (-not (Test-Path 'compose.lock.yaml')) { throw 'Missing compose.lock.yaml.' }
if (-not (Test-Path 'apps/api/domain/identity/migrations/0001_initial.py')) {
    throw 'Missing the irreversible identity.0001 initial migration.'
}
if (-not (Select-String -Path 'apps/api/config/settings/base.py' -Pattern 'AUTH_USER_MODEL = "identity.User"' -Quiet)) {
    throw 'AUTH_USER_MODEL must point to identity.User before schema work.'
}
if (-not (Select-String -Path 'apps/api/config/settings/base.py' -Pattern '"allauth.headless"' -Quiet)) {
    throw 'django-allauth headless must remain configured for the authentication phase.'
}
if (-not (Select-String -Path 'apps/api/config/settings/base.py' -Pattern 'HEADLESS_CLIENTS = \("browser",\)' -Quiet)) {
    throw 'Only the browser headless client is permitted.'
}
if (Test-Path 'apps/api/.env') { throw 'apps/api/.env must not be committed or used by this scaffold.' }
if (Test-Path 'db.sqlite3') { throw 'SQLite database is prohibited.' }

Write-Host 'Preflight completed without exposing local secrets or missing lockfiles.'
