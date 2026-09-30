# SPEC-0.1.1: Aprovisionamiento de Entorno Local en Docker

## 1. Objective
Definir y automatizar la infraestructura base de contenedores Docker para el sistema ERP de la panadería "Delicias Dulces", permitiendo orquestar de manera determinista los servicios de aplicación (Odoo 16/17) y base de datos (PostgreSQL 15/16), con aislamiento de red, persistencia de volúmenes y gestión segura de secretos según ISO-27001.

## 2. Scope
### 2.1. Included
* Archivo de orquestación `docker-compose.yml` multi-servicio:
  * Servicio `web`: Imagen oficial `odoo:16.0` con binding de puertos `8069:8069` y `8072:8072`.
  * Servicio `db`: Imagen oficial `postgres:15-alpine` con healthcheck activo y reinicio `unless-stopped`.
  * Red privada virtual Docker `panaderia-net` (driver `bridge`) para comunicación interna segura.
  * Volúmenes con nombre persistentes: `odoo-web-data` (filestore y sesiones) y `odoo-db-data` (datos PostgreSQL).
  * Montaje de volumen tipo bind-mount: `./Modulo_Odoo` mapeado a `/mnt/extra-addons/panaderia`.
* Configuración de variables de entorno mediante `.env` y archivo plantilla `.env.sample`.
* Inclusión de `.env` en `.gitignore` para salvaguardar credenciales.

### 2.2. Not Included (Out of Scope)
* Configuración de proxies inversos perimetrales Nginx / Traefik con certificados SSL en producción.
* Orquestación distribuida en Kubernetes (K8s) o Docker Swarm.
* Clusterización activa-pasiva de bases de datos PostgreSQL.

## 3. Context and Restrictions
* **Context:** Constituye la capa fundamental de ejecución (Capa 0) sobre la cual operan los módulos de negocio (Inventario, Ventas, Clientes, Facturación y Reportes).
* **Restrictions:**
  * No exponer el puerto de PostgreSQL (`5432`) al host a menos que se active explícitamente para depuración.
  * Compatibilidad cruzada garantizada para Windows (WSL2 / Docker Desktop) y Linux.
  * Ninguna credencial ni clave maestra debe quedar registrada en el historial de Git.

## 4. Design (Implementation Details)
* **Architecture:** Topología de 2 niveles (App + DB) con red bridge privada y almacenamiento desacoplado.
* **Orchestration Config (`docker-compose.yml`):**
  ```yaml
  version: '3.8'

  networks:
    panaderia-net:
      name: panaderia-net
      driver: bridge

  volumes:
    odoo-web-data:
      name: panaderia_odoo_web_data
    odoo-db-data:
      name: panaderia_odoo_db_data

  services:
    db:
      image: postgres:15-alpine
      container_name: panaderia_odoo_db
      restart: unless-stopped
      environment:
        POSTGRES_DB: ${POSTGRES_DB:-postgres}
        POSTGRES_USER: ${POSTGRES_USER:-odoo}
        POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-odoo_dev_password}
        PGDATA: /var/lib/postgresql/data/pgdata
      volumes:
        - odoo-db-data:/var/lib/postgresql/data/pgdata
      networks:
        - panaderia-net
      healthcheck:
        test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-odoo} -d ${POSTGRES_DB:-postgres}"]
        interval: 5s
        timeout: 5s
        retries: 5

    web:
      image: odoo:16.0
      container_name: panaderia_odoo_web
      restart: unless-stopped
      depends_on:
        db:
          condition: service_healthy
      ports:
        - "${ODOO_HTTP_PORT:-8069}:8069"
        - "${ODOO_CHAT_PORT:-8072}:8072"
      environment:
        HOST: db
        PORT: 5432
        USER: ${POSTGRES_USER:-odoo}
        PASSWORD: ${POSTGRES_PASSWORD:-odoo_dev_password}
      volumes:
        - odoo-web-data:/var/lib/odoo
        - ./config:/etc/odoo
        - ./Modulo_Odoo:/mnt/extra-addons/panaderia
      networks:
        - panaderia-net
  ```
* **Environment Template (`.env.sample`):**
  ```bash
  # Docker Compose Environment Configuration
  COMPOSE_PROJECT_NAME=panaderia-erp
  POSTGRES_DB=postgres
  POSTGRES_USER=odoo
  POSTGRES_PASSWORD=odoo_dev_password_change_me
  ODOO_HTTP_PORT=8069
  ODOO_CHAT_PORT=8072
  ```
* **UI/UX:**
  * Acceso web instantáneo en `http://localhost:8069`.
  * Visualización de logs unificados con nombres legibles de contenedores.

## 5. Acceptance Criteria
* **Scenario 1: Inicio exitoso de la pila de servicios**
  * **Given** un entorno local con Docker y Docker Compose activos y el archivo `.env` configurado.
  * **When** el usuario ejecuta `docker compose up -d`.
  * **Then** el contenedor `db` alcanza estado `healthy`, `web` se inicia sin errores de conexión y el puerto `8069` responde con código HTTP 200/303.

* **Scenario 2: Reanudación tras detención forzada**
  * **Given** que la base de datos de Odoo contiene productos y ventas creadas.
  * **When** se detienen los contenedores mediante `docker compose down` y se reinician con `docker compose up -d`.
  * **Then** todos los datos, configuraciones y módulos instalados persisten sin pérdida de información.

* **Scenario 3: Aislamiento seguro de PostgreSQL**
  * **Given** que los contenedores están en ejecución.
  * **When** se intenta conectar desde el host al puerto 5432 sin mapeo explícito.
  * **Then** la conexión externa es rechazada, verificando el aislamiento en la red privada `panaderia-net`.

## 6. Verification Plan
* **Manual UI & CLI Testing:**
  1. Ejecutar `docker compose config` para verificar sintaxis YAML.
  2. Ejecutar `docker compose up -d` y validar salida con `docker compose ps`.
  3. Comprobar que `http://localhost:8069` carga la pantalla de inicio o selección de base de datos.
  4. Ejecutar `docker compose down` y verificar que los volúmenes `panaderia_odoo_web_data` y `panaderia_odoo_db_data` continúen existiendo en el sistema.
* **Automated Healthcheck:**
  * Validación de estado `healthy` mediante inspección de contenedor: `docker inspect --format='{{json .State.Health.Status}}' panaderia_odoo_db`.

## 7. Security and Privacy
* **ISO-27001 Secret Management:**
  * `.env` explícitamente ignorado en `.gitignore`.
  * Parámetros por defecto en `.env.sample` marcados con sufijo `_change_me`.
  * Sin credenciales estáticas ni contraseñas maestras incrustadas en código fuente.

## 8. Risks and Mitigation
* **Risk:** Conflicto con el puerto 8069 si IIS, Apache u otra instancia de Odoo está en ejecución.
  * **Mitigation:** Configuración variable en `.env` (`ODOO_HTTP_PORT=8070`) para reasignación inmediata de puerto.

## 9. Deliverables & Config as Code
* Archivo `docker-compose.yml` en la raíz del proyecto.
* Archivo `.env.sample` en la raíz del proyecto.
* Archivo `.gitignore` asegurando la exclusión de `.env`.

## 10. Definition of Done (DoD)
* [ ] Archivo `docker-compose.yml` validado con `docker compose config`.
* [ ] Servicios `web` y `db` comunicándose a través de la red `panaderia-net`.
* [ ] Volúmenes de datos configurados y persistiendo entre reinicios.
* [ ] Procedimiento de prueba `docs/test-procedures/test-procedure-0.1.1.md` completado y verificado.
