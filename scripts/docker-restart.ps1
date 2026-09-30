<#
.SYNOPSIS
    Reinicio de servicios, con actualización opcional del módulo (SPEC-0.3.1).

.DESCRIPTION
    Un reinicio de contenedor por sí solo NO aplica un cambio en Python: solo
    vuelve a ejecutar el código existente. Cualquier cambio en la definición
    de un campo, en un @api.constrains o en el manifiesto exige una
    actualización del módulo, y para eso existe -Upgrade.

    Esto importa más de lo normal porque la bandera `reload` de `dev_mode` es
    INERTE: `watchdog` no está en la imagen oficial odoo:16.0. No hay ningún
    mecanismo automático.

    Qué comando usar según el cambio:
      Vista XML .................. ninguno (dev_mode=xml recarga con F5)
      Modelo Python .............. .\scripts\docker-restart.ps1 -Upgrade
      __manifest__.py ............ .\scripts\docker-restart.ps1 -Upgrade
      odoo.conf.template ......... render-odoo-conf.ps1 + docker compose up -d
      .env ....................... .\scripts\docker-start.ps1

.PARAMETER Upgrade
    Ejecuta `odoo -u panaderia` antes de reiniciar. Necesario para cambios
    en modelos de Python.

.PARAMETER Wait
    Sondea hasta que panaderia_odoo_web reporte estado saludable.

.PARAMETER Service
    `web` o `db`. Predeterminado `web`.

.NOTES
    Códigos de salida:
      0  Reiniciado (y actualizado / saludable, si se solicitó)
      1  Falló una precondición, o el contenedor no existe
      2  La actualización del módulo reportó un error
      3  Se pidió -Wait y el servicio no llegó a saludable
#>
[CmdletBinding()]
param(
    [switch]$Upgrade,
    [switch]$Wait,
    [string]$Service = 'web',
    [int]$TimeoutSec = 120
)

# El host puede estar en una pagina de codigos heredada (CP850/CP437), en la
# que los acentos de los mensajes en espanol se verian corruptos. Se fija la
# salida a UTF-8 para cumplir el Principio V de la Constitucion.
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

# --- Validación de -Service ----------------------------------------------
# Manual en lugar de [ValidateSet]: este último aborta con un error en inglés
# y código de salida 0, y el contrato exige salir con 1.
if ($Service -notin @('web', 'db')) {
    Write-Host "ERROR: Valor de -Service no válido: '$Service'" -ForegroundColor Red
    Write-Host '       Valores admitidos: web, db' -ForegroundColor Red
    exit 1
}

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

    $container = if ($Service -eq 'web') { 'panaderia_odoo_web' } else { 'panaderia_odoo_db' }

    docker inspect $container 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: El contenedor $container no existe." -ForegroundColor Red
        Write-Host '       Ejecuta primero: .\scripts\docker-start.ps1' -ForegroundColor Red
        exit 1
    }

    # --- Carga de .env (división en el PRIMER '=' únicamente) -------------
    $envVars = @{}
    $envPath = Join-Path $repoRoot '.env'
    if (Test-Path -LiteralPath $envPath) {
        foreach ($line in Get-Content -LiteralPath $envPath -Encoding UTF8) {
            $trimmed = $line.Trim()
            if ($trimmed -eq '' -or $trimmed.StartsWith('#')) { continue }
            $separator = $trimmed.IndexOf('=')
            if ($separator -lt 1) { continue }
            $envVars[$trimmed.Substring(0, $separator).Trim()] = $trimmed.Substring($separator + 1).Trim().Trim('"', "'")
        }
    }
    $dbName = if ($envVars['ODOO_DB_NAME']) { $envVars['ODOO_DB_NAME'] } else { 'panaderia_db' }

    Write-Host ''
    Write-Host '--- Reiniciando Panadería ERP ---' -ForegroundColor Cyan
    Write-Host ''

    # --- Actualización del módulo (antes del reinicio) --------------------
    if ($Upgrade) {
        if ($Service -ne 'web') {
            Write-Host 'ERROR: -Upgrade solo aplica al servicio web.' -ForegroundColor Red
            exit 1
        }

        Write-Host "Actualizando el módulo panaderia en la base '$dbName'..." -ForegroundColor Cyan
        docker compose exec web odoo -u panaderia -d $dbName --stop-after-init
        if ($LASTEXITCODE -ne 0) {
            Write-Host 'ERROR: La actualización del módulo panaderia falló.' -ForegroundColor Red
            Write-Host '       Revisa el detalle con: .\scripts\docker-logs.ps1' -ForegroundColor Red
            exit 2
        }
        Write-Host '[OK]   Módulo panaderia actualizado' -ForegroundColor Green
    }

    # --- Reinicio ---------------------------------------------------------
    Write-Host "Reiniciando $container..." -ForegroundColor Cyan
    docker restart $container | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: No se pudo reiniciar $container." -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK]   $container reiniciado" -ForegroundColor Green

    # --- Espera opcional de disponibilidad -------------------------------
    if ($Wait) {
        Write-Host "Esperando disponibilidad (máx. ${TimeoutSec}s)" -ForegroundColor Cyan -NoNewline
        $deadline = (Get-Date).AddSeconds($TimeoutSec)
        $ready    = $false

        while ((Get-Date) -lt $deadline) {
            $health = (docker inspect --format '{{.State.Health.Status}}' $container 2>$null)
            if ($health -eq 'healthy') { $ready = $true; break }
            Write-Host '.' -ForegroundColor Cyan -NoNewline
            Start-Sleep -Seconds 2
        }
        Write-Host ''

        if (-not $ready) {
            Write-Host "ERROR: $container no alcanzó el estado saludable en ${TimeoutSec}s." -ForegroundColor Red
            exit 3
        }
        Write-Host "[OK]   $container saludable" -ForegroundColor Green
    }
    else {
        Write-Host 'Nota: Odoo tarda entre 15 y 30 segundos en aceptar peticiones.' -ForegroundColor Yellow
        Write-Host '      Usa -Wait para esperar la disponibilidad real.' -ForegroundColor Yellow
    }

    exit 0
}
finally {
    Pop-Location -ErrorAction SilentlyContinue
}
