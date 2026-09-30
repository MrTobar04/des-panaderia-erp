# Quickstart & Verification Guide — Persistencia, Semillas y Respaldos PostgreSQL

**Feature**: `SPEC-0.2.1: Persistencia, Semillas y Respaldos de Base de Datos PostgreSQL`
**Related Spec**: [`spec.md`](./spec.md)
**CLI Contract**: [`contracts/db-scripts-cli-contract.md`](./contracts/db-scripts-cli-contract.md)
**Artifact Contract**: [`contracts/backup-artifact-contract.md`](./contracts/backup-artifact-contract.md)
**Depends On**: [`SPEC-0.1.1`](../../0.1-docker-provisioning/0.1.1-local-docker-environment/spec.md) — the stack, `panaderia_odoo_db`, and `.env`

All commands assume **PowerShell** executed from the repository root (`des-panaderia-erp/`).

---

## 1. Prerequisites

| Requirement | Verify With | Expected |
| :--- | :--- | :--- |
| Stack running | `docker inspect --format='{{.State.Running}}' panaderia_odoo_db` | `true` |
| `.env` present | `Test-Path ./.env` | `True` |
| Business DB name defined | `Select-String "^ODOO_DB_NAME=" ./.env` | One match (default `panaderia_db`) |
| Odoo database exists | `docker exec panaderia_odoo_db psql -U odoo -lqt \| Select-String panaderia_db` | One match |
| Backups directory | `Test-Path ./backups` | `True` |

> If `panaderia_db` does not exist yet, create it through the Odoo database manager at
> `http://localhost:8069/web/database/manager`, or run `./scripts/db-init-seed.ps1`.

---

## 2. Understand Which Database You Are Backing Up

This is the single most important thing to get right in this feature.

```powershell
docker exec panaderia_odoo_db psql -U odoo -c "\l"
```

**Expected**: at least two databases —

| Database | Role | Back it up? |
| :--- | :--- | :--- |
| `postgres` | PostgreSQL **maintenance** database. Created by the image from `POSTGRES_DB`. Holds no bakery data. | ❌ **No** |
| `panaderia_db` | The Odoo business database. Holds every product, sale, customer, and invoice. | ✅ **Yes** |

⚠️ The commands in `spec.md` §4 pass `-d postgres`. That produces a dump that is non-empty, has a valid
binary header, and contains **no bakery data whatsoever** — so it passes the spec's own size check
while being completely useless. Confirm your scripts target `$ODOO_DB_NAME`:

```powershell
Select-String -Path ./scripts/db-backup.ps1 -Pattern "pg_dump"
```

**Expected**: the `pg_dump` line references `$ODOO_DB_NAME` (or `$dbName`), never a literal `postgres`.

---

## 3. Confirm Volume Persistence

```powershell
docker volume inspect panaderia_odoo_db_data --format '{{.Mountpoint}}'
docker exec panaderia_odoo_db psql -U odoo -c "SHOW data_directory;"
```

**Expected**: the volume exists, and `data_directory` is `/var/lib/postgresql/data/pgdata` — the nested
path, so `initdb` always received an empty directory.

---

## 4. Acceptance Scenario 1 — On-demand backup creation

### Step 1 — Seed a recognizable record

In the Odoo UI, go to **Panadería → Inventario → Productos** and create:

| Field | Value |
| :--- | :--- |
| Nombre | `Tarta de Manzana Especial` |
| Categoría | `Pastel` |
| Costo | `4.50` |
| Precio de Venta | `12.00` |

### Step 2 — Take the backup

```powershell
./scripts/db-backup.ps1 -BackupName test_backup.dump
```

**Expected**: Cyan progress line, then
`[OK] Respaldo completado: ./backups/test_backup.dump (NNN KB)` in green.

### Step 3 — Confirm the artifact is real and non-trivial

```powershell
Get-Item ./backups/test_backup.dump | Select-Object Name, Length, LastWriteTime
```

**Expected**: `Length` greater than zero — a demo database typically yields 300–800 KB. A file of a
few kilobytes is the signature of having dumped `postgres` by mistake; verify with §7.

### Step 4 — Confirm the backup was hot

