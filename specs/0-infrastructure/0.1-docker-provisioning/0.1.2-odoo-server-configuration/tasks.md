# Tasks: Configuración del Servidor Odoo y Modos de Desarrollo

**Input**: Design documents from `specs/0-infrastructure/0.1-docker-provisioning/0.1.2-odoo-server-configuration/`

**Prerequisites**: [`plan.md`](./plan.md) (required), [`spec.md`](./spec.md) (required), [`research.md`](./research.md), [`contracts/`](./contracts/), [`quickstart.md`](./quickstart.md). **Blocked by `SPEC-0.1.1`** — the `./config` → `/etc/odoo` bind-mount and `.env` must exist first.

**Tests**: No automated unit-test suite applies — this feature delivers a configuration artifact and a renderer. Verification is textual (rendered key assertions), runtime (startup log grep, module discovery, database-manager behavior), and procedural (`spec.md` §6). Constitution Principle IV's mandatory test-procedure document is task **T035**.

**Organization**: Tasks are grouped by user story. This project's specs express requirements as BDD Acceptance Scenarios (`spec.md` §5), so each scenario maps to one story:

| Story | Source | Title |
| :--- | :--- | :--- |
| **US1** (P1) | `spec.md` §5 Scenario 1 | Detección automática del módulo de panadería |
| **US2** (P2) | `spec.md` §5 Scenario 2 | Protección del Gestor de Base de Datos |
| **US3** (P3) | `spec.md` §5 Scenario 3 | Depuración, logs personalizados y recarga en caliente |

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Infrastructure configuration-as-code at the repository root. The tracked artifact is `config/odoo.conf.template`; `config/odoo.conf` is generated output and is `.gitignore`d. Paths are relative to `des-panaderia-erp/`.

> **Single-file constraint**: `config/odoo.conf.template` is one INI artifact whose `[options]` keys serve all three scenarios. Tasks that edit it are **sequential and never marked [P]**. Each story owns a distinct key group, so the split is real rather than artificial: US1 owns `addons_path`/`data_dir`, US2 owns `admin_passwd`, US3 owns `dev_mode`/`log_*`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the upstream mount and environment surface delivered by `SPEC-0.1.1`

- [X] T001 Confirm the `./config` → `/etc/odoo` bind-mount is declared in `docker-compose.yml` and that the `config/` directory exists at the repository root
- [X] T002 [P] Confirm `.env` exists and defines a non-empty `ODOO_ADMIN_PASSWD` by running `Select-String "^ODOO_ADMIN_PASSWD=" ./.env`
- [X] T003 [P] Confirm the core addons path is correct for this image by running `docker compose exec web ls /usr/lib/python3/dist-packages/odoo/addons/base/__manifest__.py`, verifying the Debian-packaged layout assumed by `research.md` Decision 1

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The template skeleton, the secret-injection renderer, and the Git exclusion — all three stories write keys into the template the renderer consumes

**⚠️ CRITICAL**: No story can be verified until the template exists, the renderer produces `config/odoo.conf`, and the rendered file is excluded from Git. Odoo's INI parser performs **no** environment-variable interpolation, so substitution must happen on the host before the container reads the file.

- [X] T004 Create `config/odoo.conf.template` with the `[options]` section header and the Spanish header comment block from `contracts/odoo-conf-contract.md` §5, explaining that the file is a tracked template containing no secrets
- [X] T005 Verify that `.gitignore` excludes `config/odoo.conf` and retains `!config/odoo.conf.template` (the rule is added by `SPEC-0.1.1` task T007 since `.gitignore` is shared); confirm with `git check-ignore -v config/odoo.conf`
- [X] T006 Create `scripts/render-odoo-conf.ps1` that reads `.env`, substitutes `${ODOO_ADMIN_PASSWD}` in `config/odoo.conf.template`, and writes `config/odoo.conf`, splitting each `.env` line on the **first** `=` only so a password containing `=` is handled correctly
- [X] T007 Implement the failure matrix from `contracts/config-rendering-contract.md` §4 in `scripts/render-odoo-conf.ps1`: exit `1` with a Spanish diagnostic for a missing template, a missing `.env`, a blank `ODOO_ADMIN_PASSWD`, or a missing `Modulo_Odoo/__manifest__.py`; exit `0` with a yellow warning when the value is still the `bakery_master_key_change_me` placeholder
- [X] T008 Guarantee that `scripts/render-odoo-conf.ps1` never leaves a partial render — on any failure the pre-existing `config/odoo.conf` must be left untouched rather than replaced
- [X] T009 Write the output in `scripts/render-odoo-conf.ps1` as **UTF-8 without BOM and with LF line endings** using `[System.IO.File]::WriteAllText($path, $content, (New-Object System.Text.UTF8Encoding($false)))` after normalizing CRLF to LF — a BOM breaks `configparser`'s parse of the `[options]` header, and CRLF leaves a trailing `\r` in every path value inside the Linux container
- [X] T010 Verify `scripts/render-odoo-conf.ps1` is idempotent by running it twice and confirming both outputs have an identical `SHA256` hash
- [X] T011 Confirm `scripts/render-odoo-conf.ps1` never echoes the secret value to the console, printing only `[OK] config/odoo.conf generado (clave maestra inyectada desde .env)`

