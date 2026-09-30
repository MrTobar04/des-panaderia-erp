# SPEC-0.3.1: Automatización de Ciclo de Vida de Contenedores y Healthcheck

## 1. Objective
Proporcionar un conjunto de scripts y utilidades de automatización en PowerShell para la gestión del ciclo de vida de los contenedores Docker del ERP de la panadería "Delicias Dulces" (inicio, detención, reinicio, monitoreo de logs y verificación automática de estado de salud), permitiendo a los desarrolladores y evaluadores operar el sistema sin memorizar comandos complejos de Docker.

## 2. Scope
### 2.1. Included
* Scripts de automatización en PowerShell:
  * `scripts/docker-start.ps1`: Valida la existencia de `.env` (creándolo a partir de `.env.sample` si no existe), levanta los contenedores en modo detached y espera a que el servicio Odoo responda en `http://localhost:8069`.
  * `scripts/docker-stop.ps1`: Detiene ordenadamente todos los contenedores sin borrar volúmenes de datos.
  * `scripts/docker-restart.ps1`: Reinicia el contenedor `panaderia_odoo_web` para aplicar cambios en módulos de Python.
  * `scripts/docker-logs.ps1`: Muestra y sigue en tiempo real los logs formateados del contenedor web o base de datos.
  * `scripts/healthcheck.ps1`: Verifica de forma automatizada que los contenedores `panaderia_odoo_web` y `panaderia_odoo_db` estén en estado saludable y que el endpoint HTTP responda.
* Integración con la documentación de instalación (`Instrucciones_Instalacion.txt`).

### 2.2. Not Included (Out of Scope)
* Interfaces gráficas pesadas de escritorio (GUI en Electron) para controlar Docker.
* Notificaciones por webhook de Slack/Discord sobre el estado de los contenedores.
* Monitoreo APM continuo con Prometheus / Grafana.

## 3. Context and Restrictions
* **Context:** Facilita la experiencia de usuario y desarrollador en Windows/PowerShell conforme a los estándares de desarrollo rápido y la defensa del proyecto.
* **Restrictions:**
  * Debe ejecutarse con la política estándar de ejecución de PowerShell en Windows.
  * Los comandos destructivos (como `docker compose down -v`) deben requerir confirmación explícita para evitar pérdida accidental de datos.

## 4. Design (Implementation Details)
* **Architecture:** Wrappers de automatización en PowerShell estructurados modularmente bajo el directorio `scripts/`.
* **Script de Inicio (`scripts/docker-start.ps1`):**
  ```powershell
  $repoRoot = "$PSScriptRoot/.."
  $envFile = "$repoRoot/.env"
  $envSample = "$repoRoot/.env.sample"

  if (-not (Test-Path $envFile) -and (Test-Path $envSample)) {
      Write-Host "Creando archivo .env a partir de .env.sample..." -ForegroundColor Yellow
      Copy-Item $envSample $envFile
  }

  Write-Host "Iniciando contenedores de Panadería ERP..." -ForegroundColor Cyan
  Push-Location $repoRoot
  try {
      docker compose up -d
      Write-Host "Esperando a que los servicios estén listos..." -ForegroundColor Cyan
      Start-Sleep -Seconds 5
      & "$PSScriptRoot/healthcheck.ps1"
  } finally {
      Pop-Location
  }
  ```
* **Script de Healthcheck (`scripts/healthcheck.ps1`):**
  ```powershell
  Write-Host "--- Verificación de Estado de Panadería ERP ---" -ForegroundColor Cyan

  $dbStatus = docker inspect --format='{{.State.Health.Status}}' panaderia_odoo_db 2>$null
  if ($dbStatus -eq "healthy") {
      Write-Host "[OK] Base de datos PostgreSQL: Saludable" -ForegroundColor Green
  } else {
      Write-Host "[WARN] Base de datos PostgreSQL: $dbStatus" -ForegroundColor Yellow
  }

  $webRunning = docker inspect --format='{{.State.Running}}' panaderia_odoo_web 2>$null
  if ($webRunning -eq "true") {
      Write-Host "[OK] Servidor Odoo Web: En Ejecución" -ForegroundColor Green
      try {
          $response = Invoke-WebRequest -Uri "http://localhost:8069/web/login" -UseBasicParsing -TimeoutSec 5
          if ($response.StatusCode -eq 200 -or $response.StatusCode -eq 303) {
              Write-Host "[OK] Interfaz Web lista en http://localhost:8069" -ForegroundColor Green
          }
      } catch {
          Write-Host "[INFO] Odoo iniciando servicios HTTP..." -ForegroundColor Yellow
      }
  } else {
      Write-Host "[ERROR] Servidor Odoo Web no está corriendo" -ForegroundColor Red
  }
  ```
* **UI/UX:**
  * Indicadores visuales en consola con códigos de color para diagnóstico rápido.

## 5. Acceptance Criteria
* **Scenario 1: Inicio automatizado de un solo clic**
  * **Given** un entorno limpio donde no existe el archivo `.env`.
  * **When** el usuario ejecuta `.\scripts\docker-start.ps1`.
  * **Then** el script genera automáticamente `.env`, levanta los contenedores, ejecuta el healthcheck y confirma que la URL `http://localhost:8069` está activa.

* **Scenario 2: Diagnóstico instantáneo de fallos**
  * **Given** que el contenedor de base de datos se encuentra detenido.
  * **When** se ejecuta `.\scripts\healthcheck.ps1`.
  * **Then** el script reporta inmediatamente el error con salida en color rojo identificando el componente caído.

* **Scenario 3: Detención limpia de servicios**
  * **Given** los contenedores en ejecución.
  * **When** el usuario ejecuta `.\scripts\docker-stop.ps1`.
  * **Then** los contenedores se detienen ordenadamente sin arrojar errores de timeout y manteniendo la integridad de los datos.

## 6. Verification Plan
* **Manual UI & CLI Testing:**
  1. Ejecutar `.\scripts\docker-start.ps1` y comprobar que inicie el stack completo.
  2. Ejecutar `.\scripts\docker-logs.ps1 -Follow` y validar la recepción del stream de logs.
  3. Ejecutar `.\scripts\docker-restart.ps1` y validar que el reinicio tome menos de 5 segundos.
  4. Ejecutar `.\scripts\docker-stop.ps1` y verificar con `docker ps` que no queden contenedores huérfanos.
* **Automated Script Execution:**
  * Ejecutar `healthcheck.ps1` dentro del pipeline de verificación local.

## 7. Security and Privacy
* **Access Control:**
  * Scripts operan con los privilegios locales del usuario sin requerir elevación de administrador (salvo permisos Docker).

## 8. Risks and Mitigation
* **Risk:** Política de ejecución de scripts de PowerShell restringida en Windows (`Restricted`).
  * **Mitigation:** Documentar en `Instrucciones_Instalacion.txt` el comando `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` o ejecución vía `powershell -ExecutionPolicy Bypass -File ...`.

## 9. Deliverables & Config as Code
* `scripts/docker-start.ps1`
* `scripts/docker-stop.ps1`
* `scripts/docker-restart.ps1`
* `scripts/docker-logs.ps1`
* `scripts/healthcheck.ps1`

## 10. Definition of Done (DoD)
* [ ] Todos los scripts de PowerShell creados en el directorio `scripts/`.
* [ ] Flujo de inicio `docker-start.ps1` y apagado `docker-stop.ps1` verificado en Windows.
* [ ] Healthcheck validando código HTTP 200/303 en `http://localhost:8069`.
* [ ] Procedimiento de prueba `docs/test-procedures/test-procedure-0.3.1.md` documentado y verificado.
