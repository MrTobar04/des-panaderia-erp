# Tasks: Persistencia, Semillas y Respaldos de Base de Datos PostgreSQL

**Input**: Design documents from `specs/0-infrastructure/0.2-database-management/0.2.1-db-persistence-and-backups/`

**Prerequisites**: [`plan.md`](./plan.md) (required), [`spec.md`](./spec.md) (required), [`research.md`](./research.md), [`contracts/`](./contracts/), [`quickstart.md`](./quickstart.md). **Blocked by `SPEC-0.1.1`** — `panaderia_odoo_db`, the `panaderia_odoo_db_data` volume, and `.env` must exist first.

**Tests**: No automated unit-test suite applies — this feature delivers operator scripts. Verification is a **round-trip test** (create a marker record → back up → destroy it → restore → confirm it returns) plus artifact validation with `pg_restore -l`, per `spec.md` §6. Constitution Principle IV's mandatory test-procedure document is task **T059**.

**Organization**: Tasks are grouped by user story. This project's specs express requirements as BDD Acceptance Scenarios (`spec.md` §5), so each scenario maps to one story. US4 is derived from `spec.md` §2.1 and §3 rather than a scenario, because `db-init-seed.ps1` is in scope but absent from §5, §9, and §10:

| Story | Source | Title |
| :--- | :--- | :--- |
| **US1** (P1) | `spec.md` §5 Scenario 1 | Creación de respaldo bajo demanda |
| **US2** (P2) | `spec.md` §5 Scenario 2 | Restauración íntegra de estado previo |
| **US3** (P3) | `spec.md` §5 Scenario 3 | Validación de dependencias de contenedores |
| **US4** (P3) | `spec.md` §2.1 + §3 (spec gap) | Bootstrap de estado de demostración |

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

PowerShell operator scripts in `scripts/`, data artifacts in `backups/`. All PostgreSQL binaries are invoked **inside** the `panaderia_odoo_db` container, so the host needs no PostgreSQL installation. Paths are relative to `des-panaderia-erp/`.

> **Critical correctness note carried into every task**: dumps and restores target `$ODOO_DB_NAME` (`panaderia_db`), **never** `-d postgres`. The commands in `spec.md` §4 use the `postgres` maintenance database, which yields a valid, non-empty, structurally sound archive containing **no bakery data at all** — a failure that passes the spec's own size check. See `research.md` Decision 1.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the upstream stack and create the artifact directory

- [X] T001 Confirm the database container is running with `docker inspect --format='{{.State.Running}}' panaderia_odoo_db`, expecting `true`
- [X] T002 [P] Create the `backups/` directory at the repository root with a tracked `backups/.gitkeep` file so a fresh clone always has the directory present
- [X] T003 [P] Confirm `.env` defines `ODOO_DB_NAME` and `POSTGRES_USER` by running `Select-String "^ODOO_DB_NAME=|^POSTGRES_USER=" ./.env`, expecting two matches
- [X] T004 Identify the two databases by running `docker exec panaderia_odoo_db psql -U odoo -c "\l"` and confirming that `postgres` (maintenance, no bakery data) and `panaderia_db` (the Odoo business database) are distinct — the distinction every subsequent task depends on

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The Git exclusion rules and the shared precondition gate that all three scripts embed

**⚠️ CRITICAL**: Without the `.gitignore` rules, the first operator backup is staged for commit, leaking business data. Without the precondition gate, every script emits raw Docker errors instead of actionable guidance.

- [X] T005 Add the backup exclusion rules to `.gitignore` exactly as specified in `contracts/backup-artifact-contract.md` §6 — `backups/*` followed by the negations `!backups/.gitkeep`, `!backups/seed_demo.dump`, and `!backups/seed_demo_filestore.tar`
- [X] T006 Verify the wildcard form is used (`backups/*`, not `backups/`), because Git cannot re-include a file with `!` when a parent directory is itself excluded — ignoring the directory outright would silently make all three negations inert
- [X] T007 Confirm the rules work by asserting `git check-ignore -v backups/prueba.dump` prints the matching rule while `git check-ignore backups/seed_demo.dump` exits non-zero
- [X] T008 Implement the shared precondition block described in `contracts/db-scripts-cli-contract.md` §1, to be inlined at the top of all three scripts: verify `.env` exists, parse it, verify Docker responds, and verify `panaderia_odoo_db` reports `Running == true`
- [X] T009 Implement `.env` parsing in the shared precondition block by splitting each line on the **first** `=` only (a password may legitimately contain `=`), skipping blank lines and lines whose first non-whitespace character is `#`, and trimming surrounding quotes
- [X] T010 Probe `.State.Running` rather than `.State.Health.Status` in the shared precondition block, so `db-restore.ps1` remains usable while the stack is mid-recovery — a running-but-not-yet-healthy database still accepts `pg_restore`

