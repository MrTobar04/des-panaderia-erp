# Quickstart & Verification Guide — Automatización de Ciclo de Vida y Healthcheck

**Feature**: `SPEC-0.3.1: Automatización de Ciclo de Vida de Contenedores y Healthcheck`
**Related Spec**: [`spec.md`](./spec.md)
**CLI Contract**: [`contracts/lifecycle-scripts-cli-contract.md`](./contracts/lifecycle-scripts-cli-contract.md)
**Healthcheck Contract**: [`contracts/healthcheck-output-contract.md`](./contracts/healthcheck-output-contract.md)
**Depends On**: [`SPEC-0.1.1`](../../0.1-docker-provisioning/0.1.1-local-docker-environment/spec.md) (stack + healthchecks), [`SPEC-0.1.2`](../../0.1-docker-provisioning/0.1.2-odoo-server-configuration/spec.md) (config rendering)

All commands assume **PowerShell** executed from the repository root (`des-panaderia-erp/`).

---

## 1. Prerequisites

| Requirement | Verify With | Expected |
| :--- | :--- | :--- |
| Docker Desktop running | `docker info` | Exit `0` |
| Compose v2 | `docker compose version` | `v2.20` or newer |
| Scripts present | `Get-ChildItem ./scripts/*.ps1` | Nine scripts across the three Capa 0 features |
| Stack defined | `Test-Path ./docker-compose.yml` | `True` |

---

## 2. One-Time Setup — Execution Policy

Windows defaults to `Restricted`, which blocks every `.ps1` file. This is the risk in `spec.md` §8.

```powershell
# Option A — per-session, no elevation required (recommended)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Option B — per-invocation
powershell -ExecutionPolicy Bypass -File .\scripts\docker-start.ps1
```

### If the project arrived as a browser-downloaded ZIP

```powershell
Get-ChildItem ./scripts/*.ps1 | Unblock-File
```

Files extracted from a downloaded ZIP carry a `Zone.Identifier` mark-of-the-web stream and are blocked
**even under a permissive execution policy**, with an error that reads nothing like a policy problem. A
`git clone` does not set this stream, so skip this step if you cloned.

Confirm:

```powershell
Get-ExecutionPolicy -List
```

---

## 3. Acceptance Scenario 1 — One-command startup from a clean environment

### Step 1 — Simulate a truly clean environment

```powershell
Remove-Item .env -ErrorAction SilentlyContinue
Remove-Item ./config/odoo.conf -ErrorAction SilentlyContinue
```

### Step 2 — Run the single command

```powershell
./scripts/docker-start.ps1
```

**Expected output**:

```text
Creando archivo .env a partir de .env.sample...
ADVERTENCIA: Reemplaza los valores *_change_me en .env antes de la entrega.
[OK] config/odoo.conf generado (clave maestra inyectada desde .env)
Iniciando contenedores de Panadería ERP...
Esperando a que los servicios estén listos ......
--- Verificación de Estado de Panadería ERP ---
[OK]    Docker: demonio activo
[OK]    Contenedor panaderia_odoo_db: en ejecución
[OK]    Base de datos PostgreSQL: Saludable
[OK]    PostgreSQL acepta conexiones (pg_isready)
[OK]    Contenedor panaderia_odoo_web: en ejecución
[OK]    Servidor Odoo Web: Saludable
[OK]    Interfaz Web lista en http://localhost:8069
--- Resultado: SALUDABLE ---
[OK] ERP listo en http://localhost:8069
```

### Step 3 — Confirm the side effects

```powershell
Test-Path .env                                  # True
Test-Path ./config/odoo.conf                    # True
Select-String '\$\{' ./config/odoo.conf          # no output — token substituted
$LASTEXITCODE                                   # 0
```

### Step 4 — Confirm readiness was polled, not guessed

The progress dots in Step 2 are the poll loop. On a cold start it may run for 60–90 seconds; on a warm
start it finishes in 8–12.

```powershell
Select-String -Path ./scripts/docker-start.ps1 -Pattern "State.Health.Status"
```

**Expected**: at least one match.

⚠️ If the script instead relies on `Start-Sleep -Seconds 5` as its readiness mechanism, it will report a
**false failure** on every cold start — Odoo takes far longer than five seconds to load the base
registry on Windows/WSL2. That is the single most likely way to look broken in front of an evaluator.
See `research.md` Decision 1.

### Step 5 — Replace the placeholder secrets

```powershell
# Edit .env: POSTGRES_PASSWORD and ODOO_ADMIN_PASSWD
./scripts/docker-start.ps1     # recreates containers so the new values take effect
```

> An `.env` change requires `docker compose up -d` (which `docker-start.ps1` runs), **not**
> `docker-restart.ps1`. Compose interpolates `.env` at container-creation time.

✅ **Scenario 1 satisfied**: `.env` generated, containers up, healthcheck passed, URL confirmed active.

---

## 4. Acceptance Scenario 2 — Instant fault diagnosis

### Step 1 — Take the database down

