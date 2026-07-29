[CmdletBinding()]
param([switch]$WithDatabase)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repositoryRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repositoryRoot

& "$PSScriptRoot/infrastructure.ps1" -Action Validate
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

foreach ($script in @('check', 'web:test', 'web:build', 'web:test:e2e')) {
    Write-Host "== pnpm run $script =="
    pnpm run $script
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($WithDatabase) {
    foreach ($script in @('api:database:check', 'auth:check', 'auth:spec', 'api:test', 'api:test:migrations')) {
        Write-Host "== pnpm run $script =="
        pnpm run $script
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

git diff --check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host 'Static quality, migration and Compose checks completed.'
