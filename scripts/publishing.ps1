[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        'Check',
        'Migrations',
        'Schema',
        'GenerateTypes',
        'CheckTypes',
        'Test',
        'TestModels',
        'TestSnapshot',
        'TestIntegrity',
        'TestImmutability',
        'TestConcurrency',
        'TestApi',
        'SchemaApi',
        'GenerateClient',
        'CheckClient',
        'BootstrapDemo',
        'Verify',
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

function Invoke-PublishingTests([string[]]$Paths) {
    & uv run --directory $apiDirectory pytest --no-cov @Paths
    Assert-LastExitCode 'publishing pytest suite'
}

function Invoke-Web([string[]]$Arguments) {
    & pnpm --dir $webDirectory @Arguments
    Assert-LastExitCode "web $($Arguments -join ' ')"
}

Set-Location $repositoryRoot
Import-LocalEnvironment

switch ($Action) {
    'Check' {
        Invoke-Django @('check', '--database', 'default')
        Invoke-Django @('makemigrations', '--check', '--dry-run')
        Invoke-Django @('spectacular', '--validate', '--fail-on-warn')
        & $PSScriptRoot/publishing.ps1 -Action CheckTypes
        & rg -n --glob '!**/migrations/**' --glob '!**/generated/**' --glob '!**/tests/**' --glob '!**/*.test.*' 'localStorage|sessionStorage|indexedDB|dangerouslySetInnerHTML|CourseRelease\.objects\.(update|delete)|CoursePublicationEvent\.objects\.(update|delete)' apps/api/domain/publishing apps/web/src/lib/publishing apps/web/src/components/publishing
        if ($LASTEXITCODE -eq 0) { throw 'A prohibited publishing implementation marker was found.' }
        if ($LASTEXITCODE -gt 1) { throw 'Publishing prohibited-marker scan failed.' }
    }
    'Migrations' {
        Invoke-Django @('showmigrations', 'publishing')
        Invoke-Django @('migrate', '--plan')
        Invoke-Django @('sqlmigrate', 'publishing', '0001')
        Invoke-Django @('sqlmigrate', 'publishing', '0002')
        Invoke-Django @('makemigrations', '--check', '--dry-run')
    }
    'Schema' {
        Invoke-PublishingTests @('domain/publishing/tests/test_schema.py')
        & $PSScriptRoot/publishing.ps1 -Action CheckTypes
    }
    'GenerateTypes' { Invoke-Web @('publishing:types:generate') }
    'CheckTypes' { Invoke-Web @('publishing:types:check') }
    'Test' { Invoke-PublishingTests @('domain/publishing/tests') }
    'TestModels' { Invoke-PublishingTests @('domain/publishing/tests/test_services.py') }
    'TestSnapshot' { Invoke-PublishingTests @('domain/publishing/tests/test_schema.py') }
    'TestIntegrity' { Invoke-PublishingTests @('domain/publishing/tests/test_services.py') }
    'TestImmutability' { Invoke-PublishingTests @('domain/publishing/tests/test_services.py') }
    'TestConcurrency' { Invoke-PublishingTests @('domain/publishing/tests/test_concurrency.py') }
    'TestApi' { Invoke-PublishingTests @('domain/publishing/tests/test_api.py') }
    'SchemaApi' { Invoke-Django @('spectacular', '--validate', '--fail-on-warn') }
    'GenerateClient' { & $PSScriptRoot/web-auth.ps1 -Action GeneratePlatformClient }
    'CheckClient' { & $PSScriptRoot/web-auth.ps1 -Action CheckPlatformClient }
    'BootstrapDemo' {
        $courseExists = & uv run --directory $apiDirectory python manage.py shell -c "from domain.courses.models import Course; print(Course.objects.filter(organization__slug='organizacion-demo', slug='introduccion-calculo-diferencial').exists())"
        Assert-LastExitCode 'demo course presence check'
        if ($courseExists[-1].Trim() -ne 'True') {
            Invoke-Django @('bootstrap_demo_curriculum')
            Invoke-Django @('bootstrap_demo_courses')
            Invoke-Django @('bootstrap_demo_content')
        }
        Invoke-Django @('bootstrap_demo_publication')
    }
    'Verify' { Invoke-Django @('verify_course_releases') }
    'Smoke' {
        Invoke-PublishingTests @('domain/publishing/tests/test_api.py')
        Invoke-Web @('test', '--', 'src/lib/publishing')
    }
    'E2E' { & $PSScriptRoot/web-auth.ps1 -Action E2E -Grep 'immutable publication' }
    'Visual' {
        & $PSScriptRoot/infrastructure.ps1 -Action Status
        & $PSScriptRoot/publishing.ps1 -Action BootstrapDemo
        if (Get-NetTCPConnection -State Listen -LocalPort 3000,8000 -ErrorAction SilentlyContinue) {
            throw 'Ports 3000 and 8000 must be free before publishing:visual starts.'
        }
        $api = Start-Process -FilePath 'uv' -ArgumentList @('run', '--directory', $apiDirectory, 'python', 'manage.py', 'runserver', '127.0.0.1:8000', '--noreload') -PassThru -WindowStyle Hidden
        $web = Start-Process -FilePath 'pnpm.cmd' -ArgumentList @('--dir', $webDirectory, 'run', 'dev') -PassThru -WindowStyle Hidden
        try {
            Write-Host 'Publication URL: http://127.0.0.1:3000/organizaciones/organizacion-demo/cursos/introduccion-calculo-diferencial/publicacion'
            Write-Host 'Library URL: http://127.0.0.1:3000/organizaciones/organizacion-demo/biblioteca'
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
