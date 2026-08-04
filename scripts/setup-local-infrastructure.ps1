$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$environmentDirectory = Join-Path $repositoryRoot 'infrastructure/local'
$environmentFile = Join-Path $environmentDirectory '.env'

function New-CryptographicSecret {
    $bytes = [byte[]]::new(32)
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    return [Convert]::ToHexString($bytes).ToLowerInvariant()
}

if (Test-Path -LiteralPath $environmentFile) {
    if (-not (Select-String -LiteralPath $environmentFile -Pattern '^REDIS_CACHE_DB=' -Quiet)) {
        Add-Content -LiteralPath $environmentFile -Value "`n# Reserved for Django cache and django-allauth rate-limit keys.`nREDIS_CACHE_DB=1" -Encoding utf8NoBOM
        Write-Host 'Added the non-secret Redis cache database setting to the existing local environment.'
    }
    $assetDefaults = [ordered]@{
        'AWS_ACCESS_KEY_ID' = 'test'
        'AWS_SECRET_ACCESS_KEY' = 'test'
        'AWS_DEFAULT_REGION' = 'us-east-1'
        'ASSET_QUARANTINE_BUCKET' = 'lms-assets-quarantine'
        'ASSET_PRIVATE_BUCKET' = 'lms-assets-private'
    }
    foreach ($entry in $assetDefaults.GetEnumerator()) {
        if (-not (Select-String -LiteralPath $environmentFile -Pattern "^$($entry.Key)=" -Quiet)) {
            Add-Content -LiteralPath $environmentFile -Value "$($entry.Key)=$($entry.Value)" -Encoding utf8NoBOM
        }
    }
    $grafanaDefaults = [ordered]@{
        'GRAFANA_ADMIN_USER' = 'admin'
        'GRAFANA_ADMIN_PASSWORD' = New-CryptographicSecret
    }
    foreach ($entry in $grafanaDefaults.GetEnumerator()) {
        if (-not (Select-String -LiteralPath $environmentFile -Pattern "^$($entry.Key)=" -Quiet)) {
            Add-Content -LiteralPath $environmentFile -Value "$($entry.Key)=$($entry.Value)" -Encoding utf8NoBOM
        }
    }
    if (-not (Select-String -LiteralPath $environmentFile -Pattern '^LIVEKIT_API_KEY=' -Quiet)) {
        Add-Content -LiteralPath $environmentFile -Value "`n# Self-hosted LiveKit development service.`nLIVEKIT_ENABLED=true`nLIVEKIT_URL=ws://127.0.0.1:7880`nNEXT_PUBLIC_LIVEKIT_URL=ws://127.0.0.1:7880`nLIVEKIT_API_KEY=$(New-CryptographicSecret)`nLIVEKIT_API_SECRET=$(New-CryptographicSecret)`nLIVEKIT_WEBHOOK_URL=http://host.docker.internal:8010/api/v1/livekit/webhook/" -Encoding utf8NoBOM
    }
    $existingEnvironment = Get-Content -LiteralPath $environmentFile -Raw
    $upgradedEnvironment = $existingEnvironment.Replace(
        'LIVEKIT_WEBHOOK_URL=http://host.docker.internal:8000/api/v1/livekit/webhook/',
        'LIVEKIT_WEBHOOK_URL=http://host.docker.internal:8010/api/v1/livekit/webhook/'
    )
    if ($upgradedEnvironment -ne $existingEnvironment) {
        Set-Content -LiteralPath $environmentFile -Value $upgradedEnvironment -Encoding utf8NoBOM -NoNewline
    }
    Write-Host 'Local infrastructure environment already exists; keeping its secrets unchanged.'
    exit 0
}

New-Item -ItemType Directory -Path $environmentDirectory -Force | Out-Null

$postgresPassword = New-CryptographicSecret
$redisPassword = New-CryptographicSecret
$grafanaPassword = New-CryptographicSecret
$content = @"
# Generated locally by scripts/setup-local-infrastructure.ps1. Do not commit.
COMPOSE_PROJECT_NAME=lms

POSTGRES_DB=lms
POSTGRES_USER=lms
POSTGRES_PASSWORD=$postgresPassword
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5433

REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=$redisPassword
REDIS_CACHE_DB=1
CELERY_BROKER_DB=2

AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=us-east-1
ASSET_QUARANTINE_BUCKET=lms-assets-quarantine
ASSET_PRIVATE_BUCKET=lms-assets-private

GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=$grafanaPassword

LIVEKIT_ENABLED=true
LIVEKIT_URL=ws://127.0.0.1:7880
NEXT_PUBLIC_LIVEKIT_URL=ws://127.0.0.1:7880
LIVEKIT_API_KEY=$(New-CryptographicSecret)
LIVEKIT_API_SECRET=$(New-CryptographicSecret)
LIVEKIT_WEBHOOK_URL=http://host.docker.internal:8010/api/v1/livekit/webhook/
"@

Set-Content -LiteralPath $environmentFile -Value $content -Encoding utf8NoBOM
Write-Host 'Generated infrastructure/local/.env with cryptographically random local secrets.'
