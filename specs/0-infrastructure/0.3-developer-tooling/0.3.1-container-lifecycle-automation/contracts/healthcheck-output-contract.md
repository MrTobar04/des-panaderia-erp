# Contract: Healthcheck Probe Matrix, Output & Exit Semantics

**Feature**: `SPEC-0.3.1: Automatización de Ciclo de Vida de Contenedores y Healthcheck`
**Artifact under contract**: `scripts/healthcheck.ps1`
**Date**: 2026-09-29
**Consumed By**: `scripts/docker-start.ps1`, the local verification pipeline (`spec.md` §6), and the operator directly

---

## 1. Purpose

`healthcheck.ps1` is the diagnostic primitive of Capa 0. It answers one question — *is the ERP stack
serving, and if not, which component is at fault* — in under three seconds, with output an evaluator
can read at a glance and an exit code a pipeline can gate on.

---

## 2. Probe Matrix

Probes run in order. Each is independent: a failure records a result and continues, so the operator
sees the **complete** picture rather than only the first problem.

| # | Probe | Mechanism | Pass Condition |
| :--- | :--- | :--- | :--- |
| 1 | Docker daemon | `docker info` | Exit `0` |
| 2 | `db` container exists | `docker inspect panaderia_odoo_db` | Exit `0` |
| 3 | `db` running | `docker inspect --format='{{.State.Running}}'` | `true` |
| 4 | `db` healthy | `docker inspect --format='{{.State.Health.Status}}'` | `healthy` |
| 5 | `db` accepting queries | `docker exec panaderia_odoo_db pg_isready -U $POSTGRES_USER` | Exit `0` |
| 6 | `web` container exists | `docker inspect panaderia_odoo_web` | Exit `0` |
| 7 | `web` running | `docker inspect --format='{{.State.Running}}'` | `true` |
| 8 | `web` healthy | `docker inspect --format='{{.State.Health.Status}}'` | `healthy` |
| 9 | HTTP responding | `Invoke-WebRequest "http://localhost:$ODOO_HTTP_PORT/web/login" -UseBasicParsing -TimeoutSec 5` | `StatusCode` `200` |
| 10 | Business database present | `docker exec panaderia_odoo_db psql -U $POSTGRES_USER -lqt` | `$ODOO_DB_NAME` listed |

### Probe Implementation Notes

- **Probe existence before status.** When a container does not exist, `docker inspect` fails and the
  variable is `$null`. The `spec.md` §4 sketch prints `Base de datos PostgreSQL: ` with an empty status,
  which tells the operator nothing. Probes 2 and 6 exist so the message can be
  `no existe (¿ejecutaste docker-start.ps1?)` instead.
- **`starting` is a third state.** `.State.Health.Status` returns `starting`, `healthy`, or `unhealthy`.
  Report `starting` as a **yellow warning**, never a red error — it means the stack is still booting.
- **Never hardcode the port.** Probe 9 must read `ODOO_HTTP_PORT` from `.env`. Hardcoding `8069` breaks
  the port-collision escape hatch of `SPEC-0.1.1` §8 and produces a false failure precisely when the
  operator has worked around a real conflict.
- **`-UseBasicParsing` is mandatory** on Windows PowerShell 5.1; without it the cmdlet throws on
  Internet Explorer first-launch configuration. `Invoke-WebRequest` also **throws** on 4xx/5xx rather
  than returning a status, so probe 9 must sit inside `try`/`catch`.
- **Only `200` needs checking.** The cmdlet follows redirects by default, so the `303` branch in
  `spec.md` §4 is unreachable dead code. `/web/login` answers `200` directly.
- **Probe 10 is informational.** A missing business database is a *warning*, not an error: the stack is
  correctly provisioned and the operator simply has not created or seeded the database yet. The right
  response is guidance toward `db-init-seed.ps1`, not a red failure.

---

## 3. Output Format

```text
--- Verificación de Estado de Panadería ERP ---

[OK]    Docker: demonio activo
[OK]    Contenedor panaderia_odoo_db: en ejecución
[OK]    Base de datos PostgreSQL: Saludable
[OK]    PostgreSQL acepta conexiones (pg_isready)
[OK]    Contenedor panaderia_odoo_web: en ejecución
[OK]    Servidor Odoo Web: Saludable
[OK]    Interfaz Web lista en http://localhost:8069
[OK]    Base de datos de negocio 'panaderia_db' presente

--- Resultado: SALUDABLE (8/8 verificaciones) ---
```

### Degraded example