**Checkpoint**: Git exclusions verified and the precondition gate defined — script authoring can begin

---

## Phase 3: User Story 1 - Creación de respaldo bajo demanda (Priority: P1) 🎯 MVP

**Goal**: One command produces a timestamped, validated, binary-format dump of the bakery business database in `backups/`, without stopping the database.

**Independent Test**: Create a product named `Tarta de Manzana Especial` in the Odoo UI, run `./scripts/db-backup.ps1 -BackupName test_backup.dump`, and confirm the artifact exists, is larger than zero, and that `pg_restore -l` on it lists `panaderia_producto`.

### Implementation for User Story 1

- [X] T011 [US1] Create `scripts/db-backup.ps1` with the `-BackupName` parameter defaulting to `panaderia_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').dump` — a format that sorts chronologically and contains no character invalid in a Windows filename
- [X] T012 [US1] Add the `-IncludeFilestore` switch to `scripts/db-backup.ps1`, defaulting to `$false`, per `plan.md` → Complexity Tracking #4
- [X] T013 [US1] Inline the shared precondition block (T008–T010) at the top of `scripts/db-backup.ps1` and resolve the repository root with `Split-Path -Parent $PSScriptRoot`
- [X] T014 [US1] Create `backups/` if absent in `scripts/db-backup.ps1`, defensively, even though `backups/.gitkeep` should already guarantee it exists
- [X] T015 [US1] Implement the dump in `scripts/db-backup.ps1` as `docker exec panaderia_odoo_db pg_dump -U $POSTGRES_USER -d $ODOO_DB_NAME -F c -b -f "/tmp/$BackupName"` — targeting `$ODOO_DB_NAME`, **never** the literal `postgres`, per `research.md` Decision 1
- [X] T016 [US1] Omit the `-t` (TTY) flag from the `pg_dump` `docker exec` call in `scripts/db-backup.ps1`, since a pseudo-TTY performs LF→CRLF translation and must never touch a binary stream
- [X] T017 [US1] Retrieve the artifact in `scripts/db-backup.ps1` with `docker cp` for a byte-exact tar-stream transfer, and **never** with PowerShell `>` or `Out-File`, which are text operators that apply an encoding and corrupt a binary archive irrecoverably (`research.md` Decision 3)
- [X] T018 [US1] Delete the container-side `/tmp` staging file in `scripts/db-backup.ps1` even when the dump fails, leaving no residue inside the container
- [X] T019 [US1] Implement the filestore branch in `scripts/db-backup.ps1` so that when `-IncludeFilestore` is set it runs `docker exec panaderia_odoo_web tar -cf /tmp/<name>_filestore.tar -C /var/lib/odoo filestore`, then `docker cp`s it to `backups/<basename>_filestore.tar` and cleans up
- [X] T020 [US1] Validate the retrieved artifact in `scripts/db-backup.ps1` by staging it back and running `pg_restore -l`, asserting the table of contents lists `panaderia_producto` — **size and parseability alone are not evidence**, because a dump of `postgres` satisfies both
- [X] T021 [US1] Implement the exit codes from `contracts/db-scripts-cli-contract.md` §2 in `scripts/db-backup.ps1`: `0` success, `1` precondition failed, `2` `pg_dump` failed, `3` transfer or validation failed, leaving no partial file in `backups/` on any failure
- [X] T022 [US1] Implement the Spanish colour-coded console output in `scripts/db-backup.ps1` per `contracts/db-scripts-cli-contract.md` §5 (Cyan progress, Green success with path and size, Yellow warning when the filestore was not included, Red error), never echoing `POSTGRES_PASSWORD`
- [X] T023 [US1] Verify the round trip's first half by creating the product `Tarta de Manzana Especial` (Categoría `Pastel`, Costo `4.50`, Precio de Venta `12.00`) in the Odoo UI, then running `./scripts/db-backup.ps1 -BackupName test_backup.dump`
- [X] T024 [US1] Confirm the backup was **hot** by asserting `docker inspect --format='{{.State.Running}}' panaderia_odoo_db` still returns `true` and `http://localhost:8069/web/login` still answers `200` immediately after the dump (`spec.md` §3)
- [X] T025 [US1] Confirm the artifact is genuinely useful by staging it and running `docker exec panaderia_odoo_db pg_restore -l /tmp/verify.dump | Select-String "panaderia_"`, asserting `panaderia_producto` and `panaderia_categoria` both appear

