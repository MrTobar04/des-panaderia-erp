# Tasks: Aprovisionamiento de Entorno Local en Docker

**Input**: Design documents from `specs/0-infrastructure/0.1-docker-provisioning/0.1.1-local-docker-environment/`

**Prerequisites**: [`plan.md`](./plan.md) (required), [`spec.md`](./spec.md) (required), [`research.md`](./research.md), [`contracts/`](./contracts/), [`quickstart.md`](./quickstart.md)

**Tests**: No automated unit-test suite applies — this feature delivers infrastructure-as-code with no application logic. Verification is declarative (`docker compose config`), runtime (container healthchecks), and procedural (`spec.md` §6 Verification Plan, executed via `quickstart.md`). Constitution Principle IV's mandatory test-procedure document is task **T034**.

**Organization**: Tasks are grouped by user story. This project's specs express requirements as BDD Acceptance Scenarios (`spec.md` §5) rather than numbered user stories, so each scenario maps to one story:

| Story | Source | Title |
| :--- | :--- | :--- |
| **US1** (P1) | `spec.md` §5 Scenario 1 | Inicio exitoso de la pila de servicios |
| **US2** (P2) | `spec.md` §5 Scenario 2 | Reanudación tras detención forzada |
| **US3** (P3) | `spec.md` §5 Scenario 3 | Aislamiento seguro de PostgreSQL |

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Infrastructure-as-code at the repository root — there is no `src/` or `tests/` tree. Paths are relative to `des-panaderia-erp/`, per `plan.md` → *Structure Decision*.

> **Single-file constraint**: `docker-compose.yml` is one artifact that satisfies all three scenarios. Tasks that edit it are therefore **sequential and never marked [P]**, and US2/US3 consist predominantly of verification and hardening rather than new authoring. This is stated plainly rather than split artificially — see `plan.md` → *Structure Decision*.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the host toolchain and create the mount points the stack depends on

- [X] T001 Verify Docker Engine 24+ and the Compose v2 plugin by running `docker version` and `docker compose version`; abort the feature if Compose reports below v2.20
- [X] T002 [P] Create the `config/` directory at the repository root as the bind-mount target for `/etc/odoo` (contents are authored by `SPEC-0.1.2`)
- [X] T003 [P] Confirm the addon mount source exists by checking that `Modulo_Odoo/__manifest__.py` is present, mitigating the `SPEC-0.1.2` §8 risk of an unmounted module

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The environment variable surface and secret exclusions that every Compose interpolation depends on

**⚠️ CRITICAL**: `docker-compose.yml` uses `${VAR:-default}` interpolation throughout. No user story can be verified until `.env.sample` and `.env` exist and `.gitignore` is confirmed.

- [X] T004 Create `.env.sample` at the repository root with all 8 variables exactly as specified in `contracts/environment-variables-contract.md` §3, including the two additive variables `ODOO_ADMIN_PASSWD` and `ODOO_DB_NAME`
- [X] T005 Verify that both secret-valued entries in `.env.sample` carry the literal `_change_me` suffix (`POSTGRES_PASSWORD=odoo_dev_password_change_me`, `ODOO_ADMIN_PASSWD=bakery_master_key_change_me`) so an unmodified file is self-evident
- [X] T006 Confirm `.gitignore` excludes `.env` by running `git check-ignore -v .env` and asserting it prints the matching rule; abort if it prints nothing
- [X] T007 Add the `config/odoo.conf` exclusion and the `!config/odoo.conf.template` negation to `.gitignore`, per `SPEC-0.1.2` `contracts/config-rendering-contract.md` §6 (the file is shared across Capa 0 features, so the rule is added once, here)
- [X] T008 Create the local `.env` by running `Copy-Item .env.sample .env` and replace both `_change_me` values with strong secrets
- [X] T009 Verify no secret is tracked by confirming `git ls-files --error-unmatch .env` exits non-zero and `git log --all --oneline -- .env` returns no commits

**Checkpoint**: Environment surface ready — Compose interpolation will now resolve and no credential can reach Git

---

## Phase 3: User Story 1 - Inicio exitoso de la pila de servicios (Priority: P1) 🎯 MVP

**Goal**: `docker compose up -d` brings up a private-network PostgreSQL + Odoo stack in which `db` reaches `healthy`, `web` starts with no connection errors, and `http://localhost:8069` answers HTTP 200.

**Independent Test**: From a clean checkout with `.env` present, run `docker compose up -d`, then confirm `docker inspect --format='{{.State.Health.Status}}' panaderia_odoo_db` prints `healthy` and `(Invoke-WebRequest http://localhost:8069/web/login -UseBasicParsing).StatusCode` returns `200`.

### Implementation for User Story 1

