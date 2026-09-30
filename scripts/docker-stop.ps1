<#
.SYNOPSIS
    Detención limpia de la pila Panadería ERP (SPEC-0.3.1).

.DESCRIPTION
    Por defecto ejecuta `docker compose down`, que elimina contenedores y la
    red PERO PRESERVA los volúmenes con nombre. Se usa `down` y no `stop`
    porque `stop` dejaría contenedores detenidos, incumpliendo la
    verificación de "sin contenedores huérfanos".

    `docker compose down -v` aparece en EXACTAMENTE una ruta de código,
    alcanzable solo escribiendo la palabra BORRAR. Una palabra escrita, y no
    un prompt [S/n] ni un booleano -Force, precisamente para que no pueda
    volverse memoria muscular.

.PARAMETER RemoveVolumes
    DESTRUCTIVO. Elimina también los volúmenes con nombre. Requiere
    confirmación escribiendo BORRAR.

.PARAMETER KeepContainers
    Usa `docker compose stop` en lugar de `down`.

.NOTES
    Códigos de salida:
      0  Detenida limpiamente, o acción destructiva rechazada
      1  Falló una precondición
      2  `docker compose down` reportó un error
#>
[CmdletBinding()]
param(
    [switch]$RemoveVolumes,
    [switch]$KeepContainers
)

# El host puede estar en una pagina de codigos heredada (CP850/CP437), en la
# que los acentos de los mensajes en espanol se verian corruptos. Se fija la
# salida a UTF-8 para cumplir el Principio V de la Constitucion.
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

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
    Write-Host '--- Deteniendo Panadería ERP ---' -ForegroundColor Cyan
    Write-Host ''

    if ($RemoveVolumes) {
        Write-Host '*** ADVERTENCIA: OPERACIÓN DESTRUCTIVA ***' -ForegroundColor Red
        Write-Host 'Se eliminarán los volúmenes panaderia_odoo_db_data y' -ForegroundColor Red
        Write-Host 'panaderia_odoo_web_data. TODA la base de datos, el filestore y los' -ForegroundColor Red
        Write-Host 'módulos instalados se perderán de forma irreversible.' -ForegroundColor Red
        Write-Host ''
        Write-Host 'Para recuperar después necesitarás: .\scripts\db-init-seed.ps1' -ForegroundColor Yellow
        Write-Host ''
        $confirmation = Read-Host 'Escribe BORRAR (en mayúsculas) para confirmar'

        if ($confirmation -cne 'BORRAR') {
            Write-Host ''
            Write-Host 'Operación cancelada. No se eliminó ningún volumen.' -ForegroundColor Green
            exit 0
        }

        Write-Host ''
        Write-Host 'Eliminando contenedores, red y volúmenes...' -ForegroundColor Cyan
        docker compose down -v
        if ($LASTEXITCODE -ne 0) {
            Write-Host 'ERROR: docker compose down -v reportó un error.' -ForegroundColor Red
            exit 2
        }
        Write-Host ''
        Write-Host '[OK] Pila y volúmenes eliminados.' -ForegroundColor Green
    }
    elseif ($KeepContainers) {
        Write-Host 'Deteniendo servicios (los contenedores se conservan)...' -ForegroundColor Cyan
        docker compose stop
        if ($LASTEXITCODE -ne 0) {
            Write-Host 'ERROR: docker compose stop reportó un error.' -ForegroundColor Red
            exit 2
        }
        Write-Host ''
        Write-Host '[OK] Servicios detenidos. Contenedores conservados.' -ForegroundColor Green
    }
    else {
        Write-Host 'Deteniendo y eliminando contenedores y red...' -ForegroundColor Cyan
        docker compose down
        if ($LASTEXITCODE -ne 0) {
            Write-Host 'ERROR: docker compose down reportó un error.' -ForegroundColor Red
            exit 2
        }
        Write-Host ''
        Write-Host '[OK] Contenedores y red eliminados.' -ForegroundColor Green
    }

    # --- Informe de post-condición ---------------------------------------
    # Responde en pantalla la pregunta "¿acabo de perder mis datos?".
    Write-Host ''
    Write-Host 'Volúmenes de datos que sobreviven:' -ForegroundColor Cyan
    $survivors = docker volume ls --format '{{.Name}}' 2>$null | Select-String 'panaderia_odoo'

    if ($survivors) {
        foreach ($volume in $survivors) {
            Write-Host "  [OK]   $volume" -ForegroundColor Green
        }
        Write-Host ''
        Write-Host 'Tus datos están intactos. Reinicia con: .\scripts\docker-start.ps1' -ForegroundColor Green
    }
    else {
        Write-Host '  (ninguno)' -ForegroundColor Yellow
        Write-Host ''
        Write-Host 'No quedan volúmenes de datos. Restaura con: .\scripts\db-init-seed.ps1' -ForegroundColor Yellow
    }

    exit 0
}
finally {
    Pop-Location -ErrorAction SilentlyContinue
}
