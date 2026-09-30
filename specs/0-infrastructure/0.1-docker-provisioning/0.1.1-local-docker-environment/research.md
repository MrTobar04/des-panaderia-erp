# Phase 0: Outline & Research — Aprovisionamiento de Entorno Local en Docker

**Feature**: `SPEC-0.1.1: Aprovisionamiento de Entorno Local en Docker`
**Branch / Directory**: `specs/0-infrastructure/0.1-docker-provisioning/0.1.1-local-docker-environment`
**Date**: 2026-09-29
**Status**: Completed

---

## 1. Executive Summary & Objective

This research resolves the technical unknowns required to author the Capa 0 Docker Compose stack for the Panadería "Delicias Dulces" ERP. The stack must start with one command, isolate PostgreSQL from the host network, persist all business data across container recreation, expose the custom addon for live editing, and keep every credential out of Git. Six decisions were required; two of them correct defects in the literal configuration given in `spec.md` §4 that would have prevented the module from loading at all.

---

## 2. Research Findings & Technical Decisions

### Decision 1: Compose schema declaration — omit the top-level `version` key

* **Decision**: Author `docker-compose.yml` against the Compose Specification with **no** top-level `version` key, despite `spec.md` §4 showing `version: '3.8'`.
* **Rationale**:
  * Docker Compose v2 (the only variant invoked as `docker compose`, and the one the Constitution mandates) ignores `version` entirely and emits `WARN[0000] ... the attribute 'version' is obsolete, it will be ignored` on every single command.
  * `SPEC-0.1.1` §10 makes "validated with `docker compose config`" a Definition of Done item. A permanent warning on a DoD command is noise that conditions the operator — and the evaluator watching the demo — to disregard Compose diagnostics.
  * Removing the key changes no behavior: the Compose Specification supersedes the 2.x/3.x schema families, and every attribute used here (`healthcheck`, `depends_on.condition`, named volume `name:`) is part of it.
* **Alternatives Considered**:
  * *Keep `version: '3.8'`*: Rejected for the warning noise described above. It buys literal spec fidelity only.
  * *Pin `version: '3.9'`*: Rejected — same warning, plus it implies a schema constraint that Compose v2 does not enforce.

### Decision 2: `addons_path` semantics versus the bind-mount target — the module discovery defect

* **Decision**: Keep the bind-mount exactly as specified (`./Modulo_Odoo` → `/mnt/extra-addons/panaderia`) and set `addons_path` to the **parent** directory `/mnt/extra-addons`. The module's Odoo technical name therefore becomes `panaderia`.
* **Rationale**:
  * Odoo's module loader treats every `addons_path` entry as a *container of modules*: it enumerates the immediate child directories of each entry and accepts those holding a `__manifest__.py`.
  * `spec.md` §4 (this feature) mounts the addon at `/mnt/extra-addons/panaderia`, and `SPEC-0.1.2` §4 sets `addons_path = /mnt/extra-addons/panaderia,...`. Combined, Odoo would enumerate the children of the module itself — `models/`, `views/`, `data/`, `security/`, `tests/` — none of which carries a manifest. The addon would never appear in **Aplicaciones**, and `SPEC-0.1.2` Acceptance Scenario 1 would fail 100% of the time.
  * Pointing `addons_path` at `/mnt/extra-addons` makes `panaderia` the single discovered child. This also makes the log namespace `odoo.addons.panaderia`, which is precisely what `SPEC-0.1.2` Acceptance Scenario 3 asserts — so the fix reconciles that spec with itself (its own §4 snippet writes `odoo.addons.Modulo_Odoo`, contradicting its Scenario 3).
  * `/mnt/extra-addons` is also the conventional extra-addons root baked into the official `odoo` image, so the choice matches upstream expectations and community documentation the team may consult mid-demo.
* **Alternatives Considered**:
  * *Mount at `/mnt/extra-addons/Modulo_Odoo`*: Rejected. It works mechanically, but the technical name becomes `Modulo_Odoo`; Odoo module names are Python package identifiers by convention and are expected to be lower-case snake_case. Mixed case with a capital leading letter is fragile across `-i`/`-u` flags, the `odoo.addons.*` logger hierarchy, and `--test-tags` selectors.
  * *Leave `addons_path` pointing at the module and rename the module's internals*: Rejected as incoherent — there is no arrangement in which a module directory is simultaneously its own addons root.
  * *Copy the addon into the image with a `Dockerfile`*: Rejected. It defeats Principle VI's live-mount requirement and forces an image rebuild for every XML tweak.

