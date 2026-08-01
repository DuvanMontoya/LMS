[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Up', 'Status', 'Logs', 'Smoke', 'Down')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$environmentFile = Join-Path $repositoryRoot 'infrastructure/local/.env'
$composeFile = Join-Path $repositoryRoot 'compose.yaml'
$lockFile = Join-Path $repositoryRoot 'compose.lock.yaml'
$composeArguments = @(
    '--project-directory', $repositoryRoot,
    '--env-file', $environmentFile,
    '-f', $composeFile,
    '-f', $lockFile,
    '--profile', 'live'
)

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
    [Environment]::SetEnvironmentVariable('DJANGO_SETTINGS_MODULE', 'config.settings.development', 'Process')
}

function Invoke-Compose([string[]]$Command) {
    & docker compose @composeArguments @Command
    Assert-LastExitCode "docker compose $($Command -join ' ')"
}

Set-Location $repositoryRoot
Import-LocalEnvironment

switch ($Action) {
    'Up' {
        Invoke-Compose @('up', '--detach', 'livekit')
        Write-Host 'Self-hosted LiveKit is listening locally on ws://127.0.0.1:7880.'
    }
    'Status' { Invoke-Compose @('ps', 'livekit') }
    'Logs' { Invoke-Compose @('logs', '--tail', '200', 'livekit') }
    'Smoke' {
        $deadline = [DateTimeOffset]::UtcNow.AddSeconds(30)
        do {
            try {
                $response = Invoke-WebRequest -Uri 'http://127.0.0.1:7880' -TimeoutSec 2 -UseBasicParsing
                if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) { break }
            }
            catch {
                if ([DateTimeOffset]::UtcNow -ge $deadline) { throw }
                Start-Sleep -Milliseconds 500
            }
        } while ([DateTimeOffset]::UtcNow -lt $deadline)
        & uv run --directory apps/api python -c "import django,uuid; django.setup(); from domain.scheduling.livekit_gateway import LiveKitGateway; g=LiveKitGateway(); name='lk_smoke_'+uuid.uuid4().hex; room=g.create_room(room_name=name, metadata='{}'); assert room.name==name; g.close_room(room_name=name); print('LiveKit Room Service create/list/delete passed.')"
        Assert-LastExitCode 'LiveKit Room Service smoke'
    }
    'Down' { Invoke-Compose @('stop', 'livekit') }
}