```powershell
docker compose stop db
```

### Step 2 — Diagnose

```powershell
./scripts/healthcheck.ps1
```

**Expected**: a red `[ERROR]` line naming `panaderia_odoo_db` specifically, plus the suggestion to run
`docker-start.ps1`, and:

```powershell
$LASTEXITCODE    # 2  (CAÍDO)
```

### Step 3 — Confirm every probe was attempted

```powershell
docker compose stop web
./scripts/healthcheck.ps1
```

**Expected**: results for **both** containers, not just the first failure. The script records each
result and continues, so the operator sees the complete picture in one pass.

### Step 4 — Confirm "booting" is not reported as an error

```powershell
docker compose start db web
./scripts/healthcheck.ps1      # run immediately, before Odoo finishes booting
```

**Expected**: yellow `[INFO] Servidor Odoo Web: iniciando servicios HTTP...`, result `DEGRADADO`, exit
`1`. A `starting` health status means keep waiting — treating it as a failure would reintroduce the
very bug Scenario 1 guards against.

### Step 5 — Recover

```powershell
./scripts/docker-start.ps1
./scripts/healthcheck.ps1      # exit 0
```

✅ **Scenario 2 satisfied**: the failed component is identified immediately, in red, with a usable exit
code.

---

## 5. Acceptance Scenario 3 — Clean service shutdown

### Step 1 — Stop

```powershell
./scripts/docker-stop.ps1
```

**Expected**: ordered shutdown with **no timeout errors**, then a report of the surviving volumes:

```text
Deteniendo contenedores de Panadería ERP...
[OK] Contenedores detenidos correctamente.
[OK] Volúmenes de datos preservados:
       panaderia_odoo_db_data
       panaderia_odoo_web_data
```

### Step 2 — Confirm no orphan containers

```powershell
docker ps -a | Select-String panaderia
```

**Expected**: no output. The script uses `docker compose down`, which removes containers; `stop` would
leave them behind and fail this check.

### Step 3 — Confirm the data survived

```powershell
docker volume ls | Select-String panaderia_odoo
```

**Expected**: both volumes still listed. Restarting with `./scripts/docker-start.ps1` returns every
product, sale, and invoice.

### Step 4 — Confirm destructive action requires explicit confirmation

```powershell
./scripts/docker-stop.ps1 -RemoveVolumes
```

**Expected**:

```text
ADVERTENCIA: Esta acción DESTRUIRÁ todos los datos (productos, ventas, facturas).
Escribe BORRAR para confirmar:
```

Type anything other than `BORRAR` — for example `si` — and press Enter.

**Expected**: `Operación cancelada. No se eliminó ningún volumen.`, exit `0`, both volumes intact.

> The confirmation is a typed word, not `[Y/n]` and not a `-Force` boolean, precisely so it cannot
> become muscle memory. `spec.md` §3 requires explicit confirmation for destructive commands; providing
> one guarded path is stronger than omitting the capability and leaving the operator to type
> `docker compose down -v` by hand with no guard at all.

✅ **Scenario 3 satisfied**: clean shutdown, no timeout errors, data integrity preserved.

---

## 6. Log Streaming (`spec.md` §6 step 2)

```powershell
# Last 100 lines from Odoo (default)
./scripts/docker-logs.ps1

# Live stream — Ctrl+C to exit
./scripts/docker-logs.ps1 -Follow

# PostgreSQL history
./scripts/docker-logs.ps1 -Service db -Tail 200

# Only bakery-module messages
./scripts/docker-logs.ps1 -Filter "odoo.addons.panaderia"

# Both services, live
./scripts/docker-logs.ps1 -Service all -Follow
```

**Expected**: entries prefixed with the readable container names `panaderia_odoo_web` /
`panaderia_odoo_db`, courtesy of the fixed `container_name` values in the `SPEC-0.1.1` topology contract.

Confirm the parameter used by the spec's own verification plan exists:

```powershell
Get-Help ./scripts/docker-logs.ps1 -Parameter Follow
```

---

## 7. Restart Behavior (`spec.md` §6 step 3)

### Plain restart — the command returns in about 5 seconds

```powershell
Measure-Command { ./scripts/docker-restart.ps1 } | Select-Object TotalSeconds
```

**Expected**: roughly 5 seconds or less.

> Note the distinction. The `docker restart` **command** completes in about 5 seconds; Odoo is not
> *serving* for another 15–30. `spec.md` §6 asserts "el reinicio tome menos de 5 segundos", which this
> plan reads as a command-duration requirement. When readiness is what actually matters, use `-Wait`.

### Restart and wait for readiness

```powershell
./scripts/docker-restart.ps1 -Wait
```

**Expected**: polls until `panaderia_odoo_web` reports `healthy`, then reports the URL.

### Apply a Python model change

```powershell
./scripts/docker-restart.ps1 -Upgrade
```

**Expected**: runs `odoo -u panaderia -d panaderia_db --stop-after-init`, then restarts.