### Decision 3: PostgreSQL datadir placement — `PGDATA` in a volume subdirectory

* **Decision**: Set `PGDATA=/var/lib/postgresql/data/pgdata` and mount the named volume at that exact nested path, rather than mounting at `/var/lib/postgresql/data`.
* **Rationale**:
  * `initdb` refuses to initialize a directory that is not empty. A volume (or, on Linux hosts, a bind-mount) mounted directly at `/var/lib/postgresql/data` can surface filesystem artifacts — most commonly `lost+found` — causing a first-run failure that looks like data corruption.
  * Nesting `PGDATA` one level down guarantees `initdb` receives a pristine directory it created itself, and is the pattern the upstream `postgres` image documentation recommends for exactly this reason.
  * It also keeps the door open for `SPEC-0.2.1` to place scratch files (such as a staged `.dump`) under the volume root without colliding with the datadir.
* **Alternatives Considered**:
  * *Mount at `/var/lib/postgresql/data` and omit `PGDATA`*: Rejected for the `initdb` non-empty-directory failure mode, which is intermittent and therefore worse than a deterministic one.

### Decision 4: Verifying PostgreSQL isolation without publishing `5432`

* **Decision**: Declare no `ports:` key on the `db` service. Verify Acceptance Scenario 3 from the host with `Test-NetConnection -ComputerName localhost -Port 5432`, and prove positive reachability *inside* the network with `docker compose exec web python3 -c "import socket; socket.create_connection(('db', 5432), 3)"`.
* **Rationale**:
  * A negative-only test is ambiguous: a refused connection could equally mean "correctly isolated" or "the database never started". Pairing the host-side refusal with an in-network success turns the scenario into a real isolation proof rather than a liveness accident.
  * `Test-NetConnection` is built into Windows PowerShell 5.1, so the check needs no extra tooling on the primary development platform.
  * The in-network probe uses `python3`, which is present in the Odoo image; `psql` is not installed there and `curl` is not either (see Decision 5).
* **Alternatives Considered**:
  * *Publish `5432` bound to `127.0.0.1` only*: Rejected as the default. It contradicts `spec.md` §3 and weakens the isolation claim, though it remains the documented opt-in for debugging with pgAdmin or DBeaver.
  * *`internal: true` on the network*: Rejected — it would also sever the `web` service's outbound access, which Odoo needs for the Aplicaciones list and any external asset fetch.

### Decision 5: `web` readiness probe — `python3`, not `curl` or `wget`

* **Decision**: Add a healthcheck to the `web` service implemented as
  `python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8069/web/login', timeout=5)"`,
  with `start_period` set generously to absorb Odoo cold start.
* **Rationale**:
  * The official `odoo:16.0` image is Debian-based but ships **neither `curl` nor `wget`**, so the idiomatic `CMD curl -f http://localhost:8069/...` healthcheck fails with "command not found" and reports the container permanently `unhealthy` — a misleading signal mid-demo.
  * `python3` is guaranteed present: it is the interpreter running Odoo itself. `urllib.request` is stdlib, so the probe adds no dependency.
  * `/web/login` is the cheapest endpoint that proves the HTTP worker and the routing layer are live. It answers `200` before any database is selected, so the probe works on a brand-new stack with no Odoo database yet — unlike `/web`, which redirects into database selection.
  * `start_period` matters because Odoo's first boot loads the full base registry; on Windows/WSL2 this routinely exceeds 30 seconds, and without a start period the retry budget is consumed before Odoo is ever ready.
* **Alternatives Considered**:
  * *No healthcheck on `web`, rely on `Start-Sleep -Seconds 5` in `docker-start.ps1` (as `SPEC-0.3.1` §4 sketches)*: Rejected as the sole mechanism. A fixed sleep is the single most likely cause of a false "it's broken" during a timed defense. The sleep is retained in the script only as a courtesy delay before the first poll.
  * *Install `curl` via a custom `Dockerfile`*: Rejected — an image build to obtain a healthcheck is disproportionate, and it abandons the pure-upstream-image guarantee.

### Decision 6: Bind-mount parity across Windows (WSL2) and Linux

