# Contract: Database Script CLI Surface

**Feature**: `SPEC-0.2.1: Persistencia, Semillas y Respaldos de Base de Datos PostgreSQL`
**Artifacts under contract**: `scripts/db-backup.ps1`, `scripts/db-restore.ps1`, `scripts/db-init-seed.ps1`
**Date**: 2026-09-29
**Upstream contracts**: [`SPEC-0.1.1 compose-topology-contract.md`](../../../0.1-docker-provisioning/0.1.1-local-docker-environment/contracts/compose-topology-contract.md), [`environment-variables-contract.md`](../../../0.1-docker-provisioning/0.1.1-local-docker-environment/contracts/environment-variables-contract.md)

---

## 1. Shared Precondition Block (all three scripts)

Every script begins with the same gate. It is normative, not advisory — Acceptance Scenario 3 depends on it.

| Order | Check | Failure Message (Spanish) | Exit |
| :--- | :--- | :--- | :--- |
| 1 | `.env` exists at the repository root | `ERROR: No existe .env. Ejecuta: Copy-Item .env.sample .env` | `1` |
| 2 | `.env` parsed; `POSTGRES_USER` and `ODOO_DB_NAME` resolved | `ERROR: Falta POSTGRES_USER u ODOO_DB_NAME en .env` | `1` |
| 3 | `docker` is on `PATH` and the daemon responds | `ERROR: Docker no está disponible o el demonio no responde.` | `1` |
| 4 | `panaderia_odoo_db` reports `Running == true` | `ERROR: El contenedor panaderia_odoo_db no está en ejecución. Ejecuta primero: .\scripts\docker-start.ps1` | `1` |

```powershell
# Liveness probe — normative form
$running = docker inspect --format='{{.State.Running}}' panaderia_odoo_db 2>$null
if ($LASTEXITCODE -ne 0 -or $running -ne 'true') { <# message 4, exit 1 #> }
```

> Probe `.State.Running`, **not** `.State.Health.Status`. A database that is running but not yet
> marked `healthy` can still accept `pg_dump` and `pg_restore`, and `db-restore.ps1` must remain
> usable while the stack is mid-recovery.

### `.env` parsing rules

Split each line on the **first** `=` only — a password may legitimately contain `=`. Skip blank lines
and lines whose first non-whitespace character is `#`. Trim surrounding quotes if present.

---

## 2. `scripts/db-backup.ps1`

### Parameters

| Parameter | Type | Default | Purpose |
| :--- | :--- | :--- | :--- |
| `-BackupName` | `string` | `panaderia_backup_<yyyyMMdd_HHmmss>.dump` | Output file name inside `./backups/` |
| `-IncludeFilestore` | `switch` | `$false` | Also archive `/var/lib/odoo/filestore` to `<basename>_filestore.tar` |

### Behavior

1. Run the shared precondition block (§1).
2. Create `./backups/` if absent.
3. Dump **inside** the container:
   ```powershell
   docker exec panaderia_odoo_db pg_dump -U $POSTGRES_USER -d $ODOO_DB_NAME -F c -b -f "/tmp/$BackupName"
   ```
4. Retrieve byte-exactly with `docker cp`, then delete the container-side staging file.
5. When `-IncludeFilestore` is set, `docker exec panaderia_odoo_web tar -cf /tmp/<name>_filestore.tar -C /var/lib/odoo filestore`, then `docker cp` and clean up.
6. Validate the artifact with `pg_restore -l` and confirm bakery relations are present.
7. Report the absolute path and size in green.

### Contract Guarantees

