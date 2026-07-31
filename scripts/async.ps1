[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Build', 'Up', 'Status', 'Logs', 'Smoke', 'DomainSmoke', 'Down')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$apiDirectory = Join-Path $repositoryRoot 'apps/api'
$environmentFile = Join-Path $repositoryRoot 'infrastructure/local/.env'
$composeArguments = @(
    '--project-directory',
    $repositoryRoot,
    '--env-file',
    $environmentFile,
    '-f',
    (Join-Path $repositoryRoot 'compose.yaml'),
    '-f',
    (Join-Path $repositoryRoot 'compose.lock.yaml'),
    '--profile',
    'async'
)

function Assert-LastExitCode([string]$Operation) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Operation failed with exit code $LASTEXITCODE."
    }
}

if (-not (Test-Path -LiteralPath $environmentFile)) {
    throw 'Missing infrastructure/local/.env. Run pnpm infra:init first.'
}

Set-Location $repositoryRoot

switch ($Action) {
    'Build' {
        & docker compose @composeArguments build assessment-worker
        Assert-LastExitCode 'assessment worker build'
    }
    'Up' {
        & $PSScriptRoot/async.ps1 -Action Build
        & docker compose @composeArguments up -d --wait assessment-worker
        Assert-LastExitCode 'assessment worker startup'
    }
    'Status' {
        & docker compose @composeArguments ps assessment-worker
        Assert-LastExitCode 'assessment worker status'
    }
    'Logs' {
        & docker compose @composeArguments logs --tail 200 assessment-worker
        Assert-LastExitCode 'assessment worker logs'
    }
    'Smoke' {
        & docker compose @composeArguments exec -T assessment-worker `
            celery -A config inspect ping --timeout=5
        Assert-LastExitCode 'assessment worker broker smoke'
    }
    'DomainSmoke' {
        foreach ($line in Get-Content -LiteralPath $environmentFile) {
            if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith('#')) { continue }
            $parts = $line.Split('=', 2)
            if ($parts.Count -ne 2 -or [string]::IsNullOrWhiteSpace($parts[1])) {
                throw 'The local infrastructure environment contains an invalid value.'
            }
            [Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process')
        }
        & uv run --directory $apiDirectory python manage.py smoke_async_assessments
        Assert-LastExitCode 'assessment worker domain smoke'
    }
    'Down' {
        & docker compose @composeArguments stop assessment-worker
        Assert-LastExitCode 'assessment worker stop'
        & docker compose @composeArguments rm -f assessment-worker
        Assert-LastExitCode 'assessment worker removal'
    }
}
