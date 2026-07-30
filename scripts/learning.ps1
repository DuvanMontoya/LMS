[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        'Check',
        'Migrations',
        'Test',
        'TestModels',
        'TestEnrollments',
        'TestProgress',
        'TestContinuity',
        'TestConcurrency',
        'TestSecurity',
        'TestApi',
        'Schema',
        'GenerateClient',
        'CheckClient',
        'BootstrapDemo',
        'Smoke',
        'E2E',
        'Visual'
    )]
    [string]$Action
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$apiDirectory = Join-Path $repositoryRoot 'apps/api'
$webDirectory = Join-Path $repositoryRoot 'apps/web'
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

function Invoke-LearningTests([string[]]$Paths) {
    & uv run --directory $apiDirectory pytest --no-cov @Paths
    Assert-LastExitCode 'learning pytest suite'
}

Set-Location $repositoryRoot
Import-LocalEnvironment

switch ($Action) {
    'Check' {
        Invoke-Django @('check', '--database', 'default')
        Invoke-Django @('makemigrations', '--check', '--dry-run')
        Invoke-Django @('spectacular', '--validate', '--fail-on-warn')
        & $PSScriptRoot/learning.ps1 -Action CheckClient
        & rg -n --glob '!**/migrations/**' --glob '!**/generated/**' --glob '!**/tests/**' 'localStorage|sessionStorage|JWT|Bearer|AllowAny|csrf_exempt|CourseRevision|CourseUnit|UnitContent' apps/api/domain/learning apps/web/src/lib/learning apps/web/src/components/learning
        if ($LASTEXITCODE -eq 0) { throw 'A prohibited learning implementation marker was found.' }
        if ($LASTEXITCODE -gt 1) { throw 'Learning prohibited-marker scan failed.' }
    }
    'Migrations' {
        Invoke-Django @('showmigrations', 'learning')
        Invoke-Django @('migrate', '--plan')
        Invoke-Django @('sqlmigrate', 'learning', '0001')
        Invoke-Django @('sqlmigrate', 'learning', '0002')
        Invoke-Django @('sqlmigrate', 'learning', '0003')
        Invoke-Django @('makemigrations', '--check', '--dry-run')
    }
    'Test' { Invoke-LearningTests @('domain/learning/tests') }
    'TestModels' { Invoke-LearningTests @('domain/learning/tests/test_models.py') }
    'TestEnrollments' { Invoke-LearningTests @('domain/learning/tests/test_services.py') }
    'TestProgress' { Invoke-LearningTests @('domain/learning/tests/test_services.py') }
    'TestContinuity' { Invoke-LearningTests @('domain/learning/tests/test_services.py') }
    'TestConcurrency' { Invoke-LearningTests @('domain/learning/tests/test_concurrency.py') }
    'TestSecurity' { Invoke-LearningTests @('domain/learning/tests/test_api.py', 'domain/learning/tests/test_models.py') }
    'TestApi' { Invoke-LearningTests @('domain/learning/tests/test_api.py') }
    'Schema' { Invoke-Django @('spectacular', '--validate', '--fail-on-warn') }
    'GenerateClient' { & $PSScriptRoot/web-auth.ps1 -Action GeneratePlatformClient }
    'CheckClient' { & $PSScriptRoot/web-auth.ps1 -Action CheckPlatformClient }
    'BootstrapDemo' {
        & $PSScriptRoot/publishing.ps1 -Action BootstrapDemo
        Invoke-Django @('bootstrap_demo_learning')
    }
    'Smoke' {
        Invoke-LearningTests @('domain/learning/tests/test_api.py')
    }
    'E2E' { & $PSScriptRoot/web-auth.ps1 -Action E2E -Grep 'learning delivery' }
    'Visual' {
        & $PSScriptRoot/infrastructure.ps1 -Action Status
        & $PSScriptRoot/learning.ps1 -Action BootstrapDemo
        Write-Host 'Student URL: http://127.0.0.1:3000/organizaciones/organizacion-demo/aprendizaje'
        Write-Host 'Cohorts URL: http://127.0.0.1:3000/organizaciones/organizacion-demo/aprendizaje/cohortes'
        Write-Host 'Use pnpm dev:start and inspect these routes in Chromium.'
    }
}
