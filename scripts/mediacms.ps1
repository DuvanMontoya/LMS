[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Init', 'Build', 'Up', 'Status', 'Logs', 'Smoke', 'Down')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$stateDirectory = Join-Path $repositoryRoot '.local/mediacms'
$sourceDirectory = Join-Path $stateDirectory 'mediacms-v8.1.3'
$environmentFile = Join-Path $stateDirectory '.env'
$composeFile = Join-Path $repositoryRoot 'infrastructure/mediacms/compose.local.yaml'
$expectedCommit = 'a3fe375a8302f5b26fac214ef2346dd92fec7361'
$composeArguments = @(
    '--project-directory', $repositoryRoot,
    '--env-file', $environmentFile,
    '-f', $composeFile
)

function Assert-LastExitCode([string]$Operation) {
    if ($LASTEXITCODE -ne 0) { throw "$Operation failed with exit code $LASTEXITCODE." }
}

function New-LocalSecret([int]$Length = 48) {
    $bytes = New-Object byte[] ([Math]::Ceiling($Length / 2))
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($bytes) }
    finally { $generator.Dispose() }
    return ([Convert]::ToHexString($bytes)).ToLowerInvariant().Substring(0, $Length)
}

function Assert-PinnedSource {
    if (-not (Test-Path -LiteralPath $sourceDirectory)) {
        throw "Missing MediaCMS source at $sourceDirectory. The local source must be restored from official tag v8.1.3 before continuing."
    }
    $commit = (& git -C $sourceDirectory rev-parse HEAD).Trim()
    Assert-LastExitCode 'MediaCMS source revision lookup'
    if ($commit -ne $expectedCommit) {
        throw "MediaCMS source is $commit, expected official v8.1.3 commit $expectedCommit. Refusing an unpinned build."
    }
    $dirty = & git -C $sourceDirectory status --porcelain
    Assert-LastExitCode 'MediaCMS source cleanliness check'
    if ($dirty) { throw 'MediaCMS source has local modifications; refusing an unreproducible build.' }
}

function Get-LocalEnvironment {
    if (-not (Test-Path -LiteralPath $environmentFile)) {
        throw 'Missing .local/mediacms/.env. Run pnpm mediacms:init first.'
    }
    $values = @{}
    foreach ($line in Get-Content -LiteralPath $environmentFile) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith('#')) { continue }
        $parts = $line.Split('=', 2)
        if ($parts.Count -ne 2 -or [string]::IsNullOrWhiteSpace($parts[1])) {
            throw 'The MediaCMS local environment contains an invalid or empty value.'
        }
        $values[$parts[0]] = $parts[1]
    }
    foreach ($key in @(
        'COMPOSE_PROJECT_NAME', 'MEDIACMS_SOURCE_DIR', 'MEDIACMS_PORT',
        'MEDIACMS_POSTGRES_DB', 'MEDIACMS_POSTGRES_USER', 'MEDIACMS_POSTGRES_PASSWORD',
        'MEDIACMS_REDIS_PASSWORD', 'MEDIACMS_SECRET_KEY', 'MEDIACMS_ADMIN_USER',
        'MEDIACMS_ADMIN_EMAIL', 'MEDIACMS_ADMIN_PASSWORD'
    )) {
        if (-not $values.ContainsKey($key)) { throw "Missing $key in .local/mediacms/.env." }
    }
    return $values
}

function Initialize-LocalEnvironment {
    New-Item -ItemType Directory -Path $stateDirectory -Force | Out-Null
    if (-not (Test-Path -LiteralPath $environmentFile)) {
        $content = @(
            'COMPOSE_PROJECT_NAME=lms-mediacms',
            "MEDIACMS_SOURCE_DIR=$($sourceDirectory.Replace('\', '/'))",
            'MEDIACMS_PORT=8091',
            'MEDIACMS_POSTGRES_DB=mediacms',
            'MEDIACMS_POSTGRES_USER=mediacms',
            "MEDIACMS_POSTGRES_PASSWORD=$(New-LocalSecret)",
            "MEDIACMS_REDIS_PASSWORD=$(New-LocalSecret)",
            "MEDIACMS_SECRET_KEY=$(New-LocalSecret 64)",
            'MEDIACMS_ADMIN_USER=mediacms-admin',
            'MEDIACMS_ADMIN_EMAIL=mediacms-admin@localhost.test',
            "MEDIACMS_ADMIN_PASSWORD=$(New-LocalSecret)"
        )
        Set-Content -LiteralPath $environmentFile -Value $content -Encoding utf8NoBOM
        Write-Host 'Created .local/mediacms/.env with local random credentials. It is ignored by Git and is never printed.'
    }
    Get-LocalEnvironment | Out-Null
}

