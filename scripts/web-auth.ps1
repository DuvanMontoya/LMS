[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Build', 'Check', 'GenerateClient', 'CheckClient', 'GeneratePlatformClient', 'CheckPlatformClient', 'Unit', 'Components', 'Accessibility', 'E2E', 'Smoke', 'Dev', 'ClearE2E')]
    [string]$Action,
    [string]$Grep
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$apiDirectory = Join-Path $repositoryRoot 'apps/api'
$webDirectory = Join-Path $repositoryRoot 'apps/web'
$environmentFile = Join-Path $repositoryRoot 'infrastructure/local/.env'
$e2eMailDirectory = Join-Path $apiDirectory '.local/e2e-mail'
$e2eResultsDirectory = Join-Path $webDirectory '.local/e2e-results'
$composeArguments = @('--project-directory', $repositoryRoot, '--env-file', $environmentFile, '-f', (Join-Path $repositoryRoot 'compose.yaml'), '-f', (Join-Path $repositoryRoot 'compose.lock.yaml'))
$pythonExecutable = if ($IsWindows) { Join-Path $apiDirectory '.venv/Scripts/python.exe' } else { Join-Path $apiDirectory '.venv/bin/python' }

function Assert-LastExitCode([string]$Operation) {
    if ($LASTEXITCODE -ne 0) { throw "$Operation failed with exit code $LASTEXITCODE." }
}

function Import-LocalInfrastructureEnvironment {
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
    [Environment]::SetEnvironmentVariable('FRONTEND_ORIGIN', 'http://127.0.0.1:3000', 'Process')
    [Environment]::SetEnvironmentVariable('DJANGO_INTERNAL_ORIGIN', 'http://127.0.0.1:8000', 'Process')
    [Environment]::SetEnvironmentVariable('AUTH_SESSION_COOKIE_NAME', 'sessionid', 'Process')
}

function Test-DjangoServer {
    try {
        $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health/live/' -TimeoutSec 2 -SkipHttpErrorCheck
        return $response.StatusCode -eq 200
    } catch { return $false }
}

function Invoke-WithTemporaryDjango([scriptblock]$Operation) {
    $startedProcess = $null
    if (-not (Test-DjangoServer)) {
        $startedProcess = Start-Process -FilePath (Join-Path $apiDirectory '.venv/Scripts/python.exe') -ArgumentList @(
            'manage.py', 'runserver', '127.0.0.1:8000', '--noreload'
        ) -WorkingDirectory $apiDirectory -PassThru -WindowStyle Hidden
        $deadline = (Get-Date).AddSeconds(30)
        while (-not (Test-DjangoServer) -and (Get-Date) -lt $deadline) {
            Start-Sleep -Milliseconds 250
        }
        if (-not (Test-DjangoServer)) { throw 'Django did not start on 127.0.0.1:8000.' }
    }
    try { & $Operation } finally {
        if ($null -ne $startedProcess -and -not $startedProcess.HasExited) {
            Stop-Process -Id $startedProcess.Id -Force
        }
    }
}

function Clear-E2EMail {
    $resolvedApi = [IO.Path]::GetFullPath($apiDirectory)
    $resolvedMail = [IO.Path]::GetFullPath($e2eMailDirectory)
    if (-not $resolvedMail.StartsWith($resolvedApi + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Refusing to clean a path outside apps/api.'
    }
    if (Test-Path -LiteralPath $resolvedMail) {
        Remove-Item -LiteralPath $resolvedMail -Recurse -Force
    }
    Write-Host 'E2E mail directory cleared.'
}

function Clear-E2EResults {
    $resolvedWeb = [IO.Path]::GetFullPath($webDirectory)
    $resolvedResults = [IO.Path]::GetFullPath($e2eResultsDirectory)
    if (-not $resolvedResults.StartsWith($resolvedWeb + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Refusing to clean a path outside apps/web.'
    }
    if (Test-Path -LiteralPath $resolvedResults) {
        Remove-Item -LiteralPath $resolvedResults -Recurse -Force
    }
}

function Assert-E2EPortsAvailable {
    if (-not $IsWindows) { return }
    $listeners = Get-NetTCPConnection -State Listen -LocalPort 3000,8000 -ErrorAction SilentlyContinue
    if ($listeners) { throw 'Ports 3000 and 8000 must be free before isolated E2E starts.' }
}

function Invoke-E2E([string]$Grep) {
    Assert-E2EPortsAvailable
    & docker compose @composeArguments ps --status running postgres redis | Out-Null
    Assert-LastExitCode 'E2E infrastructure health check'

    $databaseName = "lms_e2e_$([Guid]::NewGuid().ToString('N'))"
    $redisPrefix = "lms-e2e-$([Guid]::NewGuid().ToString('N'))"
    $createDatabase = 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE {0}"' -f $databaseName
    $dropDatabase = 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS {0}"' -f $databaseName
    $savedEnvironment = @{}
    foreach ($name in @('POSTGRES_DB', 'DJANGO_SETTINGS_MODULE', 'E2E_REDIS_PREFIX', 'E2E_MAIL_PATH', 'E2E_ORGANIZATIONS_PASSWORD')) {
        $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
    }

    & docker compose @composeArguments exec -T postgres sh -ec $createDatabase
    Assert-LastExitCode 'E2E database creation'
    try {
        Clear-E2EMail
        Clear-E2EResults
        [Environment]::SetEnvironmentVariable('POSTGRES_DB', $databaseName, 'Process')
        [Environment]::SetEnvironmentVariable('DJANGO_SETTINGS_MODULE', 'config.settings.e2e', 'Process')
        [Environment]::SetEnvironmentVariable('E2E_REDIS_PREFIX', $redisPrefix, 'Process')
        [Environment]::SetEnvironmentVariable('E2E_MAIL_PATH', $e2eMailDirectory, 'Process')
        [Environment]::SetEnvironmentVariable('E2E_ORGANIZATIONS_PASSWORD', "E2E!$([Guid]::NewGuid().ToString('N'))aA", 'Process')
        & $pythonExecutable (Join-Path $apiDirectory 'manage.py') migrate --noinput
        Assert-LastExitCode 'E2E migrations'
        & $pythonExecutable (Join-Path $apiDirectory 'manage.py') bootstrap_e2e_organizations
        Assert-LastExitCode 'E2E organization fixture creation'
        $playwrightArguments = @('test')
        if (-not [string]::IsNullOrWhiteSpace($Grep)) {
            $playwrightArguments += @('--grep', $Grep)
        }
        & pnpm --dir $webDirectory exec playwright @playwrightArguments
        Assert-LastExitCode 'isolated Playwright suite'
    }
    finally {
        if ($redisPrefix) {
            & $pythonExecutable -c "import os; from redis import Redis; client=Redis(host=os.environ['REDIS_HOST'], port=int(os.environ['REDIS_PORT']), password=os.environ['REDIS_PASSWORD'], db=int(os.environ['REDIS_CACHE_DB'])); keys=list(client.scan_iter(match=os.environ['E2E_REDIS_PREFIX'] + ':*')); client.delete(*keys) if keys else None" 2>$null
        }
        foreach ($name in $savedEnvironment.Keys) {
            [Environment]::SetEnvironmentVariable($name, $savedEnvironment[$name], 'Process')
        }
        & docker compose @composeArguments exec -T postgres sh -ec $dropDatabase
        $mailCount = if (Test-Path -LiteralPath $e2eMailDirectory) { @(Get-ChildItem -LiteralPath $e2eMailDirectory -File).Count } else { 0 }
        Write-Host "E2E mail files before cleanup: $mailCount"
        Clear-E2EMail
        Clear-E2EResults
        if ($IsWindows) {
            $leftovers = Get-NetTCPConnection -State Listen -LocalPort 3000,8000 -ErrorAction SilentlyContinue
            foreach ($listener in $leftovers) { Stop-Process -Id $listener.OwningProcess -Force }
        }
    }
}

function Test-NextServer {
    try {
        $response = Invoke-WebRequest -Uri 'http://127.0.0.1:3000/' -TimeoutSec 2 -SkipHttpErrorCheck
        return $response.StatusCode -eq 200
    } catch { return $false }
}

function Invoke-ProductionProxySmoke {
    Invoke-WithTemporaryDjango {
        $nextProcess = $null
        $nextStdout = Join-Path ([IO.Path]::GetTempPath()) "lms-next-$([Guid]::NewGuid().ToString('N')).out.log"
        $nextStderr = Join-Path ([IO.Path]::GetTempPath()) "lms-next-$([Guid]::NewGuid().ToString('N')).err.log"
        if (-not (Test-NextServer)) {
            & pnpm --dir $webDirectory run build
            Assert-LastExitCode 'Next production build'
            $nextProcess = Start-Process -FilePath 'node.exe' -ArgumentList @((Join-Path $webDirectory 'node_modules/next/dist/bin/next'), 'start', '--hostname', '127.0.0.1', '--port', '3000') -WorkingDirectory $webDirectory -PassThru -WindowStyle Hidden -RedirectStandardOutput $nextStdout -RedirectStandardError $nextStderr
            $deadline = (Get-Date).AddSeconds(30)
            while (-not (Test-NextServer) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 250 }
            if (-not (Test-NextServer)) {
                $details = ((Get-Content -LiteralPath $nextStdout -ErrorAction SilentlyContinue) + (Get-Content -LiteralPath $nextStderr -ErrorAction SilentlyContinue)) -join [Environment]::NewLine
                throw "Next did not start on 127.0.0.1:3000. $details"
            }
        }
        try {
            foreach ($path in @('/_allauth/openapi.json', '/_allauth/browser/v1/config', '/health/live/', '/health/ready/')) {
                $response = Invoke-WebRequest -Uri "http://127.0.0.1:3000$path" -SkipHttpErrorCheck
                if ($response.StatusCode -ne 200) { throw "Proxy request $path returned HTTP $($response.StatusCode)." }
                if ($response.Headers['Access-Control-Allow-Origin']) { throw "Proxy request $path unexpectedly emitted CORS." }
            }
            $csrfRejected = Invoke-WebRequest -Uri 'http://127.0.0.1:3000/_allauth/browser/v1/auth/signup' -Method Post -ContentType 'application/json' -Body '{"email":"smoke@example.test","password":"CorrectHorseBatteryStaple42!"}' -SkipHttpErrorCheck
            if ($csrfRejected.StatusCode -ne 403) { throw 'Proxy did not preserve Django CSRF rejection for an unsafe request.' }
            $notProxied = Invoke-WebRequest -Uri 'http://127.0.0.1:3000/admin/' -SkipHttpErrorCheck
            if ($notProxied.StatusCode -eq 200) { throw '/admin/ must not be proxied through Next.' }
            Write-Host 'Production proxy smoke passed: explicit rewrites, CSRF rejection, no CORS, and /admin/ remains unproxied.'
        }
        finally {
            if ($null -ne $nextProcess -and -not $nextProcess.HasExited) { Stop-Process -Id $nextProcess.Id -Force }
            Remove-Item -LiteralPath $nextStdout, $nextStderr -Force -ErrorAction SilentlyContinue
        }
    }
}

Set-Location $repositoryRoot
Import-LocalInfrastructureEnvironment

switch ($Action) {
    'Build' {
        & pnpm --dir $webDirectory run build
        Assert-LastExitCode 'Next production build'
    }
    'GenerateClient' {
        Invoke-WithTemporaryDjango {
            & pnpm --dir $webDirectory exec node scripts/generate-allauth-client.mjs generate
            Assert-LastExitCode 'allauth client generation'
        }
    }
    'CheckClient' {
        Invoke-WithTemporaryDjango {
            & pnpm --dir $webDirectory exec node scripts/generate-allauth-client.mjs check
            Assert-LastExitCode 'allauth client drift check'
        }
    }
    'GeneratePlatformClient' {
        Invoke-WithTemporaryDjango {
            & pnpm --dir $webDirectory exec node scripts/generate-platform-client.mjs generate
            Assert-LastExitCode 'platform client generation'
        }
    }
    'CheckPlatformClient' {
        Invoke-WithTemporaryDjango {
            & pnpm --dir $webDirectory exec node scripts/generate-platform-client.mjs check
            Assert-LastExitCode 'platform client drift check'
        }
    }
    'Unit' { & pnpm --dir $webDirectory exec vitest run src/lib; Assert-LastExitCode 'web unit tests' }
    'Components' { & pnpm --dir $webDirectory exec vitest run src/app src/components; Assert-LastExitCode 'web component tests' }
    'Accessibility' { Invoke-E2E '@a11y' }
    'ClearE2E' { Clear-E2EMail }
    'Check' {
        & pnpm --dir $webDirectory run lint; Assert-LastExitCode 'web lint'
        & pnpm --dir $webDirectory run format:check; Assert-LastExitCode 'web format check'
        & pnpm --dir $webDirectory run typecheck; Assert-LastExitCode 'web typecheck'
        & $PSScriptRoot/web-auth.ps1 -Action CheckClient
    }
    'Smoke' { Invoke-ProductionProxySmoke }
    'E2E' { Invoke-E2E $Grep }
    'Dev' {
        & pnpm --dir $webDirectory run dev
        Assert-LastExitCode 'Next development server'
    }
}