**Checkpoint**: Template, renderer, and Git exclusion ready — stories can now add their key groups

---

## Phase 3: User Story 1 - Detección automática del módulo de panadería (Priority: P1) 🎯 MVP

**Goal**: Odoo discovers `Modulo_Odoo` as the module `panaderia` from `/mnt/extra-addons/panaderia`, so it appears in **Aplicaciones** and is installable.

**Independent Test**: Render the config, start the stack, refresh the apps list in the UI, and confirm **Panadería Delicias Dulces - Gestión ERP** is listed and installable. Then confirm `docker compose exec web odoo -d panaderia_db -i panaderia --stop-after-init` completes with no traceback.

> This is the MVP and the highest-risk story in Capa 0: the literal `addons_path` in `spec.md` §4 makes the module permanently undiscoverable, which would fail this scenario 100% of the time and block every Capa 1–5 feature.

### Implementation for User Story 1

- [X] T012 [US1] Add `addons_path = /mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons` to `config/odoo.conf.template` — the **parent** of the bind-mount target, never `/mnt/extra-addons/panaderia`, because Odoo enumerates the *children* of each path entry looking for `__manifest__.py` (`research.md` Decision 1)
- [X] T013 [US1] Add the inline Spanish comment above `addons_path` in `config/odoo.conf.template` warning that pointing this key at the module directory makes the addon undiscoverable, so the single most defect-prone setting carries its own rationale
- [X] T014 [US1] Confirm the core addons path `/usr/lib/python3/dist-packages/odoo/addons` is present in the `addons_path` value in `config/odoo.conf.template`; omitting it prevents the `base` module from loading and the server aborts at startup
- [X] T015 [US1] Add `data_dir = /var/lib/odoo` to `config/odoo.conf.template`, matching the `panaderia_odoo_web_data` named-volume mount point declared in `SPEC-0.1.1`
- [X] T016 [US1] Render and verify the critical values by running `./scripts/render-odoo-conf.ps1` then `Select-String -Path ./config/odoo.conf -Pattern "^addons_path|^data_dir"`, asserting `addons_path` reads `/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons` exactly
- [X] T017 [US1] Confirm no unsubstituted token remains by running `Select-String '\$\{' ./config/odoo.conf` and asserting no output, and confirm LF endings with `(Get-Content ./config/odoo.conf -Raw) -match "\r"` returning `False`
- [X] T018 [US1] Recreate the container with `docker compose up -d`, then confirm Odoo is reading this file by running `docker compose exec web printenv ODOO_RC` (expect `/etc/odoo/odoo.conf`) and `docker compose exec web cat /etc/odoo/odoo.conf | Select-String "^addons_path"`
- [X] T019 [US1] Confirm the mount resolves to a real module by running `docker compose exec web ls /mnt/extra-addons/` (expect a `panaderia` directory) and `docker compose exec web cat /mnt/extra-addons/panaderia/__manifest__.py | Select-String "'name'"`
- [X] T020 [US1] Confirm Odoo agrees by running `docker compose logs web | Select-String "addons paths|addons_path"` and asserting the startup banner lists `/mnt/extra-addons`
- [X] T021 [US1] Verify UI discovery by opening `http://localhost:8069`, going to **Aplicaciones**, clearing the default **Aplicaciones** filter, clicking **Actualizar lista de aplicaciones**, and confirming **Panadería Delicias Dulces - Gestión ERP** appears
- [X] T022 [US1] Install the module with `docker compose exec web odoo -d panaderia_db -i panaderia --stop-after-init`, then `docker compose restart web`, and confirm the log shows `module panaderia: loading` with no traceback — establishing `panaderia` as the repository-wide technical name