| Guarantee | Detail |
| :--- | :--- |
| **Hot** | The `db` container is never stopped. `pg_dump` takes a consistent snapshot in a single transaction (`spec.md` §3). |
| **Targets the business database** | `-d $ODOO_DB_NAME` (`panaderia_db`) — **never** `-d postgres`, which would produce a valid but empty archive. |
| **Binary-safe** | Written with `pg_dump -f` inside the container and transferred with `docker cp`. PowerShell `>` / `Out-File` are forbidden. |
| **No `-t` flag** | Omitted on `pg_dump` so no pseudo-TTY can perform LF→CRLF translation on a binary stream. |
| **Leaves no residue** | The `/tmp` staging file is removed even when the dump fails. |
| **Atomic from the operator's view** | On any failure, no partial file is left in `./backups/`. |

### Exit Codes

| Code | Meaning |
| :--- | :--- |
| `0` | Backup written and validated |
| `1` | Precondition failed (§1) |
| `2` | `pg_dump` failed |
| `3` | `docker cp` failed, or the retrieved artifact failed `pg_restore -l` validation |

---

## 3. `scripts/db-restore.ps1`

### Parameters

| Parameter | Type | Default | Purpose |
| :--- | :--- | :--- | :--- |
| `-BackupFile` | `string` | **mandatory** | Path to the `.dump` artifact |
| `-Force` | `switch` | `$false` | Skip the interactive confirmation |
| `-RestoreFilestore` | `string` | *(none)* | Path to a companion `*_filestore.tar` to restore alongside |

### Normative Sequence

```text
 1. Shared precondition block (§1)
 2. Test-Path $BackupFile                          → exit 1 if absent
 3. pg_restore -l on the artifact                  → exit 4 if invalid
    ── validate BEFORE destroying anything ──
 4. Confirm with the operator unless -Force        → exit 0 if declined
 5. docker compose stop web                        ← Odoo releases its pool
 6. pg_terminate_backend on $ODOO_DB_NAME          ← sweep stray psql/pgAdmin sessions
 7. dropdb -U $POSTGRES_USER --if-exists $ODOO_DB_NAME
 8. createdb -U $POSTGRES_USER -O $POSTGRES_USER $ODOO_DB_NAME
 9. docker cp $BackupFile → panaderia_odoo_db:/tmp/
10. pg_restore -U $POSTGRES_USER -d $ODOO_DB_NAME --no-owner --no-privileges /tmp/<file>
11. Restore the filestore if -RestoreFilestore was supplied
12. Remove the /tmp staging file
13. docker compose start web
14. Poll until panaderia_odoo_web is healthy, then report success
```

### Why Steps 5–8 Deviate From `spec.md` §4

| Spec Approach | Problem | This Contract |
| :--- | :--- | :--- |
| `pg_terminate_backend` only | Odoo's pool reconnects in milliseconds and `dropdb` loses the race — **intermittently**, so it passes in rehearsal and fails during the defense | `docker compose stop web` first; termination becomes a secondary sweep |
| *(no restart of `web`)* | Odoo caches the registry in memory and serves the pre-restore schema, so the UI contradicts the database | `docker compose start web` at step 13 |
| `pg_restore --clean --if-exists` | Requires the database to already exist; fails on a fresh clone or after `down -v` — the exact case `seed_demo.dump` serves | `dropdb --if-exists` + `createdb` |
| `-d postgres` | Restores into the maintenance database | `-d $ODOO_DB_NAME` |

### Contract Guarantees

| Guarantee | Detail |
| :--- | :--- |
| **Validate before destroy** | `pg_restore -l` runs at step 3. A corrupt artifact is rejected while the current database is still fully intact. |
| **Clean slate** | Drop-and-recreate leaves no orphan sequence, extension, or stale `ir_*` row. |
| **Portable** | `--no-owner --no-privileges` lets a teammate or the evaluator restore `seed_demo.dump` regardless of local role names. |
| **Idempotent** | Restoring the same artifact twice yields the same state. |
| **Confirmed** | Destructive by nature, so it prompts unless `-Force` (`spec.md` §3). |
| **`web` always comes back** | Step 13 runs in a `finally` block, so an aborted restore never leaves Odoo stopped. |