**Checkpoint**: Acceptance Scenario 1 satisfied — a validated, non-empty, bakery-data-bearing hot backup exists

---

## Phase 4: User Story 2 - Restauración íntegra de estado previo (Priority: P2)

**Goal**: One command restores the database to exactly the state captured in a dump, with full referential integrity and no stale Odoo registry.

**Independent Test**: Delete `Tarta de Manzana Especial` from the Odoo UI, run `./scripts/db-restore.ps1 -BackupFile ./backups/test_backup.dump`, refresh the browser, and confirm the product reappears with its costs and recomputed margin intact.

### Implementation for User Story 2

- [X] T026 [US2] Create `scripts/db-restore.ps1` with a mandatory `-BackupFile` parameter plus the `-Force` and `-RestoreFilestore` parameters from `contracts/db-scripts-cli-contract.md` §3, and inline the shared precondition block
- [X] T027 [US2] Implement step 3 of the normative sequence in `scripts/db-restore.ps1` — validate the artifact with `pg_restore -l` and exit `4` if invalid — **before any destructive step**, so a corrupt file is rejected while the current database remains fully intact
- [X] T028 [US2] Implement the interactive confirmation in `scripts/db-restore.ps1`, skipped only when `-Force` is passed, since restore is destructive by nature (`spec.md` §3)
- [X] T029 [US2] Implement step 5 in `scripts/db-restore.ps1` as `docker compose stop web`, because Odoo's connection pool reconnects within milliseconds and `pg_terminate_backend` alone loses the race with `dropdb` — intermittently, so it passes in rehearsal and fails during the defense (`research.md` Decision 2)
- [X] T030 [US2] Implement step 6 in `scripts/db-restore.ps1` as the `pg_terminate_backend` sweep against `$ODOO_DB_NAME`, retained as a secondary measure to clear any stray `psql` or pgAdmin session the operator left open
- [X] T031 [US2] Implement steps 7–8 in `scripts/db-restore.ps1` as `dropdb -U $POSTGRES_USER --if-exists $ODOO_DB_NAME` followed by `createdb -U $POSTGRES_USER -O $POSTGRES_USER $ODOO_DB_NAME`, both connecting through the `postgres` maintenance database — the one legitimate use of `-d postgres` in this feature
- [X] T032 [US2] Replace `pg_restore --clean --if-exists` from `spec.md` §4 with the drop-and-recreate approach in `scripts/db-restore.ps1`, because `--clean` requires the database to already exist and therefore fails on a fresh clone or after `docker compose down -v` — precisely the case `seed_demo.dump` exists to serve (`research.md` Decision 4)
- [X] T033 [US2] Implement steps 9–10 in `scripts/db-restore.ps1` as `docker cp` of the artifact to `/tmp` followed by `pg_restore -U $POSTGRES_USER -d $ODOO_DB_NAME --no-owner --no-privileges`, with the ownership flags making the artifact portable across machines whose PostgreSQL role names differ
- [X] T034 [US2] Implement the `-RestoreFilestore` branch in `scripts/db-restore.ps1`, extracting the companion `*_filestore.tar` into `/var/lib/odoo` inside `panaderia_odoo_web`
- [X] T035 [US2] Implement steps 12–14 in `scripts/db-restore.ps1` — remove the `/tmp` staging file, run `docker compose start web` inside a `finally` block so an aborted restore never leaves Odoo stopped, then poll until `panaderia_odoo_web` reports `healthy`
- [X] T036 [US2] Implement the exit codes from `contracts/db-scripts-cli-contract.md` §3 in `scripts/db-restore.ps1`: `0` success, `1` precondition or file missing, `2` drop/create failed, `3` `pg_restore` errors, `4` artifact invalid with **nothing modified**, `5` `web` never became healthy
- [X] T037 [US2] Implement the seven-step progress output in `scripts/db-restore.ps1` shown in `quickstart.md` §5, so the operator can see exactly which stage is running during the 20-second window
- [X] T038 [US2] Verify the round trip's second half by deleting `Tarta de Manzana Especial` in the Odoo UI, running `./scripts/db-restore.ps1 -BackupFile ./backups/test_backup.dump`, and confirming the product reappears with `Costo 4.50`, `Precio de Venta 12.00`, and a correctly recomputed margin
- [X] T039 [US2] Confirm no referential-integrity damage by running `docker compose logs --tail 50 web | Select-String -Pattern "ERROR|Traceback"` after the restore and asserting no output
- [X] T040 [US2] Confirm idempotency by restoring the same artifact a second time and verifying the resulting state is identical