**Checkpoint**: Acceptance Scenario 1 satisfied — the module is discovered and installable, unblocking all Capa 1–5 features

---

## Phase 4: User Story 2 - Protección del Gestor de Base de Datos (Priority: P2)

**Goal**: Destructive database-manager operations (backup, duplicate, drop) require the master password configured from `.env`, and that password never reaches Git.

**Independent Test**: Attempt a backup at `/web/database/manager` with an empty and then a wrong master password and confirm both are cleanly rejected — **not** an HTTP 500. Then confirm the correct value from `.env` succeeds.

### Implementation for User Story 2

- [X] T023 [US2] Add `admin_passwd = ${ODOO_ADMIN_PASSWD}` to `config/odoo.conf.template` as the single secret token, written in **plaintext form** — not as a hash — because Odoo accepts plaintext and self-upgrades it to `pbkdf2_sha512` on first successful verification (`research.md` Decision 3)
- [X] T024 [US2] Add `list_db = True` to `config/odoo.conf.template`, declared explicitly rather than relying on the parser default, since this scenario depends on the database manager being reachable
- [X] T025 [US2] Add `db_maxconn = 32` to `config/odoo.conf.template`, sitting under PostgreSQL's default `max_connections = 100` to leave headroom for the `psql` and `pg_dump` sessions `SPEC-0.2.1` opens
- [X] T026 [US2] Add the "deliberately absent keys" comment block to `config/odoo.conf.template` documenting that `db_host`, `db_port`, `db_user`, and `db_password` are **omitted on purpose**, because the image entrypoint gives the config file priority over the `HOST`/`USER`/`PASSWORD` environment variables, and omitting them keeps `.env` the single source of truth (`research.md` Decision 2)
- [X] T027 [US2] Verify no database credential leaked into the template by running `git grep -nE "db_host|db_user|db_password" -- config/odoo.conf.template` and asserting matches appear only inside the explanatory comment
- [X] T028 [US2] Render and confirm exactly one non-empty master password line with `Select-String '^admin_passwd\s*=\s*\S+' ./config/odoo.conf`, and confirm it is not the forbidden weak default by asserting `Select-String "^admin_passwd\s*=\s*admin$" ./config/odoo.conf` returns nothing (`spec.md` §3)
- [X] T029 [US2] Confirm the database manager loads at `http://localhost:8069/web/database/manager` and lists the existing databases
- [X] T030 [US2] Attempt a backup of `panaderia_db` with an **empty** master password and confirm a clean access-denied message — an HTTP `500` here means `admin_passwd` holds a malformed pseudo-hash and passlib raised while parsing it (`research.md` Decision 3)
- [X] T031 [US2] Repeat the backup attempt with a **wrong** master password (`clave_incorrecta`) and confirm the same clean rejection, then repeat with the correct `.env` value and confirm the `.zip` downloads
- [X] T032 [US2] Observe the automatic hash upgrade by running `docker compose exec web cat /etc/odoo/odoo.conf | Select-String "^admin_passwd"` and confirming the value now begins with `$pbkdf2-sha512$` — which is why the `./config` mount is deliberately read-write
- [X] T033 [US2] Confirm the secret never reaches Git by verifying `git ls-files --error-unmatch config/odoo.conf` exits non-zero, `git ls-files --error-unmatch config/odoo.conf.template` exits `0`, and `git log --all --oneline -- config/odoo.conf` returns no commits

**Checkpoint**: Acceptance Scenario 2 satisfied — the master key is enforced and lives only in untracked files

---

## Phase 5: User Story 3 - Depuración, logs personalizados y recarga en caliente (Priority: P3)

**Goal**: Bakery module operations emit DEBUG lines under the `odoo.addons.panaderia` namespace while other subsystems stay at INFO, and XML view edits become visible on a browser reload without restarting the container.

**Independent Test**: Edit a label in `Modulo_Odoo/views/producto_views.xml`, press F5, and confirm the change appears with no restart. Then create a product and confirm `docker compose logs web | Select-String "odoo.addons.panaderia"` shows DEBUG output.

### Implementation for User Story 3

