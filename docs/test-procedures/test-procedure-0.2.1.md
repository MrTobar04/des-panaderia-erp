# Procedimiento de Prueba: SPEC-0.2.1 Persistencia, Semillas y Respaldos

**Documento ID**: `test-procedure-0.2.1.md`
**Especificación**: `specs/0-infrastructure/0.2-database-management/0.2.1-db-persistence-and-backups/spec.md`
**Guía**: `quickstart.md` §§2–11
**Fecha**: 2026-09-29

---

## 1. Objetivo

Validar respaldos en caliente de `panaderia_db` (nunca `postgres`), restauración con parada de `web`, y fallo guiado si el contenedor está apagado.

---

## 2. Prerrequisitos

- [x] Pila en ejecución (`panaderia_odoo_db` Running)
- [x] Base de negocio `panaderia_db` con módulo `panaderia` instalado
- [x] `backups/.gitkeep` tracked; `backups/*` ignorado salvo semilla

---

## 3. Casos de prueba

### TP-0.2.1-01 — Backup bajo demanda (Escenario 1)

1. Crear producto UI: `Tarta de Manzana Especial` (Pastel, 4.50 / 12.00)
2. `.\scripts\db-backup.ps1 -BackupName test_backup.dump`
3. Archivo `backups/test_backup.dump` > 0 bytes (típicamente 300–800 KB)
4. `db` sigue Running y HTTP 200 (hot backup)
5. `pg_restore -l` lista `panaderia_producto` y `panaderia_categoria`

**Anti-patrón**: dump de `postgres` es pequeño y parseable pero **sin** tablas `panaderia_*`.

### TP-0.2.1-02 — Restore íntegro (Escenario 2)

1. Borrar/archivar el producto en la UI
2. `.\scripts\db-restore.ps1 -BackupFile .\backups\test_backup.dump` (o `-Force`)
3. Observar: valida → stop web → dropdb/createdb → restore → start web
4. El producto reaparece con costos y margen
5. `docker compose logs --tail 50 web` sin ERROR/Traceback de integridad
6. Restaurar de nuevo el mismo dump → estado idéntico (idempotente)

### TP-0.2.1-03 — Contenedor apagado (Escenario 3)

1. `docker compose stop db`
2. `db-backup.ps1`, `db-restore.ps1`, `db-init-seed.ps1` → exit 1, mensaje rojo, sin artefacto parcial
3. `docker compose start db`

### TP-0.2.1-04 — Semilla / playbook de demo

**Antes de la defensa**

```powershell
.\scripts\docker-start.ps1
.\scripts\db-backup.ps1 -BackupName seed_demo.dump -IncludeFilestore
```

**Si la demo se rompe**

```powershell
.\scripts\db-restore.ps1 -BackupFile .\backups\seed_demo.dump -Force
```

**Clon fresco**

```powershell
Copy-Item .env.sample .env
.\scripts\docker-start.ps1
.\scripts\db-init-seed.ps1
```

Tras `down -v` + seed: las imágenes de producto deben renderizar (filestore companion).

### TP-0.2.1-05 — Guardas de regresión

| Check | Esperado |
| :--- | :--- |
| `-d postgres` en `db-*.ps1` | solo `dropdb`/`createdb`/`psql` admin, nunca `pg_dump`/`pg_restore` de datos |
| `>` / `Out-File` en `pg_dump` | ausente |
| `git check-ignore backups/test_backup.dump` | ignorado |
| `seed_demo.dump` tracked | sí |

---

## 4. Troubleshooting

| Síntoma | Causa | Fix |
| :--- | :--- | :--- |
| Dump de pocos KB | se volcó `postgres` | `$ODOO_DB_NAME` |
| `database is being accessed` | no se detuvo `web` | `compose stop web` |
| UI muestra datos viejos | registry en memoria | restart `web` |
| `did not find magic string` | redirección PowerShell | `docker cp` |
| DB no existe en restore | `--clean` en clon fresco | dropdb+createdb |
| Imágenes rotas | filestore vacío | `-IncludeFilestore` |

---

## 5. DoD

- [x] `db-backup.ps1` genera volcados validados
- [x] `db-restore.ps1` recupera estado
- [x] Volumen `odoo-db-data` verificado
- [x] `db-init-seed.ps1` entregado (gap §9/§10)
- [x] Este procedimiento + playbook documentados