- [X] T010 [US1] Create `docker-compose.yml` at the repository root with only the top-level `networks:` and `volumes:` blocks — `panaderia-net` (driver `bridge`, explicit `name: panaderia-net`), `odoo-db-data` (`name: panaderia_odoo_db_data`), `odoo-web-data` (`name: panaderia_odoo_web_data`) — and **omit the `version:` key entirely** per `research.md` Decision 1, since Compose v2 reports it obsolete on every invocation
- [X] T011 [US1] Add the `db` service to `docker-compose.yml` with `image: postgres:15-alpine`, `container_name: panaderia_odoo_db`, `restart: unless-stopped`, `networks: [panaderia-net]`, and **no `ports:` key at all** (the isolation invariant verified in US3)
- [X] T012 [US1] Add the `db` service environment block to `docker-compose.yml` with `POSTGRES_DB: ${POSTGRES_DB:-postgres}`, `POSTGRES_USER: ${POSTGRES_USER:-odoo}`, `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-odoo_dev_password}`, and `PGDATA: /var/lib/postgresql/data/pgdata` — the nested path required by `research.md` Decision 3 so `initdb` never receives a non-empty directory
- [X] T013 [US1] Add the `db` volume mount `odoo-db-data:/var/lib/postgresql/data/pgdata` to `docker-compose.yml`, mounted at the nested `PGDATA` path, not at `/var/lib/postgresql/data`
- [X] T014 [US1] Add the `db` healthcheck to `docker-compose.yml` as `test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-odoo} -d ${POSTGRES_DB:-postgres}"]` with `interval: 5s`, `timeout: 5s`, `retries: 5`, per `contracts/compose-topology-contract.md` §2
- [X] T015 [US1] Add the `web` service to `docker-compose.yml` with `image: odoo:16.0`, `container_name: panaderia_odoo_web`, `restart: unless-stopped`, `networks: [panaderia-net]`, and `depends_on: db: { condition: service_healthy }` so Odoo never starts against an uninitialized cluster
- [X] T016 [US1] Add the `web` port mappings to `docker-compose.yml` as `"${ODOO_HTTP_PORT:-8069}:8069"` and `"${ODOO_CHAT_PORT:-8072}:8072"`, using variable indirection so the `spec.md` §8 collision mitigation needs no tracked-file edit
- [X] T017 [US1] Add the `web` environment block to `docker-compose.yml` with `HOST: db`, `PORT: 5432`, `USER: ${POSTGRES_USER:-odoo}`, `PASSWORD: ${POSTGRES_PASSWORD:-odoo_dev_password}`, keeping credential symmetry with the `db` service per `contracts/environment-variables-contract.md` §2 rule 4
- [X] T018 [US1] Add the three `web` volume entries to `docker-compose.yml` — `odoo-web-data:/var/lib/odoo`, `./config:/etc/odoo`, and `./Modulo_Odoo:/mnt/extra-addons/panaderia` — all read-write, with POSIX-style relative sources for Windows/Linux parity per `research.md` Decision 6
- [X] T019 [US1] Add the `web` healthcheck to `docker-compose.yml` using the image's bundled `python3` (`python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8069/web/login', timeout=5)"`) with `interval: 10s`, `timeout: 10s`, `retries: 6`, `start_period: 60s` — **never `curl` or `wget`, which are absent from `odoo:16.0`** per `research.md` Decision 5
- [X] T020 [US1] Validate `docker-compose.yml` by running `docker compose config` and asserting exit code `0` with **zero `WARN` lines**, in particular no `the attribute 'version' is obsolete` warning
- [X] T021 [US1] Inspect the `docker compose config` output to confirm the four critical rendered values: `web` publishes `8069`, `db` publishes **no ports**, the addon mount target is `/mnt/extra-addons/panaderia`, and `PGDATA` is `/var/lib/postgresql/data/pgdata`
- [X] T022 [US1] Start the stack with `docker compose up -d`, then confirm `docker compose ps` shows `db` as `Up (healthy)` and `web` as `Up`
- [X] T023 [US1] Confirm the database health gate by running `docker inspect --format='{{.State.Health.Status}}' panaderia_odoo_db` and asserting it prints `healthy` within 25 seconds
- [X] T024 [US1] Poll `docker inspect --format='{{.State.Health.Status}}' panaderia_odoo_web` until it prints `healthy` (allow up to 90 seconds on a cold start), then confirm `(Invoke-WebRequest http://localhost:8069/web/login -UseBasicParsing).StatusCode` returns `200`
- [X] T025 [US1] Confirm the addon root is visible to Odoo by running `docker compose logs web | Select-String "addons_path"` and asserting the path list contains `/mnt/extra-addons` — the **parent** of the mount target, never `/mnt/extra-addons/panaderia` (`research.md` Decision 2)
- [X] T026 [US1] Confirm `web` can reach `db` by service DNS on `panaderia-net` with `docker compose exec web python3 -c "import socket; socket.create_connection(('db', 5432), 3)"` and asserting exit code `0`

