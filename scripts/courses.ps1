[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        'Check',
        'Migrations',
        'Test',
        'TestModels',
        'TestOrdering',
        'TestWorkflow',
        'TestConcurrency',
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

function Invoke-CourseTests([string[]]$Paths) {
    & uv run --directory $apiDirectory pytest --no-cov @Paths
    Assert-LastExitCode 'courses pytest suite'
}

Set-Location $repositoryRoot
Import-LocalEnvironment

switch ($Action) {
    'Check' {
        Invoke-Django @('check', '--database', 'default')
        Invoke-Django @('makemigrations', '--check', '--dry-run')
        Invoke-Django @('spectacular', '--validate', '--fail-on-warn')
        & $PSScriptRoot/courses.ps1 -Action CheckClient
        & rg -n --glob '!**/migrations/**' --glob '!**/openapi/**' --glob '!**/generated/**' 'django-fsm|viewflow|django-ordered-model|orderable|drag.{0,8}drop|localStorage|sessionStorage|JWT|Bearer' apps/api/domain/courses apps/web/src/components/courses apps/web/src/lib/courses
        if ($LASTEXITCODE -eq 0) { throw 'A prohibited dependency, state machine, storage, or token marker was found.' }
        if ($LASTEXITCODE -gt 1) { throw 'Courses prohibited-marker scan failed.' }
    }
    'Migrations' {
        Invoke-Django @('showmigrations', 'courses')
        Invoke-Django @('migrate', '--plan')
        Invoke-Django @('sqlmigrate', 'courses', '0001')
    }
    'Test' { Invoke-CourseTests @('domain/courses/tests') }
    'TestModels' { Invoke-CourseTests @('domain/courses/tests/test_models.py') }
    'TestOrdering' { Invoke-CourseTests @('domain/courses/tests/test_ordering.py') }
    'TestWorkflow' { Invoke-CourseTests @('domain/courses/tests/test_workflow.py') }
    'TestConcurrency' { Invoke-CourseTests @('domain/courses/tests/test_concurrency.py') }
    'TestApi' { Invoke-CourseTests @('domain/courses/tests/test_api.py') }
    'Schema' { Invoke-Django @('spectacular', '--validate', '--fail-on-warn') }
    'GenerateClient' { & $PSScriptRoot/web-auth.ps1 -Action GeneratePlatformClient }
    'CheckClient' { & $PSScriptRoot/web-auth.ps1 -Action CheckPlatformClient }
    'BootstrapDemo' {
        Invoke-Django @('bootstrap_demo_curriculum')
        Invoke-Django @('bootstrap_demo_courses')
    }
    'Smoke' { Invoke-CourseTests @('domain/courses/tests/test_api.py') }
    'E2E' { & $PSScriptRoot/web-auth.ps1 -Action E2E -Grep 'course|foreign organization' }
    'Visual' {
        & $PSScriptRoot/infrastructure.ps1 -Action Status
        & $PSScriptRoot/courses.ps1 -Action BootstrapDemo
        if (Get-NetTCPConnection -State Listen -LocalPort 3000,8000 -ErrorAction SilentlyContinue) {
            throw 'Ports 3000 and 8000 must be free before courses:visual starts.'
        }
        $api = Start-Process -FilePath 'uv' -ArgumentList @('run', '--directory', $apiDirectory, 'python', 'manage.py', 'runserver', '127.0.0.1:8000', '--noreload') -PassThru -WindowStyle Hidden
        $web = Start-Process -FilePath 'pnpm.cmd' -ArgumentList @('--dir', (Join-Path $repositoryRoot 'apps/web'), 'run', 'dev') -PassThru -WindowStyle Hidden
        try {
            Write-Host 'Visual review URL: http://127.0.0.1:3000/organizaciones/organizacion-demo/cursos'
            Write-Host 'Press Ctrl+C to stop only the API and web processes started by this command.'
            Wait-Process -Id $api.Id, $web.Id
        }
        finally {
            foreach ($process in @($api, $web)) {
                if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
            }
        }
    }
}