function Invoke-Compose([string[]]$Command) {
    & docker compose @composeArguments @Command
    Assert-LastExitCode "docker compose $($Command -join ' ')"
}

function Wait-ForPortal([int]$Port) {
    $deadline = [DateTimeOffset]::UtcNow.AddSeconds(90)
    do {
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/" -TimeoutSec 4 -MaximumRedirection 5 -UseBasicParsing
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) { return }
        }
        catch {
            if ([DateTimeOffset]::UtcNow -ge $deadline) { throw }
            Start-Sleep -Milliseconds 750
        }
    } while ([DateTimeOffset]::UtcNow -lt $deadline)
    throw 'MediaCMS portal did not respond before the local timeout.'
}

Set-Location $repositoryRoot
switch ($Action) {
    'Init' {
        Assert-PinnedSource
        Initialize-LocalEnvironment
        Invoke-Compose @('config', '--quiet')
        Write-Host 'Pinned MediaCMS v8.1.3 local configuration is valid. Containers remain stopped.'
    }
    'Build' {
        Assert-PinnedSource
        Get-LocalEnvironment | Out-Null
        Invoke-Compose @('build', '--pull', 'migrations')
        Write-Host 'Built MediaCMS from official v8.1.3 source commit a3fe375a8302f5b26fac214ef2346dd92fec7361.'
    }
    'Up' {
        Assert-PinnedSource
        Get-LocalEnvironment | Out-Null
        Invoke-Compose @('up', '--detach', '--wait', '--wait-timeout', '180')
        Write-Host 'Private local MediaCMS is ready at http://127.0.0.1:8091/.'
    }
    'Status' {
        Get-LocalEnvironment | Out-Null
        Invoke-Compose @('ps')
    }
    'Logs' {
        Get-LocalEnvironment | Out-Null
        Invoke-Compose @('logs', '--tail', '200')
    }
    'Smoke' {
        $environment = Get-LocalEnvironment
        $portalPort = [int]$environment['MEDIACMS_PORT']
        Wait-ForPortal $portalPort
        $loginPage = Invoke-WebRequest -Uri "http://127.0.0.1:$portalPort/accounts/login/" -TimeoutSec 10 -UseBasicParsing
        if ($loginPage.Content -match 'sign up</a>') {
            throw 'The private MediaCMS login page still advertises self-registration.'
        }
        $signupPage = Invoke-WebRequest -Uri "http://127.0.0.1:$portalPort/accounts/signup/" -TimeoutSec 10 -UseBasicParsing
        if ($signupPage.Content -notmatch '<h1>Sign Up Closed</h1>' -or $signupPage.Content -match 'id="signup_form"') {
            throw 'The MediaCMS self-registration endpoint is not closed.'
        }
        Invoke-Compose @('exec', '-T', 'db', 'psql', '-U', $environment['MEDIACMS_POSTGRES_USER'], '-d', $environment['MEDIACMS_POSTGRES_DB'], '-c', 'SELECT 1 AS mediacms_database_ready;')
        Invoke-Compose @('exec', '-T', 'redis', 'sh', '-ec', 'REDISCLI_AUTH="$MEDIACMS_REDIS_PASSWORD" redis-cli --no-auth-warning ping')
        Invoke-Compose @('exec', '-T', 'web', 'python', 'manage.py', 'check')
        Invoke-Compose @('exec', '-T', 'web', 'python', 'manage.py', 'shell', '-c', 'from users.models import User; assert User.objects.filter(is_superuser=True).exists(); print("MediaCMS administrator exists.")')
        Write-Host 'MediaCMS smoke passed: private portal with registration closed, PostgreSQL, authenticated Redis, Django checks, and administrator.'
    }
    'Down' {
        Get-LocalEnvironment | Out-Null
        Invoke-Compose @('down', '--remove-orphans')
        Write-Host 'Stopped MediaCMS containers without removing named volumes or local credentials.'
    }
}
