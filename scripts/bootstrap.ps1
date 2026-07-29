$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repositoryRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repositoryRoot

if (-not (Test-Path 'infrastructure/local/.env')) {
    & "$PSScriptRoot/setup-local-infrastructure.ps1"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

uv sync --locked --directory apps/api
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

pnpm install --frozen-lockfile
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host 'Local infrastructure environment and locked dependencies are ready. No containers were started.'
