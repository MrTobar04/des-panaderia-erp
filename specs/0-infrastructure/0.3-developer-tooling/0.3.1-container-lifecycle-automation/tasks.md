# Tasks: Automatización de Ciclo de Vida de Contenedores y Healthcheck

**Input**: Design documents from `specs/0-infrastructure/0.3-developer-tooling/0.3.1-container-lifecycle-automation/`

**Prerequisites**: [`plan.md`](./plan.md) (required), [`spec.md`](./spec.md) (required), [`research.md`](./research.md), [`contracts/`](./contracts/), [`quickstart.md`](./quickstart.md). **Blocked by `SPEC-0.1.1`** (the stack and its healthchecks) and **`SPEC-0.1.2`** (`render-odoo-conf.ps1`).

**Tests**: No automated unit-test suite applies — this feature delivers operator scripts. Verification is behavioural: each script is exercised against a **healthy**, a **degraded**, and a **fully stopped** stack, asserting both console output and exit code. Constitution Principle IV's mandatory test-procedure document is task **T068**.

**Organization**: Tasks are grouped by user story. This project's specs express requirements as BDD Acceptance Scenarios (`spec.md` §5), so each scenario maps to one story. US4 is derived from `spec.md` §2.1 and §6 rather than a scenario, since `docker-logs.ps1` and `docker-restart.ps1` are in scope and exercised by the spec's own verification plan but have no scenario of their own:

| Story | Source | Title |
| :--- | :--- | :--- |
| **US1** (P1) | `spec.md` §5 Scenario 1 | Inicio automatizado de un solo clic |
| **US2** (P2) | `spec.md` §5 Scenario 2 | Diagnóstico instantáneo de fallos |
| **US3** (P3) | `spec.md` §5 Scenario 3 | Detención limpia de servicios |
| **US4** (P3) | `spec.md` §2.1 + §6 (spec gap) | Logs formateados y reinicio con actualización |

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

PowerShell operator scripts in `scripts/`, operator documentation in `Instrucciones_Instalacion.txt` at the repository root. Paths are relative to `des-panaderia-erp/`.

> **Design note carried into every task**: readiness is determined by **polling container health**, never by a fixed `Start-Sleep`. Odoo's cold start on Windows/WSL2 routinely exceeds 60 seconds, so the `Start-Sleep -Seconds 5` in `spec.md` §4 reports a booting stack as broken — the single highest-probability false failure in the project, landing during a timed defense. See `research.md` Decision 1.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the host toolchain, the upstream features, and that scripts can actually execute on Windows

