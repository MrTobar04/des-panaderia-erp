<#
.SYNOPSIS
    Respaldo en caliente de la base de datos de negocio (SPEC-0.2.1).

.DESCRIPTION
    Produce un volcado en formato personalizado (-F c) de $ODOO_DB_NAME,
    validado y con marca de tiempo, en ./backups/. El contenedor de base de
    datos NUNCA se detiene: `pg_dump` toma una instantánea consistente en una
    sola transacción.

    CRÍTICO: el volcado apunta a $ODOO_DB_NAME, NUNCA a `postgres`. Un
    volcado de la base de mantenimiento `postgres` produce un archivo válido,
    no vacío y estructuralmente correcto que NO CONTIENE NINGÚN DATO de
    panadería: un fallo que aprueba una verificación por tamaño.

    Por eso la validación no se conforma con el tamaño: exige que
    `pg_restore -l` liste la relación panaderia_producto.

.PARAMETER BackupName
    Nombre del archivo de salida dentro de ./backups/.

.PARAMETER IncludeFilestore
    Archiva también /var/lib/odoo/filestore como <base>_filestore.tar.
    Obligatorio si el respaldo se restaurará sobre un filestore vacío, o las
    imágenes de producto se verán rotas.

.NOTES
    Códigos de salida:
      0  Respaldo escrito y validado
      1  Falló una precondición
      2  Falló pg_dump
      3  Falló la transferencia, o el artefacto no pasó la validación
