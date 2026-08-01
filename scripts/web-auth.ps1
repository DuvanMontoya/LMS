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

function Invoke-WithCurrentPlatformSchema([scriptblock]$Operation) {
    $schemaFile = New-TemporaryFile
    $previousSchemaFile = [Environment]::GetEnvironmentVariable('PLATFORM_OPENAPI_FILE', 'Process')
    try {
        & $pythonExecutable (Join-Path $apiDirectory 'manage.py') spectacular --file $schemaFile.FullName --format openapi-json --validate --fail-on-warn
        Assert-LastExitCode 'current platform OpenAPI generation'
        [Environment]::SetEnvironmentVariable('PLATFORM_OPENAPI_FILE', $schemaFile.FullName, 'Process')
        & $Operation
    }
    finally {
        [Environment]::SetEnvironmentVariable('PLATFORM_OPENAPI_FILE', $previousSchemaFile, 'Process')
        Remove-Item -LiteralPath $schemaFile.FullName -Force -ErrorAction SilentlyContinue
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

function Get-FreeLocalPort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    try { return ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port }
    finally { $listener.Stop() }
}

function Invoke-E2E([string]$Grep) {
    & docker compose @composeArguments ps --status running postgres redis | Out-Null
    Assert-LastExitCode 'E2E infrastructure health check'

    $databaseName = "lms_e2e_$([Guid]::NewGuid().ToString('N'))"
    $redisPrefix = "lms-e2e-$([Guid]::NewGuid().ToString('N'))"
    $workerName = "$redisPrefix-worker"
    $queuePrefix = "$redisPrefix-"
    $apiPort = Get-FreeLocalPort
    $webPort = Get-FreeLocalPort
    while ($webPort -eq $apiPort) { $webPort = Get-FreeLocalPort }
    $nextDistDirectoryName = ".local/e2e-next-$([Guid]::NewGuid().ToString('N'))"
    $nextDistDirectory = Join-Path $webDirectory $nextDistDirectoryName
    $tsconfigPath = Join-Path $webDirectory 'tsconfig.json'
    $tsconfigBefore = [IO.File]::ReadAllText($tsconfigPath)
    $nextEnvPath = Join-Path $webDirectory 'next-env.d.ts'
    $nextEnvBefore = if (Test-Path -LiteralPath $nextEnvPath) {
        [IO.File]::ReadAllText($nextEnvPath)
    } else {
        $null
    }
    $createDatabase = 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE {0}"' -f $databaseName
    $dropDatabase = 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS {0}"' -f $databaseName
    $savedEnvironment = @{}
    $integrationWorkerProcess = $null
    foreach ($name in @('POSTGRES_DB', 'DJANGO_SETTINGS_MODULE', 'E2E_REDIS_PREFIX', 'E2E_MAIL_PATH', 'E2E_ORGANIZATIONS_PASSWORD', 'E2E_API_PORT', 'E2E_WEB_PORT', 'DJANGO_INTERNAL_ORIGIN', 'FRONTEND_ORIGIN', 'NEXT_DIST_DIR', 'ASSESSMENT_TASK_QUEUE_PREFIX', 'ASSESSMENT_TASK_COUNTDOWN_SECONDS')) {
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
        [Environment]::SetEnvironmentVariable('ASSESSMENT_TASK_QUEUE_PREFIX', $queuePrefix, 'Process')
        [Environment]::SetEnvironmentVariable('ASSESSMENT_TASK_COUNTDOWN_SECONDS', '2', 'Process')
        [Environment]::SetEnvironmentVariable('E2E_MAIL_PATH', $e2eMailDirectory, 'Process')
        [Environment]::SetEnvironmentVariable('E2E_ORGANIZATIONS_PASSWORD', "E2E!$([Guid]::NewGuid().ToString('N'))aA", 'Process')
        [Environment]::SetEnvironmentVariable('E2E_API_PORT', [string]$apiPort, 'Process')
        [Environment]::SetEnvironmentVariable('E2E_WEB_PORT', [string]$webPort, 'Process')
        [Environment]::SetEnvironmentVariable('DJANGO_INTERNAL_ORIGIN', "http://127.0.0.1:$apiPort", 'Process')
        [Environment]::SetEnvironmentVariable('FRONTEND_ORIGIN', "http://127.0.0.1:$webPort", 'Process')
        [Environment]::SetEnvironmentVariable('NEXT_DIST_DIR', $nextDistDirectoryName, 'Process')
        & $pythonExecutable (Join-Path $apiDirectory 'manage.py') migrate --noinput
        Assert-LastExitCode 'E2E migrations'
        & $pythonExecutable (Join-Path $apiDirectory 'manage.py') bootstrap_e2e_organizations
        Assert-LastExitCode 'E2E organization fixture creation'
        $integrationWorkerProcess = Start-Process -FilePath $pythonExecutable -ArgumentList @(
            '-m', 'celery', '-A', 'config', 'worker', '--loglevel=WARNING',
            '--pool=solo', '--queues', "$redisPrefix-integrations",
            '--hostname', "$redisPrefix-integration-worker"
        ) -WorkingDirectory $apiDirectory -PassThru -WindowStyle Hidden
        Start-Sleep -Milliseconds 750
        if ($integrationWorkerProcess.HasExited) {
            throw 'The isolated E2E integration worker did not start.'
        }
        & $pythonExecutable (Join-Path $apiDirectory 'manage.py') bootstrap_e2e_publication
        Assert-LastExitCode 'E2E publication source fixture creation'
        if ($Grep -match 'learning delivery|assessment phase 1[34]') {
            & $pythonExecutable (Join-Path $apiDirectory 'manage.py') bootstrap_e2e_learning
            Assert-LastExitCode 'E2E learning fixture creation'
        }
        if ($Grep -match 'assessment phase 1[34]') {
            & $pythonExecutable (Join-Path $apiDirectory 'manage.py') bootstrap_e2e_assessments
            Assert-LastExitCode 'E2E assessments fixture creation'
        }
        if ($Grep -match 'assessment phase 14') {
            & $pythonExecutable (Join-Path $apiDirectory 'manage.py') bootstrap_e2e_assessments_advanced
            Assert-LastExitCode 'advanced E2E assessments fixture creation'
            & docker compose @composeArguments build assessment-worker
            Assert-LastExitCode 'E2E assessment worker build'
            $workerQueues = "$queuePrefix" + "grading,$queuePrefix" + "regrading,$queuePrefix" + "analytics"
            & docker compose @composeArguments run -d --no-deps --name $workerName `
                -e "DJANGO_SETTINGS_MODULE=config.settings.e2e" `
                -e "POSTGRES_DB=$databaseName" `
                -e "E2E_REDIS_PREFIX=$redisPrefix" `
                -e "E2E_MAIL_PATH=/workspace/apps/api/.local/e2e-mail" `
                -e "FRONTEND_ORIGIN=http://127.0.0.1:$webPort" `
                -e "ASSESSMENT_TASK_QUEUE_PREFIX=$queuePrefix" `
                -e "ASSESSMENT_TASK_COUNTDOWN_SECONDS=2" `
                assessment-worker celery -A config worker --loglevel=INFO `
                --pool=prefork --concurrency=2 --prefetch-multiplier=1 `
                --max-tasks-per-child=100 --queues=$workerQueues --hostname=$workerName
            Assert-LastExitCode 'isolated E2E assessment worker startup'
            $workerDeadline = (Get-Date).AddSeconds(30)
            do {
                Start-Sleep -Milliseconds 500
                $workerRunning = (& docker inspect --format '{{.State.Running}}' $workerName 2>$null) -eq 'true'
            } while (-not $workerRunning -and (Get-Date) -lt $workerDeadline)
            if (-not $workerRunning) { throw 'The isolated E2E assessment worker did not start.' }
        }
        if ($Grep -match 'platform operations') {
            & $pythonExecutable (Join-Path $apiDirectory 'manage.py') bootstrap_e2e_platform_operations
            Assert-LastExitCode 'platform operations E2E fixture creation'
            & docker compose @composeArguments build assessment-worker
            Assert-LastExitCode 'platform operations E2E worker build'
            $workerQueues = "$redisPrefix-events,$redisPrefix-notifications"
            & docker compose @composeArguments run -d --no-deps --name $workerName `
                -e "DJANGO_SETTINGS_MODULE=config.settings.e2e" `
                -e "POSTGRES_DB=$databaseName" `
                -e "E2E_REDIS_PREFIX=$redisPrefix" `
                -e "E2E_MAIL_PATH=/workspace/apps/api/.local/e2e-mail" `
                -e "FRONTEND_ORIGIN=http://127.0.0.1:$webPort" `
                assessment-worker celery -A config worker --loglevel=INFO `
                --pool=prefork --concurrency=2 --prefetch-multiplier=1 `
                --max-tasks-per-child=100 --queues=$workerQueues --hostname=$workerName
            Assert-LastExitCode 'isolated platform operations E2E worker startup'
            $workerDeadline = (Get-Date).AddSeconds(30)
            do {
                Start-Sleep -Milliseconds 500
                $workerRunning = (& docker inspect --format '{{.State.Running}}' $workerName 2>$null) -eq 'true'
            } while (-not $workerRunning -and (Get-Date) -lt $workerDeadline)
            if (-not $workerRunning) { throw 'The isolated platform operations E2E worker did not start.' }
        }
        $playwrightArguments = @('test')
        if (-not [string]::IsNullOrWhiteSpace($Grep)) {
            $playwrightArguments += @('--grep', $Grep)
        }
        & pnpm --dir $webDirectory exec playwright @playwrightArguments
        Assert-LastExitCode 'isolated Playwright suite'
    }
    finally {
        if ($null -ne $integrationWorkerProcess -and -not $integrationWorkerProcess.HasExited) {
            Stop-Process -Id $integrationWorkerProcess.Id -Force
        }
        if ($workerName -and $workerName.StartsWith('lms-e2e-')) {
            & docker rm -f $workerName 2>$null | Out-Null
        }
        if ($redisPrefix) {
            & $pythonExecutable -c "import os; from redis import Redis; prefix=os.environ['E2E_REDIS_PREFIX']; databases={int(os.environ['REDIS_CACHE_DB']), int(os.environ['CELERY_BROKER_DB'])}; [(lambda client: (lambda keys: client.delete(*keys) if keys else None)(list(client.scan_iter(match=prefix + '*'))))(Redis(host=os.environ['REDIS_HOST'], port=int(os.environ['REDIS_PORT']), password=os.environ['REDIS_PASSWORD'], db=db)) for db in databases]" 2>$null
        }
        foreach ($name in $savedEnvironment.Keys) {
            [Environment]::SetEnvironmentVariable($name, $savedEnvironment[$name], 'Process')
        }
        & docker compose @composeArguments exec -T postgres sh -ec $dropDatabase
        $mailCount = if (Test-Path -LiteralPath $e2eMailDirectory) { @(Get-ChildItem -LiteralPath $e2eMailDirectory -File).Count } else { 0 }
        Write-Host "E2E mail files before cleanup: $mailCount"
        Clear-E2EMail
        $resolvedWeb = [IO.Path]::GetFullPath($webDirectory)
        $resolvedNextDist = [IO.Path]::GetFullPath($nextDistDirectory)
        if (-not $resolvedNextDist.StartsWith($resolvedWeb + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Refusing to clean an E2E Next directory outside apps/web.'
        }
        if (Test-Path -LiteralPath $resolvedNextDist) {
            Remove-Item -LiteralPath $resolvedNextDist -Recurse -Force
        }
        $tsconfigAfter = [IO.File]::ReadAllText($tsconfigPath)
        if ($tsconfigAfter -ne $tsconfigBefore) {
            $beforeObject = $tsconfigBefore | ConvertFrom-Json
            $afterObject = $tsconfigAfter | ConvertFrom-Json
            $escapedNextDistDirectoryName = [Regex]::Escape($nextDistDirectoryName)
            $afterObject.include = @(
                $afterObject.include | Where-Object {
                    $_ -notmatch "^$escapedNextDistDirectoryName/(dev/)?types/\*\*/\*\.ts$"
                }
            )
            $beforeNormalized = $beforeObject | ConvertTo-Json -Depth 100 -Compress
            $afterNormalized = $afterObject | ConvertTo-Json -Depth 100 -Compress
            if ($beforeNormalized -eq $afterNormalized) {
                [IO.File]::WriteAllText($tsconfigPath, $tsconfigBefore, [Text.UTF8Encoding]::new($false))
            } else {
                Write-Warning 'tsconfig.json changed beyond the temporary Next E2E includes; preserving it for review.'
            }
        }
        $nextEnvAfter = if (Test-Path -LiteralPath $nextEnvPath) {
            [IO.File]::ReadAllText($nextEnvPath)
        } else {
            $null
        }
        if ($nextEnvAfter -ne $nextEnvBefore -and $null -ne $nextEnvBefore) {
            # Next rewrites this generated file to point at the temporary E2E
            # dist directory. Restore the exact pre-run generated reference
            # (normally .next/dev) so the isolated run cannot poison local
            # route typechecking.
            [IO.File]::WriteAllText(
                $nextEnvPath,
                $nextEnvBefore,
                [Text.UTF8Encoding]::new($false)
            )
        }
        if ($IsWindows -and $apiPort -and $webPort) {
            $leftovers = Get-NetTCPConnection -State Listen -LocalPort $apiPort,$webPort -ErrorAction SilentlyContinue
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
        Invoke-WithCurrentPlatformSchema {
            & pnpm --dir $webDirectory exec node scripts/generate-platform-client.mjs generate
            Assert-LastExitCode 'platform client generation'
        }
    }
    'CheckPlatformClient' {
        Invoke-WithCurrentPlatformSchema {
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
