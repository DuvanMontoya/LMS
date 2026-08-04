[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Init', 'InitializeLtiKey', 'Build', 'Up', 'Status', 'Logs', 'Smoke', 'ConfigureAdmin', 'ConfigureLti', 'Down')]
    [string]$Action,

    [string]$AdminUser,
    [string]$AdminEmail,
    [string]$AdminPassword
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

function Set-LocalAdministratorCredentials(
    [string]$User,
    [string]$Email,
    [string]$Password
) {
    if ([string]::IsNullOrWhiteSpace($User) -or $User -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$') {
        throw 'AdminUser must contain 3 to 64 letters, numbers, dots, underscores, or hyphens.'
    }
    if ([string]::IsNullOrWhiteSpace($Email) -or $Email -notmatch '^[^@\s]+@[^@\s]+\.[^@\s]+$') {
        throw 'AdminEmail must be a valid email address.'
    }
    if ([string]::IsNullOrWhiteSpace($Password) -or $Password.Length -lt 16) {
        throw 'AdminPassword must contain at least 16 characters.'
    }

    $replacementValues = @{
        MEDIACMS_ADMIN_USER = $User
        MEDIACMS_ADMIN_EMAIL = $Email
        MEDIACMS_ADMIN_PASSWORD = $Password
    }
    $found = @{}
    $updatedLines = foreach ($line in Get-Content -LiteralPath $environmentFile) {
        $replacement = $null
        foreach ($key in $replacementValues.Keys) {
            if ($line.StartsWith("$key=")) {
                $replacement = "$key=$($replacementValues[$key])"
                $found[$key] = $true
                break
            }
        }
        if ($null -eq $replacement) { $line } else { $replacement }
    }
    foreach ($key in $replacementValues.Keys) {
        if (-not $found.ContainsKey($key)) { throw "Missing $key in .local/mediacms/.env." }
    }
    Set-Content -LiteralPath $environmentFile -Value $updatedLines -Encoding utf8NoBOM
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

function Initialize-LocalLtiSigningKey {
    $keyFile = Join-Path $stateDirectory 'lms-lti-private-key.pem'
    if (Test-Path -LiteralPath $keyFile) {
        return
    }

    New-Item -ItemType Directory -Path $stateDirectory -Force | Out-Null

    # A local key is durable across Django restarts but stays under the ignored
    # .local state directory.  It is never copied into MediaCMS: the tool gets
    # only the corresponding public JWKS from the LMS.
    $rsa = [System.Security.Cryptography.RSA]::Create()
    try {
        $rsa.KeySize = 3072
        [System.IO.File]::WriteAllText(
            $keyFile,
            $rsa.ExportPkcs8PrivateKeyPem(),
            [System.Text.UTF8Encoding]::new($false)
        )
    }
    finally {
        $rsa.Dispose()
    }
    Write-Host 'Created the ignored persistent local LMS LTI signing key. Restart the LMS development process once if it was already running.'
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

function Install-DefaultProfileMedia {
    # Official MediaCMS model defaults reference these two media files but the
    # upstream Docker image does not seed its named media volume with them.
    # Copy only absent files so a future custom avatar or channel banner stays
    # untouched while new local volumes remain deterministic.
    $installCommand = @'
install -d -m 0755 /home/mediacms.io/mediacms/media_files/userlogos
if [ ! -s /home/mediacms.io/mediacms/media_files/userlogos/user.jpg ]; then
    install -m 0644 /opt/mediacms-local/default-avatar.jpg /home/mediacms.io/mediacms/media_files/userlogos/user.jpg
fi
if [ ! -s /home/mediacms.io/mediacms/media_files/userlogos/banner.jpg ]; then
    install -m 0644 /opt/mediacms-local/default-banner.jpg /home/mediacms.io/mediacms/media_files/userlogos/banner.jpg
fi
chown www-data:www-data /home/mediacms.io/mediacms/media_files/userlogos/user.jpg /home/mediacms.io/mediacms/media_files/userlogos/banner.jpg
'@.Trim()
    Invoke-Compose @('exec', '-T', 'web', 'sh', '-ec', $installCommand)
}

function Configure-LocalLtiPlatform {
    # The platform configuration contains no credential.  The private signing
    # key stays exclusively in the LMS process; MediaCMS consumes the public
    # JWKS through Docker's documented host gateway.
    $configurationCommand = @'
from lti.models import LTIPlatform

platform, _ = LTIPlatform.objects.update_or_create(
    platform_id="http://localhost:3000",
    client_id="lms-local-mediacms",
    defaults={
        "name": "LMS local",
        "auth_login_url": "http://localhost:3000/api/v1/lti/authorize/",
        "auth_token_url": "http://localhost:3000/api/v1/lti/authorize/",
        "auth_audience": None,
        "key_set_url": "http://host.docker.internal:8010/api/v1/lti/jwks/",
        "deployment_ids": ["lms-local-mediacms-v1"],
        "enable_nrps": False,
        "enable_deep_linking": False,
        "remove_from_groups_on_unenroll": False,
    },
)
print(f"Configured local LTI platform: {platform.name}")
'@
    Invoke-Compose @('exec', '-T', 'web', 'python', 'manage.py', 'shell', '-c', $configurationCommand)
}

function Remove-LtiMediaAccessCapabilitiesFromAuditLog {
    # Earlier local launches may have occurred before the URL adapter started
    # redacting the bearer.  Retain the audit row, but remove only that
    # sensitive custom-claim field.  Future launches are redacted before the
    # upstream logger persists its diagnostic copy.
    $scrubCommand = @'
from django.db import transaction
from lti.models import LTILaunchLog

updated = 0
with transaction.atomic():
    for launch in LTILaunchLog.objects.exclude(claims__isnull=True).iterator():
        claims = launch.claims
        custom = (
            claims.get("https://purl.imsglobal.org/spec/lti/claim/custom")
            if isinstance(claims, dict)
            else None
        )
        if isinstance(custom, dict) and "lms_media_access_token" in custom:
            safe_claims = claims.copy()
            safe_custom = custom.copy()
            safe_custom.pop("lms_media_access_token", None)
            safe_claims["https://purl.imsglobal.org/spec/lti/claim/custom"] = safe_custom
            launch.claims = safe_claims
            launch.save(update_fields=["claims"])
            updated += 1
print(f"Redacted local LTI media capabilities from {updated} audit record(s).")
'@
    Invoke-Compose @('exec', '-T', 'web', 'python', 'manage.py', 'shell', '-c', $scrubCommand)
}

Set-Location $repositoryRoot
switch ($Action) {
    'InitializeLtiKey' {
        Initialize-LocalLtiSigningKey
        Write-Host 'The ignored local LMS LTI signing key is ready for verification.'
    }
    'Init' {
        Assert-PinnedSource
        Initialize-LocalEnvironment
        Initialize-LocalLtiSigningKey
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
        Initialize-LocalLtiSigningKey
        Invoke-Compose @('up', '--detach', '--wait', '--wait-timeout', '180')
        # Python processes do not reload bind-mounted local policy and URL
        # modules on their own.  Restart only the web service so an ``Up``
        # operation always applies the reviewed local access/LTI policy.
        Invoke-Compose @('restart', 'web')
        Invoke-Compose @('up', '--detach', '--wait', '--wait-timeout', '180')
        Install-DefaultProfileMedia
        Configure-LocalLtiPlatform
        Remove-LtiMediaAccessCapabilitiesFromAuditLog
        Write-Host 'Private local MediaCMS is ready at http://localhost:8091/.'
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
        $anonymousMediaAuth = Invoke-WebRequest -Uri "http://127.0.0.1:$portalPort/api/v1/media-auth" -TimeoutSec 10 -UseBasicParsing -SkipHttpErrorCheck -Headers @{
            'X-Original-URI' = '/media/original/user/unknown/00000000000000000000000000000000.mp4'
        }
        if ($anonymousMediaAuth.StatusCode -ne 403) {
            throw "The protected media authorization endpoint returned $($anonymousMediaAuth.StatusCode) instead of 403 for an anonymous request."
        }
        Invoke-Compose @('exec', '-T', 'db', 'psql', '-U', $environment['MEDIACMS_POSTGRES_USER'], '-d', $environment['MEDIACMS_POSTGRES_DB'], '-c', 'SELECT 1 AS mediacms_database_ready;')
        Invoke-Compose @('exec', '-T', 'redis', 'sh', '-ec', 'REDISCLI_AUTH="$MEDIACMS_REDIS_PASSWORD" redis-cli --no-auth-warning ping')
        Invoke-Compose @('exec', '-T', 'web', 'python', 'manage.py', 'check')
        Invoke-Compose @('exec', '-T', 'web', 'python', 'manage.py', 'shell', '-c', 'from users.models import User; assert User.objects.filter(is_superuser=True).exists(); print("MediaCMS administrator exists.")')
        Write-Host 'MediaCMS smoke passed: private portal with registration closed, anonymous media denial, PostgreSQL, authenticated Redis, Django checks, and administrator.'
    }
    'ConfigureAdmin' {
        Get-LocalEnvironment | Out-Null
        Set-LocalAdministratorCredentials -User $AdminUser -Email $AdminEmail -Password $AdminPassword
        $administratorProvisioning = @'
import os
from django.contrib.auth import get_user_model

User = get_user_model()
admin = User.objects.filter(is_superuser=True).order_by("id").first()
if admin is None:
    admin = User()
admin.username = os.environ["LOCAL_MEDIACMS_ADMIN_USER"]
admin.email = os.environ["LOCAL_MEDIACMS_ADMIN_EMAIL"]
admin.is_active = True
admin.is_staff = True
admin.is_superuser = True
if not admin.logo:
    admin.logo.name = "userlogos/user.jpg"
admin.set_password(os.environ["LOCAL_MEDIACMS_ADMIN_PASSWORD"])
admin.save()
User.objects.filter(is_superuser=True).exclude(pk=admin.pk).update(is_active=False)
print("MediaCMS local administrator configured.")
'@
        Invoke-Compose @(
            'exec', '-T',
            '-e', "LOCAL_MEDIACMS_ADMIN_USER=$AdminUser",
            '-e', "LOCAL_MEDIACMS_ADMIN_EMAIL=$AdminEmail",
            '-e', "LOCAL_MEDIACMS_ADMIN_PASSWORD=$AdminPassword",
            'web', 'python', 'manage.py', 'shell', '-c', $administratorProvisioning
        )
        Write-Host 'Configured the local MediaCMS administrator in .local/mediacms/.env and in MediaCMS.'
    }
    'ConfigureLti' {
        Assert-PinnedSource
        Get-LocalEnvironment | Out-Null
        Configure-LocalLtiPlatform
        Write-Host 'Configured the local LMS to MediaCMS LTI registration.'
    }
    'Down' {
        Get-LocalEnvironment | Out-Null
        Invoke-Compose @('down', '--remove-orphans')
        Write-Host 'Stopped MediaCMS containers without removing named volumes or local credentials.'
    }
}