> A plain restart does **not** apply a Python model change — it only re-executes the existing code. A
> new field, an `@api.constrains`, or a manifest edit requires a module upgrade. This matters more than
> usual here because the `reload` flag in `dev_mode` is inert: `watchdog` is not installed in the
> official `odoo:16.0` image. There is no automatic mechanism at all.

### Which command for which change

| You changed | Run |
| :--- | :--- |
| An XML view | Nothing — just refresh the browser (`dev_mode=xml`) |
| A Python model, field, or constraint | `./scripts/docker-restart.ps1 -Upgrade` |
| `__manifest__.py` | `./scripts/docker-restart.ps1 -Upgrade` |
| `config/odoo.conf.template` | `./scripts/render-odoo-conf.ps1` then `docker compose up -d` |
| `.env` | `./scripts/docker-start.ps1` (recreates containers) |

---

## 8. Healthcheck as a Verification Gate (`spec.md` §6)

```powershell
./scripts/healthcheck.ps1 -Quiet
if ($LASTEXITCODE -ne 0) { Write-Error "La pila no está saludable"; exit 1 }
```

| Exit | Label | Meaning |
| :--- | :--- | :--- |
| `0` | `SALUDABLE` | Every probe passed |
| `1` | `DEGRADADO` | Containers up, something incomplete or still starting |
| `2` | `CAÍDO` | Docker unreachable, or a container missing/stopped |

> The `spec.md` §4 sketch always exits `0`, which makes it unusable as a gate even though §6 requires
> exactly this use. See `research.md` Decision 2.

---

## 9. Definition of Done Mapping

| `spec.md` §10 DoD Item | Verified In |
| :--- | :--- |
| All PowerShell scripts created in `scripts/` | §1 |
| `docker-start.ps1` / `docker-stop.ps1` flow verified on Windows | §3, §5 |
| Healthcheck validating HTTP 200 on `http://localhost:8069` | §4, §8 |
| `docs/test-procedures/test-procedure-0.3.1.md` documented | Authored from this guide during `/speckit-implement` |
| *(gap)* `Instrucciones_Instalacion.txt` — required by §2.1 and §8, absent from §9 | §2; see `plan.md` → Known Cross-Artifact Inconsistencies #4 |

---

## 10. Full Operator Cheat Sheet

```powershell
# ── Ciclo de vida ────────────────────────────────────────────────
./scripts/docker-start.ps1              # arrancar todo (un comando)
./scripts/docker-stop.ps1               # detener, conservando datos
./scripts/docker-restart.ps1            # reiniciar Odoo
./scripts/docker-restart.ps1 -Upgrade   # aplicar cambios de Python
./scripts/healthcheck.ps1               # diagnóstico
./scripts/docker-logs.ps1 -Follow       # logs en vivo

# ── Base de datos (SPEC-0.2.1) ───────────────────────────────────
./scripts/db-backup.ps1                 # respaldo bajo demanda
./scripts/db-backup.ps1 -IncludeFilestore
./scripts/db-restore.ps1 -BackupFile ./backups/seed_demo.dump
./scripts/db-init-seed.ps1              # estado de demostración

# ── Configuración (SPEC-0.1.2) ───────────────────────────────────
./scripts/render-odoo-conf.ps1          # regenerar config/odoo.conf

# ── DESTRUCTIVO — exige escribir BORRAR ──────────────────────────
./scripts/docker-stop.ps1 -RemoveVolumes
```

---

## 11. Troubleshooting

| Symptom | Likely Cause | Fix |
| :--- | :--- | :--- |
| `no se puede cargar porque la ejecución de scripts está deshabilitada` | Execution policy is `Restricted` | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| Script blocked despite a permissive policy | `Zone.Identifier` from a ZIP download | `Get-ChildItem ./scripts/*.ps1 \| Unblock-File` |
| `error during connect` | Docker Desktop not started | Start Docker Desktop, wait for "Engine running" |
| `docker-start.ps1` reports failure on a stack that is actually fine | Fixed-delay readiness instead of health polling | Replace `Start-Sleep` with a `.State.Health.Status` poll loop |
| Healthcheck reports web down while the browser works | Probe hardcodes `8069` but `ODOO_HTTP_PORT` was changed | Read the port from `.env` |
| Healthcheck prints an empty status | Container does not exist; `docker inspect` returned `$null` | Probe existence before status (`healthcheck-output-contract.md` §2) |
| Python changes have no effect after a restart | Module not upgraded; `reload` is inert without `watchdog` | `./scripts/docker-restart.ps1 -Upgrade` |
| `.env` changes have no effect | `restart` does not re-read `.env` | `./scripts/docker-start.ps1` to recreate containers |
| Data disappeared | `docker compose down -v` was run manually | Restore with `./scripts/db-restore.ps1 -BackupFile ./backups/seed_demo.dump` |
| Shell left inside `scripts/` after Ctrl+C | `Pop-Location` not in a `finally` block | Wrap `Push-Location` / `Pop-Location` in `try`/`finally` |
