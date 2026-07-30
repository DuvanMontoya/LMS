[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Check', 'Migrations', 'Test', 'TestPolicies', 'TestConcurrency', 'Schema', 'GenerateClient', 'CheckClient', 'Smoke', 'E2E', 'Bootstrap', 'Demo')]
    [string]$Action,
    [string]$Name,
    [string]$Slug,
    [string]$OwnerEmail,
    [string]$DemoPassword
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$apiDirectory = Join-Path $repositoryRoot 'apps/api'
$environmentFile = Join-Path $repositoryRoot 'infrastructure/local/.env'

function Assert-LastExitCode([string]$Operation) {
    if ($LASTEXITCODE -ne 0) { throw "$Operation failed with exit code $LASTEXITCODE." }
}

function Import-LocalInfrastructureEnvironment {
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

function Invoke-OrganizationTests([string[]]$Paths) {
    & uv run --directory $apiDirectory pytest --no-cov @Paths
    Assert-LastExitCode 'organization pytest suite'
}

Set-Location $repositoryRoot
Import-LocalInfrastructureEnvironment

switch ($Action) {
    'Check' {
        Invoke-Django @('check', '--database', 'default')
        Invoke-Django @('makemigrations', '--check', '--dry-run')
        Invoke-Django @('spectacular', '--validate', '--fail-on-warn')
        & $PSScriptRoot/organizations.ps1 -Action CheckClient
        & rg -n --glob '!**/migrations/**' --glob '!**/openapi/**' --glob '!**/generated/**' --glob '!**/.next/**' --glob '!**/node_modules/**' --glob '!**/public/vendor/**' 'django-guardian|csrf_exempt|Authorization|Bearer|localStorage|sessionStorage|JWT' apps/api apps/web/src
        if ($LASTEXITCODE -eq 0) { throw 'A prohibited authorization/storage marker was found.' }
        if ($LASTEXITCODE -gt 1) { throw 'Security marker scan failed.' }
    }
    'Migrations' {
        Invoke-Django @('showmigrations', 'organizations')
        Invoke-Django @('migrate', '--plan')
        Invoke-Django @('sqlmigrate', 'organizations', '0001')
    }
    'Test' { Invoke-OrganizationTests @('domain/organizations/tests') }
    'TestPolicies' { Invoke-OrganizationTests @('domain/organizations/tests/test_policies.py') }
    'TestConcurrency' { Invoke-OrganizationTests @('domain/organizations/tests/test_concurrency.py') }
    'Schema' { Invoke-Django @('spectacular', '--validate', '--fail-on-warn') }
    'GenerateClient' { & $PSScriptRoot/web-auth.ps1 -Action GeneratePlatformClient }
    'CheckClient' { & $PSScriptRoot/web-auth.ps1 -Action CheckPlatformClient }
    'Smoke' { Invoke-OrganizationTests @('domain/organizations/tests/test_api.py') }
    'E2E' { & $PSScriptRoot/web-auth.ps1 -Action E2E }
    'Bootstrap' {
        if ([string]::IsNullOrWhiteSpace($Name) -or [string]::IsNullOrWhiteSpace($Slug) -or [string]::IsNullOrWhiteSpace($OwnerEmail)) {
            throw 'Bootstrap requires -Name, -Slug and -OwnerEmail.'
        }
        Invoke-Django @('bootstrap_organization', '--name', $Name, '--slug', $Slug, '--owner-email', $OwnerEmail)
    }
    'Demo' {
        if ([string]::IsNullOrWhiteSpace($DemoPassword)) {
            throw 'Demo requires -DemoPassword and only runs with local DEBUG=True.'
        }
        Invoke-Django @('bootstrap_demo_organizations', '--password', $DemoPassword)
    }
}
