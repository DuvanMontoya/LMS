[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Build', 'Up', 'Status', 'Logs', 'Smoke', 'Down')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$environmentFile = Join-Path $repositoryRoot 'infrastructure/local/.env'
$compose = @(
    '--project-directory', $repositoryRoot,
    '--env-file', $environmentFile,
    '-f', (Join-Path $repositoryRoot 'compose.yaml'),
    '-f', (Join-Path $repositoryRoot 'compose.lock.yaml'),
    '--profile', 'media'
)

function Assert-LastExitCode([string]$Operation) {
    if ($LASTEXITCODE -ne 0) { throw "$Operation failed with exit code $LASTEXITCODE." }
}

if (-not (Test-Path -LiteralPath $environmentFile)) {
    throw 'Missing infrastructure/local/.env. Run pnpm infra:init first.'
}
Set-Location $repositoryRoot
switch ($Action) {
    'Build' {
        & docker compose @compose build media-worker
        Assert-LastExitCode 'media worker build'
    }
    'Up' {
        & docker compose @compose up --detach --wait --wait-timeout 180 postgres redis localstack clamav media-worker
        Assert-LastExitCode 'media services startup'
    }
    'Status' {
        & docker compose @compose ps localstack clamav media-worker
        Assert-LastExitCode 'media services status'
    }
    'Logs' {
        & docker compose @compose logs --tail 200 localstack clamav media-worker
        Assert-LastExitCode 'media services logs'
    }
    'Smoke' {
        & $PSScriptRoot/storage.ps1 -Action Smoke
        if (-not $?) { throw 'storage smoke failed.' }
        & docker compose @compose exec -T clamav clamdscan --ping 1
        Assert-LastExitCode 'ClamAV ping'
        & docker compose @compose exec -T media-worker /opt/ffmpeg/bin/ffmpeg -version
        Assert-LastExitCode 'FFmpeg version'
        & docker compose @compose exec -T media-worker celery -A config inspect ping --timeout=5
        Assert-LastExitCode 'media worker ping'
    }
    'Down' {
        & docker compose @compose stop media-worker clamav localstack
        Assert-LastExitCode 'media services stop'
    }
}
