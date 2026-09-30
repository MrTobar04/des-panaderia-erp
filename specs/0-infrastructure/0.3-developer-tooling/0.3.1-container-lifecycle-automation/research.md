# Phase 0: Outline & Research — Automatización de Ciclo de Vida de Contenedores y Healthcheck

**Feature**: `SPEC-0.3.1: Automatización de Ciclo de Vida de Contenedores y Healthcheck`
**Branch / Directory**: `specs/0-infrastructure/0.3-developer-tooling/0.3.1-container-lifecycle-automation`
**Date**: 2026-09-29
**Status**: Completed

---

## 1. Executive Summary & Objective

This research validates the PowerShell automation sketched in `spec.md` §4 against the real behavior of Docker Desktop on Windows, Odoo's startup profile, and Windows PowerShell 5.1's HTTP and native-command semantics. Seven decisions were required. Two correct defects that would surface at the worst possible moment — a fixed-delay readiness check that reports failure on a stack that is still booting, and a healthcheck that always exits `0` despite being required to gate a verification pipeline.

---

## 2. Research Findings & Technical Decisions

### Decision 1: Poll container health; never sleep a fixed interval

* **Decision**: `docker-start.ps1` polls `docker inspect --format='{{.State.Health.Status}}'` for both containers in a bounded loop (2-second interval, 120-second ceiling) until each reports `healthy`. The `Start-Sleep -Seconds 5` from `spec.md` §4 is retained only as a brief courtesy pause before the first poll, never as the readiness mechanism.
* **Rationale**:
  * Odoo's first boot loads the entire base module registry. On Windows with the WSL2 backend — the project's primary platform — this routinely takes 60–90 seconds cold, and the bind-mounted addon directory adds filesystem latency on top.
  * With a 5-second sleep, the subsequent `Invoke-WebRequest` fails and the operator is told the stack is broken when it is simply still starting. This is the single highest-probability false failure in the whole project, and it lands precisely during a timed defense.
  * Polling is also *faster* in the common case: a warm start reaches `healthy` in 8–12 seconds, so the script returns sooner than a fixed 5-second sleep followed by a failed probe and a retry.
  * `SPEC-0.1.1` already defines healthchecks on both services (`pg_isready` on `db`, an HTTP probe on `web`), so the signal exists and needs no new infrastructure. The `web` probe's `start_period` absorbs cold boot without consuming the retry budget.
  * A bounded ceiling matters: an unbounded loop would hang forever on a genuinely broken stack, which is no better than a wrong answer.
* **Three-state handling**: `.State.Health.Status` returns `starting`, `healthy`, or `unhealthy`. `starting` must be treated as "keep waiting", not as a failure — conflating the two reintroduces the original bug.
* **Alternatives Considered**:
  * *Raise the sleep to 90 seconds*: Rejected — punishes every warm start with a 90-second wait and still guesses wrong when a cold start runs long.
  * *Retry the HTTP probe in a loop without consulting health status*: Rejected — it works for `web` but gives no signal for `db`, and it cannot distinguish "still booting" from "crashed and restarting".
  * *`docker compose up --wait`*: Genuinely attractive, since Compose v2 can block until healthchecks pass. Rejected as the sole mechanism because it requires a recent Compose version and, on failure, produces terse output that does not identify which component failed — which is exactly what Acceptance Scenario 2 demands. It is noted in `quickstart.md` as an equivalent manual shortcut.

### Decision 2: `healthcheck.ps1` must return a meaningful exit code

* **Decision**: Aggregate every probe result and exit `0` (all healthy), `1` (degraded — some component down or still starting), or `2` (stack down — no container running). Console output stays exactly as `spec.md` §4 describes.
* **Rationale**:
  * `spec.md` §6 requires executing the script "dentro del pipeline de verificación local". A script that always exits `0` cannot gate anything, so the requirement would be nominally met and functionally useless.
  * `docker-start.ps1` needs to branch on the result to decide between reporting success with the URL or surfacing a diagnostic, and branching on console text is brittle — it breaks the moment a message is reworded.
  * Distinguishing `1` from `2` is worth the extra code: "degraded" means investigate a specific component, while "down" means you simply have not started the stack, and those call for completely different operator actions.
  * The spec's sketch also prints an empty status when a container does not exist at all (`docker inspect` fails, the variable is `$null`, and the message renders as `Base de datos PostgreSQL: `). Probing for existence first yields an actionable message instead.