```text
--- Verificación de Estado de Panadería ERP ---

[OK]    Docker: demonio activo
[OK]    Contenedor panaderia_odoo_db: en ejecución
[OK]    Base de datos PostgreSQL: Saludable
[OK]    PostgreSQL acepta conexiones (pg_isready)
[OK]    Contenedor panaderia_odoo_web: en ejecución
[INFO]  Servidor Odoo Web: iniciando servicios HTTP...
[WARN]  Interfaz Web aún no responde en http://localhost:8069
[WARN]  Base de datos de negocio 'panaderia_db' no encontrada
        Sugerencia: ejecuta .\scripts\db-init-seed.ps1

--- Resultado: DEGRADADO (6/8 verificaciones) ---
```

### Down example

```text
--- Verificación de Estado de Panadería ERP ---

[OK]    Docker: demonio activo
[ERROR] Contenedor panaderia_odoo_db: no existe
[ERROR] Contenedor panaderia_odoo_web: no existe
        Sugerencia: ejecuta .\scripts\docker-start.ps1

--- Resultado: CAÍDO (1/8 verificaciones) ---
```

---

## 4. Color Convention (`spec.md` §4)

| Tag | Color | Meaning |
| :--- | :--- | :--- |
| `[OK]` | Green | Probe passed |
| `[INFO]` | Yellow | Transient — `starting`, still booting |
| `[WARN]` | Yellow | Non-blocking — the stack runs but something is incomplete |
| `[ERROR]` | Red | Blocking — a required component is down |
| Header / progress | Cyan | Section headers and progress |

All operator-facing text is in Spanish, per Constitution Principle V. **No message may echo
`POSTGRES_PASSWORD` or `ODOO_ADMIN_PASSWD`.**

---

## 5. Exit Code Semantics

> The `spec.md` §4 sketch always exits `0`. That makes it unusable as the pipeline gate §6 requires,
> and it prevents `docker-start.ps1` from branching on the result. See `research.md` Decision 2.

| Exit | Label | Condition | Operator Action |
| :--- | :--- | :--- | :--- |
| `0` | `SALUDABLE` | Every probe passed | None — the system is ready |
| `1` | `DEGRADADO` | Both containers running, but at least one probe failed or is `starting` | Wait, then re-run; or follow the printed suggestion |
| `2` | `CAÍDO` | Docker unreachable, or a required container missing or stopped | `./scripts/docker-start.ps1` |

### Parameters

| Parameter | Type | Default | Purpose |
| :--- | :--- | :--- | :--- |
| `-Quiet` | `switch` | `$false` | Suppress per-probe output; emit only the summary line and the exit code |
| `-TimeoutSec` | `int` | `5` | HTTP probe timeout |

`-Quiet` exists for the pipeline use in `spec.md` §6, where only the exit code matters.

---

## 6. Consumption by `docker-start.ps1`

```powershell
& "$PSScriptRoot/healthcheck.ps1"
switch ($LASTEXITCODE) {
    0 { Write-Host "[OK] ERP listo en http://localhost:$odooPort" -ForegroundColor Green }
    1 { Write-Host "[WARN] Pila degradada. Revisa el diagnóstico anterior." -ForegroundColor Yellow }
    2 { Write-Host "[ERROR] La pila no está en ejecución." -ForegroundColor Red }
}
exit $LASTEXITCODE
```

Branching on `$LASTEXITCODE` rather than on console text is what makes the two scripts composable:
rewording or translating a message can never change the control flow.

---

## 7. Verification Contract

| Assertion | Setup | Expected |
| :--- | :--- | :--- |
| Healthy stack | `./scripts/docker-start.ps1` then `./scripts/healthcheck.ps1` | All `[OK]`, `SALUDABLE`, exit `0` |
| Database down (Acceptance Scenario 2) | `docker compose stop db` then healthcheck | Red `[ERROR]` naming `panaderia_odoo_db`, exit `2` |
| Web down | `docker compose stop web` then healthcheck | Red `[ERROR]` naming `panaderia_odoo_web`, exit `2` |
| Whole stack down | `docker compose down` then healthcheck | Both containers `no existe`, exit `2` |
| Still booting | Run immediately after `up -d` | `[INFO] ... iniciando`, `DEGRADADO`, exit `1` — **not** an error |
| No business database | Fresh volumes, no Odoo database created | `[WARN]` with the `db-init-seed.ps1` suggestion, exit `1` |
| Port override honored | Set `ODOO_HTTP_PORT=8070`, recreate, healthcheck | Probe 9 targets `8070` and passes |
| Docker stopped | Quit Docker Desktop, then healthcheck | `[ERROR] Docker no responde`, exit `2`, no unhandled exception |
| Pipeline-usable | `./scripts/healthcheck.ps1 -Quiet; $LASTEXITCODE` | Summary line only, correct code |
| No secret leaked | Inspect all output | No `POSTGRES_PASSWORD` or `ODOO_ADMIN_PASSWD` value printed |
| Completes fast | `Measure-Command { ./scripts/healthcheck.ps1 }` | Under 3 seconds on a healthy stack |
| All probes attempted | `docker compose stop db web`, then healthcheck | Results reported for **both**, not just the first failure |
