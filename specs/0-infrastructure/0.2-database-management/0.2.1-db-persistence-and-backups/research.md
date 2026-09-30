# Phase 0: Outline & Research — Persistencia, Semillas y Respaldos PostgreSQL

**Feature**: `SPEC-0.2.1: Persistencia, Semillas y Respaldos de Base de Datos PostgreSQL`
**Branch / Directory**: `specs/0-infrastructure/0.2-database-management/0.2.1-db-persistence-and-backups`
**Date**: 2026-09-29
**Status**: Completed

---

## 1. Executive Summary & Objective

This research validates the backup and restore mechanics sketched in `spec.md` §4 against the actual behavior of PostgreSQL 15, the Odoo connection pool, and Windows PowerShell. Seven decisions were required. Three correct defects that would render the feature non-functional — one of them silently, by producing backups that appear valid but contain no bakery data at all. The remaining four confirm or refine choices the spec made correctly, most notably its use of `docker cp` over stream redirection, which turns out to be essential rather than incidental on Windows.

---

## 2. Research Findings & Technical Decisions

### Decision 1: The dumps must target `panaderia_db`, not `postgres`

* **Decision**: Every `pg_dump`, `pg_restore`, `dropdb`, and `createdb` invocation targets the Odoo business database, read from `ODOO_DB_NAME` in `.env` (default `panaderia_db`). The `postgres` database is used **only** as the connection endpoint for administrative statements that cannot run inside the database being dropped.
* **Rationale**:
  * `POSTGRES_DB=postgres` in `SPEC-0.1.1`'s `.env` creates the cluster's *maintenance* database. Odoo does not use it: the database manager creates a separate database (`panaderia_db`) and installs the Odoo schema there.
  * Every command in `spec.md` §4 passes `-d postgres`. A `pg_dump` of that database succeeds, exits `0`, and writes a small but structurally valid custom-format archive containing **no bakery tables whatsoever**.
  * This is the most dangerous defect in the Capa 0 specs because it fails *silently in the success direction*. The spec's own Acceptance Scenario 1 only checks that the artifact has "tamaño mayor a cero" and a valid binary format — both of which an empty dump satisfies. The operator would discover the problem only when a restore during the defense produced an empty ERP.
  * Sourcing the name from `.env` rather than hardcoding it keeps one authoritative value shared with `SPEC-0.3.1`'s lifecycle scripts.
* **Verification hardening**: Acceptance Scenario 1's check is strengthened accordingly — `pg_restore -l` must list the bakery relations (`panaderia_producto`, `panaderia_categoria`), not merely parse successfully. Size alone is not evidence.
* **Alternatives Considered**:
  * *`pg_dumpall`*: Rejected. It dumps the whole cluster including roles, producing a much larger plain-SQL artifact that cannot be restored selectively with `pg_restore` and offers nothing useful for a single-database demo.
  * *Hardcode `panaderia_db` in each script*: Rejected — three copies of the same literal, and a silent mismatch the moment someone renames the database in `.env`.

### Decision 2: Stop the `web` container for the restore — terminating sessions is not enough

* **Decision**: `db-restore.ps1` executes `docker compose stop web`, performs the restore, then `docker compose start web`. The `pg_terminate_backend` statement from `spec.md` §4 is retained, but as a secondary sweep for stray `psql`/pgAdmin sessions rather than the primary mechanism.
* **Rationale**:
  * Odoo maintains a persistent PostgreSQL connection pool. After `pg_terminate_backend` kills those backends, Odoo's pool detects the drop and **reconnects within milliseconds**. `dropdb` then fails with `database "panaderia_db" is being accessed by other users`. The failure is a race, so it is intermittent — which is strictly worse than a deterministic failure, because it will pass in rehearsal and fail during the defense.
  * Even if `dropdb` did win the race, Odoo caches the loaded registry (models, views, access rules) in process memory. A restored database would be served through the *old* registry until `web` restarts, producing bizarre mismatches between what is in PostgreSQL and what the UI shows.
  * Stopping `web` solves both problems with one action, and it is fast: Odoo shuts down in roughly 2–3 seconds and starts back into a warm registry.
  * This is fully consistent with `spec.md` §3's constraint, which requires that **backups** be hot. It says nothing about restores — and a restore is inherently a disruptive operation.