* **Alternatives Considered**:
  * *Always exit `0` and let the operator read the colors*: Rejected — unusable as an automated gate, which §6 requires.
  * *`throw` on failure*: Rejected — a PowerShell exception prints a red stack trace that buries the diagnostic the script worked to produce.

### Decision 3: `Invoke-WebRequest` semantics on Windows PowerShell 5.1

* **Decision**: Probe with `Invoke-WebRequest -Uri "http://localhost:$port/web/login" -UseBasicParsing -TimeoutSec 5` inside a `try`/`catch`, treating only `200` as success.
* **Rationale**:
  * `-UseBasicParsing` is mandatory on PowerShell 5.1. Without it the cmdlet uses the Internet Explorer parsing engine and throws `The response content cannot be parsed because the Internet Explorer engine is not available, or Internet Explorer's first-launch configuration is not complete` on a clean Windows image. `spec.md` §4 already includes the flag, which is correct.
  * `Invoke-WebRequest` **throws** on any 4xx/5xx rather than returning a status, so the `try`/`catch` in the spec's sketch is load-bearing rather than defensive.
  * The spec's `$response.StatusCode -eq 303` branch is unreachable: the cmdlet follows redirects by default (up to `-MaximumRedirection`, default 5), so a `303` is resolved before `StatusCode` is ever read. Harmless dead code. `/web/login` answers `200` directly anyway, so only `200` needs checking.
  * `/web/login` is the right endpoint because it responds before any Odoo database exists, making the probe valid on a brand-new stack. `/web` redirects into database selection and is noisier.
  * The port must come from `ODOO_HTTP_PORT` in `.env`, not be hardcoded to `8069`. Hardcoding breaks the port-collision mitigation that `SPEC-0.1.1` §8 exists to provide — the operator reassigns the port and the healthcheck then reports a false failure.
* **Alternatives Considered**:
  * *`Test-NetConnection` on the port*: Rejected — it proves the port is bound, not that Odoo is answering HTTP. Docker binds the port before Odoo finishes booting, so this reports ready far too early.
  * *`curl.exe`*: Present on modern Windows 10/11 but not guaranteed on every image; `Invoke-WebRequest` is always available.

### Decision 4: Make volume destruction unreachable by accident

* **Decision**: `docker-stop.ps1` runs `docker compose down` (no `-v`) by default. Volume destruction is available only via an explicit `-RemoveVolumes` switch that requires the operator to type the word `BORRAR` at a prompt.
* **Rationale**:
  * `spec.md` §3 requires explicit confirmation for destructive commands. Simply *omitting* the capability does not satisfy that — it pushes the operator to type `docker compose down -v` by hand, where there is no guard whatsoever. Providing the one safe path is stronger protection than providing none.
  * A typed word cannot be muscle memory. A `-Force`-style boolean or a `[Y/n]` prompt is exactly the kind of thing that gets added reflexively from shell history at 2 a.m. the night before a defense.
  * `down` rather than `stop` is the right default: it removes containers and the network while preserving named volumes, which satisfies both §2.1 ("sin borrar volúmenes de datos") and the §6 verification that `docker ps` shows no orphan containers. `stop` would leave stopped containers behind and fail that check.
  * Docker's default 10-second stop timeout is ample — PostgreSQL performs a fast shutdown and Odoo exits promptly — so no `--timeout` override is needed to satisfy Acceptance Scenario 3's "sin arrojar errores de timeout".
* **Alternatives Considered**:
  * *`docker compose stop`*: Rejected as the default — leaves orphan containers, failing the §6 check.
  * *No `-RemoveVolumes` at all*: Rejected — leaves §3's requirement unimplemented while the dangerous manual route stays unguarded.

### Decision 5: A container restart does not apply a Python model change