**Checkpoint**: Acceptance Scenario 1 satisfied — the stack starts with one command and serves HTTP 200. This is the MVP and the blocking prerequisite for every Capa 1–5 feature.

---

## Phase 4: User Story 2 - Reanudación tras detención forzada (Priority: P2)

**Goal**: All business data, configuration, and installed modules survive a full `docker compose down` followed by `docker compose up -d`, with zero loss.

**Independent Test**: Insert a marker row, run `docker compose down`, confirm both named volumes still exist, run `docker compose up -d`, and confirm the marker row is still readable.

> The volume declarations themselves were authored in US1 (T010, T013, T018) because they live in the same single artifact. This story's work is proving durability and documenting the one command that can destroy it.

### Implementation for User Story 2

- [X] T027 [P] [US2] Confirm both named volumes exist with the contracted Docker names by running `docker volume ls | Select-String "panaderia_odoo"` and asserting `panaderia_odoo_db_data` and `panaderia_odoo_web_data` are both listed
- [X] T028 [P] [US2] Confirm PostgreSQL is using the nested datadir by running `docker exec panaderia_odoo_db psql -U odoo -c "SHOW data_directory;"` and asserting it returns `/var/lib/postgresql/data/pgdata`
- [X] T029 [US2] Insert a persistence marker by running `docker exec -t panaderia_odoo_db psql -U odoo -d postgres -c "CREATE TABLE IF NOT EXISTS marcador_persistencia (nota text); INSERT INTO marcador_persistencia VALUES ('Tarta de Manzana Especial');"`
- [X] T030 [US2] Tear down containers only with `docker compose down` (never `-v`), then confirm both `panaderia_odoo_*_data` volumes survived via `docker volume ls`
- [X] T031 [US2] Restart with `docker compose up -d` and confirm the marker survived by running `docker exec -t panaderia_odoo_db psql -U odoo -d postgres -c "SELECT nota FROM marcador_persistencia;"` and asserting it returns `Tarta de Manzana Especial`
- [X] T032 [US2] Remove the test artifact with `docker exec -t panaderia_odoo_db psql -U odoo -d postgres -c "DROP TABLE marcador_persistencia;"`
- [X] T033 [US2] Document the `docker compose down -v` data-loss hazard in `quickstart.md` §5 and in `Instrucciones_Instalacion.txt`, stating that `-v` appears in no Capa 0 script and that recovery requires `SPEC-0.2.1`'s `seed_demo.dump`

**Checkpoint**: Acceptance Scenario 2 satisfied — data survives a full container lifecycle, and the single destructive command is documented

---

## Phase 5: User Story 3 - Aislamiento seguro de PostgreSQL (Priority: P3)

**Goal**: PostgreSQL port `5432` is unreachable from the host while remaining reachable from `web` over the private `panaderia-net` network.

**Independent Test**: `Test-NetConnection -ComputerName localhost -Port 5432 -InformationLevel Quiet` returns `False` **and** the in-network socket probe from `web` to `db:5432` succeeds. Both halves are required — a refused host connection alone could equally mean the database is simply down.

### Implementation for User Story 3

- [X] T034 [P] [US3] Confirm the `db` service declares no published ports by running `docker compose config` and asserting the `db` block contains no `ports:` key
- [X] T035 [P] [US3] Confirm host-side isolation by running `Test-NetConnection -ComputerName localhost -Port 5432 -InformationLevel Quiet` and asserting `False`
- [X] T036 [US3] Confirm in-network reachability by running `docker compose exec web python3 -c "import socket; socket.create_connection(('db', 5432), 3); print('OK')"`, which together with T035 proves the port is *isolated* rather than the database being down (`research.md` Decision 4)
- [X] T037 [US3] Add a commented-out, opt-in debug port mapping (`# - "127.0.0.1:5432:5432"`) to the `db` service in `docker-compose.yml`, documenting in `quickstart.md` §6 that it is loopback-bound and for pgAdmin/DBeaver debugging only

**Checkpoint**: Acceptance Scenario 3 satisfied — external connections refused, internal connections succeed on `panaderia-net`

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Risk drills, the mandatory test-procedure document, and the security sweep