* **Decision**: Express both bind-mount sources as POSIX-style relative paths (`./Modulo_Odoo`, `./config`) and mount the addon read-write, the configuration directory read-write.
* **Rationale**:
  * Relative sources are resolved by Compose against the project directory, so the same file works from `C:\Users\...\des-panaderia-erp` and from `/home/user/des-panaderia-erp` with no path rewriting and no `${PWD}` interpolation.
  * The addon mount must be read-write: Odoo writes `__pycache__/` next to the Python sources. A read-only mount produces a stream of cache warnings on every boot.
  * The `config` mount is left read-write deliberately. `:ro` would be marginally more secure, but it breaks Odoo's **Set Master Password** flow in the database manager, which writes back to `odoo.conf`. Since the master password is injected at render time by `SPEC-0.1.2`, `:ro` is documented as an optional hardening step rather than the default — the goal is to avoid a surprise failure path during the defense.
* **Alternatives Considered**:
  * *Absolute Windows paths (`C:\Users\...`)*: Rejected — breaks Linux parity, which Constitution Principle VI explicitly requires.
  * *Docker named volume for the addon source*: Rejected — named volumes are not host-editable, defeating live iteration.

---

## 3. Technology Matrix

| Parameter | Specification |
| :--- | :--- |
| **Orchestrator** | Docker Compose v2.20+ (`docker compose`, plugin form — not legacy `docker-compose`) |
| **Container Engine** | Docker Engine 24+ / Docker Desktop with WSL2 backend |
| **Application Image** | `odoo:16.0` (official, Debian-based, unmodified) |
| **Database Image** | `postgres:15-alpine` (official, unmodified) |
| **Network Driver** | `bridge`, user-defined network `panaderia-net` (embedded DNS enables `db` as a hostname) |
| **Persistence** | Docker named volumes `panaderia_odoo_db_data`, `panaderia_odoo_web_data` |
| **Secret Injection** | Compose `.env` interpolation with `${VAR:-default}` fallbacks |
| **Host Platforms** | Windows 10/11 + WSL2 (primary), Linux x86_64 (parity) |
| **Published Ports** | `8069` (HTTP), `8072` (longpolling/chat). `5432` deliberately unpublished. |

---

## 4. Risks and Mitigations

| Risk | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| Host port `8069` already bound (another Odoo, IIS, or a stray container) | Stack starts but is unreachable; `docker compose up` fails with a bind error | `ODOO_HTTP_PORT` indirection in `.env`; `quickstart.md` §7 documents reassigning to `8070` and re-running `up -d` |
| Module not discovered because `addons_path` points into the module | **Blocking** — `SPEC-0.1.2` Scenario 1 fails, no Capa 1–5 feature is demonstrable | Resolved by Decision 2: `addons_path = /mnt/extra-addons`, technical name `panaderia`. Asserted in `quickstart.md` §4 by grepping the startup log |
| `initdb` aborts on a non-empty datadir | First run fails in a way that mimics corruption | Resolved by Decision 3: `PGDATA` nested at `/var/lib/postgresql/data/pgdata` |
| `web` marked `unhealthy` because the healthcheck binary is missing | False failure signal during the defense | Resolved by Decision 5: probe uses the image's own `python3`, never `curl` |
| Odoo cold start exceeds the healthcheck retry budget | Container restarts in a loop, never reaching ready | Generous `start_period` on the `web` healthcheck; `db` gated separately via `depends_on: service_healthy` |
| `.env` committed by accident | **Credential leak** — direct ISO-27001 and Principle VI violation | `.env` already present in `.gitignore`; `quickstart.md` §8 verifies with `git check-ignore -v .env`; `.env.sample` placeholders carry the `_change_me` suffix so a leak is self-evident |
| `docker compose down -v` run reflexively, destroying volumes | Total loss of demo data | `-v` is never documented in any Capa 0 script; `SPEC-0.3.1` requires explicit confirmation for destructive commands; `SPEC-0.2.1` provides a versioned `seed_demo.dump` as the recovery path |
| WSL2 filesystem latency on the bind-mounted addon | Slow module upgrades, sluggish first page load | Keep the repository inside the Windows filesystem that Docker Desktop shares, or relocate to the WSL2 filesystem for a large speedup; documented as an optional performance note, not a requirement |

---

## 5. Open Questions

None blocking. Two follow-ups are queued for `/speckit-analyze` and recorded in `plan.md` → *Known Cross-Artifact Inconsistencies*: the Constitution's internal volume/network naming conflict, and the stale service name and module name in `SPEC-1.1.1`'s quickstart.
