[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Check', 'Migrations', 'Test', 'Schema', 'Dispatch', 'Replay', 'DeadLetters', 'Smoke', 'OperationalCheck', 'Demo')]
    [string]$Action,
    [string]$OrganizationSlug,
    [string]$Consumer,
    [string]$Actor,
    [string]$Reason
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
    'Check' { & uv run --directory apps/api ruff check domain/events config/observability; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'Migrations' { & pwsh -NoProfile -File scripts/django.ps1 -Action MakeMigrationsCheck; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'Test' { Import-LocalEnvironment; & uv run --directory apps/api pytest domain/events/test_events.py --no-cov; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'Schema' { & pwsh -NoProfile -File scripts/organizations.ps1 -Action Schema; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'Dispatch' { Import-LocalEnvironment; & uv run --directory apps/api python manage.py dispatch_pending_events; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'DeadLetters' { Import-LocalEnvironment; & uv run --directory apps/api python manage.py list_dead_event_deliveries; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'Replay' {
        if ([string]::IsNullOrWhiteSpace($OrganizationSlug) -or [string]::IsNullOrWhiteSpace($Consumer) -or [string]::IsNullOrWhiteSpace($Actor) -or [string]::IsNullOrWhiteSpace($Reason)) { throw 'Replay requires organization, consumer, actor UUID and reason.' }
        Import-LocalEnvironment
        & uv run --directory apps/api python manage.py request_event_replay --organization $OrganizationSlug --consumer $Consumer --actor $Actor --reason $Reason
        if ($LASTEXITCODE) { exit $LASTEXITCODE }
    }
    'Smoke' { Import-LocalEnvironment; & uv run --directory apps/api pytest domain/events/test_events.py -q --no-cov; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'Demo' { Import-LocalEnvironment 'config.settings.development'; & uv run --directory apps/api python manage.py bootstrap_demo_platform_operations; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'OperationalCheck' { Import-LocalEnvironment; $env:DJANGO_SETTINGS_MODULE = 'config.settings.development'; & uv run --directory apps/api python manage.py platform_operational_check; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
}