- [X] T034 [US3] Add `dev_mode = reload,qweb,xml` to `config/odoo.conf.template`, resolving this spec's internal disagreement (§2.1 says `reload,qweb,werkzeug`; §4 says `reload,qweb`) by including `xml` — the flag that actually delivers the §4 XML hot-reload promise — and **excluding `werkzeug`**, which renders full Python tracebacks into HTTP responses (`research.md` Decision 5)
- [X] T035 [US3] Add the inline Spanish comment above `dev_mode` in `config/odoo.conf.template` recording that `reload` is inert because `watchdog` is absent from the official `odoo:16.0` image, and that Python changes require `-u panaderia` instead
- [X] T036 [US3] Add `log_level = info` and `log_handler = :INFO,odoo.addons.panaderia:DEBUG` to `config/odoo.conf.template`, keeping the global floor at INFO so the boot log stays readable during the defense while raising only the bakery module to DEBUG — the namespace follows from the technical name established in US1
- [X] T037 [US3] Add `limit_memory_soft = 2147483648`, `limit_memory_hard = 2684354560`, `limit_time_cpu = 120`, and `limit_time_real = 240` to `config/odoo.conf.template`, with a comment recording that Odoo enforces these in **prefork mode only** and they are therefore inert under this stack's threaded `workers = 0` (`research.md` Decision 6)
- [X] T038 [US3] Render and confirm `dev_mode` excludes `werkzeug` by running `Select-String "^dev_mode" ./config/odoo.conf` and asserting the value is exactly `reload,qweb,xml`
- [X] T039 [US3] Recreate the container, then verify XML hot reload by editing a field label in `Modulo_Odoo/views/producto_views.xml`, pressing F5 in the browser, and confirming the change appears with **no** container restart and **no** module upgrade
- [X] T040 [US3] Generate bakery module activity by creating or editing a product under **Panadería → Inventario → Productos**, then confirm `docker compose logs --tail 80 web | Select-String "odoo.addons.panaderia"` shows DEBUG lines while unrelated subsystems remain at INFO
- [X] T041 [US3] Document the Python-change path in `quickstart.md` §7, confirming that `docker compose exec web odoo -d panaderia_db -u panaderia --stop-after-init` followed by a restart applies a model change, since `reload` cannot

**Checkpoint**: Acceptance Scenario 3 satisfied — per-module DEBUG logging works and XML iteration needs no restart

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Renderer edge cases, the mandatory test-procedure document, and the security sweep

- [X] T042 Exercise the renderer failure matrix end to end — blank `ODOO_ADMIN_PASSWD`, missing `.env`, missing template, missing `Modulo_Odoo/__manifest__.py` — confirming each exits `1` with the correct Spanish message from `contracts/config-rendering-contract.md` §4 and leaves any existing `config/odoo.conf` unmodified
- [X] T043 [P] Confirm no BOM was written by checking that `Get-Content ./config/odoo.conf -Encoding Byte -TotalCount 3` does not return `239 187 191`
- [X] T044 [P] Execute the full security verification table from `quickstart.md` §8, including host file permissions via `Get-Acl ./config/odoo.conf` per `spec.md` §7
- [X] T045 [P] Author `docs/test-procedures/test-procedure-0.1.2.md` from `quickstart.md` §§2–8, mapping each of the three acceptance scenarios to its numbered verification steps (Constitution Principle IV; `spec.md` §10 DoD item 4)
- [X] T046 [P] Populate the troubleshooting table in `docs/test-procedures/test-procedure-0.1.2.md` from `quickstart.md` §10, covering the seven known symptoms and their causes
- [X] T047 Verify the `SPEC-0.1.2` → `SPEC-0.3.1` integration contract by confirming `scripts/docker-start.ps1` invokes `scripts/render-odoo-conf.ps1` **after** the `.env` check and **before** `docker compose up -d`, aborting on a non-zero exit (`contracts/config-rendering-contract.md` §5)
- [X] T048 Update the `SPEC-0.1.2` row in `specs/spec-plan.md` and confirm all four `spec.md` §10 DoD checkboxes are satisfied, noting that the tracked deliverable is `config/odoo.conf.template` rather than `config/odoo.conf` per `plan.md` → Complexity Tracking #2

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Depends on `SPEC-0.1.1` being complete (the `./config` mount and `.env` must exist)
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories**, because every story writes keys into the template the renderer consumes
- **User Story 1 (Phase 3)**: Depends on Foundational. Highest priority — without it no module exists to configure
- **User Story 2 (Phase 4)**: Depends on Foundational. Independent of US1 in implementation, though T029–T032 are easier to observe once a database exists
- **User Story 3 (Phase 5)**: Depends on Foundational **and US1**, because the `odoo.addons.panaderia` log namespace only exists once the module is discovered under the technical name `panaderia`
- **Polish (Phase 6)**: Depends on all three stories; T047 additionally depends on `SPEC-0.3.1`