* **Decision**: `docker-restart.ps1` restarts `panaderia_odoo_web` by default and accepts an `-Upgrade` switch that first runs `odoo -u panaderia -d $ODOO_DB_NAME --stop-after-init`. A `-Wait` switch polls for `healthy` afterwards.
* **Rationale**:
  * `spec.md` §2.1 says the script exists "para aplicar cambios en módulos de Python", but restarting the container only re-executes the existing code. Any change to a field definition, a `_sql_constraints` entry, or a view file requires a **module upgrade** so Odoo re-reads the manifest, applies schema migrations, and reloads XML definitions into the database.
  * This matters more than it would otherwise, because the `reload` flag in `dev_mode` is inert: `watchdog` is not installed in the official `odoo:16.0` image (`SPEC-0.1.2` `research.md` Decision 5). There is no automatic mechanism at all, so the script is the only convenient path.
  * Without `-Upgrade`, the script silently fails to do what its own specification says it does — the developer edits a model, restarts, sees no change, and starts debugging correct code.
  * `-Upgrade` is opt-in rather than default because a plain restart is genuinely faster and is the right action for a stuck worker or a configuration change.
  * `-Wait` exists because the §6 verification asserts "el reinicio tome menos de 5 segundos". The `docker restart` command does return in about that time, but Odoo is not *serving* for considerably longer; the two readings need separate handling rather than a conflated one.
* **Alternatives Considered**:
  * *Always upgrade*: Rejected — turns a 5-second restart into a 30-second one for cases that do not need it.
  * *Document the manual `odoo -u` command instead*: Rejected — leaves the script's stated purpose unmet and forces a longer command during rapid iteration.

### Decision 6: Execution policy, `Unblock-File`, and native-command quoting

