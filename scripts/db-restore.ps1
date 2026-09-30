<#
.SYNOPSIS
    Restauración íntegra de la base de datos de negocio (SPEC-0.2.1).

.DESCRIPTION
    Devuelve la base de datos exactamente al estado capturado en un volcado,
    con integridad referencial completa y sin registro de Odoo obsoleto.

    Secuencia normativa:
       1. Bloque de precondiciones
       2. Verificar que existe -BackupFile
       3. Validar el artefacto con pg_restore -l   <-- ANTES de destruir nada
       4. Confirmar con el operador salvo -Force
       5. docker compose stop web                  <-- Odoo libera su pool
       6. pg_terminate_backend (barrido secundario)
       7. dropdb --if-exists
       8. createdb
       9. docker cp del artefacto a /tmp
      10. pg_restore --no-owner --no-privileges
      11. Restaurar el filestore si se pidió
      12. Eliminar el archivo temporal
      13. docker compose start web                 <-- en un bloque finally
      14. Sondear hasta que web esté saludable

    Por qué se detiene `web` (paso 5): el pool de conexiones de Odoo se
    reconecta en milisegundos y `pg_terminate_backend` por sí solo PIERDE la
    carrera contra `dropdb`. Lo hace de forma intermitente, por lo que
    funciona en el ensayo y falla durante la defensa.

    Por qué dropdb+createdb y no `pg_restore --clean`: `--clean` exige que la
    base ya exista, así que falla en un clon reciente o después de
    `docker compose down -v`, que es precisamente el caso al que sirve
    seed_demo.dump.

.NOTES
    Códigos de salida:
      0  Restauración completada y web saludable
      1  Falló una precondición, o no se encontró -BackupFile
      2  Falló dropdb / createdb
      3  pg_restore reportó errores
      4  El artefacto no pasó la validación: NO SE MODIFICÓ NADA
      5  La restauración funcionó pero web no llegó a saludable
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$BackupFile,
    [switch]$Force,
    [string]$RestoreFilestore,
    [int]$TimeoutSec = 120
)

# El host puede estar en una pagina de codigos heredada (CP850/CP437), en la
# que los acentos de los mensajes en espanol se verian corruptos. Se fija la
# salida a UTF-8 para cumplir el Principio V de la Constitucion.
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

$DB_CONTAINER  = 'panaderia_odoo_db'
$WEB_CONTAINER = 'panaderia_odoo_web'

# --- Bloque de precondiciones compartido ----------------------------------

$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath  = Join-Path $repoRoot '.env'

if (-not (Test-Path -LiteralPath $envPath)) {
    Write-Host 'ERROR: No existe .env. Ejecuta: Copy-Item .env.sample .env' -ForegroundColor Red
    exit 1
}

$envVars = @{}
foreach ($line in Get-Content -LiteralPath $envPath -Encoding UTF8) {
    $trimmed = $line.Trim()
    if ($trimmed -eq '' -or $trimmed.StartsWith('#')) { continue }
    $separator = $trimmed.IndexOf('=')
    if ($separator -lt 1) { continue }
    $envVars[$trimmed.Substring(0, $separator).Trim()] = $trimmed.Substring($separator + 1).Trim().Trim('"', "'")
}

$pgUser = $envVars['POSTGRES_USER']
$dbName = $envVars['ODOO_DB_NAME']

if (-not $pgUser -or -not $dbName) {
    Write-Host 'ERROR: Falta POSTGRES_USER u ODOO_DB_NAME en .env' -ForegroundColor Red
    exit 1
}

docker info 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'ERROR: Docker no está disponible o el demonio no responde.' -ForegroundColor Red
    exit 1
}

$running = docker inspect --format '{{.State.Running}}' $DB_CONTAINER 2>$null
if ($LASTEXITCODE -ne 0 -or $running -ne 'true') {
    Write-Host "ERROR: El contenedor $DB_CONTAINER no está en ejecución." -ForegroundColor Red
    Write-Host '       Ejecuta primero: .\scripts\docker-start.ps1' -ForegroundColor Red
    exit 1
}

$webWasStopped = $false