* **Alternatives Considered**:
  * *Retry `pg_terminate_backend` in a loop until `dropdb` succeeds*: Rejected — an unbounded race that can still lose, and it leaves the stale-registry problem completely unaddressed.
  * *`ALTER DATABASE ... WITH ALLOW_CONNECTIONS false` before dropping*: Rejected — it blocks new connections but not existing ones, so it must still be paired with termination, and it leaves the database in a non-default state if the script aborts midway.
  * *Restore into a new database and switch Odoo's target*: Rejected — it would require editing `.env` and recreating the container, which is far more disruptive than a 5-second `web` restart.

### Decision 3: `docker cp`, never PowerShell stream redirection

* **Decision**: Write the dump to `/tmp` **inside** the container with `pg_dump -f`, then transfer it to the host with `docker cp`. Never use `docker exec pg_dump > file.dump`. Confirms and reinforces the approach in `spec.md` §4.
* **Rationale**:
  * Windows PowerShell 5.1's `>` and `Out-File` operators are **text** operators. They decode the stream, apply an encoding (UTF-16LE by default in 5.1), and translate line endings. Applied to a binary `-Fc` archive this corrupts it irrecoverably, and the corruption is not obvious: the file has a plausible size and `pg_restore -l` may even read the header before failing deep into the restore.
  * `docker cp` performs a byte-exact copy through a tar stream with no encoding layer, making it correct on both PowerShell 5.1 and PowerShell 7.
  * Staging in `/tmp` also keeps the artifact off the `pgdata` volume, so a partial dump can never be mistaken for database content and cannot consume the datadir's space.
  * The container-side `/tmp` file is removed after the copy, as `spec.md` §4 already specifies.
* **Refinement**: drop the `-t` (TTY) flag from `docker exec` on the `pg_dump` call. Because the archive is written via `-f` rather than stdout, `-t` is harmless here — but a pseudo-TTY performs LF→CRLF translation on the stream, so the habit is one keystroke away from corrupting a future variant that does write to stdout. `-t` is retained on `psql` calls, where it improves readability of tabular output.
* **Alternatives Considered**:
  * *`[System.IO.File]::WriteAllBytes` with a captured byte stream*: Rejected — PowerShell would have to buffer the entire archive in memory as a byte array, and capturing raw bytes from `docker exec` stdout in PowerShell 5.1 is itself unreliable.
  * *A bind-mounted `./backups` directory into the `db` container*: Rejected — it would let `pg_dump` write straight to the host, but it grants the database container write access to a host directory for the entire stack lifetime, and the file would be owned by the container's `postgres` UID, creating permission friction on Linux.

### Decision 4: `dropdb` + `createdb` instead of `pg_restore --clean`

* **Decision**: Restore sequence is: terminate sessions → `dropdb --if-exists` → `createdb -O $POSTGRES_USER` → `pg_restore --no-owner --no-privileges -d $ODOO_DB_NAME`.
* **Rationale**:
  * `pg_restore --clean --if-exists` (the `spec.md` §4 approach) drops objects *within* a database that must already exist. On a fresh clone, or after `docker compose down -v`, `panaderia_db` does not exist — and that is precisely the scenario `seed_demo.dump` is versioned to serve. The spec's restore would fail at the first step of the very workflow it was written for.
  * Dropping and recreating the database guarantees a clean slate: no orphan sequence, no leftover extension, no stale Odoo `ir_*` row that `--clean` failed to reach because the dump did not mention it.
  * `--no-owner --no-privileges` makes the artifact portable between machines whose PostgreSQL role names differ, which matters because `seed_demo.dump` is committed and restored by teammates and by the evaluator.
  * `dropdb` and `createdb` must connect through the `postgres` maintenance database — PostgreSQL cannot drop the database a session is connected to. This is the one legitimate use of `-d postgres` in the whole feature.
* **Alternatives Considered**:
  * *`pg_restore --create --clean`*: Rejected — the `CREATE DATABASE` statement it emits carries the source cluster's encoding, collation, and owner. Restoring onto a differently configured cluster fails with a locale mismatch that is opaque to diagnose.
  * *`TRUNCATE` every table then restore data only*: Rejected — it cannot handle schema changes between the dump and the current state, which is the common case as Capa 1–5 modules evolve.

### Decision 5: `pg_dump` alone is not a complete Odoo backup — the filestore lives outside PostgreSQL

