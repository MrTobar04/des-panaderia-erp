# Procedimiento de Prueba: SPEC-0.1.1 Aprovisionamiento de Entorno Local en Docker

**Documento ID**: `test-procedure-0.1.1.md`
**Especificación**: `specs/0-infrastructure/0.1-docker-provisioning/0.1.1-local-docker-environment/spec.md`
**Guía de verificación**: `quickstart.md` §§3–8
**Fecha**: 2026-09-29

---

## 1. Objetivo

Validar que `docker compose up -d` levanta Odoo + PostgreSQL en `panaderia-net`, que los volúmenes sobreviven un `down`/`up`, y que el puerto 5432 no se publica en el host.

---

## 2. Prerrequisitos

- [x] Docker Engine y Compose v2 (`docker compose version` ≥ v2.20)
- [x] `.env` presente (copiado de `.env.sample`)
- [x] `Modulo_Odoo/__manifest__.py` presente
- [x] `docker compose config` sale 0 sin `WARN` (sin clave `version:`)

---

## 3. Casos de prueba

### TP-0.1.1-01 — Inicio exitoso (Escenario 1)

1. `docker compose up -d`
2. `docker inspect --format='{{.State.Health.Status}}' panaderia_odoo_db` → `healthy`
3. Esperar `healthy` en `panaderia_odoo_web` (hasta 90 s en frío)
4. `Invoke-WebRequest http://localhost:8069/web/login -UseBasicParsing` → 200
5. `docker compose logs web | Select-String addons_path` contiene `/mnt/extra-addons` (padre, no el módulo)
6. `docker compose exec web python3 -c "import socket; socket.create_connection(('db', 5432), 3)"` → exit 0

**Resultado esperado**: stack sirviendo, DNS interno `db` resuelve.

### TP-0.1.1-02 — Persistencia (Escenario 2)

1. Insertar marcador: `CREATE TABLE marcador_persistencia (nota text); INSERT ... 'Tarta de Manzana Especial'`
2. `docker compose down` (**sin** `-v`)
3. `docker volume ls` lista `panaderia_odoo_db_data` y `panaderia_odoo_web_data`
4. `docker compose up -d` y `SELECT nota FROM marcador_persistencia` → fila intacta
5. `DROP TABLE marcador_persistencia`

**Resultado esperado**: datos sobreviven. `down -v` está documentado como destructivo.

### TP-0.1.1-03 — Aislamiento de PostgreSQL (Escenario 3)

1. `docker compose config` → el servicio `db` no tiene `ports:` activo
2. `Test-NetConnection localhost -Port 5432 -InformationLevel Quiet` → `False`
3. Probe in-network desde `web` a `db:5432` → éxito

**Resultado esperado**: aislado en el host, alcanzable en `panaderia-net`.

### TP-0.1.1-04 — Colisión de puerto 8069 (`spec.md` §8)

1. `ODOO_HTTP_PORT=8070` en `.env`
2. `docker compose up -d`
3. HTTP 200 en `http://localhost:8070/web/login`
4. `git status` no muestra cambios en archivos rastreados

### TP-0.1.1-05 — ISO-27001

| Check | Esperado |
| :--- | :--- |
| `git check-ignore -v .env` | regla de `.gitignore` |
| `git ls-files --error-unmatch .env` | no tracked |
| `.env.sample` tracked | sí |
| secretos en sample | sufijo `_change_me` |

---

## 4. Metas de rendimiento (`plan.md`)

Registrar en la ejecución:

| Métrica | Meta | Medido |
| :--- | :--- | :--- |
| Cold start a HTTP 200 | < 90 s | _llenar en ejecución_ |
| Warm start | < 20 s | _llenar en ejecución_ |
| `db` healthy | < 25 s | _llenar en ejecución_ |

---

## 5. DoD

- [x] `docker-compose.yml` validado con `docker compose config`
- [x] `web` y `db` comunican por `panaderia-net`
- [x] Volúmenes persisten entre reinicios
- [x] Este procedimiento documentado
