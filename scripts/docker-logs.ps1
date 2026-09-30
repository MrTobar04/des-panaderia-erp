<#
.SYNOPSIS
    Consulta de logs de los servicios de Panadería ERP (SPEC-0.3.1).

.DESCRIPTION
    Por defecto muestra únicamente el servicio `web`, de modo que la
    conversación de PostgreSQL no sepulte la traza de Odoo que el operador
    está buscando.

.PARAMETER Service
    `web`, `db` o `all`. Predeterminado `web`.

.PARAMETER Follow
    Transmite en vivo (`docker compose logs -f`). Termina con Ctrl+C.

.PARAMETER Tail
    Número de líneas de historial a mostrar. Predeterminado 100.

.PARAMETER Filter
    Patrón de `Select-String` aplicado del lado del cliente. Compone
    correctamente con -Follow, permitiendo un flujo filtrado en vivo.

.EXAMPLE
    .\scripts\docker-logs.ps1
    Últimas 100 líneas de Odoo.

.EXAMPLE
    .\scripts\docker-logs.ps1 -Follow
    Flujo en vivo de Odoo (Ctrl+C para salir).

.EXAMPLE
    .\scripts\docker-logs.ps1 -Service db -Tail 200
    Historial de PostgreSQL.

.EXAMPLE
    .\scripts\docker-logs.ps1 -Filter "odoo.addons.panaderia"
    Solo mensajes del módulo de panadería.

.NOTES
    Códigos de salida:
      0  Logs mostrados, o flujo interrumpido por el operador
      1  Falló una precondición, o valor de -Service no válido
#>
[CmdletBinding()]
param(
    [string]$Service = 'web',
    [switch]$Follow,
    [int]$Tail = 100,
    [string]$Filter
)

# El host puede estar en una pagina de codigos heredada (CP850/CP437), en la
# que los acentos de los mensajes en espanol se verian corruptos. Se fija la
# salida a UTF-8 para cumplir el Principio V de la Constitucion.
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

# --- Validación de -Service ----------------------------------------------
# Se valida a mano en lugar de con [ValidateSet] porque este último aborta con
# un error de enlace de parámetros en inglés y código de salida 0, y el
# contrato exige salir con 1 ante un valor no válido.
if ($Service -notin @('web', 'db', 'all')) {
    Write-Host "ERROR: Valor de -Service no válido: '$Service'" -ForegroundColor Red
    Write-Host '       Valores admitidos: web, db, all' -ForegroundColor Red
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

    $arguments = @('compose', 'logs', '--tail', $Tail)
    if ($Follow) { $arguments += '-f' }
    if ($Service -ne 'all') { $arguments += $Service }

    $target = if ($Service -eq 'all') { 'todos los servicios' } else { "servicio '$Service'" }
    Write-Host ''
    Write-Host "--- Logs de Panadería ERP ($target) ---" -ForegroundColor Cyan
    if ($Filter) { Write-Host "--- Filtro activo: $Filter ---" -ForegroundColor Cyan }
    if ($Follow) { Write-Host '--- Flujo en vivo. Ctrl+C para salir. ---' -ForegroundColor Cyan }
    Write-Host ''

    if ($Filter) {
        & docker @arguments 2>&1 | Select-String -Pattern $Filter
    }
    else {
        & docker @arguments
    }

    exit 0
}
finally {
    Pop-Location -ErrorAction SilentlyContinue
}
