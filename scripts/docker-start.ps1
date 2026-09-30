<#
.SYNOPSIS
    Arranque de un solo comando de la pila Panadería ERP (SPEC-0.3.1).

.DESCRIPTION
    Desde un clon limpio sin .env y sin configuración renderizada, este
    script aprovisiona el entorno, renderiza la configuración, levanta la
    pila, ESPERA la disponibilidad real y reporta la URL.

    La disponibilidad se determina SONDEANDO el estado de salud de los
    contenedores, nunca con una espera fija. El arranque en frío de Odoo
    sobre Windows/WSL2 supera habitualmente los 60 segundos, de modo que un
    `Start-Sleep -Seconds 5` reportaría como averiada una pila que solo
    estaba iniciando.

.PARAMETER TimeoutSec
    Techo de espera de disponibilidad. Predeterminado 120 segundos.

.PARAMETER SkipHealthcheck
    Retorna justo después de `docker compose up -d`, sin esperar.

.NOTES
    Códigos de salida:
      0  Pila saludable y sirviendo
      1  Falló una precondición
      2  Falló render-odoo-conf.ps1
      3  Falló docker compose up -d
      4  Tiempo de espera agotado: la pila no llegó a saludable
#>
[CmdletBinding()]
param(
    [int]$TimeoutSec = 120,
    [switch]$SkipHealthcheck
)

# El host puede estar en una pagina de codigos heredada (CP850/CP437), en la
# que los acentos de los mensajes en espanol se verian corruptos. Se fija la
# salida a UTF-8 para cumplir el Principio V de la Constitucion.
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

$DB_CONTAINER  = 'panaderia_odoo_db'
$WEB_CONTAINER = 'panaderia_odoo_web'

# --- Bloque de precondiciones compartido ----------------------------------

docker info 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'ERROR: Docker no responde. Inicia Docker Desktop y vuelve a intentarlo.' -ForegroundColor Red
    exit 1
}

docker compose version 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'ERROR: Falta el plugin Docker Compose v2.' -ForegroundColor Red
    exit 1
}

$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $repoRoot) {
    Write-Host 'ERROR: No se pudo resolver la raíz del repositorio.' -ForegroundColor Red
    exit 1
}

try {
    Push-Location $repoRoot

    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot 'docker-compose.yml'))) {
        Write-Host 'ERROR: No se encontró docker-compose.yml en la raíz.' -ForegroundColor Red
        exit 1
    }

    Write-Host ''
    Write-Host '--- Iniciando Panadería ERP ---' -ForegroundColor Cyan
    Write-Host ''

    # --- Paso 2: aprovisionar .env ---------------------------------------
    $envPath = Join-Path $repoRoot '.env'
    if (-not (Test-Path -LiteralPath $envPath)) {
        $envExample = Join-Path $repoRoot '.env.example'
        $envSample  = Join-Path $repoRoot '.env.sample'
        $envTemplate = if (Test-Path -LiteralPath $envExample) { $envExample } else { $envSample }
        Copy-Item -LiteralPath $envTemplate -Destination $envPath
        Write-Host "[OK]   .env creado desde $(Split-Path -Leaf $envTemplate)" -ForegroundColor Green
        Write-Host 'ADVERTENCIA: reemplaza los valores *_change_me antes de la entrega.' -ForegroundColor Yellow
    }
    else {
        Write-Host '[OK]   .env presente' -ForegroundColor Green
    }

    # --- Carga de .env (división en el PRIMER '=' únicamente) -------------
    $envVars = @{}
    foreach ($line in Get-Content -LiteralPath $envPath -Encoding UTF8) {
        $trimmed = $line.Trim()
        if ($trimmed -eq '' -or $trimmed.StartsWith('#')) { continue }
        $separator = $trimmed.IndexOf('=')
        if ($separator -lt 1) { continue }
        $envVars[$trimmed.Substring(0, $separator).Trim()] = $trimmed.Substring($separator + 1).Trim().Trim('"', "'")
    }
    $odooPort = if ($envVars['ODOO_HTTP_PORT']) { $envVars['ODOO_HTTP_PORT'] } else { '8069' }

    # --- Paso 3: renderizar la configuración -----------------------------
    # El orden es normativo: DESPUÉS de garantizar .env y ANTES de `up -d`,
    # porque Compose resuelve el bind-mount al crear el contenedor y Odoo lee
    # la configuración una sola vez al arrancar.
    Write-Host 'Renderizando config/odoo.conf...' -ForegroundColor Cyan
    & (Join-Path $PSScriptRoot 'render-odoo-conf.ps1')
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'ERROR: Falló el renderizado de la configuración. Arranque abortado.' -ForegroundColor Red
        exit 2
    }

    # --- Paso 4: levantar la pila ----------------------------------------
    Write-Host 'Levantando contenedores...' -ForegroundColor Cyan
    docker compose up -d
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'ERROR: Falló docker compose up -d.' -ForegroundColor Red
        exit 3
    }

    if ($SkipHealthcheck) {
        Write-Host ''
        Write-Host "[OK]   Contenedores iniciados. URL: http://localhost:$odooPort" -ForegroundColor Green
        exit 0
    }

    # --- Paso 5: sondeo acotado del estado de salud ----------------------
    # `starting` significa SEGUIR ESPERANDO, nunca un fallo.
    Write-Host "Esperando disponibilidad (máx. ${TimeoutSec}s)" -ForegroundColor Cyan -NoNewline
    Start-Sleep -Seconds 2   # cortesía antes del primer sondeo

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $ready    = $false

    while ((Get-Date) -lt $deadline) {
        $dbHealth  = (docker inspect --format '{{.State.Health.Status}}' $DB_CONTAINER  2>$null)
        $webHealth = (docker inspect --format '{{.State.Health.Status}}' $WEB_CONTAINER 2>$null)

        if ($dbHealth -eq 'healthy' -and $webHealth -eq 'healthy') {
            $ready = $true
            break
        }

        Write-Host '.' -ForegroundColor Cyan -NoNewline
        Start-Sleep -Seconds 2
    }
    Write-Host ''

    if (-not $ready) {
        Write-Host ''
        Write-Host "ERROR: La pila no alcanzó el estado saludable en ${TimeoutSec}s." -ForegroundColor Red
        Write-Host "       db=$dbHealth  web=$webHealth" -ForegroundColor Red
        Write-Host '       Revisa los logs con: .\scripts\docker-logs.ps1' -ForegroundColor Red
        exit 4
    }

    # --- Paso 6: diagnóstico completo ------------------------------------
    & (Join-Path $PSScriptRoot 'healthcheck.ps1')
    $healthExit = $LASTEXITCODE

    # --- Paso 7: informe final -------------------------------------------
    # Se ramifica sobre el CÓDIGO DE SALIDA, nunca sobre el texto en consola:
    # reescribir un mensaje no puede alterar el flujo de control.
    Write-Host ''
    switch ($healthExit) {
        0 { Write-Host "[OK] ERP listo en http://localhost:$odooPort" -ForegroundColor Green }
        1 { Write-Host '[WARN] Pila degradada. Revisa el diagnóstico anterior.' -ForegroundColor Yellow }
        2 { Write-Host '[ERROR] La pila no está en ejecución.' -ForegroundColor Red }
    }

    exit $healthExit
}
finally {
    Pop-Location -ErrorAction SilentlyContinue
}
