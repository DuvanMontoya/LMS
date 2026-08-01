[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Init', 'Validate', 'Pull', 'Lock', 'Up', 'Status', 'Logs', 'Smoke', 'Restart', 'Down', 'Reset')]
    [string]$Action,
    [ValidateSet('all', 'postgres', 'redis')]
    [string]$Service = 'all',
    [switch]$ConfirmReset
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$environmentFile = Join-Path $repositoryRoot 'infrastructure/local/.env'
$composeFile = Join-Path $repositoryRoot 'compose.yaml'
$lockFile = Join-Path $repositoryRoot 'compose.lock.yaml'
$baseComposeArguments = @('--project-directory', $repositoryRoot, '--env-file', $environmentFile, '-f', $composeFile)
$lockedComposeArguments = @($baseComposeArguments + @('-f', $lockFile))

function Assert-LastExitCode([string]$Operation) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Operation failed with exit code $LASTEXITCODE."
    }
}

function Ensure-Environment {
    if (-not (Test-Path -LiteralPath $environmentFile)) {
        throw 'Missing infrastructure/local/.env. Run the Init action first.'
    }
}

function Invoke-Compose([string[]]$Arguments, [string[]]$Command) {
    & docker compose @Arguments @Command
    Assert-LastExitCode "docker compose $($Command -join ' ')"
}

function Invoke-ExpectedComposeFailure([string[]]$Arguments, [string[]]$Command) {
    & docker compose @Arguments @Command 2>$null
    if ($LASTEXITCODE -eq 0) {
        throw "Expected docker compose $($Command -join ' ') to fail."
    }
}

function Get-EnvironmentValues {
    Ensure-Environment
    $values = @{}
    foreach ($line in Get-Content -LiteralPath $environmentFile) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith('#')) { continue }
        $parts = $line.Split('=', 2)
        if ($parts.Count -ne 2 -or [string]::IsNullOrWhiteSpace($parts[1])) {
            throw 'The local infrastructure environment contains an invalid or empty value.'
        }
        $values[$parts[0]] = $parts[1]
    }
    foreach ($key in @('POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_HOST', 'POSTGRES_PORT', 'REDIS_HOST', 'REDIS_PORT', 'REDIS_PASSWORD', 'REDIS_CACHE_DB')) {
        if (-not $values.ContainsKey($key)) { throw "Missing $key in infrastructure/local/.env." }
    }
    return $values
}

function Get-ImageDigest([string]$Image, [string]$Repository) {
    $digests = docker image inspect $Image --format '{{range .RepoDigests}}{{println .}}{{end}}'
    Assert-LastExitCode "docker image inspect $Image"
    $digest = @($digests | Where-Object { $_ -like "$Repository@sha256:*" } | Select-Object -First 1)
    if ($digest.Count -ne 1) { throw "No immutable digest for $Image was found." }
    return $digest[0].Trim()
}

function Write-ImageLock {
    $postgresDigest = Get-ImageDigest 'postgres:18.4-trixie' 'postgres'
    $redisDigest = Get-ImageDigest 'redis:8.8.1-trixie' 'redis'
    $localstackDigest = Get-ImageDigest 'localstack/localstack:4.14.0' 'localstack/localstack'
    $clamavDigest = Get-ImageDigest 'clamav/clamav:1.5.3_base' 'clamav/clamav'
    $collectorDigest = Get-ImageDigest 'otel/opentelemetry-collector-contrib:0.157.0' 'otel/opentelemetry-collector-contrib'
    $prometheusDigest = Get-ImageDigest 'prom/prometheus:v3.13.2' 'prom/prometheus'
    $jaegerDigest = Get-ImageDigest 'jaegertracing/jaeger:2.20.0' 'jaegertracing/jaeger'
    $lokiDigest = Get-ImageDigest 'grafana/loki:3.7.4' 'grafana/loki'
    $grafanaDigest = Get-ImageDigest 'grafana/grafana:13.1.1' 'grafana/grafana'
    $content = @"
# Generated from approved image manifests for linux/amd64. Review before committing.
# Regenerate intentionally with: pnpm infra:lock
services:
  postgres:
    image: postgres:18.4-trixie@$($postgresDigest.Split('@', 2)[1])
  redis:
    image: redis:8.8.1-trixie@$($redisDigest.Split('@', 2)[1])
  assessment-worker:
    image: lms-assessment-worker:python-3.13.13
  localstack:
    image: localstack/localstack:4.14.0@$($localstackDigest.Split('@', 2)[1])
  clamav:
    image: clamav/clamav:1.5.3_base@$($clamavDigest.Split('@', 2)[1])
  media-worker:
    image: lms-media-worker:ffmpeg-8.1.2
  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.157.0@$($collectorDigest.Split('@', 2)[1])
  prometheus:
    image: prom/prometheus:v3.13.2@$($prometheusDigest.Split('@', 2)[1])
  jaeger:
    image: jaegertracing/jaeger:2.20.0@$($jaegerDigest.Split('@', 2)[1])
  loki:
    image: grafana/loki:3.7.4@$($lokiDigest.Split('@', 2)[1])
  grafana:
    image: grafana/grafana:13.1.1@$($grafanaDigest.Split('@', 2)[1])
"@
    Set-Content -LiteralPath $lockFile -Value $content -Encoding utf8NoBOM
    Write-Host 'Updated compose.lock.yaml from locally pulled official image digests.'
}

