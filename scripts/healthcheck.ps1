<#
.SYNOPSIS
    Diagnóstico de estado de la pila Panadería ERP (SPEC-0.3.1).

.DESCRIPTION
    Ejecuta 10 sondas independientes sobre Docker, PostgreSQL y Odoo, y
    responde una sola pregunta: ¿está sirviendo el ERP y, si no, qué
    componente falla? Cada sonda registra su resultado y continúa, de modo
    que el operador ve el cuadro COMPLETO en una sola pasada.

.PARAMETER Quiet
    Suprime la salida por sonda y emite solo la línea de resumen.

.PARAMETER TimeoutSec
    Tiempo máximo de la sonda HTTP. Predeterminado 5 segundos.

.NOTES
    Códigos de salida:
      0  SALUDABLE  -> todas las verificaciones pasaron
      1  DEGRADADO  -> ambos contenedores corren, pero algo falla o inicia
      2  CAÍDO      -> Docker inalcanzable, o falta/está detenido un contenedor
#>
[CmdletBinding()]
param(
    [switch]$Quiet,
    [int]$TimeoutSec = 5
)

# El host puede estar en una pagina de codigos heredada (CP850/CP437), en la
# que los acentos de los mensajes en espanol se verian corruptos. Se fija la
# salida a UTF-8 para cumplir el Principio V de la Constitucion.
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

$DB_CONTAINER  = 'panaderia_odoo_db'
$WEB_CONTAINER = 'panaderia_odoo_web'
$TOTAL_CHECKS  = 8

# --- Utilidades de salida -------------------------------------------------

function Write-Probe {
    param(
        [ValidateSet('OK', 'INFO', 'WARN', 'ERROR')][string]$Tag,
        [string]$Message,
        [string]$Hint
    )
    if ($Quiet) { return }

    $color = switch ($Tag) {
        'OK'    { 'Green' }
        'INFO'  { 'Yellow' }
        'WARN'  { 'Yellow' }
        'ERROR' { 'Red' }
    }
    Write-Host ("[{0}]{1}{2}" -f $Tag, (' ' * (6 - $Tag.Length)), $Message) -ForegroundColor $color
    if ($Hint) {
        Write-Host ("        Sugerencia: {0}" -f $Hint) -ForegroundColor $color
    }
}

