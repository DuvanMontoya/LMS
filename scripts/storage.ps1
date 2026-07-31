[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Validate', 'Init', 'Status', 'Smoke', 'ResetLocal')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$apiDirectory = Join-Path $repositoryRoot 'apps/api'
$environmentFile = Join-Path $repositoryRoot 'infrastructure/local/.env'

function Assert-LastExitCode([string]$Operation) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Operation failed with exit code $LASTEXITCODE."
    }
}

if (-not (Test-Path -LiteralPath $environmentFile)) {
    throw 'Missing infrastructure/local/.env. Run pnpm infra:init first.'
}

foreach ($line in Get-Content -LiteralPath $environmentFile) {
    if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith('#')) {
        continue
    }
    $parts = $line.Split('=', 2)
    if ($parts.Count -ne 2 -or [string]::IsNullOrWhiteSpace($parts[1])) {
        throw 'The local infrastructure environment contains an invalid value.'
    }
    [Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process')
}

[Environment]::SetEnvironmentVariable('DJANGO_SETTINGS_MODULE', 'config.settings.development', 'Process')
[Environment]::SetEnvironmentVariable('FRONTEND_ORIGIN', 'http://127.0.0.1:3000', 'Process')
[Environment]::SetEnvironmentVariable('ASSET_S3_INTERNAL_ENDPOINT', 'http://127.0.0.1:4566', 'Process')
[Environment]::SetEnvironmentVariable('ASSET_S3_PUBLIC_ENDPOINT', 'http://127.0.0.1:4566', 'Process')
[Environment]::SetEnvironmentVariable('ASSET_S3_ACCESS_KEY_ID', 'test', 'Process')
[Environment]::SetEnvironmentVariable('ASSET_S3_SECRET_ACCESS_KEY', 'test', 'Process')
[Environment]::SetEnvironmentVariable('ASSET_S3_FORCE_PATH_STYLE', 'true', 'Process')

$command = switch ($Action) {
    'Validate' { 'validate' }
    'Init' { 'init' }
    'Status' { 'status' }
    'Smoke' { 'smoke' }
    'ResetLocal' { 'reset-local' }
}

& uv run --directory $apiDirectory python manage.py asset_storage $command
Assert-LastExitCode "asset storage $command"
