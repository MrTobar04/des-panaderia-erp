# Contract: Odoo Server Configuration (`[options]` key surface)

**Feature**: `SPEC-0.1.2: Configuración del Servidor Odoo y Modos de Desarrollo`
**Artifacts under contract**: `config/odoo.conf.template` (tracked) → `config/odoo.conf` (rendered, untracked) → `/etc/odoo/odoo.conf` (mounted)
**Date**: 2026-09-29
**Upstream contract**: [`SPEC-0.1.1 compose-topology-contract.md`](../../0.1.1-local-docker-environment/contracts/compose-topology-contract.md)

---

## 1. Key-by-Key Contract

| Key | Normative Value | Effect | Enforced? |
| :--- | :--- | :--- | :--- |
| `addons_path` | `/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons` | Module search roots, custom first | **Yes** |
| `data_dir` | `/var/lib/odoo` | Filestore + sessions; backed by `panaderia_odoo_web_data` | **Yes** |
| `admin_passwd` | `${ODOO_ADMIN_PASSWD}` → rendered plaintext | Guards the database manager | **Yes** |
| `db_host` | `db` | Database hostname on `panaderia-net` | **Yes** — see §2.1 |
| `db_port` | `5432` | Container-internal port | **Yes** — see §2.1 |
| `db_user` | `${POSTGRES_USER}` → rendered | Cluster role | **Yes** — see §2.1 |
| `db_password` | `${POSTGRES_PASSWORD}` → rendered | Database authentication | **Yes** — see §2.1 |
| `dev_mode` | `reload,qweb,xml` | XML hot reload, QWeb diagnostics, Python auto-reload (see §3) | Partially — see §3 |
| `list_db` | `True` | Database selector and manager reachable | **Yes** |
| `db_maxconn` | `32` | Odoo-side connection pool ceiling | **Yes** |
| `log_level` | `info` | Global log floor | **Yes** |
| `log_handler` | `:INFO,odoo.addons.panaderia:DEBUG` | Bakery module at DEBUG, everything else at INFO | **Yes** |
| `limit_memory_soft` | `2147483648` (2 GiB) | Worker soft memory cap | **No** — prefork only |
| `limit_memory_hard` | `2684354560` (2.5 GiB) | Worker hard memory cap | **No** — prefork only |
| `limit_time_cpu` | `120` | Per-request CPU seconds | **No** — prefork only |
| `limit_time_real` | `240` | Per-request wall-clock seconds | **No** — prefork only |

### Deliberately Absent Keys

| Key | Why Absent |
| :--- | :--- |
| `workers` | Left at the default `0` (threaded). Multi-worker is out of scope per `spec.md` §2.2, and threaded mode keeps Capa 1–5 transactions in a single process. |
| `smtp_*` | Out of scope per `spec.md` §2.2. |
| `db_name`, `dbfilter` | Would pin the server to one database and hide the selector, breaking Acceptance Scenario 2. The business database name lives in `.env` as `ODOO_DB_NAME` for the scripts of `SPEC-0.2.1`. |

---

## 2. The `addons_path` Invariant

> **`addons_path` MUST name `/mnt/extra-addons`, never `/mnt/extra-addons/panaderia`.**

| | Value | Odoo enumerates | Result |
| :--- | :--- | :--- | :--- |
| ❌ Wrong | `/mnt/extra-addons/panaderia` | `models/`, `views/`, `data/`, `security/`, `tests/` | No `__manifest__.py` in any child → **module never discovered** |
| ✅ Correct | `/mnt/extra-addons` | `panaderia/` | `panaderia/__manifest__.py` found → **module available** |

**Derived identities** (consumed repository-wide):

| Identity | Value |
| :--- | :--- |
| Module technical name | `panaderia` |
| Install / upgrade flag | `-i panaderia` / `-u panaderia` |
| Logger namespace | `odoo.addons.panaderia` |
| Test tag selector | `--test-tags=panaderia` |

The core path `/usr/lib/python3/dist-packages/odoo/addons` is **mandatory**: declaring `addons_path` replaces the parser default, and without it the `base` module cannot load and the server aborts during startup.

