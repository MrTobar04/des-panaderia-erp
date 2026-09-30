<#
.SYNOPSIS
    Renderiza config/odoo.conf.template a config/odoo.conf inyectando la clave
    maestra desde .env (SPEC-0.1.2).

.DESCRIPTION
    El parser INI de Odoo NO interpola variables de entorno: una línea
    `admin_passwd = ${ODOO_ADMIN_PASSWD}` se consume como ese literal. La
    sustitución debe ocurrir en el host antes de que el contenedor lea el
    archivo. Este script es la única pieza de inyección de secretos en
    tiempo de ejecución de la Capa 0.

    Es idempotente: ejecutarlo N veces con el mismo .env produce una salida
    byte a byte idéntica. Nunca omite el renderizado por marcas de tiempo.

.NOTES
    Códigos de salida:
      0  Renderizado correcto (o correcto con advertencia de placeholder)
      1  Plantilla ausente, .env ausente, ODOO_ADMIN_PASSWD vacía,
         o Modulo_Odoo/__manifest__.py ausente
#>
[CmdletBinding()]
param()

# El host puede estar en una pagina de codigos heredada (CP850/CP437), en la
# que los acentos de los mensajes en espanol se verian corruptos. Se fija la
# salida a UTF-8 para cumplir el Principio V de la Constitucion.
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

$ErrorActionPreference = 'Stop'

$repoRoot     = Split-Path -Parent $PSScriptRoot
$templatePath = Join-Path $repoRoot 'config/odoo.conf.template'
$outputPath   = Join-Path $repoRoot 'config/odoo.conf'
$envPath      = Join-Path $repoRoot '.env'
$manifestPath = Join-Path $repoRoot 'Modulo_Odoo/__manifest__.py'

# --- Validaciones previas (ninguna escribe nada) -------------------------
# Todo fallo ocurre ANTES de tocar config/odoo.conf, por lo que un
# renderizado fallido deja intacto el archivo previo.

if (-not (Test-Path -LiteralPath $templatePath)) {
    Write-Host 'ERROR: No se encontró la plantilla config/odoo.conf.template' -ForegroundColor Red
    exit 1
}

if (-not (Test-Path -LiteralPath $envPath)) {
    Write-Host 'ERROR: No existe .env. Ejecuta: Copy-Item .env.sample .env' -ForegroundColor Red
    exit 1
}

if (-not (Test-Path -LiteralPath $manifestPath)) {
    Write-Host 'ERROR: No se encontró Modulo_Odoo/__manifest__.py. El módulo no se montará.' -ForegroundColor Red
    exit 1
}

# --- Lectura de .env ------------------------------------------------------
# Se divide en el PRIMER '=' únicamente: una contraseña puede contenerlo.
$envVars = @{}
foreach ($line in Get-Content -LiteralPath $envPath -Encoding UTF8) {
    $trimmed = $line.Trim()
    if ($trimmed -eq '' -or $trimmed.StartsWith('#')) { continue }

    $separator = $trimmed.IndexOf('=')
    if ($separator -lt 1) { continue }

    $key   = $trimmed.Substring(0, $separator).Trim()
    $value = $trimmed.Substring($separator + 1).Trim()

    if ($value.Length -ge 2 -and
        (($value.StartsWith('"') -and $value.EndsWith('"')) -or
         ($value.StartsWith("'") -and $value.EndsWith("'")))) {
        $value = $value.Substring(1, $value.Length - 2)
    }

    $envVars[$key] = $value
}

$adminPasswd = $envVars['ODOO_ADMIN_PASSWD']
$pgUser      = $envVars['POSTGRES_USER']
$pgPassword  = $envVars['POSTGRES_PASSWORD']

if ([string]::IsNullOrWhiteSpace($adminPasswd)) {
    Write-Host 'ERROR: ODOO_ADMIN_PASSWD no está definida en .env' -ForegroundColor Red
    exit 1
}

if ([string]::IsNullOrWhiteSpace($pgUser)) {
    Write-Host 'ERROR: POSTGRES_USER no está definida en .env' -ForegroundColor Red
    exit 1
}

if ([string]::IsNullOrWhiteSpace($pgPassword)) {
    Write-Host 'ERROR: POSTGRES_PASSWORD no está definida en .env' -ForegroundColor Red
    exit 1
}

# --- Sustitución ---------------------------------------------------------
$content = Get-Content -LiteralPath $templatePath -Raw -Encoding UTF8
$content = $content.Replace('${ODOO_ADMIN_PASSWD}', $adminPasswd)
$content = $content.Replace('${POSTGRES_USER}',     $pgUser)
$content = $content.Replace('${POSTGRES_PASSWORD}', $pgPassword)

# LF obligatorio: el archivo se lee dentro de un contenedor Linux y un CRLF
# dejaría un retorno de carro al final de cada valor, de modo que
# `addons_path` resolvería a una ruta inexistente.
$content = $content -replace "`r`n", "`n"
$content = $content -replace "`r", "`n"

# UTF-8 SIN BOM: un BOM en la primera línea rompe el parseo de la
# cabecera [options] por parte de configparser.
[System.IO.File]::WriteAllText($outputPath, $content, (New-Object System.Text.UTF8Encoding($false)))

# --- Informe (nunca imprime el valor de ningún secreto) ------------------
Write-Host '[OK] config/odoo.conf generado (credenciales inyectadas desde .env)' -ForegroundColor Green

if ($adminPasswd -eq 'bakery_master_key_change_me') {
    Write-Host 'ADVERTENCIA: ODOO_ADMIN_PASSWD conserva el valor de ejemplo. Cámbialo antes de la entrega.' -ForegroundColor Yellow
}

exit 0
