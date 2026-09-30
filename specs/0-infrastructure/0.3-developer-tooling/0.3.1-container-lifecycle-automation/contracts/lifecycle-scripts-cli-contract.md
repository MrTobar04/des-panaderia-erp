# Contract: Lifecycle Script CLI Surface

**Feature**: `SPEC-0.3.1: Automatización de Ciclo de Vida de Contenedores y Healthcheck`
**Artifacts under contract**: `scripts/docker-start.ps1`, `docker-stop.ps1`, `docker-restart.ps1`, `docker-logs.ps1`
**Date**: 2026-09-29
**Upstream contracts**: [`SPEC-0.1.1 compose-topology-contract.md`](../../../0.1-docker-provisioning/0.1.1-local-docker-environment/contracts/compose-topology-contract.md), [`SPEC-0.1.2 config-rendering-contract.md`](../../../0.1-docker-provisioning/0.1.2-odoo-server-configuration/contracts/config-rendering-contract.md)

---

## 1. Shared Precondition Block (all scripts)

Inlined in each script rather than dot-sourced, so every script stays independently runnable — see
`research.md` Decision 7.

| Order | Check | Failure Message (Spanish) | Exit |
| :--- | :--- | :--- | :--- |
| 1 | `docker` on `PATH` and the daemon responds (`docker info`) | `ERROR: Docker no responde. Inicia Docker Desktop y vuelve a intentarlo.` | `1` |
| 2 | Compose v2 plugin available (`docker compose version`) | `ERROR: Falta el plugin Docker Compose v2.` | `1` |
| 3 | Repository root resolved via `Split-Path -Parent $PSScriptRoot` | `ERROR: No se pudo resolver la raíz del repositorio.` | `1` |
| 4 | `docker-compose.yml` present at the root | `ERROR: No se encontró docker-compose.yml en la raíz.` | `1` |

`Push-Location $repoRoot` / `Pop-Location` must be wrapped in `try`/`finally` so an aborted run never
leaves the operator's shell inside `scripts/`.

---

## 2. `scripts/docker-start.ps1` — the one command

### Parameters

| Parameter | Type | Default | Purpose |
| :--- | :--- | :--- | :--- |
| `-TimeoutSec` | `int` | `120` | Readiness ceiling before giving up |
| `-SkipHealthcheck` | `switch` | `$false` | Return right after `up -d`, without waiting |

### Normative Sequence

```text
1. Shared precondition block (§1)
2. .env missing?  → Copy-Item .env.sample .env
                  → warn in yellow that the *_change_me values must be replaced
3. ./scripts/render-odoo-conf.ps1                  (SPEC-0.1.2)
     └─ non-zero exit → ABORT the start
4. docker compose up -d                            (SPEC-0.1.1)
5. Poll both containers' .State.Health.Status until healthy or -TimeoutSec
     ├─ 2-second interval, progress dots in cyan
     └─ `starting` means KEEP WAITING, not failure
6. ./scripts/healthcheck.ps1
7. Report http://localhost:${ODOO_HTTP_PORT} in green
```

**Ordering is normative.** Step 3 must fall between 2 and 4: rendering needs `.env` to exist, and
Compose resolves the bind-mount at container creation while Odoo reads the config once at boot.
Rendering after `up -d` would leave the running server on the previous configuration.

### Contract Guarantees

| Guarantee | Detail |
| :--- | :--- |
| **Truly one command** | A fresh clone with no `.env` and no `config/odoo.conf` reaches a serving ERP (Acceptance Scenario 1). |
| **No fixed-delay readiness** | Health polling replaces `Start-Sleep -Seconds 5`, which declares a booting stack broken. See `research.md` Decision 1. |
| **Bounded** | Never hangs. On timeout it prints a diagnostic and exits non-zero. |
| **Aborts on a bad render** | A non-zero exit from the renderer stops the start rather than booting Odoo without a config. |
| **Idempotent** | Running it on an already-healthy stack is a no-op that re-reports the URL. |
| **Honors the port override** | The reported URL and the probe both use `ODOO_HTTP_PORT` from `.env`. |

### Exit Codes

| Code | Meaning |
| :--- | :--- |
| `0` | Stack healthy and serving |
| `1` | Precondition failed (§1) |
| `2` | `render-odoo-conf.ps1` failed |
| `3` | `docker compose up -d` failed |
| `4` | Timeout — the stack did not become healthy within `-TimeoutSec` |

---

## 3. `scripts/docker-stop.ps1`

### Parameters

