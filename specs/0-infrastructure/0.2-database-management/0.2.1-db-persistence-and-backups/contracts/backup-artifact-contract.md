# Contract: Backup Artifact Format, Naming & Retention

**Feature**: `SPEC-0.2.1: Persistencia, Semillas y Respaldos de Base de Datos PostgreSQL`
**Artifacts under contract**: `backups/*.dump`, `backups/*_filestore.tar`, `backups/seed_demo.dump`, `backups/.gitkeep`
**Date**: 2026-09-29

---

## 1. Dump Format

| Property | Value | Why |
| :--- | :--- | :--- |
| Format flag | `-F c` (custom) | Compressed, selectively restorable, and the only format `pg_restore` can inspect with `-l` |
| Blobs | `-b` | Explicit, though implied by custom format |
| Compression | zlib, `pg_dump` default level | Adequate; a demo database compresses to a few hundred KB |
| Extension | `.dump` | Distinguishes custom format from a plain-SQL `.sql` |
| Encoding | Inherited from the source database (UTF-8) | Odoo mandates UTF-8 |
| Ownership flags | Applied on **restore** (`--no-owner --no-privileges`), not on dump | Keeps the artifact portable across machines with different role names |
| Producing image | `postgres:15-alpine` | The dump is always produced and consumed inside the same pinned image |

> **Never** produce these artifacts with PowerShell stream redirection. `>` and `Out-File` are text
> operators that apply an encoding and translate line endings, corrupting a binary archive in a way
> that is not obvious from its size. Use `pg_dump -f` inside the container plus `docker cp`.

---

## 2. Naming Convention

| Artifact Kind | Pattern | Example |
| :--- | :--- | :--- |
| Automatic backup | `panaderia_backup_<yyyyMMdd_HHmmss>.dump` | `panaderia_backup_20260929_221500.dump` |
| Named backup | `<name>.dump` (operator-supplied) | `test_backup.dump` |
| Filestore companion | `<basename>_filestore.tar` | `panaderia_backup_20260929_221500_filestore.tar` |
| Versioned seed | `seed_demo.dump` + `seed_demo_filestore.tar` | fixed names |

The `yyyyMMdd_HHmmss` timestamp is deliberate: it sorts lexicographically into chronological order and
contains no character that is invalid in a Windows filename (unlike an ISO-8601 time with colons).

---

## 3. Artifact Pairing

A dump and its filestore companion are a **unit**. Restoring one without the other is valid but
partial:

| Restored | Result |
| :--- | :--- |
| Dump only, into an existing filestore | ✅ Works. The filestore only ever grows, so it is a superset of what the older database references. |
| Dump only, into an **empty** filestore | ⚠️ Rows load, but `ir.attachment` payloads are missing — product images and generated PDFs render broken. |
| Dump + filestore | ✅ Complete restoration of both relational and binary state. |

The empty-filestore case is exactly the fresh-clone and post-`down -v` path, which is why
`seed_demo.dump` **must** ship with `seed_demo_filestore.tar`.

---

## 4. `seed_demo.dump` — the one versioned artifact

| Requirement | Detail |
| :--- | :--- |
| **Synthetic data only** | Invented products, fictitious customers, fabricated sales. No real business or personal data — `spec.md` §7. |
| **Complete demo state** | Roughly 15 products across the four categories (Pan, Pastel, Galleta, Bebida), 8 sales orders spanning `Borrador` and `Confirmada`, matching invoices in `Pendiente` and `Pagada`, and at least one product below its minimum stock threshold so the low-stock alert of `SPEC-1.2.1` is visible. |
| **Filestore companion** | `seed_demo_filestore.tar` is mandatory, since this artifact targets the empty-filestore path. |
| **Size budget** | Under 1 MB. Adopt Git LFS if it ever exceeds a few megabytes rather than growing the repository history. |
| **Regeneration** | `./scripts/db-backup.ps1 -BackupName seed_demo.dump -IncludeFilestore` against a fully populated demo database. |
| **Purpose** | The 10-second recovery path if the live demo goes wrong mid-defense, and the one-command bootstrap for a teammate or the evaluator cloning fresh. |