**Checkpoint**: Acceptance Scenario 2 satisfied — the round-trip test passes and Odoo serves the restored data, not a stale registry

---

## Phase 5: User Story 3 - Validación de dependencias de contenedores (Priority: P3)

**Goal**: Every script detects a stopped database container and guides the operator to start the stack, instead of surfacing a raw Docker error.

**Independent Test**: Run `docker compose stop db`, then invoke all three scripts and confirm each prints the red Spanish guidance message, exits `1`, and writes no partial artifact.

> The precondition block itself was defined in Foundational (T008–T010) because US1 and US2 both embed it. This story verifies the behaviour across all three scripts and confirms the operator-facing guidance.

### Implementation for User Story 3

- [X] T041 [US3] Confirm the precondition block is present in all three scripts by running `Select-String 'State.Running' ./scripts/db-*.ps1` and asserting three matches
- [X] T042 [US3] Stop the database with `docker compose stop db`, then run `./scripts/db-backup.ps1` and confirm it prints `[ERROR] El contenedor panaderia_odoo_db no está en ejecución.` followed by the guidance `Ejecuta primero: .\scripts\docker-start.ps1`, exits `1`, and leaves no file in `backups/`
- [X] T043 [US3] With the database still stopped, run `./scripts/db-restore.ps1 -BackupFile ./backups/test_backup.dump` and `./scripts/db-init-seed.ps1`, confirming both produce the same red message and exit `1`
- [X] T044 [US3] Confirm the distinct error paths by also testing with Docker Desktop itself stopped, verifying the message is `ERROR: Docker no está disponible o el demonio no responde.` rather than the container-specific one
- [X] T045 [US3] Restore normal service with `docker compose start db` and confirm all three scripts return to exit `0`

**Checkpoint**: Acceptance Scenario 3 satisfied — all three scripts fail gracefully with actionable Spanish guidance

---

## Phase 6: User Story 4 - Bootstrap de estado de demostración (Priority: P3)

**Goal**: One command takes any state — including a fresh clone with empty volumes — to a fully populated, demonstrable ERP.

**Independent Test**: Run `docker compose down -v`, then `./scripts/docker-start.ps1` followed by `./scripts/db-init-seed.ps1`, and confirm the Odoo UI shows the full demo catalogue, sales, invoices, and at least one low-stock alert.

> Derived from `spec.md` §2.1 (in scope) and §3 (stated operational purpose), **not** from an acceptance scenario. `db-init-seed.ps1` is absent from §5, §9, and §10 — a spec gap recorded in `plan.md` → Complexity Tracking #5.

### Implementation for User Story 4

- [X] T046 [US4] Create `scripts/db-init-seed.ps1` with the `-SeedFile` parameter defaulting to `./backups/seed_demo.dump` and a `-Force` switch, and inline the shared precondition block
- [X] T047 [US4] Implement the seed-present branch in `scripts/db-init-seed.ps1` to delegate to `./scripts/db-restore.ps1 -BackupFile $SeedFile -RestoreFilestore <paired tar> -Force`, reusing the validated restore path rather than duplicating it
- [X] T048 [US4] Implement the bootstrap branch in `scripts/db-init-seed.ps1` for when no seed file exists — create `$ODOO_DB_NAME`, run `docker compose exec web odoo -d $ODOO_DB_NAME -i panaderia --stop-after-init`, and report that the module's own XML seed data has loaded while transactional demo state must still be created through the UI
- [X] T049 [US4] Report the resulting state and the URL `http://localhost:$ODOO_HTTP_PORT` at the end of `scripts/db-init-seed.ps1`, reading the port from `.env` rather than hardcoding `8069`
- [X] T050 [US4] Populate a complete demo state through the Odoo UI per `contracts/backup-artifact-contract.md` §4 — roughly 15 synthetic products across Pan, Pastel, Galleta, and Bebida; 8 sales orders spanning `Borrador` and `Confirmada`; matching invoices in `Pendiente` and `Pagada`; and at least one product below its minimum stock threshold so the `SPEC-1.2.1` low-stock alert is visible
- [X] T051 [US4] Generate the versioned seed artifacts by running `./scripts/db-backup.ps1 -BackupName seed_demo.dump -IncludeFilestore`, producing both `backups/seed_demo.dump` and `backups/seed_demo_filestore.tar`
- [X] T052 [US4] Confirm the seed contains only synthetic data — invented products and fictitious customers, no real business or personal information — per `spec.md` §7
- [X] T053 [US4] Confirm the seed artifacts are under the 1 MB size budget from `contracts/backup-artifact-contract.md` §4, and note that Git LFS becomes the right answer if they ever exceed a few megabytes
- [X] T054 [US4] Verify the full-reset recovery path by running `docker compose down -v`, then `./scripts/docker-start.ps1`, then `./scripts/db-init-seed.ps1`, and confirming product **images render correctly** — which is the whole reason the filestore companion archive is mandatory for this artifact
- [X] T055 [US4] Confirm both seed artifacts are tracked by asserting `git ls-files --error-unmatch backups/seed_demo.dump backups/seed_demo_filestore.tar` exits `0`