---

## 2.1 The `db_*` Keys Are Mandatory (corrected during implementation)

> **This reverses an earlier design decision.** The plan originally omitted `db_host`, `db_port`,
> `db_user`, and `db_password`, reasoning that the container's `HOST`/`USER`/`PASSWORD` environment
> variables already carried the credentials and that omitting the keys kept `.env` the single source of
> truth. That reasoning holds for the **long-running server** but breaks every **CLI invocation**.

What translates those environment variables into Odoo arguments is `/entrypoint.sh`, not Odoo itself:

```sh
check_config "db_host" "$HOST"
check_config "db_user" "$USER"
check_config "db_password" "$PASSWORD"
exec odoo "$@" "${DB_ARGS[@]}"
```

`docker compose exec web odoo ...` runs the `odoo` binary **directly**, bypassing the entrypoint, so
`DB_ARGS` is never computed. Odoo then falls back to its defaults, logs
`database: default@default:default`, and dies with:

```text
psycopg2.OperationalError: connection to server on socket
"/var/run/postgresql/.s.PGSQL.5432" failed: No such file or directory
```

Every CLI path in Capa 0 is affected — module install (`-i panaderia`), module upgrade
(`-u panaderia`, used by `docker-restart.ps1 -Upgrade`), and the `db-init-seed.ps1` bootstrap branch.

**No divergence risk.** `check_config` reads the config file's value in preference to the environment
variable when the key is present, so the server's behaviour is unchanged: both sources are rendered
from the same `.env`. **No new secret exposure.** `config/odoo.conf` is already untracked and already
holds `admin_passwd`; the template stays secret-free and carries only `${POSTGRES_USER}` and
`${POSTGRES_PASSWORD}` tokens.

---

## 3. `dev_mode` Flag Contract

| Flag | Included | Effect | Caveat |
| :--- | :--- | :--- | :--- |
| `xml` | ✅ | Views re-read from the XML files instead of the database copy — the actual hot reload | None |
| `qweb` | ✅ | QWeb template rendering diagnostics | None |
| `reload` | ✅ | Auto-restart on Python file change | **Inert without `watchdog`**, which is not installed in `odoo:16.0`. Odoo logs a warning; Python changes need `-u panaderia` or `docker-restart.ps1` |
| `werkzeug` | ❌ | Full Python traceback rendered into HTTP responses | Excluded: information disclosure with no benefit over `docker compose logs web` |
| `all` | ❌ | Implies every flag, including `werkzeug` | Excluded for the same reason |

---

## 4. `admin_passwd` Contract

| Property | Value |
| :--- | :--- |
| Source | `ODOO_ADMIN_PASSWD` in `.env` (never committed) |
| Format written | **Plaintext** |
| Format after first use | Odoo re-hashes to `pbkdf2_sha512` and rewrites `/etc/odoo/odoo.conf` in place |
| Mount mode required | **read-write** — `:ro` blocks the self-upgrade (warning only; auth still works) |
| Forbidden values | `admin` (`spec.md` §3); empty (disables the database manager entirely) |
| Anti-pattern | A `$pbkdf2-sha512$...`-prefixed string that is not a complete modular-crypt hash. Odoo routes it to passlib, which raises on the malformed payload → `500` in the database manager instead of a prompt |

---

## 5. Reference `config/odoo.conf.template`

