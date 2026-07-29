[CmdletBinding()]
param([Parameter(Mandatory = $true)][ValidateSet('Check','Migrations','Test','TestModels','TestTree','TestGraphs','TestConcurrency','Schema','GenerateClient','CheckClient','BootstrapDemo','Smoke','E2E','Visual')][string]$Action)
$ErrorActionPreference = 'Stop'; Set-StrictMode -Version Latest
$root = Split-Path -Parent $PSScriptRoot
$environmentFile = Join-Path $root 'infrastructure/local/.env'
function Import-LocalEnvironment {
  foreach ($line in Get-Content -LiteralPath $environmentFile) {
    if ($line -match '^(?<key>[^#=]+)=(?<value>.+)$') { [Environment]::SetEnvironmentVariable($matches.key, $matches.value, 'Process') }
  }
}
Import-LocalEnvironment
switch ($Action) {
  'Check' { & $PSScriptRoot/django.ps1 -Action Check -WithDatabase; & $PSScriptRoot/django.ps1 -Action MakeMigrationsCheck; & $PSScriptRoot/organizations.ps1 -Action CheckClient }
  'Migrations' { & $PSScriptRoot/django.ps1 -Action ShowMigrations; & $PSScriptRoot/django.ps1 -Action MigrationPlan }
  'Test' { & $PSScriptRoot/django.ps1 -Action Test }
  'TestModels' { & uv run --directory (Join-Path $root 'apps/api') pytest --no-cov domain/catalog/tests/test_services.py }
  'TestTree' { & uv run --directory (Join-Path $root 'apps/api') pytest --no-cov domain/catalog/tests/test_services.py -k 'topic or tree' }
  'TestGraphs' { & uv run --directory (Join-Path $root 'apps/api') pytest --no-cov domain/catalog/tests/test_services.py -k 'prerequisite or cycle' }
  'TestConcurrency' { & uv run --directory (Join-Path $root 'apps/api') pytest --no-cov domain/catalog/tests/test_concurrency.py }
  'Schema' { & $PSScriptRoot/organizations.ps1 -Action Schema }
  'GenerateClient' { & $PSScriptRoot/organizations.ps1 -Action GenerateClient }
  'CheckClient' { & $PSScriptRoot/organizations.ps1 -Action CheckClient }
  'BootstrapDemo' { & $PSScriptRoot/organizations.ps1 -Action Demo -DemoPassword 'DemoLms!2026Organization'; & uv run --directory (Join-Path $root 'apps/api') python manage.py bootstrap_demo_curriculum }
  'Smoke' { & $PSScriptRoot/django.ps1 -Action Check -WithDatabase }
  'E2E' { & $PSScriptRoot/organizations.ps1 -Action E2E }
  'Visual' { & $PSScriptRoot/organizations.ps1 -Action E2E }
}
