[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        'Check',
        'Migrations',
        'Schema',
        'GenerateTypes',
        'CheckTypes',
        'GenerateClient',
        'CheckClient',
        'Test',
        'TestScoring',
        'TestConcurrency',
        'TestSecurity',
        'TestApi',
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

function Invoke-AssessmentTests([string[]]$Paths) {
    & uv run --directory $apiDirectory pytest --no-cov @Paths
    Assert-LastExitCode 'assessments pytest suite'
}

Set-Location $repositoryRoot
Import-LocalEnvironment

switch ($Action) {
    'Check' {
        Invoke-Django @('check', '--database', 'default')
        Invoke-Django @('makemigrations', '--check', '--dry-run')
        Invoke-Django @('spectacular', '--validate', '--fail-on-warn')
        & $PSScriptRoot/assessments.ps1 -Action CheckTypes
        & $PSScriptRoot/assessments.ps1 -Action CheckClient
        & rg -n --glob '!**/migrations/**' --glob '!**/generated/**' --glob '!**/tests/**' 'localStorage|sessionStorage|JWT|Bearer|AllowAny|csrf_exempt|Math\.random|float\(' apps/api/domain/assessments apps/web/src/lib/assessments apps/web/src/components/assessments
        if ($LASTEXITCODE -eq 0) { throw 'A prohibited assessments implementation marker was found.' }
        if ($LASTEXITCODE -gt 1) { throw 'Assessments prohibited-marker scan failed.' }
        & rg -n 'domain\.assessments|from domain\.assessments|@/lib/assessments' apps/api/domain/learning apps/api/domain/publishing apps/api/domain/courses apps/api/domain/content
        if ($LASTEXITCODE -eq 0) { throw 'A reverse dependency on assessments was found.' }
        if ($LASTEXITCODE -gt 1) { throw 'Assessments reverse-dependency scan failed.' }
    }
    'Migrations' {
        Invoke-Django @('showmigrations', 'assessments')
        Invoke-Django @('migrate', '--plan')
        Invoke-Django @('sqlmigrate', 'assessments', '0001')
        Invoke-Django @('sqlmigrate', 'assessments', '0002')
        Invoke-Django @('sqlmigrate', 'assessments', '0003')
        Invoke-Django @('sqlmigrate', 'assessments', '0004')
        Invoke-Django @('sqlmigrate', 'assessments', '0005')
        Invoke-Django @('makemigrations', '--check', '--dry-run')
    }
    'Schema' { Invoke-Django @('spectacular', '--validate', '--fail-on-warn') }
    'GenerateTypes' {
        & pnpm --dir $webDirectory run assessment:types:generate
        Assert-LastExitCode 'assessment type generation'
    }
    'CheckTypes' {
        & pnpm --dir $webDirectory run assessment:types:check
        Assert-LastExitCode 'assessment type drift check'
    }
    'GenerateClient' { & $PSScriptRoot/web-auth.ps1 -Action GeneratePlatformClient }
    'CheckClient' { & $PSScriptRoot/web-auth.ps1 -Action CheckPlatformClient }
    'Test' { Invoke-AssessmentTests @('domain/assessments/tests') }
    'TestScoring' { Invoke-AssessmentTests @('domain/assessments/tests/test_scoring.py') }
    'TestConcurrency' { Invoke-AssessmentTests @('domain/assessments/tests/test_concurrency.py') }
    'TestSecurity' { Invoke-AssessmentTests @('domain/assessments/tests/test_api.py', 'domain/assessments/tests/test_schemas.py') }
    'TestApi' { Invoke-AssessmentTests @('domain/assessments/tests/test_api.py') }
    'BootstrapDemo' {
        & $PSScriptRoot/learning.ps1 -Action BootstrapDemo
        Invoke-Django @('bootstrap_demo_assessments')
    }
    'Smoke' { Invoke-AssessmentTests @('domain/assessments/tests/test_api.py') }
    'E2E' { & $PSScriptRoot/web-auth.ps1 -Action E2E -Grep 'assessment phase 13' }
    'Visual' {
        & $PSScriptRoot/infrastructure.ps1 -Action Status
        & $PSScriptRoot/assessments.ps1 -Action BootstrapDemo
        Write-Host 'Authoring URL: http://127.0.0.1:3000/organizaciones/organizacion-demo/evaluaciones'
        Write-Host 'Learner URL: http://127.0.0.1:3000/organizaciones/organizacion-demo/evaluaciones/asignadas'
        Write-Host 'Delivery URL: http://127.0.0.1:3000/organizaciones/organizacion-demo/evaluaciones/entregas'
        Write-Host 'Use pnpm dev:start and inspect these routes in Chromium at desktop and 390 px.'
    }
}