**Checkpoint**: A fresh clone reaches a fully demonstrable ERP in three commands, and the 20-second mid-defense recovery path is proven

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: The security sweep, the mandatory test-procedure document, and defect-regression guards

- [X] T056 Guard against the highest-severity defect by asserting `Select-String -Path ./scripts/db-*.ps1 -Pattern '\-d\s+postgres'` matches **only** the `dropdb`/`createdb` administrative connections in `db-restore.ps1`, and never a `pg_dump` or `pg_restore` line
- [X] T057 [P] Guard against binary corruption by asserting no `pg_dump` line in `scripts/db-backup.ps1` uses PowerShell stream redirection (`>` or `Out-File`)
- [X] T058 [P] Execute the full security verification table from `quickstart.md` §8, confirming operator backups are ignored, the seed artifacts and `.gitkeep` are tracked, `git status --short backups/` lists no untracked `.dump`, and `git log --all --oneline -- backups/` shows only the intended files
- [X] T059 [P] Author `docs/test-procedures/test-procedure-0.2.1.md` from `quickstart.md` §§2–8, mapping each of the three acceptance scenarios to its numbered verification steps (Constitution Principle IV; `spec.md` §10 DoD item 4)
- [X] T060 [P] Add the demo playbook from `quickstart.md` §9 to `docs/test-procedures/test-procedure-0.2.1.md` — pre-defense freeze, mid-defense recovery, and fresh-clone bootstrap — since that is the feature's stated operational purpose
- [X] T061 [P] Populate the troubleshooting table in `docs/test-procedures/test-procedure-0.2.1.md` from `quickstart.md` §11, covering all eight known symptoms
- [X] T062 Document the retention guidance from `contracts/backup-artifact-contract.md` §7 in `Instrucciones_Instalacion.txt`, including the housekeeping snippet that keeps the five most recent automatic backups
- [X] T063 Confirm measured performance against the `plan.md` targets — a demo-sized backup under 5 seconds producing an artifact under 1 MB, and a full restore under 20 seconds including the `web` stop/start cycle
- [X] T064 Update the `SPEC-0.2.1` row in `specs/spec-plan.md`, confirm the four `spec.md` §10 DoD checkboxes are satisfied, and record the two spec gaps for `/speckit-analyze`: `db-init-seed.ps1` missing from §9/§10, and §4's scripts targeting the wrong database

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Depends on `SPEC-0.1.1` being complete
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories**
- **User Story 1 (Phase 3)**: Depends on Foundational
- **User Story 2 (Phase 4)**: Depends on Foundational, and **on US1** for an artifact to restore. T038 also needs T023's marker product
- **User Story 3 (Phase 5)**: Depends on US1, US2, and US4 existing, since it verifies the gate across all three scripts
- **User Story 4 (Phase 6)**: Depends on **US2**, because `db-init-seed.ps1` delegates to `db-restore.ps1`
- **Polish (Phase 7)**: Depends on all four stories

### Cross-Feature Dependencies