- [X] T001 Confirm Docker responds and the Compose v2 plugin is present by running `docker info` and `docker compose version`
- [X] T002 [P] Confirm the upstream artifacts exist — `docker-compose.yml`, `.env.sample`, `config/odoo.conf.template`, and `scripts/render-odoo-conf.ps1` — since `docker-start.ps1` orchestrates all four
- [X] T003 [P] Set the session execution policy with `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and confirm with `Get-ExecutionPolicy -List`, mitigating the `spec.md` §8 risk without requiring elevation
- [X] T004 [P] Clear any mark-of-the-web by running `Get-ChildItem ./scripts/*.ps1 | Unblock-File`, which is required only for a browser-downloaded ZIP — a `git clone` does not set the `Zone.Identifier` stream

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The shared precondition block every script embeds

**⚠️ CRITICAL**: Without this block each script fails with an opaque `error during connect` instead of actionable Spanish guidance, and an aborted run can leave the operator's shell stranded inside `scripts/`.

- [X] T005 Implement the shared precondition block from `contracts/lifecycle-scripts-cli-contract.md` §1, to be inlined at the top of all five scripts: verify Docker responds, verify the Compose v2 plugin, resolve the repository root, and verify `docker-compose.yml` exists — each failure exiting `1` with its specific Spanish message
- [X] T006 Resolve the repository root in the shared block with `Split-Path -Parent $PSScriptRoot` rather than the string concatenation `"$PSScriptRoot/.."` used in `spec.md` §4, avoiding mixed path separators in error messages
- [X] T007 Wrap `Push-Location $repoRoot` / `Pop-Location` in a `try`/`finally` in the shared block so an aborted or Ctrl+C-interrupted run never leaves the operator's shell inside `scripts/`
- [X] T008 Implement `.env` loading in the shared block, splitting each line on the **first** `=` only, skipping comments and blank lines, so `ODOO_HTTP_PORT` and `ODOO_DB_NAME` are available to every script
- [X] T009 Decide and document that the block is **inlined per script rather than dot-sourced** from a shared `common.ps1`, so each script stays independently runnable and a missing helper cannot break all five at once (`research.md` Decision 7)

**Checkpoint**: Precondition gate defined — script authoring can begin

---

## Phase 3: User Story 1 - Inicio automatizado de un solo clic (Priority: P1) 🎯 MVP

**Goal**: From a clean checkout with no `.env` and no rendered config, one command provisions the environment, renders the configuration, starts the stack, waits for genuine readiness, and reports the URL.

**Independent Test**: Delete `.env` and `config/odoo.conf`, run `./scripts/docker-start.ps1`, and confirm `.env` was created, `config/odoo.conf` contains no `${` token, `$LASTEXITCODE` is `0`, and `http://localhost:8069` answers.

### Implementation for User Story 1

- [X] T010 [US1] Create `scripts/docker-start.ps1` with the `-TimeoutSec` parameter defaulting to `120` and a `-SkipHealthcheck` switch, per `contracts/lifecycle-scripts-cli-contract.md` §2, and inline the shared precondition block
- [X] T011 [US1] Implement step 2 of the normative sequence in `scripts/docker-start.ps1` — when `.env` is absent, run `Copy-Item .env.sample .env` and print a yellow warning that the `_change_me` values must be replaced before delivery
- [X] T012 [US1] Implement step 3 in `scripts/docker-start.ps1` by invoking `./scripts/render-odoo-conf.ps1` and **aborting the whole start with exit `2` on a non-zero result**, since booting Odoo against a stale or absent `odoo.conf` produces a "module not found" symptom whose real cause is two steps upstream (`plan.md` → Complexity Tracking #5)
- [X] T013 [US1] Enforce the normative ordering in `scripts/docker-start.ps1` — render **after** the `.env` check and **before** `docker compose up -d` — because Compose resolves the bind-mount at container creation and Odoo reads the config once at boot
- [X] T014 [US1] Implement step 4 in `scripts/docker-start.ps1` as `docker compose up -d`, exiting `3` on failure
- [X] T015 [US1] Implement step 5 in `scripts/docker-start.ps1` as a bounded poll of `docker inspect --format='{{.State.Health.Status}}'` for both `panaderia_odoo_db` and `panaderia_odoo_web`, at a 2-second interval up to `-TimeoutSec`, printing cyan progress dots
- [X] T016 [US1] Treat a `.State.Health.Status` of `starting` as **keep waiting**, never as a failure, in `scripts/docker-start.ps1` — conflating the two reintroduces the very bug this story exists to avoid
- [X] T017 [US1] Exit `4` with a diagnostic when the poll in `scripts/docker-start.ps1` exceeds `-TimeoutSec`, so the script never hangs forever on a genuinely broken stack
- [X] T018 [US1] Remove any reliance on `Start-Sleep -Seconds 5` as the readiness mechanism in `scripts/docker-start.ps1`, retaining it at most as a brief courtesy pause before the first poll (`research.md` Decision 1)
- [X] T019 [US1] Report the final URL in `scripts/docker-start.ps1` using `ODOO_HTTP_PORT` from `.env` rather than a hardcoded `8069`, so the `SPEC-0.1.1` §8 port-collision escape hatch keeps working
- [X] T020 [US1] Make `scripts/docker-start.ps1` idempotent so that running it against an already-healthy stack is a no-op that simply re-reports the URL
- [X] T021 [US1] Verify the clean-environment path by deleting `.env` and `config/odoo.conf`, running `./scripts/docker-start.ps1`, and confirming the full expected output sequence from `quickstart.md` §3 Step 2
- [X] T022 [US1] Confirm the side effects after T021 — `.env` exists, `config/odoo.conf` exists, `Select-String '\$\{' ./config/odoo.conf` returns nothing, and `$LASTEXITCODE` is `0`
- [X] T023 [US1] Confirm readiness was polled rather than guessed by asserting `Select-String -Path ./scripts/docker-start.ps1 -Pattern "State.Health.Status"` returns at least one match
- [X] T024 [US1] Verify the `.env`-change path by editing a value and confirming that `./scripts/docker-start.ps1` (which runs `up -d`) applies it, while documenting that `docker-restart.ps1` does **not**, because Compose interpolates `.env` at container-creation time

**Checkpoint**: Acceptance Scenario 1 satisfied — one command takes a fresh clone to a serving ERP. This is the MVP and the Constitution's "containerized one-command launch" quality gate.

---

## Phase 4: User Story 2 - Diagnóstico instantáneo de fallos (Priority: P2)

**Goal**: A single command reports the health of every stack component in under three seconds, names the failed one in red, and returns an exit code a verification pipeline can gate on.

**Independent Test**: Run `docker compose stop db`, then `./scripts/healthcheck.ps1`, and confirm a red `[ERROR]` line names `panaderia_odoo_db` specifically and `$LASTEXITCODE` is `2`.

### Implementation for User Story 2

- [X] T025 [US2] Create `scripts/healthcheck.ps1` with the `-Quiet` and `-TimeoutSec` parameters from `contracts/healthcheck-output-contract.md` §5, and inline the shared precondition block
- [X] T026 [US2] Implement probes 1 through 10 from `contracts/healthcheck-output-contract.md` §2 in `scripts/healthcheck.ps1`, running them **independently** so a failure records a result and continues rather than short-circuiting — the operator must see the complete picture in one pass
- [X] T027 [US2] Probe container **existence before status** in `scripts/healthcheck.ps1` (probes 2 and 6), so a missing container yields `no existe (¿ejecutaste docker-start.ps1?)` instead of the empty status the `spec.md` §4 sketch produces when `docker inspect` returns `$null`
- [X] T028 [US2] Handle all three `.State.Health.Status` values in `scripts/healthcheck.ps1`, reporting `starting` as a yellow `[INFO]` rather than a red error
- [X] T029 [US2] Implement the HTTP probe in `scripts/healthcheck.ps1` as `Invoke-WebRequest -Uri "http://localhost:$odooPort/web/login" -UseBasicParsing -TimeoutSec $TimeoutSec` inside a `try`/`catch`, since the cmdlet **throws** on 4xx/5xx rather than returning a status
- [X] T030 [US2] Include `-UseBasicParsing` on every `Invoke-WebRequest` call in `scripts/healthcheck.ps1`; without it PowerShell 5.1 uses the Internet Explorer parsing engine and throws on first-launch configuration on a clean Windows image
- [X] T031 [US2] Check only `StatusCode -eq 200` in `scripts/healthcheck.ps1` and drop the `303` branch from `spec.md` §4, which is unreachable because `Invoke-WebRequest` follows redirects by default
- [X] T032 [US2] Read the HTTP port from `ODOO_HTTP_PORT` in `scripts/healthcheck.ps1` rather than hardcoding `8069`, so the probe does not report a false failure exactly when the operator has worked around a real port conflict
- [X] T033 [US2] Implement probe 10 in `scripts/healthcheck.ps1` as an **informational warning**, not an error, when `$ODOO_DB_NAME` is absent from `psql -lqt` — the stack is correctly provisioned and the operator simply has not seeded it, so the message suggests `db-init-seed.ps1`
- [X] T034 [US2] Implement the aggregate exit semantics from `contracts/healthcheck-output-contract.md` §5 in `scripts/healthcheck.ps1` — `0` `SALUDABLE`, `1` `DEGRADADO`, `2` `CAÍDO` — replacing the always-`0` behaviour of the `spec.md` §4 sketch, which cannot gate the verification pipeline §6 requires
- [X] T035 [US2] Implement the tagged, colour-coded Spanish output format from `contracts/healthcheck-output-contract.md` §3 and §4 in `scripts/healthcheck.ps1` (`[OK]` green, `[INFO]`/`[WARN]` yellow, `[ERROR]` red, cyan header), ending with an `N/8` summary line and never echoing `POSTGRES_PASSWORD` or `ODOO_ADMIN_PASSWD`
- [X] T036 [US2] Implement `-Quiet` in `scripts/healthcheck.ps1` to suppress per-probe output and emit only the summary line, for the pipeline use in `spec.md` §6
- [X] T037 [US2] Integrate with User Story 1 by having `scripts/docker-start.ps1` invoke `./scripts/healthcheck.ps1` at step 6 and branch on `$LASTEXITCODE` per `contracts/healthcheck-output-contract.md` §6 — branching on the code, never on console text, so a reworded message can never change control flow
- [X] T038 [US2] Verify the degraded path by running `docker compose stop db` then `./scripts/healthcheck.ps1`, confirming a red `[ERROR]` names `panaderia_odoo_db` and `$LASTEXITCODE` is `2`
- [X] T039 [US2] Verify that all probes are attempted by stopping both services with `docker compose stop db web` and confirming results are reported for **both** containers, not only the first failure
- [X] T040 [US2] Verify the transient path by running `docker compose start db web` followed immediately by `./scripts/healthcheck.ps1`, confirming a yellow `[INFO] ... iniciando`, the `DEGRADADO` result, and exit `1` — **not** an error
- [X] T041 [US2] Verify the daemon-down path by quitting Docker Desktop and confirming `./scripts/healthcheck.ps1` prints `[ERROR] Docker no responde` with exit `2` and no unhandled PowerShell exception
- [X] T042 [US2] Confirm the speed target by running `Measure-Command { ./scripts/healthcheck.ps1 }` against a healthy stack and asserting under 3 seconds

**Checkpoint**: Acceptance Scenario 2 satisfied — faults are named immediately in red and the exit code is usable as an automated gate

---

## Phase 5: User Story 3 - Detención limpia de servicios (Priority: P3)

**Goal**: One command stops the stack in an orderly way with no timeout errors, leaves no orphan containers, and cannot destroy a data volume without a typed confirmation.

**Independent Test**: Run `./scripts/docker-stop.ps1`, then confirm `docker ps -a | Select-String panaderia` returns nothing while `docker volume ls | Select-String panaderia_odoo` still lists both volumes.

### Implementation for User Story 3

- [X] T043 [US3] Create `scripts/docker-stop.ps1` with the `-RemoveVolumes` and `-KeepContainers` switches from `contracts/lifecycle-scripts-cli-contract.md` §3, and inline the shared precondition block
- [X] T044 [US3] Implement the default path in `scripts/docker-stop.ps1` as `docker compose down` **without `-v`**, which removes containers and the network while preserving named volumes — satisfying both `spec.md` §2.1 and the §6 check that no orphan container remains, which plain `stop` would fail
- [X] T045 [US3] Implement the `-RemoveVolumes` path in `scripts/docker-stop.ps1` so it prints a red warning, then requires the operator to type exactly `BORRAR`; any other input aborts with exit `0` and no action taken (`spec.md` §3)
- [X] T046 [US3] Confirm that `down -v` appears on exactly **one** code path in `scripts/docker-stop.ps1`, reachable only through the `BORRAR` prompt — a typed word rather than a `[Y/n]` prompt or a `-Force` boolean, precisely so it cannot become muscle memory (`research.md` Decision 4)
- [X] T047 [US3] Report the surviving volumes at the end of `scripts/docker-stop.ps1`, so the question "did I just lose my data?" is answered on screen
- [X] T048 [US3] Verify the clean shutdown by running `./scripts/docker-stop.ps1` and confirming no timeout errors appear — Docker's default 10-second grace period is ample for both services
- [X] T049 [US3] Confirm no orphan containers remain by asserting `docker ps -a | Select-String panaderia` returns nothing, and confirm data survived by asserting `docker volume ls | Select-String panaderia_odoo` still lists both volumes
- [X] T050 [US3] Verify the destructive guard by running `./scripts/docker-stop.ps1 -RemoveVolumes`, typing `si` instead of `BORRAR`, and confirming `Operación cancelada. No se eliminó ningún volumen.`, exit `0`, and both volumes intact

**Checkpoint**: Acceptance Scenario 3 satisfied — orderly shutdown, no orphans, data integrity preserved, destruction gated

---

## Phase 6: User Story 4 - Logs formateados y reinicio con actualización (Priority: P3)

**Goal**: The operator can tail either service's logs with a filter, and can apply a Python model change with one command.

**Independent Test**: Run `./scripts/docker-logs.ps1 -Follow` and confirm a live Odoo stream. Edit a field in a model, run `./scripts/docker-restart.ps1 -Upgrade`, and confirm the change takes effect in the UI.

> Derived from `spec.md` §2.1 (both scripts in scope) and §6 (the verification plan invokes `docker-logs.ps1 -Follow`, a parameter §4 never defines), **not** from an acceptance scenario. Recorded in `plan.md` → Known Cross-Artifact Inconsistencies #1.

### Implementation for User Story 4

- [X] T051 [US4] Create `scripts/docker-logs.ps1` with the `-Service` (`web`/`db`/`all`, default `web`), `-Follow`, `-Tail` (default `100`), and `-Filter` parameters from `contracts/lifecycle-scripts-cli-contract.md` §5, and inline the shared precondition block
- [X] T052 [US4] Default `scripts/docker-logs.ps1` to the `web` service only, so PostgreSQL chatter does not bury the Odoo traceback the operator is looking for, and exit `1` on an invalid `-Service` value
- [X] T053 [US4] Implement `-Filter` in `scripts/docker-logs.ps1` as a client-side `Select-String` that composes correctly with `-Follow`, enabling a live filtered stream such as `-Filter "odoo.addons.panaderia"`
- [X] T054 [US4] Verify `scripts/docker-logs.ps1` satisfies the `spec.md` §6 verification step by running `./scripts/docker-logs.ps1 -Follow`, confirming a live stream prefixed with the readable container names, and confirming `Get-Help ./scripts/docker-logs.ps1 -Parameter Follow` documents the parameter
- [X] T055 [US4] Create `scripts/docker-restart.ps1` with the `-Upgrade`, `-Wait`, and `-Service` parameters from `contracts/lifecycle-scripts-cli-contract.md` §4, and inline the shared precondition block
- [X] T056 [US4] Implement the default path in `scripts/docker-restart.ps1` as `docker restart panaderia_odoo_web`, satisfying the `spec.md` §6 requirement that the restart command return in under 5 seconds
- [X] T057 [US4] Implement `-Upgrade` in `scripts/docker-restart.ps1` to run `docker compose exec web odoo -u panaderia -d $ODOO_DB_NAME --stop-after-init` before restarting, because a container restart alone only re-executes existing code and does **not** apply a model change — and `dev_mode`'s `reload` flag is inert since `watchdog` is absent from `odoo:16.0` (`plan.md` → Complexity Tracking #3)
- [X] T058 [US4] Implement `-Wait` in `scripts/docker-restart.ps1` to poll until `panaderia_odoo_web` reports `healthy`, separating the command-duration reading of `spec.md` §6 from the readiness reading
- [X] T059 [US4] Implement the exit codes from `contracts/lifecycle-scripts-cli-contract.md` §4 in `scripts/docker-restart.ps1`: `0` success, `1` precondition or missing container, `2` upgrade failed, `3` `-Wait` timed out
- [X] T060 [US4] Verify the restart duration with `Measure-Command { ./scripts/docker-restart.ps1 }`, asserting roughly 5 seconds or less
- [X] T061 [US4] Verify `-Upgrade` end to end by editing a field label in a `Modulo_Odoo/models/*.py` file, running `./scripts/docker-restart.ps1 -Upgrade`, and confirming the change is visible in the Odoo UI
- [X] T062 [US4] Document the "which command for which change" matrix from `contracts/lifecycle-scripts-cli-contract.md` §4 in `Instrucciones_Instalacion.txt`, covering XML edits (no command), Python edits (`-Upgrade`), manifest edits (`-Upgrade`), template edits (re-render plus `up -d`), and `.env` edits (`docker-start.ps1`)

**Checkpoint**: The full operator surface is complete — five lifecycle scripts covering start, stop, restart, logs, and diagnosis

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Operator documentation, regression guards, and the mandatory test-procedure document

- [X] T063 Create or amend `Instrucciones_Instalacion.txt` at the repository root with the execution-policy bypass, the conditional `Unblock-File` step, and the one-command launch — a deliverable `spec.md` §9 omits despite §2.1 requiring the integration and §8 placing the mitigation there (`plan.md` → Known Cross-Artifact Inconsistencies #4)
- [X] T064 [P] Add the full operator cheat sheet from `quickstart.md` §10 to `Instrucciones_Instalacion.txt`, covering all nine Capa 0 scripts grouped by concern, with the destructive command clearly separated
- [X] T065 [P] Guard against the readiness regression by asserting that `Select-String -Path ./scripts/docker-start.ps1 -Pattern 'Start-Sleep -Seconds 5'` either matches nothing or matches only a pre-poll courtesy pause
- [X] T066 [P] Guard against the hardcoded-port regression by asserting that `Select-String -Path ./scripts/*.ps1 -Pattern '8069'` matches only as an `ODOO_HTTP_PORT` fallback default
- [X] T067 [P] Guard the orchestration order by asserting that in `scripts/docker-start.ps1` the `render-odoo-conf.ps1` invocation precedes the `docker compose up` line
- [X] T068 [P] Author `docs/test-procedures/test-procedure-0.3.1.md` from `quickstart.md` §§2–8, mapping each of the three acceptance scenarios to its numbered verification steps (Constitution Principle IV; `spec.md` §10 DoD item 4)
- [X] T069 [P] Populate the troubleshooting table in `docs/test-procedures/test-procedure-0.3.1.md` from `quickstart.md` §11, covering all ten known symptoms including the execution-policy and mark-of-the-web cases
- [X] T070 Verify the shell-location guarantee by interrupting each of the five scripts with Ctrl+C and confirming `Get-Location` is unchanged afterwards, proving the `try`/`finally` of T007 holds
- [X] T071 Verify the whole-stack-down path by running `docker compose down` then `./scripts/healthcheck.ps1`, confirming both containers report `no existe` with exit `2`
- [X] T072 Confirm the port-override path end to end by setting `ODOO_HTTP_PORT=8070` in `.env`, running `./scripts/docker-start.ps1`, and confirming both the reported URL and the healthcheck probe target `8070`
- [X] T073 Update the `SPEC-0.3.1` row in `specs/spec-plan.md`, confirm the four `spec.md` §10 DoD checkboxes are satisfied, and record the five spec gaps for `/speckit-analyze` from `plan.md` → Known Cross-Artifact Inconsistencies

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Depends on `SPEC-0.1.1` and `SPEC-0.1.2` being complete
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories**
- **User Story 1 (Phase 3)**: Depends on Foundational. Self-contained: T015's inline health poll means it does **not** require `healthcheck.ps1`
- **User Story 2 (Phase 4)**: Depends on Foundational. T037 integrates back into US1's `docker-start.ps1`, following the template's "integrate with User Story 1 components" pattern
- **User Story 3 (Phase 5)**: Depends on Foundational only. Fully independent of US1, US2, and US4
- **User Story 4 (Phase 6)**: Depends on Foundational only. Fully independent of the other stories
- **Polish (Phase 7)**: Depends on all four stories

### Cross-Feature Dependencies

| This Feature Needs | From | Why |
| :--- | :--- | :--- |
| `docker-compose.yml` | `SPEC-0.1.1` | Every script wraps `docker compose` |
| Healthchecks on both services | `SPEC-0.1.1` T014, T019 | T015's poll reads `.State.Health.Status`; without them the poll has no signal |
| `.env.sample` + `.env` | `SPEC-0.1.1` T004, T008 | T011 bootstraps `.env`; T019/T032 read `ODOO_HTTP_PORT` |
| `scripts/render-odoo-conf.ps1` | `SPEC-0.1.2` T006 | T012 invokes it as step 3 of the start sequence |
| Module technical name `panaderia` | `SPEC-0.1.2` T012 | T057 runs `odoo -u panaderia` |
| `scripts/db-init-seed.ps1` | `SPEC-0.2.1` T046 | T033's warning suggests it when the business database is absent |

### User Story Dependencies

Unlike the chained stories of `SPEC-0.2.1`, three of these four are genuinely independent:

- **US1 (P1)**: Independent. Delivers the headline one-command launch on its own
- **US2 (P2)**: Independent in implementation; T037 then enriches US1 rather than blocking it
- **US3 (P3)**: Fully independent — a different script, a different concern
- **US4 (P3)**: Fully independent — two more scripts, no shared state

This means that after Foundational completes, four developers could work all four stories concurrently.

### Within Each User Story

Each script is a single file, so its authoring tasks are sequential. The behavioural verification tasks that follow a completed script are independent and parallelizable.

### Parallel Opportunities

- **Phase 1**: T002, T003, T004 in parallel
- **Phase 2**: None — sequential build of one shared block
- **Phases 3–6**: Script authoring sequential within a story, but **all four stories can run in parallel** once Foundational is done
- **Phase 7**: T064, T065, T066, T067, T068, T069 in parallel (different files)

---

## Parallel Example: All Four Stories After Foundational

```powershell
# Four independent scripts, four developers, no shared files:
Task: "US1 - Create scripts/docker-start.ps1 with .env bootstrap, render call, and health polling"
Task: "US2 - Create scripts/healthcheck.ps1 with the 10-probe matrix and aggregate exit codes"
Task: "US3 - Create scripts/docker-stop.ps1 with the BORRAR-gated -RemoveVolumes switch"
Task: "US4 - Create scripts/docker-logs.ps1 and scripts/docker-restart.ps1"
```

```powershell
# Phase 7 regression guards, all independent:
Task: "Assert docker-start.ps1 does not rely on Start-Sleep -Seconds 5 for readiness"
Task: "Assert no script hardcodes port 8069 outside an ODOO_HTTP_PORT fallback"
Task: "Assert render-odoo-conf.ps1 is invoked before docker compose up in docker-start.ps1"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T004) — T003 in particular, or no script can run at all on Windows
2. Complete Phase 2: Foundational (T005–T009)
3. Complete Phase 3: User Story 1 (T010–T024)
4. **STOP and VALIDATE**: delete `.env`, run `./scripts/docker-start.ps1`, and confirm a fresh clone reaches a serving ERP
5. This single story satisfies the Constitution's "containerized one-command launch" quality gate and Principle V's turnkey installation requirement

### Incremental Delivery

1. Foundational → precondition gate defined
2. Add US1 → **MVP**: one-command launch with real readiness polling
3. Add US2 → diagnosis with a gate-able exit code, wired back into US1 via T037
4. Add US3 → safe shutdown with the destruction guard
5. Add US4 → logs and module-upgrade restart
6. Polish → operator documentation, regression guards, test procedure

### Why T015 and T034 Matter Most

Two tasks carry disproportionate weight for the defense:

- **T015/T016/T018** replace fixed-delay readiness with health polling. Without them `docker-start.ps1` reports a booting stack as broken — the highest-probability false failure in the project, and it would happen in front of the evaluator
- **T034** gives `healthcheck.ps1` a real exit code. Without it the script `spec.md` §6 requires as a verification gate cannot gate anything, and T037's integration is impossible

---

## Notes

- `[P]` tasks touch different files with no dependency on incomplete work
- `[Story]` labels map tasks to the BDD Acceptance Scenarios in `spec.md` §5, except US4 which is derived from §2.1/§6
- **Two tasks correct defects**: T018 (health polling instead of `Start-Sleep`) and T034 (meaningful exit codes). Rationale in `plan.md` → Complexity Tracking #1 and #2
- **Four task groups are additive but required by the spec's own text**: T057 (`-Upgrade`, because §2.1 claims the script applies Python changes), T045 (`-RemoveVolumes` gated by `BORRAR`, because §3 requires confirmation for destructive commands), T012 (the render call, without which a fresh clone starts misconfigured), and T051–T053 (`-Service`/`-Follow`/`-Tail`, because §6 invokes `-Follow`). Rationale in `plan.md` → Complexity Tracking #3–#6
- **T031 removes dead code**: the `303` branch in the `spec.md` §4 sketch is unreachable because `Invoke-WebRequest` follows redirects by default
- The `--format='{{...}}'` quoting used throughout `spec.md` §4 was **verified to work** — PowerShell strips the embedded quotes and Docker accepts the resulting `--format={{...}}` form. New code may use the explicit two-token form for readability, but the spec's form is not a bug
- Commit after each logical group