### Cross-Feature Dependencies

| This Feature Needs | From | Why |
| :--- | :--- | :--- |
| `./config` → `/etc/odoo` mount | `SPEC-0.1.1` T018 | Configuration is injected by bind-mount only |
| `.env` with `ODOO_ADMIN_PASSWD` | `SPEC-0.1.1` T004, T008 | Runtime secret injection |
| `.gitignore` rule for `config/odoo.conf` | `SPEC-0.1.1` T007 | Shared file, edited once |
| Renderer invoked at startup | `SPEC-0.3.1` | Otherwise the operator must render manually |

### User Story Dependencies

- **US1 (P1)**: Can start right after Foundational. No dependency on other stories
- **US2 (P2)**: Can start right after Foundational, in parallel with US1 — it owns a disjoint key group (`admin_passwd`, `list_db`, `db_maxconn`)
- **US3 (P3)**: Depends on US1 for the `odoo.addons.panaderia` namespace to exist

### Within Each User Story

`config/odoo.conf.template` is a single file, so the tasks that edit it are sequential within each story. Because the three stories own **disjoint key groups**, two developers can work US1 and US2 concurrently provided they coordinate writes to the template — or, more simply, one developer writes all key groups (T012–T015, T023–T026, T034–T037) and then the verification tasks fan out in parallel.

### Parallel Opportunities

- **Phase 1**: T002 and T003 in parallel
- **Phase 2**: None — all tasks build the same two files sequentially
- **Phases 3–5**: Template edits are sequential; the verification tasks that follow each render are independent
- **Phase 6**: T043, T044, T045, T046 in parallel (different files)

---

## Parallel Example: Phase 6 Polish

```powershell
# Four independent deliverables, different files:
Task: "Confirm no BOM in config/odoo.conf via a 3-byte read"
Task: "Execute the security verification table from quickstart.md §8"
Task: "Author docs/test-procedures/test-procedure-0.1.2.md from quickstart.md §§2-8"
Task: "Populate the troubleshooting table in docs/test-procedures/test-procedure-0.1.2.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T011) — **CRITICAL**, the renderer is the secret-injection pipeline
3. Complete Phase 3: User Story 1 (T012–T022)
4. **STOP and VALIDATE**: the module appears in **Aplicaciones** and installs cleanly
5. This single story unblocks all of Capa 1–5. Nothing else in the project can be demonstrated without it

### Incremental Delivery

1. Foundational → template + renderer + Git exclusion
2. Add US1 → **MVP**: module discovered and installable
3. Add US2 → database manager protected, master key out of Git
4. Add US3 → per-module DEBUG logging and XML hot reload
5. Polish → renderer edge cases, test procedure, DoD closure

### Recommended Sequencing Note

Write all three key groups into the template in one pass (T012–T015, T023–T026, T034–T037), render once, then run the verification tasks of all three stories. This avoids three separate render-and-recreate cycles while keeping the story boundaries intact for traceability.

---

## Notes

- `[P]` tasks touch different files with no dependency on incomplete work
- `[Story]` labels map tasks to the BDD Acceptance Scenarios in `spec.md` §5
- **Four tasks correct defects in the literal `spec.md` §4 configuration**: T012 (`addons_path` names the parent), T023 (plaintext `admin_passwd` instead of the malformed pseudo-hash), T026 (database keys omitted), and T034 (`dev_mode` includes `xml`, excludes `werkzeug`). Rationale is in `plan.md` → Complexity Tracking #1, #3, #5, #4
- **The tracked deliverable is `config/odoo.conf.template`, not `config/odoo.conf`**, deviating from `spec.md` §9 because the rendered file holds the master password. The Constitution's Technical Stack §2 clause "`.env.sample` template with runtime secret injection" is the authority — see `plan.md` → Complexity Tracking #2
- T037 adds keys that are **inert** under `workers = 0`. They are declared intent, not an active memory guard, and the comment says so
- Commit after each logical group; never commit `config/odoo.conf`