function Invoke-PostgresSql([string]$Sql) {
    $sqlForShell = $Sql.Replace('"', '\"')
    $command = 'PGPASSWORD="$POSTGRES_PASSWORD" psql -w -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "{0}"' -f $sqlForShell
    Invoke-Compose $lockedComposeArguments @('exec', '-T', 'postgres', 'sh', '-ec', $command)
}

function Invoke-RedisCommand([string]$Command) {
    Invoke-Compose $lockedComposeArguments @('exec', '-T', 'redis', 'sh', '-ec', "REDISCLI_AUTH=`"`$REDIS_PASSWORD`" redis-cli --no-auth-warning -h 127.0.0.1 -p 6379 $Command")
}

function Assert-NoRedisSmokeKeys {
    $remaining = & docker compose @lockedComposeArguments exec -T redis sh -ec 'REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli --no-auth-warning --scan --pattern "lms:infrastructure:smoke:*"'
    Assert-LastExitCode 'Redis smoke-key cleanup check'
    if (@($remaining | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }).Count -ne 0) {
        throw 'Redis smoke keys remain after cleanup.'
    }
}

function Invoke-DjangoConnectionSmoke([hashtable]$EnvironmentValues) {
    $keys = @('POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_HOST', 'POSTGRES_PORT', 'REDIS_HOST', 'REDIS_PORT', 'REDIS_PASSWORD', 'REDIS_CACHE_DB', 'DJANGO_SETTINGS_MODULE')
    $previous = @{}
    foreach ($key in $keys) {
        $previous[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
        $value = if ($key -eq 'DJANGO_SETTINGS_MODULE') { 'config.settings.development' } else { $EnvironmentValues[$key] }
        [Environment]::SetEnvironmentVariable($key, $value, 'Process')
    }
    try {
        & uv run --directory apps/api python -c "import django; django.setup(); from django.db import connection; cursor = connection.cursor(); cursor.execute('SELECT 1'); assert cursor.fetchone()[0] == 1"
        Assert-LastExitCode 'Django PostgreSQL connection smoke'
    }
    finally {
        foreach ($key in $keys) {
            if ($key -eq 'DJANGO_SETTINGS_MODULE') {
                [Environment]::SetEnvironmentVariable($key, $previous[$key], 'Process')
            }
            else {
                # Keep Compose interpolation deterministic for the remaining smoke steps.
                # This process exits when the action completes, so secrets do not persist in the user environment.
                [Environment]::SetEnvironmentVariable($key, $EnvironmentValues[$key], 'Process')
            }
        }
    }
}

Set-Location $repositoryRoot

switch ($Action) {
    'Init' {
        & "$PSScriptRoot/setup-local-infrastructure.ps1"
        if (-not $?) { throw 'local environment setup failed.' }
        Get-EnvironmentValues | Out-Null
        Invoke-Compose $baseComposeArguments @('config', '--quiet')
        Write-Host 'Local infrastructure environment and Compose configuration are ready. Containers remain stopped.'
    }
    'Validate' {
        Get-EnvironmentValues | Out-Null
        if (-not (Test-Path -LiteralPath $lockFile)) { throw 'Missing compose.lock.yaml.' }
        Invoke-Compose $lockedComposeArguments @('config', '--quiet')
        $images = & docker compose @lockedComposeArguments config --images
        Assert-LastExitCode 'docker compose config --images'
        if (-not ($images | Where-Object { $_ -match '^postgres:18\.4-trixie@sha256:[0-9a-f]{64}$' })) { throw 'PostgreSQL image lock is not effective.' }
        if (-not ($images | Where-Object { $_ -match '^redis:8\.8\.1-trixie@sha256:[0-9a-f]{64}$' })) { throw 'Redis image lock is not effective.' }
        $mediaImages = & docker compose @lockedComposeArguments --profile media config --images
        Assert-LastExitCode 'docker compose media config --images'
        if (-not ($mediaImages | Where-Object { $_ -match '^localstack/localstack:4\.14\.0@sha256:[0-9a-f]{64}$' })) { throw 'LocalStack image lock is not effective.' }
        if (-not ($mediaImages | Where-Object { $_ -match '^clamav/clamav:1\.5\.3_base@sha256:[0-9a-f]{64}$' })) { throw 'ClamAV image lock is not effective.' }
        $observabilityImages = & docker compose @lockedComposeArguments --profile observability config --images
        Assert-LastExitCode 'docker compose observability config --images'
        foreach ($expected in @(
            '^otel/opentelemetry-collector-contrib:0\.157\.0@sha256:[0-9a-f]{64}$',
            '^prom/prometheus:v3\.13\.2@sha256:[0-9a-f]{64}$',
            '^jaegertracing/jaeger:2\.20\.0@sha256:[0-9a-f]{64}$',
            '^grafana/loki:3\.7\.4@sha256:[0-9a-f]{64}$',
            '^grafana/grafana:13\.1\.1@sha256:[0-9a-f]{64}$'
        )) {
            if (-not ($observabilityImages | Where-Object { $_ -match $expected })) { throw "Observability image lock is not effective: $expected" }
        }
        Write-Host 'Compose configuration, required variables, and approved image locks validate.'
    }
    'Pull' {
        Get-EnvironmentValues | Out-Null
        Invoke-Compose $baseComposeArguments @('pull')
        Write-Host 'Approved exact image tags were pulled. Run Lock to review and record their current digests.'
    }
    'Lock' {
        Get-EnvironmentValues | Out-Null
        Invoke-Compose $baseComposeArguments @('pull')
        Write-ImageLock
        Invoke-Compose $lockedComposeArguments @('config', '--quiet')
    }
    'Up' {
        Get-EnvironmentValues | Out-Null
        if (-not (Test-Path -LiteralPath $lockFile)) { throw 'Missing compose.lock.yaml. Run Lock first.' }
        $targets = if ($Service -eq 'all') { @() } else { @($Service) }
        Invoke-Compose $lockedComposeArguments (@('up', '--detach', '--wait', '--wait-timeout', '90') + $targets)
    }
    'Status' {
        Get-EnvironmentValues | Out-Null
        Invoke-Compose $lockedComposeArguments @('ps')
    }
    'Logs' {
        Get-EnvironmentValues | Out-Null
        $targets = if ($Service -eq 'all') { @() } else { @($Service) }
        Invoke-Compose $lockedComposeArguments (@('logs', '--tail', '200') + $targets)
    }
    'Smoke' {
        $environmentValues = Get-EnvironmentValues
        $table = 'lms_infrastructure_smoke_persistence'
        $redisKey = 'lms:infrastructure:smoke:persistence'
        try {
            Invoke-Compose $lockedComposeArguments @('ps', '--status', 'running')
            Invoke-PostgresSql "SHOW server_version; SHOW server_encoding; SHOW TimeZone; SHOW password_encryption; SHOW data_checksums;"
            Invoke-ExpectedComposeFailure $lockedComposeArguments @('exec', '-T', 'postgres', 'sh', '-ec', 'unset PGPASSWORD; psql -w -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1"')
            Invoke-ExpectedComposeFailure $lockedComposeArguments @('exec', '-T', 'postgres', 'sh', '-ec', 'PGPASSWORD=incorrect psql -w -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1"')
            Invoke-ExpectedComposeFailure $lockedComposeArguments @('exec', '-T', 'postgres', 'sh', '-ec', 'PGPASSWORD="$POSTGRES_PASSWORD" psql -w -h 127.0.0.1 -U lms_invalid_user -d "$POSTGRES_DB" -c "SELECT 1"')
            Invoke-DjangoConnectionSmoke $environmentValues
            Invoke-PostgresSql "DROP TABLE IF EXISTS $table; CREATE TABLE $table (marker text NOT NULL); INSERT INTO $table VALUES ('persisted');"
            Invoke-Compose $lockedComposeArguments @('restart', 'postgres')
            Invoke-Compose $lockedComposeArguments @('up', '--detach', '--wait', '--wait-timeout', '90', 'postgres')
            Invoke-PostgresSql "SELECT marker FROM $table;"
            Invoke-PostgresSql "DROP TABLE IF EXISTS $table;"
            Invoke-PostgresSql "SELECT CASE WHEN to_regclass('public.$table') IS NULL THEN 'clean' ELSE 'residue' END AS smoke_table_cleanup;"

            Invoke-RedisCommand 'PING'
            Invoke-ExpectedComposeFailure $lockedComposeArguments @('exec', '-T', 'redis', 'sh', '-ec', 'redis-cli -h 127.0.0.1 -p 6379 PING 2>&1 | grep -q "NOAUTH Authentication required" && exit 1; exit 0')
            Invoke-ExpectedComposeFailure $lockedComposeArguments @('exec', '-T', 'redis', 'sh', '-ec', 'REDISCLI_AUTH=incorrect redis-cli --no-auth-warning -h 127.0.0.1 -p 6379 PING 2>&1 | grep -q WRONGPASS && exit 1; exit 0')
            $redisUser = & docker compose @lockedComposeArguments exec -T redis sh -ec 'set -- $(grep "^Uid:" /proc/1/status); test "$2" -ne 0; printf "%s\n" "$2"'
            Assert-LastExitCode 'Redis effective-service-user check'
            if ($redisUser.Trim() -eq '0') { throw 'Redis service process must not run as root.' }
            Write-Host "Redis PID 1 effective uid: $($redisUser.Trim())"
            Invoke-RedisCommand "SET $redisKey persisted"
            Start-Sleep -Seconds 2
            Invoke-Compose $lockedComposeArguments @('restart', 'redis')
            Invoke-Compose $lockedComposeArguments @('up', '--detach', '--wait', '--wait-timeout', '90', 'redis')
            Invoke-RedisCommand "GET $redisKey"
            Invoke-RedisCommand "DEL $redisKey"
            Assert-NoRedisSmokeKeys
            Write-Host 'Smoke completed: authenticated PostgreSQL/Django and Redis, persistence, restart, non-root Redis, and cleanup passed.'
        }
        finally {
            try { Invoke-PostgresSql "DROP TABLE IF EXISTS $table;" } catch { Write-Warning 'Could not clean the PostgreSQL smoke table; inspect the running service.' }
            try { Invoke-RedisCommand "DEL $redisKey" } catch { Write-Warning 'Could not clean the Redis smoke key; inspect the running service.' }
        }
    }
    'Restart' {
        Get-EnvironmentValues | Out-Null
        $targets = if ($Service -eq 'all') { @() } else { @($Service) }
        Invoke-Compose $lockedComposeArguments (@('restart') + $targets)
        Invoke-Compose $lockedComposeArguments (@('up', '--detach', '--wait', '--wait-timeout', '90') + $targets)
    }
    'Down' {
        Get-EnvironmentValues | Out-Null
        Invoke-Compose $lockedComposeArguments @('down', '--remove-orphans')
        Write-Host 'Stopped lms infrastructure without removing named volumes.'
    }
    'Reset' {
        if (-not $ConfirmReset) { throw 'Reset is destructive for lms named volumes. Re-run with -ConfirmReset.' }
        Get-EnvironmentValues | Out-Null
        Invoke-Compose $lockedComposeArguments @('down', '--volumes', '--remove-orphans')
        Write-Host 'Removed only lms Compose containers, network, and named volumes.'
    }
}