# --- Bloque de precondiciones compartido ----------------------------------

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

    $odooPort = if ($envVars['ODOO_HTTP_PORT']) { $envVars['ODOO_HTTP_PORT'] } else { '8069' }
    $pgUser   = if ($envVars['POSTGRES_USER'])  { $envVars['POSTGRES_USER'] }  else { 'odoo' }
    $dbName   = if ($envVars['ODOO_DB_NAME'])   { $envVars['ODOO_DB_NAME'] }   else { 'panaderia_db' }

    if (-not $Quiet) {
        Write-Host ''
        Write-Host '--- Verificación de Estado de Panadería ERP ---' -ForegroundColor Cyan
        Write-Host ''
    }

    $passed        = 0
    $containerDown = $false

    # --- Sonda 1: demonio de Docker --------------------------------------
    docker info 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Probe -Tag 'OK' -Message 'Docker: demonio activo'
        $passed++
    }
    else {
        Write-Probe -Tag 'ERROR' -Message 'Docker no responde' -Hint 'Inicia Docker Desktop y vuelve a intentarlo.'
        if (-not $Quiet) { Write-Host '' }
        Write-Host '--- Resultado: CAÍDO (0/8 verificaciones) ---' -ForegroundColor Red
        exit 2
    }

    # --- Sondas 2-4: contenedor de base de datos -------------------------
    # Se comprueba la EXISTENCIA antes del estado: si el contenedor no
    # existe, `docker inspect` falla y el estado sería una cadena vacía.
    docker inspect $DB_CONTAINER 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Probe -Tag 'ERROR' -Message "Contenedor ${DB_CONTAINER}: no existe" -Hint 'ejecuta .\scripts\docker-start.ps1'
        $containerDown = $true
    }
    else {
        $dbRunning = (docker inspect --format '{{.State.Running}}' $DB_CONTAINER 2>$null)
        if ($dbRunning -eq 'true') {
            Write-Probe -Tag 'OK' -Message "Contenedor ${DB_CONTAINER}: en ejecución"
            $passed++

            $dbHealth = (docker inspect --format '{{.State.Health.Status}}' $DB_CONTAINER 2>$null)
            switch ($dbHealth) {
                'healthy' {
                    Write-Probe -Tag 'OK' -Message 'Base de datos PostgreSQL: Saludable'
                    $passed++
                }
                'starting' {
                    Write-Probe -Tag 'INFO' -Message 'Base de datos PostgreSQL: iniciando...'
                }
                default {
                    Write-Probe -Tag 'ERROR' -Message "Base de datos PostgreSQL: $dbHealth"
                }
            }

            docker exec $DB_CONTAINER pg_isready -U $pgUser 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Probe -Tag 'OK' -Message 'PostgreSQL acepta conexiones (pg_isready)'
                $passed++
            }
            else {
                Write-Probe -Tag 'ERROR' -Message 'PostgreSQL no acepta conexiones'
            }
        }
        else {
            Write-Probe -Tag 'ERROR' -Message "Contenedor ${DB_CONTAINER}: detenido" -Hint 'ejecuta .\scripts\docker-start.ps1'
            $containerDown = $true
        }
    }

    # --- Sondas 6-8: contenedor de aplicación ----------------------------
    docker inspect $WEB_CONTAINER 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Probe -Tag 'ERROR' -Message "Contenedor ${WEB_CONTAINER}: no existe" -Hint 'ejecuta .\scripts\docker-start.ps1'
        $containerDown = $true
    }
    else {
        $webRunning = (docker inspect --format '{{.State.Running}}' $WEB_CONTAINER 2>$null)
        if ($webRunning -eq 'true') {
            Write-Probe -Tag 'OK' -Message "Contenedor ${WEB_CONTAINER}: en ejecución"
            $passed++

            $webHealth = (docker inspect --format '{{.State.Health.Status}}' $WEB_CONTAINER 2>$null)
            switch ($webHealth) {
                'healthy' {
                    Write-Probe -Tag 'OK' -Message 'Servidor Odoo Web: Saludable'
                    $passed++
                }
                'starting' {
                    Write-Probe -Tag 'INFO' -Message 'Servidor Odoo Web: iniciando servicios HTTP...'
                }
                default {
                    Write-Probe -Tag 'ERROR' -Message "Servidor Odoo Web: $webHealth"
                }
            }
        }
        else {
            Write-Probe -Tag 'ERROR' -Message "Contenedor ${WEB_CONTAINER}: detenido" -Hint 'ejecuta .\scripts\docker-start.ps1'
            $containerDown = $true
        }
    }

    # --- Sonda 9: interfaz HTTP ------------------------------------------
    # `Invoke-WebRequest` LANZA en 4xx/5xx en lugar de devolver el estado, de
    # ahí el try/catch. `-UseBasicParsing` es obligatorio en PowerShell 5.1.
    $webUrl = "http://localhost:$odooPort/web/login"
    try {
        $response = Invoke-WebRequest -Uri $webUrl -UseBasicParsing -TimeoutSec $TimeoutSec
        if ($response.StatusCode -eq 200) {
            Write-Probe -Tag 'OK' -Message "Interfaz Web lista en http://localhost:$odooPort"
            $passed++
        }
        else {
            Write-Probe -Tag 'WARN' -Message "Interfaz Web respondió $($response.StatusCode) en http://localhost:$odooPort"
        }
    }
    catch {
        Write-Probe -Tag 'WARN' -Message "Interfaz Web aún no responde en http://localhost:$odooPort"
    }

    # --- Sonda 10: base de datos de negocio ------------------------------
    # Informativa: una base ausente significa que la pila está bien
    # aprovisionada y el operador simplemente no la ha sembrado.
    $dbList = docker exec $DB_CONTAINER psql -U $pgUser -lqt 2>$null
    if ($LASTEXITCODE -eq 0 -and ($dbList -join "`n") -match [regex]::Escape($dbName)) {
        Write-Probe -Tag 'OK' -Message "Base de datos de negocio '$dbName' presente"
        $passed++
    }
    else {
        Write-Probe -Tag 'WARN' -Message "Base de datos de negocio '$dbName' no encontrada" -Hint 'ejecuta .\scripts\db-init-seed.ps1'
    }

    # --- Resultado agregado ----------------------------------------------
    if (-not $Quiet) { Write-Host '' }

    if ($containerDown) {
        Write-Host "--- Resultado: CAÍDO ($passed/$TOTAL_CHECKS verificaciones) ---" -ForegroundColor Red
        exit 2
    }
    elseif ($passed -eq $TOTAL_CHECKS) {
        Write-Host "--- Resultado: SALUDABLE ($passed/$TOTAL_CHECKS verificaciones) ---" -ForegroundColor Green
        exit 0
    }
    else {
        Write-Host "--- Resultado: DEGRADADO ($passed/$TOTAL_CHECKS verificaciones) ---" -ForegroundColor Yellow
        exit 1
    }
}
finally {
    Pop-Location -ErrorAction SilentlyContinue
}