| Parameter | Type | Default | Purpose |
| :--- | :--- | :--- | :--- |
| `-RemoveVolumes` | `switch` | `$false` | **DESTRUCTIVE** — also delete the named volumes |
| `-KeepContainers` | `switch` | `$false` | Use `docker compose stop` instead of `down` |

### Behavior

1. Shared precondition block (§1).
2. Without `-RemoveVolumes`: `docker compose down`. Containers and the network are removed; **named volumes are preserved**.
3. With `-RemoveVolumes`: prompt, require the operator to type exactly `BORRAR`, then `docker compose down -v`. Any other input aborts with exit `0` and no action taken.
4. Report the volumes that survived, so the operator can see the data is still there.

### Why `down` and not `stop` by default

| Command | Containers | Network | Volumes | §6 check "no orphan containers" |
| :--- | :--- | :--- | :--- | :--- |
| `docker compose stop` | Kept (stopped) | Kept | Kept | ❌ Stopped containers remain |
| `docker compose down` | **Removed** | Removed | **Kept** | ✅ Passes |
| `docker compose down -v` | Removed | Removed | ❌ **DESTROYED** | Never a default path |

### Contract Guarantees

| Guarantee | Detail |
| :--- | :--- |
| **Volumes safe by construction** | `-v` appears on exactly one code path, reachable only by typing `BORRAR`. |
| **Confirmation cannot be muscle memory** | A typed word, not `[Y/n]` and not a `-Force` boolean — see `research.md` Decision 4. |
| **No timeout errors** | Docker's default 10-second stop grace period is ample for both services (Acceptance Scenario 3). |
| **Post-condition reported** | Surviving volumes are listed, so "did I just lose my data?" is answered on screen. |

### Exit Codes

| Code | Meaning |
| :--- | :--- |
| `0` | Stopped cleanly, or destructive action declined |
| `1` | Precondition failed |
| `2` | `docker compose down` reported an error |

---

## 4. `scripts/docker-restart.ps1`

### Parameters

| Parameter | Type | Default | Purpose |
| :--- | :--- | :--- | :--- |
| `-Upgrade` | `switch` | `$false` | Run `odoo -u panaderia` before restarting — **required for Python model changes** |
| `-Wait` | `switch` | `$false` | Poll until `panaderia_odoo_web` is `healthy` |
| `-Service` | `string` | `web` | `web` or `db` |

### Behavior

| Invocation | Action | Typical Duration |
| :--- | :--- | :--- |
| `./docker-restart.ps1` | `docker restart panaderia_odoo_web` | Command returns in ~5 s; Odoo serves in 15–30 s |
| `./docker-restart.ps1 -Wait` | Restart, then poll to `healthy` | 15–30 s |
| `./docker-restart.ps1 -Upgrade` | `odoo -u panaderia -d $ODOO_DB_NAME --stop-after-init`, then restart | 30–60 s |

### Why `-Upgrade` Exists

`spec.md` §2.1 says this script applies "cambios en módulos de Python". A container restart alone does
**not** do that — it only re-executes the existing code. Any change to a field definition, an
`@api.constrains`, or a view file requires a module upgrade so Odoo re-reads the manifest, applies
schema migrations, and reloads the XML definitions into the database.

This matters more than it otherwise would because the `reload` flag in `dev_mode` is **inert**:
`watchdog` is absent from the official `odoo:16.0` image (`SPEC-0.1.2` `research.md` Decision 5). There
is no automatic mechanism at all.

| Change Type | Correct Command |
| :--- | :--- |
| XML view edit | Nothing — `dev_mode=xml` reloads it on browser refresh |
| Python model field, constraint, or method | `./docker-restart.ps1 -Upgrade` |
| `__manifest__.py` edit (new data file, new dependency) | `./docker-restart.ps1 -Upgrade` |
| `config/odoo.conf.template` edit | `./scripts/render-odoo-conf.ps1` then `docker compose up -d` |
| `.env` edit | `docker compose up -d` — `restart` does **not** re-read `.env` |

### Exit Codes

| Code | Meaning |
| :--- | :--- |
| `0` | Restarted (and upgraded / healthy, if requested) |
| `1` | Precondition failed, or the container does not exist |
| `2` | Module upgrade reported an error |
| `3` | `-Wait` specified and the service did not become healthy |

---

## 5. `scripts/docker-logs.ps1`

> `-Follow` is used by `spec.md` §6 verification step 2 but never defined in §4. Defined here.

### Parameters

