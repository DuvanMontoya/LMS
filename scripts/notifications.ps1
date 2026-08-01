[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Check', 'Migrations', 'Test', 'Schema', 'EmailSmoke', 'Retry', 'E2E', 'Visual')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root 'infrastructure/local/.env'

function Import-LocalEnvironment {
    foreach ($line in Get-Content -LiteralPath $envFile) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith('#')) { continue }
        $parts = $line.Split('=', 2)
        [Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process')
    }
    $env:DJANGO_SETTINGS_MODULE = 'config.settings.test'
}

Set-Location $root
switch ($Action) {
    'Check' { & uv run --directory apps/api ruff check domain/notifications; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'Migrations' { & pwsh -NoProfile -File scripts/django.ps1 -Action MakeMigrationsCheck; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'Test' { Import-LocalEnvironment; & uv run --directory apps/api pytest domain/notifications/test_notifications.py --no-cov; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'Schema' { & pwsh -NoProfile -File scripts/organizations.ps1 -Action Schema; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'EmailSmoke' { Import-LocalEnvironment; & uv run --directory apps/api pytest domain/notifications/test_notifications.py -q --no-cov; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'Retry' { Import-LocalEnvironment; & uv run --directory apps/api python manage.py retry_due_email_deliveries; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'E2E' { & pwsh -NoProfile -File scripts/web-auth.ps1 -Action E2E -Grep 'platform operations'; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'Visual' { & pwsh -NoProfile -File scripts/web-auth.ps1 -Action E2E -Grep 'platform operations visual'; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
}