```ini
[options]
; ==========================================================================
; Panadería "Delicias Dulces" ERP — Configuración del Servidor Odoo
; --------------------------------------------------------------------------
; Este archivo es una PLANTILLA versionada en Git. NO contiene secretos.
; `scripts/render-odoo-conf.ps1` lo renderiza a `config/odoo.conf`
; sustituyendo ${ODOO_ADMIN_PASSWD} desde `.env` (SPEC-0.1.1).
; El archivo renderizado está excluido de Git.
; ==========================================================================

; --- Rutas de Addons ---
; CRÍTICO: debe apuntar al directorio PADRE del módulo montado.
; El bind-mount es ./Modulo_Odoo -> /mnt/extra-addons/panaderia, por lo que
; Odoo debe escanear /mnt/extra-addons para descubrir el módulo `panaderia`.
; La ruta del núcleo es obligatoria: sin ella el módulo `base` no carga.
addons_path = /mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons

; --- Directorio de datos y filestore ---
; Respaldado por el volumen con nombre panaderia_odoo_web_data.
data_dir = /var/lib/odoo

; --- Clave maestra del Gestor de Bases de Datos ---
; Inyectada en tiempo de ejecución desde .env. Odoo la convierte
; automáticamente a un hash pbkdf2_sha512 en el primer uso exitoso.
admin_passwd = ${ODOO_ADMIN_PASSWD}

; --- Modo desarrollador y recarga en caliente ---
; xml   -> recarga vistas XML desde disco al recargar el navegador (F5)
; qweb  -> diagnóstico de renderizado de plantillas QWeb
; reload-> reinicio automático ante cambios en Python (requiere watchdog,
;          ausente en la imagen oficial: usar `-u panaderia` en su lugar)
; werkzeug se OMITE a propósito: expone trazas completas por HTTP.
dev_mode = reload,qweb,xml

; --- Gestión de base de datos ---
; list_db debe permanecer en True: el selector y el gestor de bases de datos
; son necesarios para el Escenario de Aceptación 2.
list_db = True
db_maxconn = 32

; --- Parámetros de logs ---
; Piso global en INFO para mantener legible el arranque durante la defensa;
; solo el módulo de panadería se eleva a DEBUG.
log_level = info
log_handler = :INFO,odoo.addons.panaderia:DEBUG

; --- Límites de memoria y tiempo ---
; NOTA: Odoo solo aplica estos límites en modo prefork (workers > 0).
; Esta pila corre en modo threaded (workers = 0), por lo que quedan
; declarados como intención y NO se aplican en tiempo de ejecución.
limit_memory_soft = 2147483648
limit_memory_hard = 2684354560
limit_time_cpu = 120
limit_time_real = 240

; --- Conexión a la base de datos ---
; OBLIGATORIAS: `docker compose exec web odoo ...` no pasa por
; /entrypoint.sh, que es quien traduce HOST/USER/PASSWORD a --db_host.
; Sin estas claves toda invocación de la CLI falla. Ver §2.1.
db_host = db
db_port = 5432
db_user = ${POSTGRES_USER}
db_password = ${POSTGRES_PASSWORD}

; --- Claves deliberadamente ausentes ---
; workers: valor por defecto 0 (modo threaded).
; db_name / dbfilter: ocultarían el selector de bases de datos.
```

---

## 6. Verification Contract

| Assertion | Command | Expected |
| :--- | :--- | :--- |
| Template is tracked | `git ls-files --error-unmatch config/odoo.conf.template` | Exit `0` |
| Rendered file is ignored | `git check-ignore -v config/odoo.conf` | Prints the matching rule |
| No secret in the template | `git grep -n "admin_passwd" -- config/odoo.conf.template` | Matches only the `${ODOO_ADMIN_PASSWD}` token |
| Token was substituted | `Select-String '\$\{' ./config/odoo.conf` | **No match** |
| File is mounted | `docker compose exec web cat /etc/odoo/odoo.conf` | Renders the full `[options]` section |
| Odoo read this file | `docker compose exec web printenv ODOO_RC` | `/etc/odoo/odoo.conf` |
| `addons_path` is correct | `docker compose logs web \| Select-String "addons_path"` | Contains `/mnt/extra-addons`, **not** `/mnt/extra-addons/panaderia` |
| Module is discoverable | `docker compose exec web ls /mnt/extra-addons/panaderia/__manifest__.py` | Path exists |
| Module loads | `docker compose logs web \| Select-String "module panaderia"` | Loading/loaded lines present after install |
| Bakery DEBUG active | `docker compose logs web \| Select-String "odoo.addons.panaderia"` | DEBUG lines present during bakery operations |
| Master password enforced | POST to `/web/database/backup` with a wrong key | Rejected with an access-denied message, not a `500` |
