[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('GenerateOpenApi', 'Build', 'Check', 'Serve')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$apiDirectory = Join-Path $repositoryRoot 'apps/api'
$documentationDirectory = Join-Path $repositoryRoot 'documentation'
$configurationFile = Join-Path $documentationDirectory 'zensical.toml'
$schemaFile = Join-Path $documentationDirectory 'docs/api/schema.yaml'
$environmentFile = Join-Path $repositoryRoot 'infrastructure/local/.env'

function Assert-LastExitCode([string]$Operation) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Operation failed with exit code $LASTEXITCODE."
    }
}

function Import-LocalInfrastructureEnvironment {
    if (-not (Test-Path -LiteralPath $environmentFile)) {
        throw 'Missing infrastructure/local/.env. Run pnpm infra:init before generating the local OpenAPI schema.'
    }

    foreach ($line in Get-Content -LiteralPath $environmentFile) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith('#')) {
            continue
        }
        $parts = $line.Split('=', 2)
        if ($parts.Count -ne 2 -or [string]::IsNullOrWhiteSpace($parts[1])) {
            throw 'The local infrastructure environment contains an invalid value.'
        }
        [Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process')
    }
    [Environment]::SetEnvironmentVariable(
        'DJANGO_SETTINGS_MODULE', 'config.settings.development', 'Process'
    )
}

function Invoke-OpenApiGeneration {
    Import-LocalInfrastructureEnvironment
    & uv run --directory $apiDirectory python manage.py spectacular `
        --file $schemaFile --validate --fail-on-warn
    Assert-LastExitCode 'OpenAPI generation and validation'
}

function Invoke-DocumentationAssetSync {
    & node (Join-Path $repositoryRoot 'scripts/sync-documentation-assets.mjs')
    Assert-LastExitCode 'Documentation asset synchronization'
}

function Invoke-Zensical([string[]]$Arguments) {
    Invoke-DocumentationAssetSync
    & uv run --directory $apiDirectory --group docs zensical @Arguments `
        --config-file $configurationFile
    Assert-LastExitCode "zensical $($Arguments -join ' ')"
}

switch ($Action) {
    'GenerateOpenApi' { Invoke-OpenApiGeneration }
    'Build' {
        Invoke-OpenApiGeneration
        Invoke-Zensical @('build', '--clean', '--strict')
    }
    'Check' {
        Invoke-OpenApiGeneration
        Invoke-Zensical @('build', '--clean', '--strict')
    }
    'Serve' {
        Invoke-OpenApiGeneration
        Invoke-Zensical @('serve', '--dev-addr', '127.0.0.1:8100')
    }
}