#>
[CmdletBinding()]
param(
    [string]$BackupName = "panaderia_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').dump",
    [switch]$IncludeFilestore
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

# División en el PRIMER '=' únicamente: una contraseña puede contenerlo.
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

# Se sondea .State.Running y NO .State.Health.Status: una base en ejecución
# pero aún no marcada como saludable acepta perfectamente pg_dump.
$running = docker inspect --format '{{.State.Running}}' $DB_CONTAINER 2>$null
if ($LASTEXITCODE -ne 0 -or $running -ne 'true') {
    Write-Host "ERROR: El contenedor $DB_CONTAINER no está en ejecución." -ForegroundColor Red
    Write-Host '       Ejecuta primero: .\scripts\docker-start.ps1' -ForegroundColor Red
    exit 1
}

try {
    Push-Location $repoRoot

    $backupDir = Join-Path $repoRoot 'backups'
    if (-not (Test-Path -LiteralPath $backupDir)) {
        New-Item -ItemType Directory -Path $backupDir | Out-Null
    }

    $hostPath      = Join-Path $backupDir $BackupName
    $containerPath = "/tmp/$BackupName"
    $baseName      = [System.IO.Path]::GetFileNameWithoutExtension($BackupName)

    Write-Host ''
    Write-Host "Generando respaldo de base de datos: $BackupName..." -ForegroundColor Cyan
    Write-Host "  Base de datos de origen: $dbName" -ForegroundColor Cyan

    # --- Volcado dentro del contenedor -----------------------------------
    # Sin la bandera -t: un pseudo-TTY traduce LF a CRLF y jamás debe tocar
    # un flujo binario.
    docker exec $DB_CONTAINER pg_dump -U $pgUser -d $dbName -F c -b -f $containerPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host '[ERROR] pg_dump falló. No se generó ningún respaldo.' -ForegroundColor Red
        docker exec $DB_CONTAINER rm -f $containerPath 2>&1 | Out-Null
        exit 2
    }

    # --- Recuperación byte a byte ----------------------------------------
    # `docker cp` transfiere un flujo tar exacto. Nunca se usa `>` ni
    # `Out-File`: son operadores de TEXTO que aplican una codificación y
    # corromperían el archivo binario de forma irrecuperable.
    docker cp "${DB_CONTAINER}:${containerPath}" $hostPath
    $copyFailed = ($LASTEXITCODE -ne 0)

    # La limpieza ocurre incluso si la copia falló: no se deja residuo.
    docker exec $DB_CONTAINER rm -f $containerPath 2>&1 | Out-Null

    if ($copyFailed -or -not (Test-Path -LiteralPath $hostPath)) {
        Write-Host '[ERROR] Falló la transferencia del artefacto con docker cp.' -ForegroundColor Red
        if (Test-Path -LiteralPath $hostPath) { Remove-Item -LiteralPath $hostPath -Force }
        exit 3
    }

    # --- Validación del artefacto ----------------------------------------
    # El tamaño y la capacidad de ser parseado NO son evidencia: un volcado
    # de `postgres` satisface ambos. Se exige la presencia de las relaciones.
    Write-Host 'Validando el artefacto...' -ForegroundColor Cyan
    docker cp $hostPath "${DB_CONTAINER}:/tmp/verify.dump" 2>&1 | Out-Null
    $toc = docker exec $DB_CONTAINER pg_restore -l /tmp/verify.dump 2>$null
    $tocExit = $LASTEXITCODE
    docker exec $DB_CONTAINER rm -f /tmp/verify.dump 2>&1 | Out-Null

    if ($tocExit -ne 0) {
        Write-Host '[ERROR] El artefacto no es un archivo válido de formato personalizado.' -ForegroundColor Red
        Remove-Item -LiteralPath $hostPath -Force
        exit 3
    }

    if (($toc -join "`n") -notmatch 'panaderia_producto') {
        Write-Host '[ERROR] El respaldo NO contiene datos de panadería.' -ForegroundColor Red
        Write-Host "        pg_restore -l no lista la relación panaderia_producto." -ForegroundColor Red
        Write-Host "        ¿El módulo está instalado en la base '$dbName'?" -ForegroundColor Red
        Remove-Item -LiteralPath $hostPath -Force
        exit 3
    }

    # --- Rama del filestore ----------------------------------------------
    $filestoreDone = $false
    if ($IncludeFilestore) {
        $webRunning = docker inspect --format '{{.State.Running}}' $WEB_CONTAINER 2>$null
        if ($webRunning -ne 'true') {
            Write-Host "[WARN] $WEB_CONTAINER no está en ejecución: se omite el filestore." -ForegroundColor Yellow
        }
        else {
            Write-Host 'Archivando el filestore...' -ForegroundColor Cyan
            $tarName          = "${baseName}_filestore.tar"
            $tarContainerPath = "/tmp/$tarName"
            $tarHostPath      = Join-Path $backupDir $tarName

            docker exec $WEB_CONTAINER tar -cf $tarContainerPath -C /var/lib/odoo filestore
            if ($LASTEXITCODE -eq 0) {
                docker cp "${WEB_CONTAINER}:${tarContainerPath}" $tarHostPath 2>&1 | Out-Null
                $filestoreDone = ($LASTEXITCODE -eq 0)
            }
            docker exec $WEB_CONTAINER rm -f $tarContainerPath 2>&1 | Out-Null

            if ($filestoreDone) {
                $tarSize = [math]::Round((Get-Item -LiteralPath $tarHostPath).Length / 1KB, 0)
                Write-Host "[OK]   Filestore archivado: backups/$tarName ($tarSize KB)" -ForegroundColor Green
            }
            else {
                Write-Host '[WARN] No se pudo archivar el filestore.' -ForegroundColor Yellow
            }
        }
    }

    # --- Informe ---------------------------------------------------------
    $sizeKB = [math]::Round((Get-Item -LiteralPath $hostPath).Length / 1KB, 0)
    Write-Host ''
    Write-Host "[OK] Respaldo completado: backups/$BackupName ($sizeKB KB)" -ForegroundColor Green
    Write-Host "     Contiene datos de panadería verificados (panaderia_producto presente)." -ForegroundColor Green

    if (-not $IncludeFilestore) {
        Write-Host '[WARN] Filestore no incluido. Usa -IncludeFilestore para un respaldo completo.' -ForegroundColor Yellow
    }

    exit 0
}
finally {
    Pop-Location -ErrorAction SilentlyContinue
}