* **Decision**: Document `powershell -ExecutionPolicy Bypass -File .\scripts\docker-start.ps1` and the session-scoped `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in `Instrucciones_Instalacion.txt`, plus `Get-ChildItem ./scripts/*.ps1 | Unblock-File` for copies obtained as a ZIP download.
* **Rationale**:
  * Windows 10/11 defaults to `Restricted` for the `LocalMachine` scope, so an unprepared evaluator cannot run any `.ps1` file. This is the exact risk in `spec.md` §8, and its mitigation belongs in the installation instructions, which §9 forgets to list as a deliverable.
  * `-Scope Process` is the right guidance: it lasts only for the current session and needs no administrator rights, unlike a `CurrentUser` or `LocalMachine` change.
  * `Unblock-File` addresses a separate and frequently-missed failure: files extracted from a ZIP downloaded through a browser carry a `Zone.Identifier` mark-of-the-web stream. They are blocked even under a permissive execution policy, with an error that reads nothing like a policy problem. A `git clone` does not set this stream, so the step is conditional — but the evaluator may well receive a ZIP.
  * **Native-command quoting was verified rather than assumed.** In PowerShell, `--format='{{.State.Health.Status}}'` is passed to the child process as `--format={{.State.Health.Status}}` — the embedded single quotes are stripped, and Docker accepts the `=` form. The snippets in `spec.md` §4 therefore work as written. The explicit two-token form `--format "{{.State.Health.Status}}"` is preferred in new code only for readability, not because the spec's form is broken.
* **Alternatives Considered**:
  * *Ship `.cmd` wrappers that invoke PowerShell with the bypass flag*: Rejected as scope creep for a documentation problem, and it doubles the number of entry points the operator must reason about.
  * *`Set-ExecutionPolicy -Scope LocalMachine`*: Rejected — requires elevation, which `spec.md` §7 explicitly avoids, and it weakens the machine's posture well beyond this project.

### Decision 7: Script structure — inline helpers over a shared module

* **Decision**: Duplicate the short precondition block (verify Docker responds, resolve the repository root, load `.env`) inline in each script rather than dot-sourcing a shared `common.ps1`.
* **Rationale**:
  * Each script must remain independently runnable and copy-pasteable. A missing or renamed `common.ps1` would break all five simultaneously, converting a small convenience into a single point of failure for the entire operational surface.
  * The duplicated block is roughly ten lines. The coupling cost of a shared module exceeds the duplication cost at this scale.
  * `SPEC-0.2.1`'s three database scripts share the same pattern, keeping the whole `scripts/` directory internally consistent.
  * Resolve the repository root with `Split-Path -Parent $PSScriptRoot` rather than the string concatenation `"$PSScriptRoot/.."` used in `spec.md` §4. The concatenated form works, but it produces mixed path separators that are confusing in error messages and awkward to compare.
  * `Push-Location` / `Pop-Location` must be wrapped in `try`/`finally`, as the spec's `docker-start.ps1` sketch correctly does, so an aborted run never leaves the operator's shell in `scripts/`.
* **Alternatives Considered**:
  * *A `common.ps1` dot-sourced by all five*: Rejected for the single-point-of-failure reason above. Reasonable at twenty scripts; not at five.
  * *A PowerShell module with a manifest*: Rejected — installation and `$env:PSModulePath` concerns for ten lines of shared logic.

---

## 3. Technology Matrix

| Parameter | Specification |
| :--- | :--- |
| **Runtime** | Windows PowerShell 5.1+ (PowerShell 7 compatible) |
| **Orchestration** | `docker compose` v2 (plugin form) |
| **Health Source** | `docker inspect --format='{{.State.Health.Status}}'` against the healthchecks of `SPEC-0.1.1` |
| **HTTP Probe** | `Invoke-WebRequest -UseBasicParsing -TimeoutSec 5` on `/web/login` |
| **Probe Port** | `${ODOO_HTTP_PORT}` from `.env` — never hardcoded |
| **Readiness Policy** | Bounded poll: 2-second interval, 120-second ceiling, `starting` treated as "keep waiting" |
| **Target Containers** | `panaderia_odoo_web`, `panaderia_odoo_db` (per the `SPEC-0.1.1` topology contract) |
| **Module Technical Name** | `panaderia` (for `-u` in `docker-restart.ps1 -Upgrade`) |
| **Console Convention** | Cyan = progress, Green = OK, Yellow = warning, Red = error; all text in Spanish |
| **Exit Semantics** | `0` healthy, `1` degraded, `2` down |

---

## 4. Risks and Mitigations

| Risk | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| Fixed 5-second delay declares a booting stack broken | **Highest-probability false failure**, landing during the timed defense | Decision 1: bounded health polling; `starting` is not a failure |
| `healthcheck.ps1` always exits `0` | Cannot gate the local verification pipeline that §6 requires | Decision 2: aggregate exit code `0`/`1`/`2` |
| HTTP probe hardcodes port `8069` | False failure whenever the operator uses the `ODOO_HTTP_PORT` collision escape hatch | Decision 3: read the port from `.env` |
| `Invoke-WebRequest` fails on IE first-launch configuration | Healthcheck errors on a clean Windows image | `-UseBasicParsing` on every call |
| `docker compose down -v` typed from habit | **Total data loss** | Decision 4: `-RemoveVolumes` requires typing `BORRAR`; `-v` appears in no default path |
| Restart assumed to apply Python model changes | Developer debugs correct code; `reload` is inert without `watchdog` | Decision 5: `-Upgrade` switch runs `odoo -u panaderia` |
| Execution policy blocks every script | Evaluator cannot start the system at all | Decision 6: bypass documented in `Instrucciones_Instalacion.txt` |
| ZIP-downloaded scripts blocked by mark-of-the-web | Confusing error unrelated to policy | Decision 6: `Unblock-File` documented |
| Docker Desktop not started | Every script fails with an opaque `error during connect` | Shared precondition block verifies the daemon responds and says so in Spanish |
| Unbounded readiness wait | Script hangs forever on a genuinely broken stack | 120-second ceiling, then a diagnostic and a non-zero exit |
| `.env` missing on a fresh clone | Compose starts with defaults and `odoo.conf` never renders | `docker-start.ps1` copies `.env.sample` first (Acceptance Scenario 1) |
| Config rendering skipped | Odoo boots without a valid config; module appears missing | Decision from `plan.md` #5: `render-odoo-conf.ps1` is invoked and a non-zero exit aborts the start |
| Operator's shell left inside `scripts/` after an abort | Confusing relative paths in later commands | `Push-Location` / `Pop-Location` in `try`/`finally` |

---

## 5. Open Questions

None blocking. Five artifact-level gaps are recorded in `plan.md` → *Known Cross-Artifact Inconsistencies* for `/speckit-analyze`: the undefined `-Follow` parameter used by the spec's own verification plan, the ambiguous "restart under 5 seconds" wording, the unreachable `303` branch, the missing `Instrucciones_Instalacion.txt` deliverable, and the absent config-rendering step in `docker-start.ps1`.
