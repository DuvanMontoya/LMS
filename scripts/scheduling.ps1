[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Check', 'Migrations', 'Test', 'Schema', 'GenerateClient', 'CheckClient', 'E2E', 'Visual')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$apiDirectory = Join-Path $repositoryRoot 'apps/api'
$environmentFile = Join-Path $repositoryRoot 'infrastructure/local/.env'

function Assert-LastExitCode([string]$Operation) {
    if ($LASTEXITCODE -ne 0) { throw "$Operation failed with exit code $LASTEXITCODE." }
}

function Import-LocalEnvironment {
    if (-not (Test-Path -LiteralPath $environmentFile)) {
        throw 'Missing infrastructure/local/.env. Run pnpm infra:init first.'
    }
    foreach ($line in Get-Content -LiteralPath $environmentFile) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith('#')) { continue }
        $parts = $line.Split('=', 2)
        if ($parts.Count -ne 2 -or [string]::IsNullOrWhiteSpace($parts[1])) {
            throw 'The local infrastructure environment contains an invalid value.'
        }
        [Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process')
    }
    [Environment]::SetEnvironmentVariable('FRONTEND_ORIGIN', 'http://127.0.0.1:3000', 'Process')
    [Environment]::SetEnvironmentVariable('DJANGO_INTERNAL_ORIGIN', 'http://127.0.0.1:8000', 'Process')
}

function Invoke-Django([string[]]$Arguments) {
    & uv run --directory $apiDirectory python manage.py @Arguments
    Assert-LastExitCode "manage.py $($Arguments -join ' ')"
}

Set-Location $repositoryRoot
Import-LocalEnvironment

switch ($Action) {
    'Check' {
        Invoke-Django @('check', '--database', 'default')
        Invoke-Django @('makemigrations', '--check', '--dry-run')
        Invoke-Django @('spectacular', '--validate', '--fail-on-warn')
        & $PSScriptRoot/scheduling.ps1 -Action CheckClient
    }
    'Migrations' {
        Invoke-Django @('showmigrations', 'scheduling')
        Invoke-Django @('migrate', '--plan')
        Invoke-Django @('sqlmigrate', 'scheduling', '0001')
        Invoke-Django @('makemigrations', '--check', '--dry-run')
    }
    'Test' {
        & uv run --directory $apiDirectory pytest --no-cov domain/scheduling/tests
        Assert-LastExitCode 'scheduling pytest suite'
    }
    'Schema' { Invoke-Django @('spectacular', '--validate', '--fail-on-warn') }
    'GenerateClient' { & $PSScriptRoot/web-auth.ps1 -Action GeneratePlatformClient }
    'CheckClient' { & $PSScriptRoot/web-auth.ps1 -Action CheckPlatformClient }
    'E2E' { & $PSScriptRoot/web-auth.ps1 -Action E2E -Grep 'academic scheduling' }
    'Visual' {
        Write-Host 'Calendar URL: http://127.0.0.1:3000/organizaciones/organizacion-demo/calendario'
        Write-Host 'A live-class route is obtained from the calendar event detail.'
    }
}
