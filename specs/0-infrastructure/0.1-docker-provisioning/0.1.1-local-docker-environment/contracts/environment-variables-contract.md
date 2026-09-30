# Contract: Environment Variable Surface (`.env` / `.env.sample`)

**Feature**: `SPEC-0.1.1: Aprovisionamiento de Entorno Local en Docker`
**Artifacts under contract**: `.env.sample` (committed), `.env` (generated, **never** committed)
**Date**: 2026-09-29
**Consumers**: `docker-compose.yml`, `SPEC-0.1.2` config rendering, `SPEC-0.2.1` backup/restore scripts, `SPEC-0.3.1` lifecycle scripts

---

## 1. Variable Surface

| Variable | Default in `.env.sample` | Secret? | Consumed By | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `COMPOSE_PROJECT_NAME` | `panaderia-erp` | No | Compose itself | Namespaces the project; keeps `docker compose ls` readable |
| `POSTGRES_DB` | `postgres` | No | `db`, `web` | Maintenance database. Odoo creates its own business database separately |
| `POSTGRES_USER` | `odoo` | No | `db`, `web`, `SPEC-0.2.1` | Cluster superuser — required so Odoo can `CREATEDB` from the database manager |
| `POSTGRES_PASSWORD` | `odoo_dev_password_change_me` | **Yes** | `db`, `web` | PostgreSQL authentication |
| `ODOO_HTTP_PORT` | `8069` | No | `web` port mapping | Host HTTP port; the collision escape hatch of `spec.md` §8 |
| `ODOO_CHAT_PORT` | `8072` | No | `web` port mapping | Host longpolling/chat port |
| `ODOO_ADMIN_PASSWD` | `bakery_master_key_change_me` | **Yes** | `SPEC-0.1.2` config rendering | Odoo master password guarding the database manager |
| `ODOO_DB_NAME` | `panaderia_db` | No | `SPEC-0.2.1`, `SPEC-0.3.1` | Authoritative name of the Odoo business database |

> `ODOO_ADMIN_PASSWD` and `ODOO_DB_NAME` are additive to the six variables in `spec.md` §4.
> Justification is recorded in `plan.md` → Complexity Tracking #4: the master password must be
> injected at runtime rather than committed inside `config/odoo.conf`, and the backup, restore, and
> seed scripts need one authoritative database name instead of three independent literals.

---

## 2. Contract Rules

1. **`.env.sample` contains no real secret.** Every secret-valued variable ends in the literal suffix `_change_me`, so a leaked or unmodified file is self-evident on inspection.
2. **`.env` is never tracked.** `.gitignore` excludes it; `git check-ignore -v .env` must confirm the rule before any commit.
3. **Compose defaults mirror `.env.sample`.** Every reference in `docker-compose.yml` uses `${VAR:-default}` so the stack still starts if a variable is missing, with the sole exception of secrets, where a weak default is acceptable only because the port is unpublished and the stack is local-only.
4. **Credential symmetry is mandatory.** `POSTGRES_USER` / `POSTGRES_PASSWORD` are consumed by both `db` (as cluster credentials) and `web` (as `USER` / `PASSWORD`). They are declared once and interpolated twice; they must never be written as literals in either service.
5. **`.env` is auto-provisioned.** `SPEC-0.3.1`'s `docker-start.ps1` copies `.env.sample` to `.env` when absent, so a fresh clone starts with one command (Acceptance Scenario 1 of `SPEC-0.3.1`).
6. **Changing a value requires a container recreate.** Compose interpolates at parse time, so `docker compose up -d` (not `restart`) is required for an `.env` edit to take effect. `docker-restart.ps1` is for code changes only.

---

## 3. Reference `.env.sample`

```bash
# ==========================================================================
# Panadería "Delicias Dulces" ERP — Docker Compose Environment Configuration
# --------------------------------------------------------------------------
# Copiar a `.env` y reemplazar TODO valor marcado con el sufijo `_change_me`.
# `.env` está excluido de Git (ISO-27001). NUNCA lo agregues al repositorio.
# ==========================================================================

# --- Identidad del proyecto Compose ---
COMPOSE_PROJECT_NAME=panaderia-erp

# --- Base de datos PostgreSQL ---
POSTGRES_DB=postgres
POSTGRES_USER=odoo
POSTGRES_PASSWORD=odoo_dev_password_change_me

# --- Puertos publicados en el host ---
# Si el puerto 8069 está ocupado (IIS, otra instancia de Odoo), cambiar a 8070.
ODOO_HTTP_PORT=8069
ODOO_CHAT_PORT=8072

# --- Servidor Odoo ---
# Clave maestra del Gestor de Bases de Datos (SPEC-0.1.2).
ODOO_ADMIN_PASSWD=bakery_master_key_change_me

# Nombre de la base de datos de negocio (SPEC-0.2.1 / SPEC-0.3.1).
ODOO_DB_NAME=panaderia_db
```

---

## 4. Verification Contract

| Assertion | Command | Expected |
| :--- | :--- | :--- |
| `.env` is ignored by Git | `git check-ignore -v .env` | Prints the matching `.gitignore` rule; exit `0` |
| `.env` is not tracked | `git ls-files --error-unmatch .env` | Exit non-zero ("did not match any file") |
| `.env.sample` is tracked | `git ls-files --error-unmatch .env.sample` | Exit `0` |
| No real secret was committed | `git grep -nE "_change_me" -- .env.sample` | Both secret lines match |
| Interpolation resolves | `docker compose config` | `ODOO_HTTP_PORT` renders as a concrete port; no `variable is not set` warning |
