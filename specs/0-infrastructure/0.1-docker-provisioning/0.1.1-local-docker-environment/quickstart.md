# Quickstart & Verification Guide — Aprovisionamiento de Entorno Local en Docker

**Feature**: `SPEC-0.1.1: Aprovisionamiento de Entorno Local en Docker`
**Related Spec**: [`spec.md`](./spec.md)
**Topology Contract**: [`contracts/compose-topology-contract.md`](./contracts/compose-topology-contract.md)
**Environment Contract**: [`contracts/environment-variables-contract.md`](./contracts/environment-variables-contract.md)

All commands assume **PowerShell** executed from the repository root (`des-panaderia-erp/`).

---

## 1. Prerequisites

| Requirement | Verify With | Expected |
| :--- | :--- | :--- |
| Docker Engine running | `docker version` | Client **and** Server sections both print |
| Compose v2 plugin | `docker compose version` | `Docker Compose version v2.20` or newer |
| Repository root | `Test-Path ./docker-compose.yml` | `True` |
| Addon present | `Test-Path ./Modulo_Odoo/__manifest__.py` | `True` |

> On Windows, Docker Desktop must be started and report "Engine running" before continuing. A stopped engine produces `error during connect`, which is not a configuration problem.

---

## 2. First-Time Setup

### Step 1 — Create the local environment file

```powershell
Copy-Item .env.sample .env
```

### Step 2 — Replace every placeholder secret

Open `.env` and change both values ending in `_change_me`:

```bash
POSTGRES_PASSWORD=<una_contrasena_fuerte>
ODOO_ADMIN_PASSWD=<una_clave_maestra_fuerte>
```

### Step 3 — Confirm `.env` is excluded from Git

```powershell
git check-ignore -v .env
```

**Expected**: a line such as `.gitignore:2:.env	.env`. If this prints nothing, **stop** — the file would be committed, violating ISO-27001 secret management (`spec.md` §7).

---

## 3. Static Validation (before ever starting a container)

```powershell
docker compose config
```

**Expected**: the fully interpolated stack is printed to stdout, exit code `0`, and **no `WARN` lines**. In particular there must be no `the attribute 'version' is obsolete` warning — see `research.md` Decision 1.

Confirm the critical values in the output:

| Look For | Expected Value |
| :--- | :--- |
| `web` published port | `8069` (or your `ODOO_HTTP_PORT` override) |
| `db` published ports | **none at all** |
| Addon mount target | `/mnt/extra-addons/panaderia` |
| `PGDATA` | `/var/lib/postgresql/data/pgdata` |

---

## 4. Acceptance Scenario 1 — Successful stack startup

### Step 1 — Start the stack

```powershell
docker compose up -d
```

### Step 2 — Confirm both services and the database health gate

```powershell
docker compose ps
docker inspect --format='{{.State.Health.Status}}' panaderia_odoo_db
```

**Expected**: `db` shows `Up (healthy)`, `web` shows `Up`; the inspect command prints `healthy`.

### Step 3 — Wait for Odoo, then confirm HTTP

Cold start loads the full base registry and can take 60–90 s on Windows/WSL2. Poll instead of guessing:

```powershell
docker inspect --format='{{.State.Health.Status}}' panaderia_odoo_web
```

Once it prints `healthy`:

```powershell
(Invoke-WebRequest http://localhost:8069/web/login -UseBasicParsing).StatusCode
```

**Expected**: `200`. Opening `http://localhost:8069` in a browser shows the Odoo database selector or login screen.

### Step 4 — Confirm the addon is discoverable

```powershell
docker compose logs web | Select-String "addons_path"
```

**Expected**: the path list contains `/mnt/extra-addons` — the **parent** of the mount target, never `/mnt/extra-addons/panaderia`. If it contains the latter, the module will not appear in **Aplicaciones**; see `research.md` Decision 2.

✅ **Scenario 1 satisfied**: `db` healthy, `web` started with no connection errors, port `8069` answering `200`.

---

## 5. Acceptance Scenario 2 — Resume after forced shutdown

### Step 1 — Create a marker row that must survive

```powershell
docker exec -t panaderia_odoo_db psql -U odoo -d postgres -c "CREATE TABLE IF NOT EXISTS marcador_persistencia (nota text); INSERT INTO marcador_persistencia VALUES ('Tarta de Manzana Especial');"
```

