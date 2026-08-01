[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Check', 'Migrations', 'Test', 'Schema', 'Rebuild', 'Status', 'Smoke', 'E2E', 'Visual')]
    [string]$Action,
    [string]$OrganizationSlug
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root 'infrastructure/local/.env'

function Import-LocalEnvironment([string]$Settings = 'config.settings.test') {
    foreach ($line in Get-Content -LiteralPath $envFile) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith('#')) { continue }
        $parts = $line.Split('=', 2)
        [Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process')
    }
    $env:DJANGO_SETTINGS_MODULE = $Settings
}

Set-Location $root
switch ($Action) {
    'Check' { & uv run --directory apps/api ruff check domain/discovery; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'Migrations' { & pwsh -NoProfile -File scripts/django.ps1 -Action MakeMigrationsCheck; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'Test' { Import-LocalEnvironment; & uv run --directory apps/api pytest domain/discovery/test_discovery.py --no-cov; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'Schema' { & pwsh -NoProfile -File scripts/organizations.ps1 -Action Schema; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'Rebuild' {
        if ([string]::IsNullOrWhiteSpace($OrganizationSlug)) { throw 'Rebuild requires -OrganizationSlug.' }
        Import-LocalEnvironment 'config.settings.development'
        & uv run --directory apps/api python manage.py rebuild_search_index --organization $OrganizationSlug
        if ($LASTEXITCODE) { exit $LASTEXITCODE }
    }
    'Status' { Import-LocalEnvironment 'config.settings.development'; & uv run --directory apps/api python manage.py platform_operational_check; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'Smoke' { Import-LocalEnvironment; & uv run --directory apps/api pytest domain/discovery/test_discovery.py -q --no-cov; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'E2E' { & pwsh -NoProfile -File scripts/web-auth.ps1 -Action E2E -Grep 'platform operations'; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'Visual' { & pwsh -NoProfile -File scripts/web-auth.ps1 -Action E2E -Grep 'platform operations visual'; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
}