### Why a dump and not just Odoo XML seed data

`Modulo_Odoo/data/*.xml` already seeds master data — categories and products — and that belongs to
Capa 1. It cannot express **transactional** state: a confirmed sale with its computed totals, the
resulting stock decrement, and the generated invoice. Only a database dump captures that, which is
what makes the end-to-end flow demonstrable from the very first minute of the defense.

---

## 5. Validation Contract

Every artifact must pass these checks before it is trusted.

| Check | Command | Expected |
| :--- | :--- | :--- |
| Non-empty | `(Get-Item ./backups/x.dump).Length` | `> 0` |
| Valid custom-format header | `docker exec panaderia_odoo_db pg_restore -l /tmp/x.dump` | A TOC listing, exit `0` |
| **Contains bakery data** | `pg_restore -l` output | Includes `panaderia_producto` and `panaderia_categoria` |
| Row-level sanity | `pg_restore -l \| Select-String "TABLE DATA"` | Multiple bakery tables listed |
| Filestore archive valid | `tar -tf ./backups/x_filestore.tar` | Lists `filestore/<dbname>/…` entries |

> The bakery-data check is not optional pedantry. `pg_dump -d postgres` — the command written in
> `spec.md` §4 — produces an archive that is non-empty and passes a header check while containing
> **no bakery tables at all**. Size and parseability are not evidence that a backup is useful; the
> presence of the actual relations is.

---

## 6. `.gitignore` Contract

```gitignore
# Respaldos de base de datos (SPEC-0.2.1)
# Contienen datos de negocio: NO se versionan.
backups/*
# Excepciones: marcador de directorio y semilla sintética de demostración.
!backups/.gitkeep
!backups/seed_demo.dump
!backups/seed_demo_filestore.tar
```

**Why `backups/*` and not `backups/`**: Git cannot re-include a file with `!` if one of its parent
directories is itself excluded. Ignoring the directory outright would make all three negations inert
and silently drop `seed_demo.dump` from the repository.

| File | Tracked? |
| :--- | :--- |
| `backups/.gitkeep` | ✅ Yes |
| `backups/seed_demo.dump` | ✅ Yes |
| `backups/seed_demo_filestore.tar` | ✅ Yes |
| `backups/panaderia_backup_*.dump` | ❌ No |
| `backups/*_filestore.tar` (other than the seed) | ❌ No |

---

## 7. Retention Guidance

No automatic rotation is implemented — `spec.md` §2.2 places continuous and automated backup
strategies out of scope. Manual guidance:

| Artifact | Keep |
| :--- | :--- |
| `seed_demo.dump` | Permanently, versioned. Regenerate when the demo script changes. |
| Pre-demo snapshot | Until the defense is over. |
| Ad-hoc test backups | Delete freely; they are untracked. |

```powershell
# Housekeeping: keep the 5 most recent automatic backups
Get-ChildItem ./backups/panaderia_backup_*.dump |
  Sort-Object LastWriteTime -Descending |
  Select-Object -Skip 5 |
  Remove-Item
```

---

## 8. Security Contract (`spec.md` §7)

| Rule | Enforcement |
| :--- | :--- |
| Backups stay local | `backups/*` ignored by Git with only synthetic exceptions |
| No real business data committed | `seed_demo.dump` contains invented records only |
| No credential inside an artifact | `pg_dump` of a single database captures no role passwords; `pg_dumpall` — which would — is explicitly rejected in `research.md` Decision 1 |
| No credential in script output | Console messages never echo `POSTGRES_PASSWORD` or `ODOO_ADMIN_PASSWD` |
| History is clean | `git log --all --oneline -- backups/` shows only `.gitkeep` and the seed artifacts |