try {
    Push-Location $repoRoot

    # --- Paso 2: existencia del artefacto --------------------------------
    if (-not (Test-Path -LiteralPath $BackupFile)) {
        Write-Host "ERROR: No se encontró el archivo de respaldo: $BackupFile" -ForegroundColor Red
        exit 1
    }
    $resolvedBackup = (Resolve-Path -LiteralPath $BackupFile).Path
    $stagedName     = Split-Path -Leaf $resolvedBackup

    Write-Host ''
    Write-Host '--- Restauración de Panadería ERP ---' -ForegroundColor Cyan
    Write-Host ''

    # --- Paso 3: validar ANTES de destruir -------------------------------
    # Un artefacto corrupto se rechaza mientras la base actual sigue intacta.
    Write-Host '[1/7] Validando el artefacto...' -ForegroundColor Cyan
    docker cp $resolvedBackup "${DB_CONTAINER}:/tmp/validate.dump" 2>&1 | Out-Null
    $toc     = docker exec $DB_CONTAINER pg_restore -l /tmp/validate.dump 2>$null
    $tocExit = $LASTEXITCODE
    docker exec $DB_CONTAINER rm -f /tmp/validate.dump 2>&1 | Out-Null

    if ($tocExit -ne 0) {
        Write-Host '[ERROR] El artefacto no es un volcado válido. No se modificó nada.' -ForegroundColor Red
        exit 4
    }

    if (($toc -join "`n") -notmatch 'panaderia_') {
        Write-Host '[ERROR] El artefacto no contiene relaciones de panadería. No se modificó nada.' -ForegroundColor Red
        exit 4
    }
    Write-Host '      Artefacto válido y con datos de panadería.' -ForegroundColor Green

    # --- Paso 4: confirmación --------------------------------------------
    if (-not $Force) {
        Write-Host ''
        Write-Host "ADVERTENCIA: se reemplazará por completo la base de datos '$dbName'." -ForegroundColor Yellow
        Write-Host 'Todo dato actual no respaldado se perderá.' -ForegroundColor Yellow
        $answer = Read-Host '¿Continuar? (s/N)'
        if ($answer -notmatch '^[sS]([iíIÍ])?$') {
            Write-Host 'Operación cancelada. No se modificó nada.' -ForegroundColor Green
            exit 0
        }
        Write-Host ''
    }

    # --- Paso 5: detener Odoo --------------------------------------------
    Write-Host '[2/7] Deteniendo el servidor Odoo...' -ForegroundColor Cyan
    docker compose stop web 2>&1 | Out-Null
    $webWasStopped = $true

    # --- Paso 6: barrido de sesiones residuales --------------------------
    Write-Host '[3/7] Cerrando conexiones residuales...' -ForegroundColor Cyan
    $terminateSql = "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$dbName' AND pid <> pg_backend_pid();"
    docker exec $DB_CONTAINER psql -U $pgUser -d postgres -c $terminateSql 2>&1 | Out-Null

    # --- Pasos 7-8: recrear la base de datos -----------------------------
    # Único uso legítimo de `-d postgres` en esta función: es la base de
    # MANTENIMIENTO desde la que se administra el clúster.
    Write-Host "[4/7] Recreando la base de datos '$dbName'..." -ForegroundColor Cyan
    docker exec $DB_CONTAINER dropdb -U $pgUser --if-exists $dbName
    if ($LASTEXITCODE -ne 0) {
        Write-Host '[ERROR] dropdb falló.' -ForegroundColor Red
        exit 2
    }
    docker exec $DB_CONTAINER createdb -U $pgUser -O $pgUser $dbName
    if ($LASTEXITCODE -ne 0) {
        Write-Host '[ERROR] createdb falló.' -ForegroundColor Red
        exit 2
    }

    # --- Pasos 9-10: restaurar -------------------------------------------
    # --no-owner --no-privileges hacen el artefacto portable entre máquinas
    # cuyos nombres de rol de PostgreSQL difieren.
    Write-Host '[5/7] Restaurando los datos...' -ForegroundColor Cyan
    docker cp $resolvedBackup "${DB_CONTAINER}:/tmp/$stagedName" 2>&1 | Out-Null
    docker exec $DB_CONTAINER pg_restore -U $pgUser -d $dbName --no-owner --no-privileges "/tmp/$stagedName"
    $restoreExit = $LASTEXITCODE
    docker exec $DB_CONTAINER rm -f "/tmp/$stagedName" 2>&1 | Out-Null

    if ($restoreExit -ne 0) {
        Write-Host '[ERROR] pg_restore reportó errores durante la restauración.' -ForegroundColor Red
        exit 3
    }

    # --- Paso 11: filestore ----------------------------------------------
    # `web` está detenido a propósito (paso 5). `docker exec` no corre en un
    # contenedor parado, así que aquí solo se COPIA el tar; la extracción
    # ocurre después de `docker compose start web` (paso 13).
    if ($RestoreFilestore) {
        Write-Host '[6/7] Preparando el filestore (extracción tras reiniciar web)...' -ForegroundColor Cyan
        if (-not (Test-Path -LiteralPath $RestoreFilestore)) {
            Write-Host "[WARN] No se encontró el filestore: $RestoreFilestore" -ForegroundColor Yellow
            Write-Host '       Las imágenes de producto pueden verse rotas.' -ForegroundColor Yellow
            $script:pendingFilestoreTar = $null
        }
        else {
            $script:pendingFilestoreTar = (Resolve-Path -LiteralPath $RestoreFilestore).Path
        }
    }
    else {
        Write-Host '[6/7] Filestore no solicitado (usa -RestoreFilestore).' -ForegroundColor Yellow
        $script:pendingFilestoreTar = $null
    }
}
finally {
    # --- Paso 13: web SIEMPRE vuelve -------------------------------------
    # En un finally para que una restauración abortada (incluido Ctrl+C)
    # jamás deje a Odoo detenido.
    if ($webWasStopped) {
        Write-Host '[7/7] Reiniciando el servidor Odoo...' -ForegroundColor Cyan
        docker compose start web 2>&1 | Out-Null
    }

    # Extraer el filestore ahora que `web` está en ejecución.
    if ($script:pendingFilestoreTar) {
        $tarName = Split-Path -Leaf $script:pendingFilestoreTar
        docker cp $script:pendingFilestoreTar "${WEB_CONTAINER}:/tmp/$tarName" 2>&1 | Out-Null
        docker exec $WEB_CONTAINER tar -xf "/tmp/$tarName" -C /var/lib/odoo
        if ($LASTEXITCODE -eq 0) {
            Write-Host '      Filestore restaurado.' -ForegroundColor Green
        }
        else {
            Write-Host '[WARN] No se pudo extraer el filestore.' -ForegroundColor Yellow
        }
        docker exec $WEB_CONTAINER rm -f "/tmp/$tarName" 2>&1 | Out-Null
    }

    Pop-Location -ErrorAction SilentlyContinue
}