* **Decision**: `db-backup.ps1` accepts an `-IncludeFilestore` switch that produces a companion `<name>_filestore.tar` from `/var/lib/odoo/filestore` inside the `web` container. The switch is **off by default** but **mandatory** when generating `backups/seed_demo.dump`.
* **Rationale**:
  * Odoo stores `ir.attachment` binary payloads — product images, generated PDF reports, uploaded documents — as files on disk under `data_dir/filestore/<dbname>`, not as PostgreSQL bytea. A `pg_dump` therefore captures the attachment *metadata rows* while leaving the actual bytes behind on a different volume (`panaderia_odoo_web_data`).
  * Within one long-lived stack this rarely bites: the filestore only ever grows, so restoring an older dump finds a filestore that is a superset of what it needs, and images still resolve by checksum.
  * It bites hard in exactly one scenario — a fresh clone, or a restore after `docker compose down -v`, where the filestore volume is empty. The restored database references attachments whose files do not exist, and the UI renders broken images. That is a visible, on-screen failure in front of the evaluator, which is the one place this project cannot afford one.
  * Because `seed_demo.dump` exists specifically to serve the fresh-clone path, pairing it with a filestore archive is not optional.
  * Keeping the switch off by default preserves the fast, lightweight day-to-day backup the spec describes.
* **Alternatives Considered**:
  * *Odoo's own `/web/database/backup` ZIP*: Rejected as the primary mechanism. It bundles dump and filestore in one file, which is genuinely convenient, but it requires the master password, a live HTTP session, and Odoo to be running and healthy — so it is unusable as a recovery tool precisely when Odoo is broken. It is documented in `quickstart.md` as a complementary manual option.
  * *Always archive the filestore*: Rejected — it slows the common case and produces a second file the operator must keep paired for every routine backup.
  * *Ignore the filestore entirely*: Rejected — it works until the fresh-clone demo, then fails visibly.

### Decision 6: Container-liveness preconditions and `.env` loading

* **Decision**: All three scripts begin with a shared precondition block: verify `panaderia_odoo_db` reports `Running == true` via `docker inspect`, load `.env` into script-scoped variables, and exit non-zero with a Spanish diagnostic if either check fails.
* **Rationale**:
  * Acceptance Scenario 3 requires exactly this behavior. Without it, `docker exec` against a stopped container emits a raw Docker error the operator must interpret under time pressure.
  * `docker inspect --format='{{.State.Running}}'` is more precise than parsing `docker ps` output, and it distinguishes "stopped" from "does not exist" when paired with the command's exit code.
  * Checking `Running` rather than `Health.Status` is deliberate for `db-restore.ps1`: it must also work while the stack is mid-recovery, and a database that is running but not yet marked `healthy` can still accept `pg_restore`.
  * Loading `.env` in PowerShell requires skipping comments and blank lines and splitting on the *first* `=` only, since a password may legitimately contain `=`.
* **Alternatives Considered**:
  * *Assume the containers are up and let Docker fail*: Rejected — directly contradicts Acceptance Scenario 3.
  * *Auto-start the containers when they are down*: Rejected — a backup script silently starting infrastructure is surprising, and `SPEC-0.3.1`'s `docker-start.ps1` already owns that responsibility.

### Decision 7: Versioning one seed artifact while ignoring every other dump

* **Decision**: `.gitignore` uses `backups/*` with explicit negations for `!backups/.gitkeep` and `!backups/seed_demo.dump`.
* **Rationale**:
  * `spec.md` §2.1 requires `seed_demo.dump` versioned for evaluation, while §7 forbids committing backups of real business data. The negation pattern encodes that distinction mechanically instead of relying on operator discipline.
  * `backups/*` (with a wildcard) rather than `backups/` is required: Git cannot re-include a file with `!` if one of its parent directories is itself excluded, so ignoring the directory outright would make the negations inert.
  * `.gitkeep` keeps the directory present in a fresh clone, so `db-backup.ps1` never has to create it — though the script still does, defensively.
  * `seed_demo.dump` must contain only synthetic bakery data (invented products, fictitious customers). At demo scale it is well under a megabyte, so Git LFS is unnecessary; if it ever exceeds a few megabytes, LFS becomes the right answer rather than growing the repository history.