| This Feature Needs | From | Why |
| :--- | :--- | :--- |
| `panaderia_odoo_db` container | `SPEC-0.1.1` | Every PostgreSQL binary runs inside it |
| `panaderia_odoo_db_data` volume | `SPEC-0.1.1` | Durable persistence being backed up |
| `.env` with `ODOO_DB_NAME`, `POSTGRES_USER` | `SPEC-0.1.1` T004 | Single source of truth for the target database |
| `panaderia_odoo_web` + filestore | `SPEC-0.1.1` | `-IncludeFilestore` archives `/var/lib/odoo/filestore` |
| Module installed as `panaderia` | `SPEC-0.1.2` | T048's bootstrap runs `-i panaderia`; T025 asserts `panaderia_*` relations exist |
| `docker-start.ps1` | `SPEC-0.3.1` | Referenced by every precondition-failure message |

### User Story Dependencies

Unlike a typical spec-kit feature, these stories form a chain rather than a parallel set:

```text
US1 (backup) ──► US2 (restore) ──► US4 (seed) ──► US3 (verify the gate across all three)
```

- **US1 (P1)**: Independent. Delivers standalone value — a working backup is useful before a restore exists
- **US2 (P2)**: Needs an artifact from US1 to restore
- **US4 (P3)**: Delegates to US2's restore path
- **US3 (P3)**: Verification-only; needs all three scripts to exist

### Within Each User Story

Each script is a single file, so its authoring tasks are sequential. Verification tasks that follow a completed script are independent and parallelizable.

### Parallel Opportunities

- **Phase 1**: T002 and T003 in parallel
- **Phase 2**: None — sequential build of `.gitignore` and the shared block
- **Phases 3–6**: Script authoring is sequential within each story; different stories cannot be parallelized because of the dependency chain above
- **Phase 7**: T057, T058, T059, T060, T061 in parallel (different files)

---

## Parallel Example: Phase 7 Polish

```powershell
# Five independent deliverables, different files:
Task: "Assert no pg_dump line in db-backup.ps1 uses PowerShell stream redirection"
Task: "Execute the security verification table from quickstart.md §8"
Task: "Author docs/test-procedures/test-procedure-0.2.1.md from quickstart.md §§2-8"
Task: "Add the demo playbook from quickstart.md §9 to the test procedure"
Task: "Populate the troubleshooting table from quickstart.md §11"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T004) — T004 in particular, so the `postgres` versus `panaderia_db` distinction is understood before any script is written
2. Complete Phase 2: Foundational (T005–T010) — **CRITICAL**, the `.gitignore` rules prevent a data leak on the first backup
3. Complete Phase 3: User Story 1 (T011–T025)
4. **STOP and VALIDATE**: run the T025 check and confirm `pg_restore -l` lists `panaderia_producto`. A backup that passes a size check but contains no bakery data is worse than no backup at all
5. Deliverable: a working hot backup

### Incremental Delivery

1. Setup + Foundational → exclusions in place, precondition gate defined
2. Add US1 → **MVP**: validated hot backups
3. Add US2 → the round trip closes; mid-demo recovery becomes possible
4. Add US4 → versioned `seed_demo.dump`; fresh-clone bootstrap works
5. Add US3 → graceful failure verified across all three scripts
6. Polish → regression guards, security sweep, test procedure

### Why the Round Trip Is the Real Gate

T023 (create the marker) → T025 (validate the artifact) → T038 (restore and confirm the marker returns) is one continuous test spanning US1 and US2. Neither story is genuinely done until T038 passes, because a backup nobody has restored is an untested backup — and the defence is the worst possible place to discover that.

---

## Notes

- `[P]` tasks touch different files with no dependency on incomplete work
- `[Story]` labels map tasks to the BDD Acceptance Scenarios in `spec.md` §5, except US4 which is derived from §2.1/§3
- **Three tasks correct defects that would make this feature non-functional**: T015 (target `$ODOO_DB_NAME`, not `postgres`), T029 (stop `web` rather than only terminating sessions), and T032 (`dropdb`+`createdb` rather than `pg_restore --clean`). Rationale is in `plan.md` → Complexity Tracking #1, #2, #3
- **T056 is a permanent regression guard** against the `-d postgres` defect, which is the highest-severity issue in the Capa 0 specs because it fails silently in the direction of apparent success
- **Two tasks are additive**: T012/T019 (the filestore companion) and the whole of US4 (`db-init-seed.ps1`). Rationale in `plan.md` → Complexity Tracking #4 and #5
- Never validate an artifact by size alone; always assert `pg_restore -l` lists the bakery relations
- Commit after each logical group; never commit an operator backup