# --- Paso 14: sondear la disponibilidad -----------------------------------
# Odoo cachea el registro en memoria, por lo que sin este ciclo de parada y
# arranque la interfaz seguiría sirviendo el esquema previo a la restauración.
Write-Host "      Esperando a que Odoo esté disponible (máx. ${TimeoutSec}s)" -ForegroundColor Cyan -NoNewline
$deadline = (Get-Date).AddSeconds($TimeoutSec)
$ready    = $false

while ((Get-Date) -lt $deadline) {
    $health = (docker inspect --format '{{.State.Health.Status}}' $WEB_CONTAINER 2>$null)
    if ($health -eq 'healthy') { $ready = $true; break }
    Write-Host '.' -ForegroundColor Cyan -NoNewline
    Start-Sleep -Seconds 2
}
Write-Host ''

if (-not $ready) {
    Write-Host ''
    Write-Host "[ERROR] Los datos se restauraron, pero Odoo no llegó a saludable en ${TimeoutSec}s." -ForegroundColor Red
    Write-Host '        Revisa: .\scripts\docker-logs.ps1' -ForegroundColor Red
    exit 5
}

Write-Host ''
Write-Host "[OK] Restauración completada. La base '$dbName' refleja el respaldo." -ForegroundColor Green
exit 0
