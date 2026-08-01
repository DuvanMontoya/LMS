[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Start', 'Stop', 'Restart', 'Status', 'Logs')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$apiDirectory = Join-Path $repositoryRoot 'apps/api'
$webDirectory = Join-Path $repositoryRoot 'apps/web'
$environmentFile = Join-Path $repositoryRoot 'infrastructure/local/.env'
$runtimeDirectory = Join-Path $repositoryRoot '.local/dev'
$stateFile = Join-Path $runtimeDirectory 'processes.json'
$apiLog = Join-Path $runtimeDirectory 'api.log'
$apiErrorLog = Join-Path $runtimeDirectory 'api.error.log'
$webLog = Join-Path $runtimeDirectory 'web.log'
$webErrorLog = Join-Path $runtimeDirectory 'web.error.log'
$pythonExecutable = Join-Path $apiDirectory '.venv/Scripts/python.exe'
$nextExecutable = Join-Path $webDirectory 'node_modules/next/dist/bin/next'
$apiPort = 8010
$apiLoopbackOrigin = "http://127.0.0.1:$apiPort"

function Import-LocalEnvironment {
    if (-not (Test-Path -LiteralPath $environmentFile)) {
        throw 'Falta infrastructure/local/.env. Ejecuta pnpm infra:init.'
    }
    foreach ($line in Get-Content -LiteralPath $environmentFile) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith('#')) {
            continue
        }
        $parts = $line.Split('=', 2)
        if ($parts.Count -ne 2 -or [string]::IsNullOrWhiteSpace($parts[1])) {
            throw 'El entorno local de infraestructura contiene un valor inválido.'
        }
        [Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process')
    }
    [Environment]::SetEnvironmentVariable(
        'FRONTEND_ORIGIN',
        'http://127.0.0.1:3000',
        'Process'
    )
    [Environment]::SetEnvironmentVariable(
        'DJANGO_INTERNAL_ORIGIN',
        $apiLoopbackOrigin,
        'Process'
    )
    [Environment]::SetEnvironmentVariable(
        'AUTH_SESSION_COOKIE_NAME',
        'sessionid',
        'Process'
    )
    [Environment]::SetEnvironmentVariable(
        'STRUCTURED_LOG_PATH',
        (Join-Path $apiDirectory '.local/observability/lms.jsonl'),
        'Process'
    )
}

function Test-Endpoint([string]$Uri) {
    try {
        $response = Invoke-WebRequest -Uri $Uri -TimeoutSec 2 -SkipHttpErrorCheck
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    }
    catch {
        return $false
    }
}

function Wait-Endpoint([string]$Uri, [string]$Name) {
    $deadline = (Get-Date).AddSeconds(45)
    while ((Get-Date) -lt $deadline) {
        if (Test-Endpoint $Uri) {
            return
        }
        Start-Sleep -Milliseconds 250
    }
    throw "$Name no respondió en $Uri."
}

function Get-SavedState {
    if (-not (Test-Path -LiteralPath $stateFile)) {
        return $null
    }
    return Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
}

function Test-ExpectedProcess([int]$ProcessId, [ValidateSet('api', 'web')][string]$Kind) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        return $false
    }
    if ($Kind -eq 'api') {
        return (
            $process.ExecutablePath -eq $pythonExecutable -and
            $process.CommandLine -like "*manage.py*runserver*0.0.0.0:$apiPort*"
        )
    }
    return (
        $process.CommandLine -like "*$nextExecutable*" -and
        $process.CommandLine -like '*next*dev*127.0.0.1*3000*'
    )
}

function Test-LmsProcess([int]$ProcessId, [ValidateSet('api', 'web')][string]$Kind) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        return $false
    }
    if ($Kind -eq 'api') {
        return (
            $process.ExecutablePath -eq $pythonExecutable -and
            $process.CommandLine -like "*manage.py*runserver*0.0.0.0:$apiPort*"
        )
    }
    return (
        $process.CommandLine -like "*$repositoryRoot*" -and
        (
            $process.CommandLine -like "*$nextExecutable*" -or
            $process.CommandLine -like '*next*start-server.js*'
        )
    )
}

