[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        'Check',
        'ProductionCheck',
        'MakeMigrationsCheck',
        'MakeMigrations',
        'MigrationPlan',
        'ShowMigrations',
        'Migrate',
        'CreateSuperuser',
        'Health',
        'Dev',
        'Test',
        'TestMigrations'
    )]
    [string]$Action,
    [string]$AppLabel,
    [switch]$WithDatabase,
    [switch]$SkipPlan
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$apiDirectory = Join-Path $repositoryRoot 'apps/api'
$environmentFile = Join-Path $repositoryRoot 'infrastructure/local/.env'
$composeArguments = @(
    '--project-directory',
    $repositoryRoot,
    '--env-file',
    $environmentFile,
    '-f',
    (Join-Path $repositoryRoot 'compose.yaml'),
    '-f',
    (Join-Path $repositoryRoot 'compose.lock.yaml')
)

function Assert-LastExitCode([string]$Operation) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Operation failed with exit code $LASTEXITCODE."
    }
}

function Import-LocalInfrastructureEnvironment {
    if (-not (Test-Path -LiteralPath $environmentFile)) {
        throw 'Missing infrastructure/local/.env. Run pnpm infra:init first.'
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
}

function Invoke-Django([string[]]$Arguments) {
    & uv run --directory $apiDirectory python manage.py @Arguments
    Assert-LastExitCode "manage.py $($Arguments -join ' ')"
}

function Assert-PostgreSQLHealthy {
    & docker compose @composeArguments ps --status running postgres | Out-Null
    Assert-LastExitCode 'PostgreSQL status check'
}

function Assert-RedisHealthy {
    & docker compose @composeArguments ps --status running redis | Out-Null
    Assert-LastExitCode 'Redis status check'
}

function Invoke-HealthRequest([string]$Uri, [string]$Method) {
    $response = Invoke-WebRequest -Uri $Uri -Method $Method -SkipHttpErrorCheck
    if ($response.StatusCode -ne 200) {
        throw "$Method $Uri returned HTTP $($response.StatusCode)."
    }
    if ($response.Headers['Cache-Control'] -ne 'no-store') {
        throw "$Method $Uri did not return Cache-Control: no-store."
    }
    return $response
}

function Invoke-TemporaryHealthServer {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    $port = ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
    $listener.Stop()

    $process = Start-Process -FilePath 'uv' -ArgumentList @(
        'run', '--directory', $apiDirectory, 'python', 'manage.py', 'runserver', "127.0.0.1:$port", '--noreload'
    ) -PassThru -WindowStyle Hidden
    try {
        $baseUri = "http://127.0.0.1:$port"
        $deadline = (Get-Date).AddSeconds(30)
        do {
            try {
                $live = Invoke-WebRequest -Uri "$baseUri/health/live/" -Method Get -TimeoutSec 2 -SkipHttpErrorCheck
                if ($live.StatusCode -eq 200) { break }
            }
            catch {
                Start-Sleep -Milliseconds 250
            }
        } while ((Get-Date) -lt $deadline)

        Invoke-HealthRequest "$baseUri/health/live/" 'GET' | Out-Null
        Invoke-HealthRequest "$baseUri/health/live/" 'HEAD' | Out-Null
        Invoke-HealthRequest "$baseUri/health/ready/" 'GET' | Out-Null
        Invoke-HealthRequest "$baseUri/health/ready/" 'HEAD' | Out-Null
    }
    finally {
        if (-not $process.HasExited) {
            Stop-Process -Id $process.Id -Force
        }
    }
}

function Invoke-CleanMigrationTest {
    $temporaryDatabase = "lms_migration_$([Guid]::NewGuid().ToString('N'))"
    $createCommand = 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE {0}"' -f $temporaryDatabase
    $dropCommand = 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS {0}"' -f $temporaryDatabase

    Assert-PostgreSQLHealthy
    & docker compose @composeArguments exec -T postgres sh -ec $createCommand
    Assert-LastExitCode 'temporary migration database creation'

    $previousDatabase = [Environment]::GetEnvironmentVariable('POSTGRES_DB', 'Process')
    [Environment]::SetEnvironmentVariable('POSTGRES_DB', $temporaryDatabase, 'Process')
    try {
        Invoke-Django @('migrate', '--noinput')
        Invoke-Django @('migrate', '--check')
        Invoke-Django @('showmigrations', 'identity')
    }
    finally {
        [Environment]::SetEnvironmentVariable('POSTGRES_DB', $previousDatabase, 'Process')
        & docker compose @composeArguments exec -T postgres sh -ec $dropCommand
        Assert-LastExitCode 'temporary migration database cleanup'
    }
}

Set-Location $repositoryRoot
Import-LocalInfrastructureEnvironment

switch ($Action) {
    'Check' {
        Invoke-Django @('check')
        if ($WithDatabase) {
            Assert-PostgreSQLHealthy
            Invoke-Django @('check', '--database', 'default')
        }
    }
    'ProductionCheck' {
        [Environment]::SetEnvironmentVariable('DJANGO_SETTINGS_MODULE', 'config.settings.production', 'Process')
        [Environment]::SetEnvironmentVariable('DJANGO_SECRET_KEY', 'production-check-only-key-with-more-than-fifty-characters-and-no-secret-value', 'Process')
        [Environment]::SetEnvironmentVariable('DJANGO_ALLOWED_HOSTS', 'lms.invalid', 'Process')
        [Environment]::SetEnvironmentVariable('FRONTEND_ORIGIN', 'https://lms.invalid', 'Process')
        [Environment]::SetEnvironmentVariable('EMAIL_HOST', 'smtp.invalid', 'Process')
        [Environment]::SetEnvironmentVariable('EMAIL_PORT', '587', 'Process')
        [Environment]::SetEnvironmentVariable('EMAIL_HOST_USER', 'placeholder', 'Process')
        [Environment]::SetEnvironmentVariable('EMAIL_HOST_PASSWORD', 'placeholder', 'Process')
        [Environment]::SetEnvironmentVariable('ASSET_S3_REGION', 'us-east-1', 'Process')
        [Environment]::SetEnvironmentVariable('ASSET_QUARANTINE_BUCKET', 'lms-production-check-quarantine', 'Process')
        [Environment]::SetEnvironmentVariable('ASSET_PRIVATE_BUCKET', 'lms-production-check-private', 'Process')
        [Environment]::SetEnvironmentVariable('ASSET_S3_INTERNAL_ENDPOINT', $null, 'Process')
        [Environment]::SetEnvironmentVariable('ASSET_S3_PUBLIC_ENDPOINT', $null, 'Process')
        [Environment]::SetEnvironmentVariable('ASSET_S3_ACCESS_KEY_ID', $null, 'Process')
        [Environment]::SetEnvironmentVariable('ASSET_S3_SECRET_ACCESS_KEY', $null, 'Process')
        $localLtiKeyPath = Join-Path $repositoryRoot '.local/mediacms/lms-lti-private-key.pem'
        if (-not (Test-Path -LiteralPath $localLtiKeyPath)) {
            throw 'Missing local LTI private key. Run pnpm mediacms:init before api:check:production.'
        }
        [Environment]::SetEnvironmentVariable('MEDIACMS_LTI_ENABLED', 'true', 'Process')
        [Environment]::SetEnvironmentVariable('MEDIACMS_LTI_TOOL_ORIGIN', 'https://mediacms.invalid', 'Process')
        [Environment]::SetEnvironmentVariable('LMS_LTI_ISSUER', 'https://lms.invalid', 'Process')
        [Environment]::SetEnvironmentVariable('LMS_LTI_CLIENT_ID', 'lms-production-check-mediacms', 'Process')
        [Environment]::SetEnvironmentVariable('LMS_LTI_DEPLOYMENT_ID', 'lms-production-check-mediacms-v1', 'Process')
        [Environment]::SetEnvironmentVariable('LMS_LTI_KEY_ID', 'lms-production-check-mediacms-v1', 'Process')
        [Environment]::SetEnvironmentVariable('LMS_LTI_PRIVATE_KEY_PEM', [IO.File]::ReadAllText($localLtiKeyPath), 'Process')
        [Environment]::SetEnvironmentVariable('LMS_LTI_MEDIA_ACCESS_VALIDATION_URL', 'https://lms.invalid/api/v1/lti/media-access/', 'Process')
        Invoke-Django @('check', '--deploy')
    }
    'MakeMigrationsCheck' { Invoke-Django @('makemigrations', '--check', '--dry-run') }
    'MakeMigrations' {
        if ([string]::IsNullOrWhiteSpace($AppLabel)) {
            throw 'MakeMigrations requires -AppLabel to avoid generating unrelated migrations.'
        }
        Invoke-Django @('makemigrations', $AppLabel)
    }
    'MigrationPlan' { Invoke-Django @('migrate', '--plan') }
    'ShowMigrations' { Invoke-Django @('showmigrations') }
    'Migrate' {
        Assert-PostgreSQLHealthy
        if (-not $SkipPlan) { Invoke-Django @('migrate', '--plan') }
        Invoke-Django @('migrate', '--noinput')
        Invoke-Django @('migrate', '--check')
    }
    'CreateSuperuser' {
        Assert-PostgreSQLHealthy
        Invoke-Django @('createsuperuser')
    }
    'Health' {
        Assert-PostgreSQLHealthy
        Assert-RedisHealthy
        Invoke-TemporaryHealthServer
        Write-Host 'Liveness and readiness endpoints passed against the local PostgreSQL service.'
    }
    'Dev' {
        Assert-PostgreSQLHealthy
        Assert-RedisHealthy
        Invoke-Django @('runserver', '127.0.0.1:8000')
    }
    'Test' {
        Assert-PostgreSQLHealthy
        Assert-RedisHealthy
        & uv run --directory $apiDirectory pytest
        Assert-LastExitCode 'pytest'
    }
    'TestMigrations' { Invoke-CleanMigrationTest }
}