```powershell
docker inspect --format='{{.State.Running}}' panaderia_odoo_db
(Invoke-WebRequest http://localhost:8069/web/login -UseBasicParsing).StatusCode
```

**Expected**: `true` and `200`. The database was never stopped and Odoo kept serving throughout, as
`spec.md` §3 requires.

### Step 5 — Optional: capture the filestore too

```powershell
./scripts/db-backup.ps1 -BackupName completo.dump -IncludeFilestore
```

**Expected**: two artifacts — `completo.dump` and `completo_filestore.tar`. You need the companion
archive whenever the restore target might have an **empty** filestore (a fresh clone, or after
`docker compose down -v`); otherwise product images resolve to nothing and render broken.

✅ **Scenario 1 satisfied**: a valid, non-empty, binary-format `.dump` exists in `backups/`.

---

## 5. Acceptance Scenario 2 — Full restore of a prior state

### Step 1 — Destroy the record

In the Odoo UI, delete (or archive) **Tarta de Manzana Especial**. Confirm it is gone from the product
list.

### Step 2 — Restore

```powershell
./scripts/db-restore.ps1 -BackupFile ./backups/test_backup.dump
```

Confirm the prompt when asked (or pass `-Force` to skip it).

**Observe the sequence.** The script validates the artifact *before* destroying anything, then stops
Odoo, recreates the database, restores, and brings Odoo back:

```text
[1/7] Validando artefacto con pg_restore -l...
[2/7] Deteniendo panaderia_odoo_web...
[3/7] Terminando sesiones activas...
[4/7] Recreando base de datos panaderia_db...
[5/7] Restaurando volcado...
[6/7] Iniciando panaderia_odoo_web...
[7/7] Esperando estado saludable...
[OK] Restauración finalizada exitosamente.
```

> Odoo is stopped rather than merely disconnected because its connection pool reconnects within
> milliseconds — `pg_terminate_backend` alone loses the race with `dropdb`, intermittently. Stopping
> `web` also clears Odoo's in-memory registry cache, which would otherwise serve the pre-restore
> schema against the restored data. See `research.md` Decision 2.

### Step 3 — Confirm the record returned

Refresh the browser and navigate to **Panadería → Inventario → Productos**.

**Expected**: **Tarta de Manzana Especial** is back with `Costo 4.50` and `Precio de Venta 12.00`, and
its computed margin recalculates correctly. No referential-integrity error appears in the log:

```powershell
docker compose logs --tail 50 web | Select-String -Pattern "ERROR|Traceback"
```

**Expected**: no output.

✅ **Scenario 2 satisfied**: the database returns exactly to the saved state with full referential
integrity.

---

## 6. Acceptance Scenario 3 — Container dependency validation

### Step 1 — Stop the database

```powershell
docker compose stop db
```

### Step 2 — Attempt each operation

```powershell
./scripts/db-backup.ps1
./scripts/db-restore.ps1 -BackupFile ./backups/test_backup.dump
./scripts/db-init-seed.ps1
```

**Expected**, from all three:

```text
[ERROR] El contenedor panaderia_odoo_db no está en ejecución.
        Ejecuta primero: .\scripts\docker-start.ps1
```

in red, with exit code `1` and **no partial artifact** written to `backups/`.

```powershell
$LASTEXITCODE   # → 1
```

### Step 3 — Restore normal service

```powershell
docker compose start db
```

✅ **Scenario 3 satisfied**: each script detects the stopped container and guides the operator.

---

## 7. Automated Artifact Validation (`spec.md` §6)

Header parsing alone is **not** sufficient evidence that a backup is useful.

```powershell
# Stage the artifact and inspect its table of contents
docker cp ./backups/test_backup.dump panaderia_odoo_db:/tmp/verify.dump
docker exec panaderia_odoo_db pg_restore -l /tmp/verify.dump | Select-String "panaderia_"
docker exec panaderia_odoo_db rm /tmp/verify.dump
```

**Expected**: entries for `panaderia_producto` and `panaderia_categoria` appear in the listing.

