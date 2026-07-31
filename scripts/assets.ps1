[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        'Check',
        'Migrations',
        'Test',
        'TestUploads',
        'TestSecurity',
        'TestProcessing',
        'TestContent',
        'TestPublishing',
        'TestAccess',
        'TestConcurrency',
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

function Import-Environment {
    if (-not (Test-Path -LiteralPath $environmentFile)) {
        throw 'Missing infrastructure/local/.env. Run pnpm infra:init first.'
    }
    foreach ($line in Get-Content -LiteralPath $environmentFile) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith('#')) { continue }
        $parts = $line.Split('=', 2)
        [Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process')
    }
    $settings = @{
        DJANGO_SETTINGS_MODULE = 'config.settings.development'
        FRONTEND_ORIGIN = 'http://127.0.0.1:3000'
        ASSET_S3_INTERNAL_ENDPOINT = 'http://127.0.0.1:4566'
        ASSET_S3_PUBLIC_ENDPOINT = 'http://127.0.0.1:4566'
        ASSET_S3_ACCESS_KEY_ID = 'test'
        ASSET_S3_SECRET_ACCESS_KEY = 'test'
        ASSET_S3_FORCE_PATH_STYLE = 'true'
    }
    foreach ($entry in $settings.GetEnumerator()) {
        [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, 'Process')
    }
}

function Invoke-Django([string[]]$Arguments) {
    & uv run --directory $apiDirectory python manage.py @Arguments
    Assert-LastExitCode "manage.py $($Arguments -join ' ')"
}

function Invoke-Tests([string[]]$Paths) {
    & uv run --directory $apiDirectory pytest --no-cov @Paths
    Assert-LastExitCode 'asset pytest suite'
}

Set-Location $repositoryRoot
Import-Environment
switch ($Action) {
    'Check' {
        Invoke-Django @('check', '--database', 'default')
        Invoke-Django @('makemigrations', '--check', '--dry-run')
        & uv run --directory $apiDirectory ruff check domain/assets
        Assert-LastExitCode 'asset Ruff'
        & rg -n 'public-read|AllowedOrigins\s*:\s*\[\s*"\*"|shell=True|os\.system|csrf_exempt|AllowAny|source_url|remote_url|import_url|localStorage|sessionStorage|JWT' apps/api/domain/assets apps/web/src/components/assets apps/web/src/lib/assets
        if ($LASTEXITCODE -eq 0) { throw 'A prohibited asset implementation marker was found.' }
        if ($LASTEXITCODE -gt 1) { throw 'asset security scan failed.' }
    }
    'Migrations' {
        Invoke-Django @('showmigrations', 'assets', 'content', 'publishing')
        Invoke-Django @('migrate', '--plan')
        Invoke-Django @('sqlmigrate', 'assets', '0001')
        Invoke-Django @('sqlmigrate', 'assets', '0002')
        Invoke-Django @('sqlmigrate', 'content', '0002')
        Invoke-Django @('sqlmigrate', 'content', '0003')
    }
    'Test' { Invoke-Tests @('domain/assets/tests') }
    'TestUploads' { Invoke-Tests @('domain/assets/tests/test_uploads.py', 'domain/assets/tests/test_storage_gateway.py') }
    'TestSecurity' { Invoke-Tests @('domain/assets/tests/test_security.py', 'domain/assets/tests/test_api.py') }
    'TestProcessing' { Invoke-Tests @('domain/assets/tests/test_processing.py', 'domain/assets/tests/test_formats.py') }
    'TestContent' { Invoke-Tests @('domain/content/tests') }
    'TestPublishing' { Invoke-Tests @('domain/publishing/tests') }
    'TestAccess' { Invoke-Tests @('domain/assets/tests/test_delivery.py', 'domain/learning/tests') }
    'TestConcurrency' { Invoke-Tests @('domain/assets/tests/test_concurrency.py') }
    'Schema' { Invoke-Django @('spectacular', '--validate', '--fail-on-warn') }
    'GenerateClient' { & $PSScriptRoot/web-auth.ps1 -Action GeneratePlatformClient }
    'CheckClient' { & $PSScriptRoot/web-auth.ps1 -Action CheckPlatformClient }
    'BootstrapDemo' { Invoke-Django @('bootstrap_demo_assets') }
    'Smoke' {
        & $PSScriptRoot/media.ps1 -Action Smoke
        Invoke-Django @('verify_asset_storage', '--sample', '10')
        Invoke-Django @('smoke_asset_malware')
    }
    'E2E' { & $PSScriptRoot/web-auth.ps1 -Action E2E -Grep 'academic assets' }
    'Visual' { & $PSScriptRoot/web-auth.ps1 -Action E2E -Grep 'asset visual' }
}
