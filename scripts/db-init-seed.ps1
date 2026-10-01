<#
.SYNOPSIS
    Lleva la pila desde cualquier estado a un ERP demostrable (SPEC-0.2.1).

.DESCRIPTION
    Es la única ruta de un solo comando desde cualquier estado -- incluido un
    clon reciente con volúmenes vacíos -- hasta un ERP demostrable.

    Dos ramas:
      * Si existe -SeedFile, delega en db-restore.ps1, reutilizando la ruta de
        restauración ya validada en lugar de duplicarla.
      * Si no existe, arranca desde cero: crea $ODOO_DB_NAME e instala el
        módulo, con lo que se cargan los datos maestros XML del propio módulo
        (Modulo_Odoo/data/*.xml).

.PARAMETER SeedFile
    Artefacto de semilla a cargar. Predeterminado ./backups/seed_demo.dump.

.PARAMETER Force
    Omite la confirmación interactiva.

.NOTES
    Códigos de salida:
      0  Estado de demostración listo
      1  Falló una precondición
      2  Falló la creación de la base de datos o la instalación del módulo
      3+ Propagado desde db-restore.ps1
#>
[CmdletBinding()]
param(
    [string]$SeedFile = './backups/seed_demo.dump',
    [switch]$Force
)

# El host puede estar en una pagina de codigos heredada (CP850/CP437), en la
# que los acentos de los mensajes en espanol se verian corruptos. Se fija la
# salida a UTF-8 para cumplir el Principio V de la Constitucion.
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

$DB_CONTAINER = 'panaderia_odoo_db'

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

$pgUser   = $envVars['POSTGRES_USER']
$dbName   = $envVars['ODOO_DB_NAME']
$odooPort = if ($envVars['ODOO_HTTP_PORT']) { $envVars['ODOO_HTTP_PORT'] } else { '8069' }

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

try {
    Push-Location $repoRoot

    Write-Host ''
    Write-Host '--- Inicialización de datos de demostración ---' -ForegroundColor Cyan
    Write-Host ''

    # --- Rama 1: existe la semilla -> delegar en la restauración ----------
    if (Test-Path -LiteralPath $SeedFile) {
        Write-Host "Semilla encontrada: $SeedFile" -ForegroundColor Cyan

        # El volcado y su acompañante de filestore son una UNIDAD: restaurar
        # uno sin el otro es válido pero parcial, y en un filestore vacío las
        # imágenes de producto se ven rotas.
        $seedBase     = [System.IO.Path]::GetFileNameWithoutExtension($SeedFile)
        $seedDir      = Split-Path -Parent $SeedFile
        $pairedTar    = Join-Path $seedDir "${seedBase}_filestore.tar"

        # Splatting con TABLA HASH, no con arreglo: un arreglo se enlaza por
        # POSICIÓN, de modo que `-Force` acabaría en `-TimeoutSec`.
        $restoreParams = @{ BackupFile = $SeedFile; Force = $true }
        if (Test-Path -LiteralPath $pairedTar) {
            Write-Host "Filestore acompañante encontrado: $pairedTar" -ForegroundColor Cyan
            $restoreParams['RestoreFilestore'] = $pairedTar
        }
        else {
            Write-Host '[WARN] Sin filestore acompañante: las imágenes pueden verse rotas.' -ForegroundColor Yellow
        }

        if (-not $Force) {
            Write-Host ''
            Write-Host "ADVERTENCIA: se reemplazará por completo la base de datos '$dbName'." -ForegroundColor Yellow
            $answer = Read-Host '¿Continuar? (s/N)'
            if ($answer -notmatch '^[sS]([iíIÍ])?$') {
                Write-Host 'Operación cancelada. No se modificó nada.' -ForegroundColor Green
                exit 0
            }
        }

        # Un fallo de enlace de parámetros no fija $LASTEXITCODE, así que se
        # captura como excepción: de lo contrario el fallo pasaría por éxito.
        $global:LASTEXITCODE = 0
        try {
            $prevErrorAction = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            if (Test-Path Variable:PSNativeCommandUseErrorActionPreference) {
                $PSNativeCommandUseErrorActionPreference = $false
            }
            & (Join-Path $PSScriptRoot 'db-restore.ps1') @restoreParams
            $restoreExit = $LASTEXITCODE
        }
        catch {
            Write-Host "[ERROR] No se pudo invocar db-restore.ps1: $($_.Exception.Message)" -ForegroundColor Red
            exit 3
        }
        finally {
            $ErrorActionPreference = $prevErrorAction
        }

        if ($restoreExit -ne 0) {
            Write-Host "[ERROR] La restauración de la semilla falló (código $restoreExit)." -ForegroundColor Red
            exit $restoreExit
        }

        Write-Host ''
        Write-Host '[OK] Estado de demostración restaurado desde la semilla.' -ForegroundColor Green
        Write-Host "     Catálogo, ventas, facturas y alertas de stock disponibles." -ForegroundColor Green
        Write-Host ''
        Write-Host "     Abre: http://localhost:$odooPort" -ForegroundColor Green
        exit 0
    }

    # --- Rama 2: sin semilla -> arranque desde cero -----------------------
    Write-Host "No existe $SeedFile. Arrancando desde cero." -ForegroundColor Yellow
    Write-Host ''

    $dbList = docker exec $DB_CONTAINER psql -U $pgUser -lqt 2>$null
    $dbExists = ($LASTEXITCODE -eq 0 -and ($dbList -join "`n") -match [regex]::Escape($dbName))

    if ($dbExists) {
        Write-Host "La base de datos '$dbName' ya existe." -ForegroundColor Cyan
        if (-not $Force) {
            $answer = Read-Host "¿Reinstalar el módulo panaderia sobre ella? (s/N)"
            if ($answer -notmatch '^[sS]([iíIÍ])?$') {
                Write-Host 'Operación cancelada. No se modificó nada.' -ForegroundColor Green
                exit 0
            }
        }
    }
    else {
        Write-Host "Creando la base de datos '$dbName'..." -ForegroundColor Cyan
        docker exec $DB_CONTAINER createdb -U $pgUser -O $pgUser $dbName
        if ($LASTEXITCODE -ne 0) {
            Write-Host '[ERROR] No se pudo crear la base de datos.' -ForegroundColor Red
            exit 2
        }
    }

    Write-Host 'Instalando el módulo panaderia (puede tardar ~60s)...' -ForegroundColor Cyan
    docker compose exec web odoo -d $dbName -i panaderia --stop-after-init
    if ($LASTEXITCODE -ne 0) {
        Write-Host '[ERROR] La instalación del módulo panaderia falló.' -ForegroundColor Red
        Write-Host '        Revisa el detalle con: .\scripts\docker-logs.ps1' -ForegroundColor Red
        exit 2
    }

    Write-Host 'Reiniciando el servidor Odoo...' -ForegroundColor Cyan
    docker compose restart web 2>&1 | Out-Null

    Write-Host ''
    Write-Host '[OK] Módulo panaderia instalado con sus datos maestros XML.' -ForegroundColor Green
    Write-Host '     Se cargaron las categorías y los productos de Modulo_Odoo/data/*.xml.' -ForegroundColor Green
    Write-Host ''
    Write-Host '[WARN] El estado TRANSACCIONAL (órdenes de venta, facturas, movimientos' -ForegroundColor Yellow
    Write-Host '       de stock) NO puede sembrarse desde XML: debe crearse a través de la' -ForegroundColor Yellow
    Write-Host '       interfaz antes de capturar una nueva semilla con:' -ForegroundColor Yellow
    Write-Host '       .\scripts\db-backup.ps1 -BackupName seed_demo.dump -IncludeFilestore' -ForegroundColor Yellow
    Write-Host ''
    Write-Host "     Abre: http://localhost:$odooPort" -ForegroundColor Green

    exit 0
}
finally {
    Pop-Location -ErrorAction SilentlyContinue
}