function Get-ProcessTreeIds([int]$RootProcessId) {
    $ids = @()
    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $RootProcessId" -ErrorAction SilentlyContinue
    foreach ($child in $children) {
        $ids += @(Get-ProcessTreeIds -RootProcessId ([int]$child.ProcessId))
    }
    $ids += $RootProcessId
    return $ids
}

function Get-ListenerProcessIds([int]$Port) {
    return @(
        Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    )
}

function Test-RegisteredDevelopment {
    $state = Get-SavedState
    if ($null -eq $state) {
        return $false
    }
    if (
        -not (Test-ExpectedProcess -ProcessId ([int]$state.apiPid) -Kind 'api') -or
        -not (Test-ExpectedProcess -ProcessId ([int]$state.webPid) -Kind 'web')
    ) {
        return $false
    }
    $apiListeners = @(Get-ListenerProcessIds -Port $apiPort)
    $webListeners = @(Get-ListenerProcessIds -Port 3000)
    return (
        $apiListeners.Count -gt 0 -and
        $webListeners.Count -gt 0 -and
        -not ($apiListeners | Where-Object { -not (Test-LmsProcess -ProcessId $_ -Kind 'api') }) -and
        -not ($webListeners | Where-Object { -not (Test-LmsProcess -ProcessId $_ -Kind 'web') })
    )
}

function Write-Status {
    $state = Get-SavedState
    $apiReady = Test-Endpoint "$apiLoopbackOrigin/health/live/"
    $webReady = Test-Endpoint 'http://127.0.0.1:3000/'
    $apiPid = @(Get-ListenerProcessIds -Port $apiPort) -join ','
    $webPid = @(Get-ListenerProcessIds -Port 3000) -join ','
    if (-not $apiPid) { $apiPid = '-' }
    if (-not $webPid) { $webPid = '-' }
    Write-Host "API   : $(if ($apiReady) { 'lista' } else { 'detenida' }) | PID $apiPid | $apiLoopbackOrigin"
    Write-Host "Web   : $(if ($webReady) { 'lista' } else { 'detenida' }) | PID $webPid | http://127.0.0.1:3000"
    Write-Host "Estado: $stateFile"
}

function Start-Development {
    if (
        (Test-Endpoint "$apiLoopbackOrigin/health/live/") -and
        (Test-Endpoint 'http://127.0.0.1:3000/') -and
        (Test-RegisteredDevelopment)
    ) {
        Write-Host 'El entorno de desarrollo ya está disponible.'
        Write-Status
        return
    }

    $listeners = Get-NetTCPConnection -State Listen -LocalPort 3000, $apiPort -ErrorAction SilentlyContinue
    if ($listeners) {
        throw "Los puertos 3000 o $apiPort están ocupados por un entorno incompleto. Revisa pnpm dev:status y pnpm dev:logs."
    }

    New-Item -ItemType Directory -Path $runtimeDirectory -Force | Out-Null
    & pnpm infra:up
    if ($LASTEXITCODE -ne 0) {
        throw 'No fue posible iniciar PostgreSQL y Redis.'
    }
    & pnpm api:migrate
    if ($LASTEXITCODE -ne 0) {
        throw 'No fue posible aplicar las migraciones locales.'
    }
    & pnpm --dir $webDirectory run content:assets:prepare
    if ($LASTEXITCODE -ne 0) {
        throw 'No fue posible preparar los recursos matemáticos locales.'
    }

    $apiProcess = Start-Process `
        -FilePath $pythonExecutable `
        -ArgumentList @('manage.py', 'runserver', "0.0.0.0:$apiPort", '--noreload') `
        -WorkingDirectory $apiDirectory `
        -PassThru `
        -WindowStyle Hidden `
        -RedirectStandardOutput $apiLog `
        -RedirectStandardError $apiErrorLog
    $webProcess = Start-Process `
        -FilePath 'node.exe' `
        -ArgumentList @($nextExecutable, 'dev', '--webpack', '--hostname', '127.0.0.1', '--port', '3000') `
        -WorkingDirectory $webDirectory `
        -PassThru `
        -WindowStyle Hidden `
        -RedirectStandardOutput $webLog `
        -RedirectStandardError $webErrorLog

    try {
        Wait-Endpoint "$apiLoopbackOrigin/health/live/" 'Django'
        Wait-Endpoint 'http://127.0.0.1:3000/' 'Next.js'
        @{
            apiPid = $apiProcess.Id
            webPid = $webProcess.Id
            startedAt = (Get-Date).ToString('o')
        } | ConvertTo-Json | Set-Content -LiteralPath $stateFile -Encoding utf8NoBOM
        Write-Host 'Entorno persistente iniciado. No se detendrá al finalizar las pruebas.'
        Write-Status
    }
    catch {
        foreach ($process in @($apiProcess, $webProcess)) {
            if (-not $process.HasExited) {
                Stop-Process -Id $process.Id -Force
            }
        }
        throw
    }
}

