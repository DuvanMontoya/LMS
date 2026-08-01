[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Check', 'Migrations', 'Test', 'Schema', 'EmailSmoke', 'EmailSendSmoke', 'Retry', 'E2E', 'Visual')]
    [string]$Action,

    [string]$Recipient = ''
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
    'Check' { & uv run --directory apps/api ruff check domain/notifications; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'Migrations' { & pwsh -NoProfile -File scripts/django.ps1 -Action MakeMigrationsCheck; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'Test' { Import-LocalEnvironment; & uv run --directory apps/api pytest domain/notifications/test_notifications.py --no-cov; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'Schema' { & pwsh -NoProfile -File scripts/organizations.ps1 -Action Schema; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'EmailSmoke' {
        Import-LocalEnvironment 'config.settings.development'
        $env:EMAIL_DELIVERY_MODE = 'smtp'
        & uv run --directory apps/api python manage.py check_smtp_connection
        if ($LASTEXITCODE) { exit $LASTEXITCODE }
    }
    'EmailSendSmoke' {
        if ([string]::IsNullOrWhiteSpace($Recipient)) {
            throw 'EmailSendSmoke requires -Recipient.'
        }
        Import-LocalEnvironment 'config.settings.development'
        $env:EMAIL_DELIVERY_MODE = 'smtp'
        & uv run --directory apps/api python manage.py send_smtp_test_email --to $Recipient --confirm
        if ($LASTEXITCODE) { exit $LASTEXITCODE }
    }
    'Retry' { Import-LocalEnvironment; & uv run --directory apps/api python manage.py retry_due_email_deliveries; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'E2E' { & pwsh -NoProfile -File scripts/web-auth.ps1 -Action E2E -Grep 'platform operations'; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
    'Visual' { & pwsh -NoProfile -File scripts/web-auth.ps1 -Action E2E -Grep 'platform operations visual'; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
}
