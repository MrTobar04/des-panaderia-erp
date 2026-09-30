# Procedimiento de Prueba: SPEC-0.1.2 Configuración del Servidor Odoo

**Documento ID**: `test-procedure-0.1.2.md`
**Especificación**: `specs/0-infrastructure/0.1-docker-provisioning/0.1.2-odoo-server-configuration/spec.md`
**Guía**: `quickstart.md` §§2–8
**Fecha**: 2026-09-29

---

## 1. Objetivo

Validar que Odoo lee `config/odoo.conf` (renderizado), descubre el módulo `panaderia`, protege el gestor de bases de datos y emite DEBUG bajo `odoo.addons.panaderia`.

---

## 2. Prerrequisitos

- [x] SPEC-0.1.1 operativo
- [x] `config/odoo.conf.template` tracked; `config/odoo.conf` gitignored
- [x] `.\scripts\render-odoo-conf.ps1` produce UTF-8 sin BOM y LF

---

## 3. Casos de prueba

### TP-0.1.2-01 — Detección del módulo (Escenario 1)

1. `.\scripts\render-odoo-conf.ps1`
2. `Select-String "^addons_path" .\config\odoo.conf` = `/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons`
3. `Select-String '\$\{' .\config\odoo.conf` → vacío
4. `(Get-Content .\config\odoo.conf -Raw) -match "\r"` → `False`
5. `docker compose exec web printenv ODOO_RC` → `/etc/odoo/odoo.conf`
6. `docker compose exec web ls /mnt/extra-addons/panaderia/__manifest__.py` existe
7. UI: Aplicaciones → quitar filtro → Actualizar lista → buscar «Panadería»
8. `docker compose exec web odoo -d panaderia_db -i panaderia --stop-after-init` sin traceback

**Anti-patrón**: `addons_path = /mnt/extra-addons/panaderia` hace el módulo invisible.

### TP-0.1.2-02 — Gestor de base de datos (Escenario 2)

1. Abrir `http://localhost:8069/web/database/manager`
2. Backup con clave vacía → denegado, **no** HTTP 500
3. Backup con clave incorrecta → denegado
4. Backup con `ODOO_ADMIN_PASSWD` de `.env` → `.zip` descarga
5. Tras uso exitoso, `admin_passwd` en el archivo montado puede empezar por `$pbkdf2-sha512$`

### TP-0.1.2-03 — Logs y hot-reload (Escenario 3)

1. `dev_mode = reload,qweb,xml` (sin `werkzeug`)
2. Editar una etiqueta XML en `Modulo_Odoo/views/producto_views.xml` → F5 sin reiniciar
3. Operar un producto → `docker compose logs web | Select-String odoo.addons.panaderia` muestra DEBUG
4. Cambio Python: `odoo -u panaderia --stop-after-init` ( `reload` inerte sin `watchdog` )

### TP-0.1.2-04 — Matriz de fallos del renderer

| Condición | Exit | `odoo.conf` previo |
| :--- | :--- | :--- |
| Plantilla ausente | 1 | intacto |
| `.env` ausente | 1 | intacto |
| `ODOO_ADMIN_PASSWD` vacío | 1 | intacto |
| Manifest ausente | 1 | intacto |
| Placeholder `_change_me` | 0 + WARN | regenerado |

### TP-0.1.2-05 — Seguridad

| Check | Esperado |
| :--- | :--- |
| `git check-ignore -v config/odoo.conf` | ignorado |
| Template tracked | sí |
| `admin_passwd = admin` | ausente |
| `git log -- config/odoo.conf` | vacío |

---

## 4. Troubleshooting (síntomas conocidos)

| Síntoma | Causa | Fix |
| :--- | :--- | :--- |
| Módulo ausente en Aplicaciones | `addons_path` apunta al módulo | padre `/mnt/extra-addons` |
| `base` no carga | falta ruta core | reañadir path Debian |
| 500 en database manager | pseudo-hash malformado | plaintext desde `.env` |
| Token `${...}` literal | no se renderizó | `render-odoo-conf.ps1` |
| Ruta de addons inexistente | CRLF | re-render LF sin BOM |

---

## 5. DoD

- [x] Plantilla + render con todos los parámetros de desarrollo
- [x] Montaje `/etc/odoo/odoo.conf` verificado
- [x] Addons path reconoce `Modulo_Odoo/` como `panaderia`
- [x] Este procedimiento documentado