function Stop-Development {
    $state = Get-SavedState
    $processIds = @()
    if ($null -ne $state) {
        foreach ($entry in @(
            @{ id = [int]$state.apiPid; kind = 'api' },
            @{ id = [int]$state.webPid; kind = 'web' }
        )) {
            if (Test-ExpectedProcess -ProcessId $entry.id -Kind $entry.kind) {
                $processIds += @(Get-ProcessTreeIds -RootProcessId $entry.id)
            }
        }
    }
    foreach ($processId in @(Get-ListenerProcessIds -Port $apiPort)) {
        if (Test-LmsProcess -ProcessId $processId -Kind 'api') {
            $processIds += @(Get-ProcessTreeIds -RootProcessId $processId)
        }
    }
    foreach ($processId in @(Get-ListenerProcessIds -Port 3000)) {
        if (Test-LmsProcess -ProcessId $processId -Kind 'web') {
            $processIds += @(Get-ProcessTreeIds -RootProcessId $processId)
        }
    }
    foreach ($processId in @($processIds | Select-Object -Unique)) {
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
    $deadline = (Get-Date).AddSeconds(8)
    while ((Get-Date) -lt $deadline) {
        if (-not (Get-NetTCPConnection -State Listen -LocalPort 3000, $apiPort -ErrorAction SilentlyContinue)) {
            break
        }
        Start-Sleep -Milliseconds 200
    }
    $remaining = Get-NetTCPConnection -State Listen -LocalPort 3000, $apiPort -ErrorAction SilentlyContinue
    if ($remaining) {
        $summary = ($remaining | ForEach-Object { "$($_.LocalPort):PID $($_.OwningProcess)" }) -join ', '
        throw "No se detuvieron procesos ajenos al LMS en sus puertos: $summary"
    }
    Remove-Item -LiteralPath $stateFile -Force -ErrorAction SilentlyContinue
    Write-Host 'Frontend y backend persistentes detenidos. PostgreSQL y Redis permanecen activos.'
}

function Show-Logs {
    foreach ($entry in @(
        @{ label = 'API'; path = $apiLog },
        @{ label = 'API errores'; path = $apiErrorLog },
        @{ label = 'Web'; path = $webLog },
        @{ label = 'Web errores'; path = $webErrorLog }
    )) {
        Write-Host "`n[$($entry.label)] $($entry.path)"
        if (Test-Path -LiteralPath $entry.path) {
            Get-Content -LiteralPath $entry.path -Tail 80
        }
        else {
            Write-Host 'Sin registros.'
        }
    }
}

Set-Location $repositoryRoot
Import-LocalEnvironment

switch ($Action) {
    'Start' { Start-Development }
    'Stop' { Stop-Development }
    'Restart' {
        Stop-Development
        Start-Development
    }
    'Status' { Write-Status }
    'Logs' { Show-Logs }
}
