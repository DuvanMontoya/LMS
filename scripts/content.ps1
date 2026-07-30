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
        'TestSchema',
        'TestVersioning',
        'TestReadiness',
        'TestSecurity',
        'TestMath',
        'TestEditor',
        'SchemaApi',
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

function Invoke-ContentTests([string[]]$Paths) {
    & uv run --directory $apiDirectory pytest --no-cov @Paths
    Assert-LastExitCode 'content pytest suite'
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
        & $PSScriptRoot/content.ps1 -Action Schema
        & $PSScriptRoot/content.ps1 -Action CheckTypes
        & $PSScriptRoot/content.ps1 -Action CheckClient
        Invoke-Web @('content:assets:check')
        & rg -n --glob '!**/*.test.*' --glob '!**/tests/**' --glob '!**/generated/**' --glob '!**/public/vendor/**' 'dangerouslySetInnerHTML|innerHTML\s*=|\beval\s*\(|new Function|localStorage|sessionStorage|indexedDB|KaTeX|katex|unpkg|jsdelivr|cdnjs' apps/api/domain/content apps/web/src/components/content apps/web/src/lib/content
        if ($LASTEXITCODE -eq 0) { throw 'A prohibited content implementation marker was found.' }
        if ($LASTEXITCODE -gt 1) { throw 'Content prohibited-marker scan failed.' }
    }
    'Migrations' {
        Invoke-Django @('showmigrations', 'content')
        Invoke-Django @('migrate', '--plan')
        Invoke-Django @('sqlmigrate', 'content', '0001')
        Invoke-Django @('makemigrations', '--check', '--dry-run')
    }
    'Schema' {
        Invoke-ContentTests @('domain/content/tests/test_schema.py')
        Invoke-Web @('content:types:check')
    }
    'GenerateTypes' {
        Invoke-Web @('content:types:generate')
    }
    'CheckTypes' {
        Invoke-Web @('content:types:check')
    }
    'Test' { Invoke-ContentTests @('domain/content/tests') }
    'TestSchema' { Invoke-ContentTests @('domain/content/tests/test_schema.py') }
    'TestVersioning' {
        Invoke-ContentTests @(
            'domain/content/tests/test_versioning.py',
            'domain/content/tests/test_concurrency.py'
        )
    }
    'TestReadiness' { Invoke-ContentTests @('domain/content/tests/test_readiness.py') }
    'TestSecurity' {
        Invoke-ContentTests @(
            'domain/content/tests/test_schema.py',
            'domain/content/tests/test_api.py',
            'domain/content/tests/test_api_security.py',
            'domain/content/tests/test_permissions.py'
        )
    }
    'TestMath' {
        Invoke-Web @('test', '--', 'src/components/content/mathjax-formula.test.tsx', 'src/lib/content/schema/validator.test.ts')
    }
    'TestEditor' {
        Invoke-Web @('test', '--', 'src/components/content', 'src/lib/content')
    }
    'SchemaApi' { Invoke-Django @('spectacular', '--validate', '--fail-on-warn') }
    'GenerateClient' { & $PSScriptRoot/web-auth.ps1 -Action GeneratePlatformClient }
    'CheckClient' { & $PSScriptRoot/web-auth.ps1 -Action CheckPlatformClient }
    'BootstrapDemo' {
        Invoke-Django @('bootstrap_demo_curriculum')
        Invoke-Django @('bootstrap_demo_courses')
        Invoke-Django @('bootstrap_demo_content')
    }
    'Smoke' {
        Invoke-ContentTests @('domain/content/tests/test_api.py')
        Invoke-Web @('test', '--', 'src/components/content', 'src/lib/content')
    }
    'E2E' { & $PSScriptRoot/web-auth.ps1 -Action E2E -Grep 'semantic content' }
    'Visual' {
        & $PSScriptRoot/infrastructure.ps1 -Action Status
        & $PSScriptRoot/content.ps1 -Action BootstrapDemo
        if (Get-NetTCPConnection -State Listen -LocalPort 3000,8000 -ErrorAction SilentlyContinue) {
            throw 'Ports 3000 and 8000 must be free before content:visual starts.'
        }
        $api = Start-Process -FilePath 'uv' -ArgumentList @('run', '--directory', $apiDirectory, 'python', 'manage.py', 'runserver', '127.0.0.1:8000', '--noreload') -PassThru -WindowStyle Hidden
        $web = Start-Process -FilePath 'pnpm.cmd' -ArgumentList @('--dir', $webDirectory, 'run', 'dev') -PassThru -WindowStyle Hidden
        try {
            Write-Host 'Visual review starts at http://127.0.0.1:3000/organizaciones/organizacion-demo/cursos/introduccion-calculo-diferencial/estructura'
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