| Result | Meaning |
| :--- | :--- |
| Bakery relations listed | ✅ A genuinely useful backup |
| TOC parses but lists no `panaderia_*` table | ❌ You dumped `postgres`, not `panaderia_db` |
| `pg_restore -l` errors out | ❌ Corrupt artifact — almost always PowerShell `>` redirection instead of `docker cp` |

---

## 8. Security Verification (`spec.md` §7)

| Check | Command | Expected |
| :--- | :--- | :--- |
| Operator backups ignored | `git check-ignore -v backups/test_backup.dump` | Prints the matching rule |
| Seed artifact tracked | `git ls-files --error-unmatch backups/seed_demo.dump` | Exit `0` |
| Directory marker tracked | `git ls-files --error-unmatch backups/.gitkeep` | Exit `0` |
| Nothing unexpected staged | `git status --short backups/` | No untracked `.dump` listed |
| History clean | `git log --all --oneline -- backups/` | Only `.gitkeep` and seed artifacts |
| No credential echoed | Re-read the script console output | No `POSTGRES_PASSWORD` value printed |

---

## 9. Demo Playbook — the reason this feature exists

### Before the defense

```powershell
# 1. Bring up a known-good state and populate it through the UI
./scripts/docker-start.ps1
# 2. Freeze it, filestore included
./scripts/db-backup.ps1 -BackupName seed_demo.dump -IncludeFilestore
# 3. Validate before you rely on it
docker cp ./backups/seed_demo.dump panaderia_odoo_db:/tmp/v.dump
docker exec panaderia_odoo_db pg_restore -l /tmp/v.dump | Select-String "panaderia_producto"
docker exec panaderia_odoo_db rm /tmp/v.dump
```

### If the live demo goes wrong

```powershell
./scripts/db-restore.ps1 -BackupFile ./backups/seed_demo.dump -Force
```

Roughly 20 seconds, including the Odoo restart. Refresh the browser and continue.

### On a teammate's or the evaluator's fresh clone

```powershell
Copy-Item .env.sample .env      # edit both *_change_me values
./scripts/docker-start.ps1
./scripts/db-init-seed.ps1      # restores seed_demo.dump + its filestore
```

---

## 10. Definition of Done Mapping

| `spec.md` §10 DoD Item | Verified In |
| :--- | :--- |
| `db-backup.ps1` tested, producing dumps without errors | §4 |
| `db-restore.ps1` tested, recovering state successfully | §5 |
| Persistence of the `odoo-db-data` volume verified | §3 and `SPEC-0.1.1` `quickstart.md` §5 |
| `docs/test-procedures/test-procedure-0.2.1.md` documented | Authored from this guide during `/speckit-implement` |
| *(gap)* `db-init-seed.ps1` — in scope per §2.1, absent from §9 and §10 | §6, §9; see `plan.md` → Complexity Tracking #5 |

---

## 11. Troubleshooting

| Symptom | Likely Cause | Fix |
| :--- | :--- | :--- |
| Dump is only a few KB | Dumped `postgres` instead of `panaderia_db` | Target `$ODOO_DB_NAME`; verify with §7 |
| `database "panaderia_db" is being accessed by other users` | `web` was not stopped; Odoo's pool reconnected | Ensure `db-restore.ps1` runs `docker compose stop web` before `dropdb` |
| Restore succeeds but the UI shows old data | Odoo's in-memory registry is stale | Restart `web` — the script does this at step 6 |
| `pg_restore: error: did not find magic string` | Artifact corrupted by PowerShell `>` redirection | Regenerate using `pg_dump -f` inside the container plus `docker cp` |
| `database "panaderia_db" does not exist` during restore | Using `pg_restore --clean` on a fresh clone | Use `dropdb --if-exists` + `createdb` first |
| Product images broken after a restore | Filestore missing (empty volume) | Restore the paired `*_filestore.tar`, or re-capture with `-IncludeFilestore` |
| Odoo will not start after a restore | Restored dump came from a different Odoo major version | Restore only artifacts produced by this stack's pinned `odoo:16.0` / `postgres:15-alpine` |
| `docker cp` permission denied on Linux | Container-side file owned by the `postgres` UID | Copy from `/tmp` (as the scripts do), not from inside `pgdata` |
