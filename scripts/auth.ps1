[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Check', 'Routes', 'Specification', 'Migrations', 'Test', 'TestSecurity', 'TestEmail', 'TestRateLimits', 'Smoke', 'ClearDevelopmentMail')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$apiDirectory = Join-Path $repositoryRoot 'apps/api'
$environmentFile = Join-Path $repositoryRoot 'infrastructure/local/.env'
$mailDirectory = Join-Path $apiDirectory '.local/mail'

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
}

function Invoke-Django([string[]]$Arguments) {
    & uv run --directory $apiDirectory python manage.py @Arguments
    Assert-LastExitCode "manage.py $($Arguments -join ' ')"
}

function Assert-ServicesHealthy {
    & docker compose --project-directory $repositoryRoot --env-file $environmentFile -f (Join-Path $repositoryRoot 'compose.yaml') -f (Join-Path $repositoryRoot 'compose.lock.yaml') ps --status running postgres redis | Out-Null
    Assert-LastExitCode 'PostgreSQL and Redis status check'
}

function Invoke-AuthTests([string[]]$Arguments) {
    Assert-ServicesHealthy
    & uv run --directory $apiDirectory pytest @Arguments
    Assert-LastExitCode 'authentication test suite'
}

function Clear-DevelopmentMail {
    $resolvedApiDirectory = [IO.Path]::GetFullPath($apiDirectory)
    $resolvedMailDirectory = [IO.Path]::GetFullPath($mailDirectory)
    if (-not $resolvedMailDirectory.StartsWith($resolvedApiDirectory + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Refusing to clean a path outside apps/api.'
    }
    if (Test-Path -LiteralPath $resolvedMailDirectory) {
        Remove-Item -LiteralPath $resolvedMailDirectory -Recurse -Force
    }
    Write-Host 'Development mail directory cleared.'
}

Set-Location $repositoryRoot
Import-LocalInfrastructureEnvironment

switch ($Action) {
    'Check' {
        Assert-ServicesHealthy
        Invoke-Django @('check', '--database', 'default')
        Invoke-Django @('migrate', '--check')
        Invoke-Django @('shell', '-c', "import allauth, redis; from django.conf import settings; assert settings.HEADLESS_CLIENTS == ('browser',); assert settings.HEADLESS_ONLY; assert settings.CACHES['default']['BACKEND'] == 'django.core.cache.backends.redis.RedisCache'; print('allauth browser/session configuration and Redis cache are configured')")
    }
    'Routes' {
        Invoke-Django @('shell', '-c', "from django.test import Client; schema=Client(HTTP_HOST='127.0.0.1').get('/_allauth/openapi.json').json(); print('/accounts/ internal routes'); print(*sorted(schema['paths']), sep=' | ')")
    }
    'Specification' {
        Invoke-Django @('shell', '-c', "from django.test import Client; response=Client(HTTP_HOST='127.0.0.1').get('/_allauth/openapi.json'); assert response.status_code == 200; schema=response.json(); assert schema['openapi'].startswith('3.'); assert not any(capability in path for path in schema['paths'] for capability in ('/app/', 'phone', 'mfa', 'social')); print('validated', len(schema['paths']), 'official browser OpenAPI paths without disabled capabilities')")
    }
    'Migrations' { Invoke-Django @('showmigrations', 'account') }
    'Test' { Invoke-AuthTests @() }
    'TestSecurity' { Invoke-AuthTests @('domain/identity/tests/test_auth_headless.py', '--no-cov', '-k', 'csrf or rate_limit or logout') }
    'TestEmail' { Invoke-AuthTests @('domain/identity/tests/test_auth_headless.py', '--no-cov', '-k', 'signup or password_reset') }
    'TestRateLimits' { Invoke-AuthTests @('domain/identity/tests/test_auth_headless.py', '--no-cov', '-k', 'rate_limit') }
    'Smoke' { Invoke-AuthTests @() }
    'ClearDevelopmentMail' { Clear-DevelopmentMail }
}