### Exit Codes

| Code | Meaning |
| :--- | :--- |
| `0` | Restore completed and `web` is healthy |
| `1` | Precondition failed, or `-BackupFile` not found |
| `2` | `dropdb` / `createdb` failed |
| `3` | `pg_restore` reported errors |
| `4` | Artifact failed `pg_restore -l` validation — **nothing was modified** |
| `5` | Restore succeeded but `web` did not become healthy within the timeout |

---

## 4. `scripts/db-init-seed.ps1`

> Listed in `spec.md` §2.1 but absent from §9 and §10. Treated as a first-class deliverable —
> see `plan.md` → Complexity Tracking #5.

### Parameters

| Parameter | Type | Default | Purpose |
| :--- | :--- | :--- | :--- |
| `-SeedFile` | `string` | `./backups/seed_demo.dump` | Seed artifact to load |
| `-Force` | `switch` | `$false` | Skip confirmation |

### Behavior

1. Shared precondition block (§1).
2. If `-SeedFile` exists → delegate to `db-restore.ps1 -BackupFile $SeedFile -RestoreFilestore <paired tar> -Force`.
3. If it does **not** exist → bootstrap from scratch: create `$ODOO_DB_NAME`, install the module (`odoo -d $ODOO_DB_NAME -i panaderia --stop-after-init`), then report that the module's own XML seed data (`Modulo_Odoo/data/*.xml`) has been loaded and that transactional demo state must be created through the UI before capturing a new `seed_demo.dump`.
4. Report the resulting state and the URL `http://localhost:${ODOO_HTTP_PORT}`.

### Contract Guarantee

The script is the single one-command path from any state — including a fresh clone with empty volumes — to a demonstrable ERP. This is the operational purpose stated in `spec.md` §3.

---

## 5. Console Output Convention (`spec.md` §4)

| Color | Meaning | Example |
| :--- | :--- | :--- |
| Cyan | Progress | `Generando respaldo de base de datos: panaderia_backup_20260929_221500.dump...` |
| Green | Success | `[OK] Respaldo completado: ./backups/... (412 KB)` |
| Yellow | Warning / non-fatal | `[WARN] Filestore no incluido. Usa -IncludeFilestore para un respaldo completo.` |
| Red | Error | `[ERROR] El contenedor panaderia_odoo_db no está en ejecución.` |

Every message is in Spanish, consistent with Constitution Principle V. Messages must never echo
`POSTGRES_PASSWORD` or `ODOO_ADMIN_PASSWD`.

---

## 6. Verification Contract

| Assertion | Command | Expected |
| :--- | :--- | :--- |
| Backup targets the business database | `Select-String '\-d\s+\$' ./scripts/db-backup.ps1` | Resolves to `$ODOO_DB_NAME`; no literal `-d postgres` on the `pg_dump` line |
| No stream redirection | `Select-String '>\s*"?\$' ./scripts/db-backup.ps1` | No match on any `pg_dump` line |
| Artifact is a valid custom-format archive | `docker exec panaderia_odoo_db pg_restore -l /tmp/x.dump` | Lists a TOC |
| Artifact contains bakery data | `pg_restore -l` output | Includes `panaderia_producto`, `panaderia_categoria` |
| Restore stops `web` | `Select-String 'compose stop web' ./scripts/db-restore.ps1` | One match |
| Restore recreates the database | `Select-String 'dropdb\|createdb' ./scripts/db-restore.ps1` | Both present |
| Restore validates before destroying | Line order in the script | `pg_restore -l` precedes `dropdb` |
| Liveness gate present in all three | `Select-String 'State.Running' ./scripts/db-*.ps1` | Three matches |
| Stopped-stack behavior | `docker compose stop db`, then run each script | Exit `1` with the red Spanish message; no partial artifact |
| `web` always restarts | Abort a restore mid-run (Ctrl+C) | `panaderia_odoo_web` returns to running |
