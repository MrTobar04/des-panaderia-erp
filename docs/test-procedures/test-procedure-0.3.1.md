# Procedimiento de Prueba: SPEC-0.3.1 Ciclo de Vida y Healthcheck

**Documento ID**: `test-procedure-0.3.1.md`
**Especificación**: `specs/0-infrastructure/0.3-developer-tooling/0.3.1-container-lifecycle-automation/spec.md`
**Guía**: `quickstart.md` §§2–11
**Fecha**: 2026-09-29

---

## 1. Objetivo

Validar arranque de un comando, diagnóstico con código de salida, parada segura y logs/reinicio.

---

## 2. Prerrequisitos

- [x] Docker Desktop en ejecución
- [x] `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
- [x] Scripts en `scripts/` (start, stop, restart, logs, healthcheck, render, db-*)

---

## 3. Casos de prueba

### TP-0.3.1-01 — Un clic desde limpio (Escenario 1)

1. `Remove-Item .env, .\config\odoo.conf -ErrorAction SilentlyContinue`
2. `.\scripts\docker-start.ps1`
3. `.env` y `config/odoo.conf` creados; sin tokens `${`
4. Exit 0; URL `http://localhost:$ODOO_HTTP_PORT`
5. `Select-String State.Health.Status .\scripts\docker-start.ps1` tiene match
6. `Start-Sleep -Seconds 5` no es el mecanismo de readiness (solo pausa de cortesía ≤ 2 s)

### TP-0.3.1-02 — Diagnóstico (Escenario 2)

1. `docker compose stop db` → `healthcheck.ps1` nombra `panaderia_odoo_db` en rojo, exit 2
2. Stop db+web → resultados de **ambos**, no solo el primero
3. Start inmediato → `[INFO] iniciando`, DEGRADADO, exit 1 (no error)
4. Stack sano → exit 0, < 3 s
5. `-Quiet` emite solo el resumen

### TP-0.3.1-03 — Stop limpio (Escenario 3)

1. `.\scripts\docker-stop.ps1` sin timeout
2. `docker ps -a | Select-String panaderia` vacío
3. Volúmenes `panaderia_odoo_*_data` siguen
4. `-RemoveVolumes` + escribir `si` → cancelado, volúmenes intactos
5. `down -v` solo tras escribir `BORRAR`

### TP-0.3.1-04 — Logs y restart (`spec.md` §6)

1. `Get-Help .\scripts\docker-logs.ps1 -Parameter Follow`
2. `.\scripts\docker-logs.ps1 -Follow` (Ctrl+C)
3. `Measure-Command { .\scripts\docker-restart.ps1 }` ~5 s
4. `-Upgrade` ejecuta `odoo -u panaderia`

### TP-0.3.1-05 — Guardas

| Check | Esperado |
| :--- | :--- |
| Puerto 8069 en scripts | solo fallback `${ODOO_HTTP_PORT}` |
| `render-odoo-conf.ps1` antes de `compose up` | sí |
| Override `ODOO_HTTP_PORT=8070` | URL y probe usan 8070 |
| Ctrl+C en scripts | `Get-Location` no queda en `scripts/` |

---

## 4. Troubleshooting

| Síntoma | Causa | Fix |
| :--- | :--- | :--- |
| Scripts deshabilitados | ExecutionPolicy Restricted | Bypass de sesión |
| Bloqueo con política permisiva | Zone.Identifier (ZIP) | `Unblock-File` |
| `error during connect` | Docker Desktop apagado | iniciar motor |
| Falso fallo al arrancar | sleep fijo de 5 s | poll Health.Status |
| Healthcheck web down, browser OK | puerto hardcodeado | leer `.env` |
| Python sin efecto tras restart | falta `-Upgrade` | `-Upgrade` |

---

## 5. DoD

- [x] Scripts de ciclo de vida en `scripts/`
- [x] start/stop verificados
- [x] Healthcheck HTTP 200 / exit codes 0/1/2
- [x] `Instrucciones_Instalacion.txt` (gap §9)
- [x] Este procedimiento documentado