| Parameter | Type | Default | Purpose |
| :--- | :--- | :--- | :--- |
| `-Service` | `string` | `web` | `web`, `db`, or `all` |
| `-Follow` | `switch` | `$false` | Stream continuously (`docker compose logs -f`) |
| `-Tail` | `int` | `100` | Lines of history to show |
| `-Filter` | `string` | *(none)* | Client-side `Select-String` pattern |

### Behavior

```powershell
# Last 100 lines from Odoo
./scripts/docker-logs.ps1
# Live stream from Odoo (Ctrl+C to exit)
./scripts/docker-logs.ps1 -Follow
# PostgreSQL history
./scripts/docker-logs.ps1 -Service db -Tail 200
# Only bakery-module messages
./scripts/docker-logs.ps1 -Filter "odoo.addons.panaderia"
# Everything, both services
./scripts/docker-logs.ps1 -Service all -Follow
```

### Contract Guarantees

| Guarantee | Detail |
| :--- | :--- |
| **Targeted by default** | `web` only, so PostgreSQL chatter does not bury an Odoo traceback. |
| **`-Follow` blocks** | Documented as Ctrl+C-terminated; `-Follow` and `-Filter` together stream filtered output live. |
| **Readable** | Container names in the prefix, courtesy of the fixed `container_name` values in the `SPEC-0.1.1` topology contract. |

### Exit Codes

| Code | Meaning |
| :--- | :--- |
| `0` | Logs displayed, or the stream was interrupted by the operator |
| `1` | Precondition failed, or an invalid `-Service` value |

---

## 6. Cross-Feature Orchestration Map

```text
docker-start.ps1                         (SPEC-0.3.1)
  ├─ .env ← .env.sample                  (SPEC-0.1.1 environment contract)
  ├─ render-odoo-conf.ps1                (SPEC-0.1.2 rendering contract)
  ├─ docker compose up -d                (SPEC-0.1.1 topology contract)
  ├─ poll .State.Health.Status           (SPEC-0.1.1 healthchecks)
  └─ healthcheck.ps1                     (SPEC-0.3.1 healthcheck contract)

db-init-seed.ps1                         (SPEC-0.2.1)
  └─ db-restore.ps1                      (SPEC-0.2.1)
       ├─ docker compose stop web
       └─ docker compose start web
```

---

## 7. Execution Policy Contract (`spec.md` §8)

Documented in `Instrucciones_Instalacion.txt` — which `spec.md` §9 omits from its deliverables list and
which this plan therefore adds.

```powershell
# Option A — per-session, no elevation required (recommended)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
./scripts/docker-start.ps1

# Option B — per-invocation
powershell -ExecutionPolicy Bypass -File .\scripts\docker-start.ps1

# If the project arrived as a browser-downloaded ZIP, clear the mark-of-the-web.
# A `git clone` does NOT set this stream, so this step is conditional.
Get-ChildItem ./scripts/*.ps1 | Unblock-File
```

The `Unblock-File` step addresses a distinct failure from the execution policy: files carrying a
`Zone.Identifier` stream are blocked even under a permissive policy, with an error that reads nothing
like a policy problem.

---

## 8. Verification Contract

| Assertion | Command | Expected |
| :--- | :--- | :--- |
| One-command start from clean | `Remove-Item .env; ./scripts/docker-start.ps1` | `.env` created, config rendered, stack healthy, exit `0` |
| No fixed-delay readiness | `Select-String 'Start-Sleep -Seconds 5' ./scripts/docker-start.ps1` | Absent, or present only as a pre-poll courtesy pause |
| Health polling present | `Select-String 'State.Health.Status' ./scripts/docker-start.ps1` | At least one match |
| Renderer invoked before `up` | Line order in the script | `render-odoo-conf.ps1` precedes `compose up` |
| Port not hardcoded | `Select-String '8069' ./scripts/*.ps1` | Only as an `ODOO_HTTP_PORT` fallback default |
| `-v` reachable only via confirmation | `Select-String 'down -v' ./scripts/docker-stop.ps1` | One match, guarded by the `BORRAR` prompt |
| Volumes survive a stop | `./scripts/docker-stop.ps1; docker volume ls` | Both `panaderia_odoo_*_data` still listed |
| No orphan containers | `./scripts/docker-stop.ps1; docker ps -a \| Select-String panaderia` | No match |
| `-Follow` defined | `Get-Help ./scripts/docker-logs.ps1 -Parameter Follow` | Parameter documented |
| `-Upgrade` runs the upgrade | `Select-String '\-u panaderia' ./scripts/docker-restart.ps1` | One match |
| Shell location restored | Abort a script with Ctrl+C | `Get-Location` unchanged |
