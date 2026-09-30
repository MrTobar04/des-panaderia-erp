# SPEC-0.2.1: Persistencia, Semillas y Respaldos de Base de Datos PostgreSQL

## 1. Objective
Definir los mecanismos de persistencia de datos, carga de datos semilla de demostración y automatización de respaldos (`backup`) y restauraciones (`restore`) para la base de datos PostgreSQL del ERP de la panadería "Delicias Dulces", garantizando la integridad de las transacciones, la continuidad operativa y la facilidad para reiniciar el entorno de pruebas antes de una defensa o demo presencial.

## 2. Scope
### 2.1. Included
* Persistencia en almacenamiento con nombre `odoo-db-data` montado en `/var/lib/postgresql/data/pgdata`.
* Scripts de automatización en PowerShell:
  * `scripts/db-backup.ps1`: Generación de volcado binario comprimido de PostgreSQL (`pg_dump -Fc`) con timestamp en la carpeta `backups/`.
  * `scripts/db-restore.ps1`: Restauración limpia de base de datos desde un archivo de volcado `.dump` o `.sql`.
  * `scripts/db-init-seed.ps1`: Inicialización rápida con base de datos de demostración preconfigurada con productos, clientes y órdenes de prueba.
* Carpeta `backups/` en el proyecto, excluida en `.gitignore` para volcados pesados, pero permitiendo un archivo `seed_demo.dump` versionado para la evaluación.

### 2.2. Not Included (Out of Scope)
* Respaldos automáticos continuos en tiempo real mediante replicación streaming WAL.
* Envío automatizado de backups a buckets de Amazon S3 o Google Cloud Storage.
* Herramientas de recuperación ante desastres en tiempo real (RPO = 0 / RTO = 0).

## 3. Context and Restrictions
* **Context:** Permite congelar el estado de la base de datos tras cargar datos de prueba para la evaluación del Desafío 3 (defensa de 10-12 minutos) y restaurarlo instantáneamente si ocurre algún error durante la demostración.
* **Restrictions:**
  * Los volcados deben generarse sin detener el contenedor de base de datos (`hot backup`).
  * Los scripts deben verificar que los contenedores de Docker estén activos antes de intentar el volcado o restauración.

## 4. Design (Implementation Details)
* **Architecture:** Ejecución de comandos nativos de PostgreSQL (`pg_dump`, `pg_restore`, `dropdb`, `createdb`) dentro del contenedor `panaderia_odoo_db` mediante llamadas directas `docker exec`.
* **Script de Backup (`scripts/db-backup.ps1`):**
  ```powershell
  param(
      [string]$BackupName = "panaderia_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').dump"
  )

  $backupDir = "$PSScriptRoot/../backups"
  if (-not (Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir | Out-Null }

  Write-Host "Generando respaldo de base de datos: $BackupName..." -ForegroundColor Cyan
  docker exec -t panaderia_odoo_db pg_dump -U odoo -d postgres -F c -b -v -f "/tmp/$BackupName"
  docker cp "panaderia_odoo_db:/tmp/$BackupName" "$backupDir/$BackupName"
  docker exec panaderia_odoo_db rm "/tmp/$BackupName"

  Write-Host "Respaldo completado exitosamente en: $backupDir/$BackupName" -ForegroundColor Green
  ```
* **Script de Restore (`scripts/db-restore.ps1`):**
  ```powershell
  param(
      [Parameter(Mandatory=$true)]
      [string]$BackupFile
  )

  if (-not (Test-Path $BackupFile)) {
      Write-Error "El archivo de respaldo especificado no existe: $BackupFile"
      exit 1
  }

  $fileName = Split-Path $BackupFile -Leaf
  Write-Host "Restaurando base de datos desde: $fileName..." -ForegroundColor Yellow

  # Copiar respaldo al contenedor
  docker cp $BackupFile "panaderia_odoo_db:/tmp/$fileName"

  # Reiniciar conexiones y restaurar
  docker exec -t panaderia_odoo_db psql -U odoo -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'postgres' AND pid <> pg_backend_pid();"
  docker exec -t panaderia_odoo_db pg_restore -U odoo -d postgres --clean --if-exists "/tmp/$fileName"
  docker exec panaderia_odoo_db rm "/tmp/$fileName"

  Write-Host "Restauración finalizada exitosamente." -ForegroundColor Green
  ```
* **UI/UX:**
  * Mensajes claros por consola con colores informativos (Cyan = progreso, Green = éxito, Red = error).

## 5. Acceptance Criteria
* **Scenario 1: Creación de respaldo bajo demanda**
  * **Given** que el sistema ERP contiene 15 productos y 8 ventas registradas.
  * **When** el usuario ejecuta `.\scripts\db-backup.ps1`.
  * **Then** se genera un archivo `.dump` en la carpeta `backups/` con tamaño mayor a cero y formato binario válido.

* **Scenario 2: Restauración íntegra de estado previo**
  * **Given** un archivo de respaldo generado previamente y una base de datos alterada o con registros eliminados.
  * **When** el usuario ejecuta `.\scripts\db-restore.ps1 -BackupFile .\backups\seed_demo.dump`.
  * **Then** la base de datos se restablece exactamente al estado guardado, recuperando todos los registros sin errores de integridad referencial.

* **Scenario 3: Validación de dependencias de contenedores**
  * **Given** que los contenedores de Docker están apagados.
  * **When** se intenta ejecutar el script de respaldo o restauración.
  * **Then** el script detecta que el contenedor `panaderia_odoo_db` no está en ejecución y muestra un mensaje de advertencia guiando a iniciar los contenedores primero.

## 6. Verification Plan
* **Manual UI & CLI Testing:**
  1. Crear un producto de prueba "Tarta de Manzana Especial".
  2. Ejecutar `.\scripts\db-backup.ps1 -BackupName test_backup.dump`.
  3. Eliminar el producto desde la interfaz web de Odoo.
  4. Ejecutar `.\scripts\db-restore.ps1 -BackupFile .\backups\test_backup.dump`.
  5. Refrescar la vista en Odoo y verificar que "Tarta de Manzana Especial" reaparece con todos sus datos.
* **Automated File Check:**
  * Verificación de existencia del archivo en `backups/` y validación de cabecera con comando `pg_restore -l`.

## 7. Security and Privacy
* **Access Control:**
  * Los respaldos contienen datos del negocio y deben almacenarse localmente.
  * No subir archivos de respaldo con datos reales a repositorios públicos.

## 8. Risks and Mitigation
* **Risk:** Bloqueo de restauración por sesiones activas en Odoo.
  * **Mitigation:** Terminación forzada de conexiones activas (`pg_terminate_backend`) previo a la ejecución del comando `pg_restore`.

## 9. Deliverables & Config as Code
* Script `scripts/db-backup.ps1`.
* Script `scripts/db-restore.ps1`.
* Carpeta `backups/` con archivo `.gitkeep` y reglas en `.gitignore`.

## 10. Definition of Done (DoD)
* [ ] Script `db-backup.ps1` probado y generando volcados sin errores.
* [ ] Script `db-restore.ps1` probado recuperando estados de base de datos con éxito.
* [ ] Persistencia de volumen `odoo-db-data` verificada.
* [ ] Procedimiento de prueba `docs/test-procedures/test-procedure-0.2.1.md` documentado y verificado.