### Step 2 — Tear the stack down (containers only, never `-v`)

```powershell
docker compose down
```

### Step 3 — Confirm the volumes outlived the containers

```powershell
docker volume ls | Select-String "panaderia_odoo"
```

**Expected**: both `panaderia_odoo_db_data` and `panaderia_odoo_web_data` are still listed.

### Step 4 — Restart and confirm the data is intact

```powershell
docker compose up -d
Start-Sleep -Seconds 10
docker exec -t panaderia_odoo_db psql -U odoo -d postgres -c "SELECT nota FROM marcador_persistencia;"
```

**Expected**: `Tarta de Manzana Especial` is returned.

### Step 5 — Clean up the marker

```powershell
docker exec -t panaderia_odoo_db psql -U odoo -d postgres -c "DROP TABLE marcador_persistencia;"
```

⚠️ **Never** run `docker compose down -v` to "reset" the stack. `-v` destroys both volumes and all demo data with no confirmation prompt.

✅ **Scenario 2 satisfied**: data, configuration, and installed modules persist across a full `down` / `up -d` cycle.

---

## 6. Acceptance Scenario 3 — PostgreSQL isolation

### Step 1 — Prove the host cannot reach `5432`

```powershell
Test-NetConnection -ComputerName localhost -Port 5432 -InformationLevel Quiet
```

**Expected**: `False`. The `db` service declares no `ports:` key, so nothing is published.

### Step 2 — Prove it *is* reachable inside the private network

```powershell
docker compose exec web python3 -c "import socket; socket.create_connection(('db', 5432), 3); print('OK: db alcanzable en panaderia-net')"
```

**Expected**: `OK: db alcanzable en panaderia-net`.

Step 2 is what makes Step 1 meaningful: together they prove the port is *isolated* rather than the database simply being down. See `research.md` Decision 4.

✅ **Scenario 3 satisfied**: external connection refused, internal connection succeeds on `panaderia-net`.

---

## 7. Risk Drill — Host port `8069` collision

If `docker compose up -d` fails with `Bind for 0.0.0.0:8069 failed: port is already allocated`:

```powershell
# 1. Identify the occupant
Get-NetTCPConnection -LocalPort 8069 -State Listen | Select-Object OwningProcess
# 2. Reassign in .env (edit the file)
#    ODOO_HTTP_PORT=8070
# 3. Recreate the container — `restart` will NOT pick up an .env change
docker compose up -d
# 4. Verify on the new port
(Invoke-WebRequest http://localhost:8070/web/login -UseBasicParsing).StatusCode
```

**Expected**: `200` on the reassigned port, with **no tracked file modified** — the mitigation in `spec.md` §8 is satisfied entirely through `.env`.

---

## 8. Security Verification (ISO-27001, `spec.md` §7)

| Check | Command | Expected |
| :--- | :--- | :--- |
| `.env` ignored | `git check-ignore -v .env` | Prints the matching rule |
| `.env` untracked | `git ls-files --error-unmatch .env` | Exit non-zero |
| `.env.sample` tracked | `git ls-files --error-unmatch .env.sample` | Exit `0` |
| Placeholders are obvious | `git grep -nE "_change_me" -- .env.sample` | Both secret lines match |
| No secret in the Compose file | `git grep -nE "password\s*[:=]\s*[^$]" -- docker-compose.yml` | No match outside `${...}` defaults |
| Nothing leaked historically | `git log --all --oneline -- .env` | No commits |

---

## 9. Definition of Done Mapping

| `spec.md` §10 DoD Item | Verified In |
| :--- | :--- |
| `docker-compose.yml` validated with `docker compose config` | §3 |
| `web` and `db` communicating over `panaderia-net` | §4 Step 2, §6 Step 2 |
| Volumes configured and persisting across restarts | §5 |
| `docs/test-procedures/test-procedure-0.1.1.md` completed | Authored from this guide during `/speckit-implement` |

---

## 10. Teardown

```powershell
# Stop containers, keep all data (the normal path)
docker compose down

# Full reset — DESTROYS ALL DATA. Only with a fresh seed_demo.dump on hand (SPEC-0.2.1).
# docker compose down -v
```