* **Alternatives Considered**:
  * *Keep `seed_demo.dump` outside `backups/` to avoid negations*: Rejected — `spec.md` §2.1 names the path, and the negation pattern is idiomatic Git.
  * *Generate the seed from an Odoo XML data file instead of a dump*: Rejected as a replacement. Module seed data (`Modulo_Odoo/data/*.xml`) already covers products and categories and belongs to Capa 1; a dump additionally captures *transactional* state — confirmed sales, stock movements, issued invoices — which XML data files cannot express.

---

## 3. Technology Matrix

| Parameter | Specification |
| :--- | :--- |
| **Script Runtime** | Windows PowerShell 5.1+ (PowerShell 7 compatible) |
| **Backup Tool** | `pg_dump` from `postgres:15-alpine`, executed via `docker exec` |
| **Archive Format** | PostgreSQL custom format (`-Fc`) — compressed, selective, `pg_restore`-compatible |
| **Restore Tool** | `pg_restore --no-owner --no-privileges`, preceded by `dropdb` / `createdb` |
| **Transfer Mechanism** | `docker cp` (byte-exact tar stream) — **never** PowerShell `>` or `Out-File` |
| **Target Database** | `${ODOO_DB_NAME}` from `.env`, default `panaderia_db` |
| **Admin Endpoint** | `postgres` maintenance database, used only for `dropdb` / `createdb` / session termination |
| **Target Container** | `panaderia_odoo_db` (per `SPEC-0.1.1` topology contract) |
| **Filestore Path** | `/var/lib/odoo/filestore/<dbname>` inside `panaderia_odoo_web` |
| **Artifact Location** | `./backups/` on the host |
| **Console Convention** | Cyan = progress, Green = success, Yellow = warning, Red = error (`spec.md` §4) |

---

## 4. Risks and Mitigations

| Risk | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| Dump targets the `postgres` maintenance database | **Critical, silent** — backups look valid but contain no bakery data; discovered only when a restore produces an empty ERP | Decision 1: target `$ODOO_DB_NAME`. `quickstart.md` §7 validates with `pg_restore -l` that bakery relations are actually listed, not just that the file parses |
| Odoo's pool reconnects and `dropdb` loses the race | Intermittent restore failure — passes in rehearsal, fails during the defense | Decision 2: `docker compose stop web` for the duration of the restore |
| Odoo serves a stale in-memory registry after a restore | UI contradicts the database; looks like data corruption | Decision 2: `web` is restarted as part of the restore, not merely reconnected |
| Target database absent on a fresh clone | `pg_restore --clean` fails at the first step of the seed workflow | Decision 4: `dropdb --if-exists` + `createdb` |
| Binary dump corrupted by PowerShell redirection | Unrestorable artifact; corruption not obvious from the file size | Decision 3: `docker cp` only; `quickstart.md` §7 validates every artifact with `pg_restore -l` |
| Filestore not captured; images broken after a full reset | Visible on-screen failure during the defense | Decision 5: `-IncludeFilestore`, mandatory for `seed_demo.dump` |
| Operator backup committed to the repository | Business-data leak; `spec.md` §7 violation | Decision 7: `backups/*` ignored with targeted negations; verified in `quickstart.md` §8 |
| Scripts run against a stopped stack | Raw Docker errors instead of actionable guidance | Decision 6: liveness precondition in all three scripts (Acceptance Scenario 3) |
| PostgreSQL major-version mismatch on restore | `pg_restore` refuses or misbehaves | The dump is always produced and consumed inside the same pinned `postgres:15-alpine` image; the pin is part of the `SPEC-0.1.1` contract |
| `seed_demo.dump` grows large enough to bloat Git history | Slow clones for the whole team | Keep the seed synthetic and minimal; adopt Git LFS if it ever exceeds a few megabytes |
| Restore aborts midway, leaving no database at all | Stack starts but Odoo finds nothing | `db-restore.ps1` validates the artifact with `pg_restore -l` **before** dropping anything, so a bad file is rejected while the current state is still intact |

---

## 5. Open Questions

None blocking. Two spec gaps are recorded in `plan.md` → *Known Cross-Artifact Inconsistencies* for `/speckit-analyze`: `db-init-seed.ps1` is in scope (§2.1) but missing from both the deliverables list (§9) and the Definition of Done (§10), and `.gitignore` currently carries no `backups/` rules at all.
