# SPEC-0.1.2: Configuración del Servidor Odoo y Modos de Desarrollo

## 1. Objective
Definir la configuración técnica del servidor Odoo (`config/odoo.conf`) para el ERP de la panadería "Delicias Dulces", estableciendo rutas de addons personalizadas, activación de herramientas de desarrollo (recarga en caliente de plantillas QWeb y código Python), parámetros de rendimiento, nivel de log detallado y protección de la clave maestra de base de datos.

## 2. Scope
### 2.1. Included
* Archivo de configuración `config/odoo.conf` conteniendo:
  * `addons_path`: Inclusión prioritaria de `/mnt/extra-addons/panaderia` junto con las rutas estándar del núcleo de Odoo.
  * `data_dir`: Ruta estandarizada a `/var/lib/odoo` para el filestore.
  * `admin_passwd`: Clave maestra protegida para la creación y duplicación de bases de datos.
  * `dev_mode`: Activación de modos de recarga en caliente (`reload,qweb,werkzeug`) para acelerar el ciclo de desarrollo de vistas y modelos.
  * `log_level`: Nivel de depuración `info` / `debug` con filtrado de logs.
  * `list_db`: Habilitado para facilitar la selección de base de datos de pruebas en entorno local.
* Montaje del archivo en el contenedor web en `/etc/odoo/odoo.conf`.

### 2.2. Not Included (Out of Scope)
* Configuración de balanceadores de carga con múltiples workers (`workers > 0`) o multiproceso gevent (reservado para entornos de producción masiva).
* Configuración de servidores de correo saliente SMTP externos con DKIM/SPF.
* Integración con almacenamiento en la nube AWS S3 / Azure Blob Storage para el filestore.

## 3. Context and Restrictions
* **Context:** Este archivo es leído por el contenedor `web` durante el arranque y dicta el comportamiento de carga del módulo `Modulo_Odoo/` y sus vistas.
* **Restrictions:**
  * Debe mantener sintaxis INI estándar compatible con Odoo 16/17/18.
  * La clave de administración no debe ser la predeterminada débil (`admin`).

## 4. Design (Implementation Details)
* **Architecture:** Inyección de configuración mediante volumen bind-mount hacia `/etc/odoo/odoo.conf`.
* **Configuration Specification (`config/odoo.conf`):**
  ```ini
  [options]
  ; Rutas de Addons (Módulo personalizado primero)
  addons_path = /mnt/extra-addons/panaderia,/usr/lib/python3/dist-packages/odoo/addons

  ; Directorio de datos y filestore
  data_dir = /var/lib/odoo

  ; Clave maestra para gestión de bases de datos (Database Manager)
  admin_passwd = $pbkdf2-sha512$25000$local_bakery_erp_master_pwd

  ; Modo desarrollador y recarga en caliente
  dev_mode = reload,qweb

  ; Gestión de base de datos
  list_db = True
  db_maxconn = 32

  ; Parámetros de logs
  log_level = info
  log_handler = :INFO,odoo.addons.Modulo_Odoo:DEBUG

  ; Límite de memoria y tiempo de ejecución para desarrollo
  limit_memory_hard = 2684354560
  limit_memory_soft = 2147483648
  limit_time_cpu = 120
  limit_time_real = 240
  ```
* **UI/UX:**
  * En modo de desarrollo, las vistas modificadas en el código fuente XML se actualizan en el navegador al recargar la página (F5) o actualizar el módulo sin reiniciar el contenedor.
  * Los mensajes de error de Odoo presentan trazas completas de depuración en la consola de logs.

## 5. Acceptance Criteria
* **Scenario 1: Detección automática del módulo de panadería**
  * **Given** que el servidor Odoo inicia con el archivo `odoo.conf` montado.
  * **When** el usuario ingresa a Aplicaciones $\to$ Actualizar Lista de Aplicaciones.
  * **Then** el módulo de la panadería aparece listado y disponible para instalación inmediata desde la ruta `/mnt/extra-addons/panaderia`.

* **Scenario 2: Protección del Gestor de Base de Datos**
  * **Given** que se intenta acceder a `/web/database/manager`.
  * **When** un usuario intenta eliminar o respaldar una base de datos sin la clave maestra.
  * **Then** el sistema bloquea la acción y exige la clave `admin_passwd` configurada en `odoo.conf`.

* **Scenario 3: Depuración y visualización de logs personalizados**
  * **Given** que se ejecutan operaciones en los modelos de panadería.
  * **When** se generan eventos o excepciones de negocio.
  * **Then** los logs del contenedor muestran los mensajes de debug detallados bajo el prefijo `odoo.addons.panaderia`.

## 6. Verification Plan
* **Manual UI & CLI Testing:**
  1. Verificar que `config/odoo.conf` exista con permisos de lectura.
  2. Iniciar el contenedor y verificar en los logs iniciales (`docker compose logs web`) que la línea `addons_path` contenga `/mnt/extra-addons/panaderia`.
  3. Comprobar la activación de `dev_mode` verificando la recarga inmediata de modificaciones XML.
* **Automated Log Inspection:**
  * Grep en logs de arranque: `docker compose logs web | findstr "addons_path"`.

## 7. Security and Privacy
* **Access Control:**
  * Restricción de acceso a `odoo.conf` mediante permisos de archivo en el host (`644` o `600`).
  * Clave maestra `admin_passwd` cifrada o definida con alta entropía.

## 8. Risks and Mitigation
* **Risk:** Conflicto de rutas si la carpeta `Modulo_Odoo` no se monta correctamente.
  * **Mitigation:** Validación en el script de arranque que confirme la existencia física del directorio antes de lanzar Docker Compose.

## 9. Deliverables & Config as Code
* Archivo `config/odoo.conf`.
* Mapeo de volumen en `docker-compose.yml`.

## 10. Definition of Done (DoD)
* [ ] Archivo `config/odoo.conf` creado con todos los parámetros de desarrollo.
* [ ] Montaje hacia `/etc/odoo/odoo.conf` verificado en el contenedor `web`.
* [ ] Addons path reconociendo `Modulo_Odoo/` al iniciar Odoo.
* [ ] Procedimiento de prueba `docs/test-procedures/test-procedure-0.1.2.md` documentado y verificado.
