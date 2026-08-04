[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Validate', 'Pull', 'Up', 'Status', 'Smoke', 'Dashboards', 'Logs', 'Traces', 'Metrics', 'Down')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root 'infrastructure/local/.env'
$compose = @('--project-directory', $root, '--env-file', $envFile, '-f', (Join-Path $root 'compose.yaml'), '-f', (Join-Path $root 'compose.lock.yaml'), '--profile', 'observability')
$services = @('otel-collector', 'prometheus', 'jaeger', 'loki', 'grafana')

function Invoke-Compose([string[]]$Arguments) {
    & docker compose @compose @Arguments
    if ($LASTEXITCODE -ne 0) { throw "docker compose failed: $($Arguments -join ' ')" }
}

function Assert-Http([string]$Uri, [int]$ReadyTimeoutSeconds = 30) {
    $deadline = (Get-Date).AddSeconds($ReadyTimeoutSeconds)
    $lastFailure = $null
    do {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 10
            if ($response.StatusCode -eq 200) { return }
            $lastFailure = "HTTP $($response.StatusCode)"
        }
        catch {
            $lastFailure = $_.Exception.Message
        }
        if ((Get-Date) -lt $deadline) { Start-Sleep -Seconds 1 }
    } while ((Get-Date) -lt $deadline)
    throw "Unhealthy endpoint after $ReadyTimeoutSeconds seconds: $Uri. Last response: $lastFailure"
}

function Get-GrafanaHeaders {
    $username = [Environment]::GetEnvironmentVariable('GRAFANA_ADMIN_USER', 'Process')
    $password = [Environment]::GetEnvironmentVariable('GRAFANA_ADMIN_PASSWORD', 'Process')
    if ([string]::IsNullOrWhiteSpace($username) -or [string]::IsNullOrWhiteSpace($password)) { throw 'Grafana admin credentials are required in the local env file.' }
    $token = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${username}:$password"))
    return @{ Authorization = "Basic $token" }
}

function Import-LocalEnvironment {
    foreach ($line in Get-Content -LiteralPath $envFile) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith('#')) { continue }
        $parts = $line.Split('=', 2)
        [Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process')
    }
    $env:DJANGO_SETTINGS_MODULE = 'config.settings.development'
    $env:OTEL_EXPORTER_OTLP_ENDPOINT = 'http://127.0.0.1:4317'
}

Set-Location $root
switch ($Action) {
    'Validate' {
        Invoke-Compose @('config', '--quiet')
        Get-ChildItem -File infrastructure/observability/grafana/dashboards -Filter '*.json' |
            ForEach-Object { Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json | Out-Null }
        Write-Host 'Observability Compose and dashboard JSON validate.'
    }
    'Pull' { Invoke-Compose (@('pull') + $services) }
    'Up' {
        New-Item -ItemType Directory -Path (Join-Path $root 'apps/api/.local/observability') -Force | Out-Null
        Invoke-Compose (@('up', '--detach', '--wait', '--wait-timeout', '180') + $services)
    }
    'Status' { Invoke-Compose (@('ps') + $services) }
    'Smoke' {
        Assert-Http 'http://127.0.0.1:9090/-/ready'
        Assert-Http 'http://127.0.0.1:16686/'
        Assert-Http 'http://127.0.0.1:3100/ready'
        Assert-Http 'http://127.0.0.1:3001/api/health'
        Import-LocalEnvironment
        & uv run --directory apps/api python manage.py emit_observability_smoke
        if ($LASTEXITCODE -ne 0) { throw 'OTLP SDK smoke failed.' }
        $nanoseconds = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() * 1000000
        $logPayload = @{
            resourceLogs = @(@{
                resource = @{ attributes = @(@{ key = 'service.name'; value = @{ stringValue = 'lms-smoke' } }) }
                scopeLogs = @(@{ scope = @{ name = 'lms.observability.smoke' }; logRecords = @(@{ timeUnixNano = [string]$nanoseconds; severityText = 'INFO'; body = @{ stringValue = 'observability_smoke' }; attributes = @(@{ key = 'outcome'; value = @{ stringValue = 'pass' } }) }) })
            })
        } | ConvertTo-Json -Depth 12 -Compress
        Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:4318/v1/logs' -ContentType 'application/json' -Body $logPayload -TimeoutSec 10 | Out-Null
        $deadline = (Get-Date).AddSeconds(30)
        do {
            $traceResponse = Invoke-RestMethod -Uri 'http://127.0.0.1:16686/api/traces?service=lms-api&operation=lms.observability.smoke&limit=1' -TimeoutSec 10
            $metricResponse = Invoke-RestMethod -Uri 'http://127.0.0.1:9090/api/v1/query?query=lms_observability_smoke_total' -TimeoutSec 10
            $encodedQuery = [Uri]::EscapeDataString('{service_name="lms-smoke"}')
            $logResponse = Invoke-RestMethod -Uri "http://127.0.0.1:3100/loki/api/v1/query_range?query=$encodedQuery&limit=1" -TimeoutSec 10
            $complete = @($traceResponse.data).Count -gt 0 -and @($metricResponse.data.result).Count -gt 0 -and @($logResponse.data.result).Count -gt 0
            if (-not $complete) { Start-Sleep -Seconds 1 }
        } while (-not $complete -and (Get-Date) -lt $deadline)
        if (-not $complete) { throw 'Trace, metric or log did not reach the local backends.' }
        Write-Host 'Collector, Prometheus, Jaeger, Loki and Grafana passed an end-to-end telemetry smoke.'
    }
    'Dashboards' {
        Import-LocalEnvironment
        $headers = Get-GrafanaHeaders
        $response = Invoke-RestMethod -Uri 'http://127.0.0.1:3001/api/search?type=dash-db' -Headers $headers -TimeoutSec 10
        if (@($response).Count -lt 5) { throw 'Expected at least five provisioned dashboards.' }
        $datasources = Invoke-RestMethod -Uri 'http://127.0.0.1:3001/api/datasources' -Headers $headers -TimeoutSec 10
        if (@($datasources).Count -ne 3) { throw 'Expected three provisioned Grafana datasources.' }
        Write-Host 'Grafana dashboards and datasources are provisioned.'
    }
    'Logs' { Assert-Http 'http://127.0.0.1:3100/ready'; Invoke-RestMethod -Uri 'http://127.0.0.1:3100/loki/api/v1/labels' -TimeoutSec 10 | Out-Null; Write-Host 'Loki query API is ready.' }
    'Traces' { $response = Invoke-RestMethod -Uri 'http://127.0.0.1:16686/api/services' -TimeoutSec 10; if ($null -eq $response.data) { throw 'Jaeger query API unavailable.' }; Write-Host 'Jaeger query API is ready.' }
    'Metrics' {
        $targets = Invoke-RestMethod -Uri 'http://127.0.0.1:9090/api/v1/targets' -TimeoutSec 10
        $rules = Invoke-RestMethod -Uri 'http://127.0.0.1:9090/api/v1/rules' -TimeoutSec 10
        if ($targets.status -ne 'success' -or $rules.status -ne 'success') { throw 'Prometheus targets or rules unavailable.' }
        Write-Host 'Prometheus targets and alert rules are loaded.'
    }
    'Down' { Invoke-Compose (@('stop') + $services) }
}