- [X] T038 Run the port-collision risk drill from `quickstart.md` §7 — set `ODOO_HTTP_PORT=8070` in `.env`, run `docker compose up -d`, confirm HTTP 200 on the new port, and verify `git status` shows **no tracked file modified**, proving the `spec.md` §8 mitigation works through `.env` alone
- [X] T039 [P] Execute the full ISO-27001 security verification table from `quickstart.md` §8, confirming `.env` ignored and untracked, `.env.sample` tracked, both `_change_me` placeholders present, no non-interpolated password in `docker-compose.yml`, and no historical `.env` commit
- [X] T040 [P] Author `docs/test-procedures/test-procedure-0.1.1.md` from `quickstart.md` §§3–8, mapping each of the three acceptance scenarios to its numbered verification steps (Constitution Principle IV; `spec.md` §10 DoD item 4)
- [X] T041 [P] Record measured cold-start and warm-start durations in `docs/test-procedures/test-procedure-0.1.1.md` against the `plan.md` targets (cold under 90 s, warm under 20 s, `db` healthy within 25 s)
- [X] T042 Verify Linux parity by confirming both bind-mount sources in `docker-compose.yml` are POSIX-style relative paths (`./Modulo_Odoo`, `./config`) with no absolute or `${PWD}` form, per Constitution Principle VI
- [X] T043 Update the `SPEC-0.1.1` row in `specs/spec-plan.md` to reflect implementation status and confirm all four `spec.md` §10 DoD checkboxes are satisfied

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories**, because every Compose interpolation resolves against `.env`
- **User Story 1 (Phase 3)**: Depends on Foundational. Authors the single `docker-compose.yml` artifact
- **User Story 2 (Phase 4)**: Depends on US1 — verifies durability of the volumes US1 declared
- **User Story 3 (Phase 5)**: Depends on US1 — verifies the isolation invariant US1 established by omitting `ports:`
- **Polish (Phase 6)**: Depends on US1; T038–T039 also benefit from US2/US3 being complete

### User Story Dependencies

Unusually for a spec-kit feature, the three stories are **not** independent in their implementation, because all three scenarios are satisfied by one file:

- **US1 (P1)**: Authors `docker-compose.yml` in full. Independently testable and independently valuable
- **US2 (P2)**: Depends on US1. Its tasks are verification plus documentation — no new artifact
- **US3 (P3)**: Depends on US1. Its tasks are verification plus one commented opt-in block

This is inherent to infrastructure-as-code and is documented rather than worked around. See `plan.md` → *Structure Decision*.

### Within User Story 1

`docker-compose.yml` is a single file, so **T010 → T026 are strictly sequential** and none carries `[P]`. Order matters: the top-level `networks:`/`volumes:` blocks (T010) must exist before any service references them, and `db` (T011–T014) must be complete before `web`'s `depends_on: service_healthy` (T015) is meaningful.

### Parallel Opportunities

- **Phase 1**: T002 and T003 in parallel
- **Phase 3**: None — single-file constraint
- **Phase 4**: T027 and T028 in parallel (independent read-only probes)
- **Phase 5**: T034 and T035 in parallel (independent read-only probes)
- **Phase 6**: T039, T040, T041 in parallel (different files)

---

## Parallel Example: Phase 6 Polish

```powershell
# Three independent deliverables, different files:
Task: "Execute the ISO-27001 security verification table from quickstart.md §8"
Task: "Author docs/test-procedures/test-procedure-0.1.1.md from quickstart.md §§3-8"
Task: "Record cold/warm start durations in docs/test-procedures/test-procedure-0.1.1.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T009) — **CRITICAL**, blocks everything
3. Complete Phase 3: User Story 1 (T010–T026)
4. **STOP and VALIDATE**: `docker compose up -d` yields a serving ERP at `http://localhost:8069`
5. At this point every Capa 1–5 feature is unblocked, which is the whole purpose of Capa 0

### Incremental Delivery

1. Setup + Foundational → environment surface ready, secrets excluded
2. Add US1 → **MVP**: one-command stack, HTTP 200
3. Add US2 → durability proven, destructive command documented
4. Add US3 → isolation proven in both directions
5. Polish → risk drills, test procedure, DoD closure

### Suggested Parallel Team Split

Phases 1–3 are essentially one person's work because of the single-file constraint. After US1 is green, work fans out cleanly:

- Developer A: US2 (persistence verification) + T041
- Developer B: US3 (isolation verification) + T038
- Developer C: T039 (security sweep) + T040 (test procedure)

---

## Notes

- `[P]` tasks touch different files with no dependency on incomplete work
- `[Story]` labels map tasks to the BDD Acceptance Scenarios in `spec.md` §5
- **Two tasks correct defects in the literal `spec.md` §4 configuration**: T010 omits the obsolete `version:` key, and T025 asserts `addons_path` names `/mnt/extra-addons` rather than the module directory. Rationale is in `plan.md` → Complexity Tracking #1 and #2
- **Two tasks are additive beyond `spec.md` §4**: T019 (the `web` healthcheck) and T004's two extra variables. Rationale in `plan.md` → Complexity Tracking #3 and #4
- T007 edits `.gitignore` on behalf of `SPEC-0.1.2` because the file is shared across Capa 0; doing it once here avoids a merge conflict between the two features
- Commit after each logical group, and never run `docker compose down -v` during any task
