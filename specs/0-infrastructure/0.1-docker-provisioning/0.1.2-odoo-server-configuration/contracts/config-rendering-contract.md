# Contract: Configuration Rendering Pipeline

**Feature**: `SPEC-0.1.2: Configuración del Servidor Odoo y Modos de Desarrollo`
**Artifact under contract**: `scripts/render-odoo-conf.ps1`
**Date**: 2026-09-29
**Invoked By**: `SPEC-0.3.1` `scripts/docker-start.ps1`, before `docker compose up -d`
**Authority**: Constitution v1.1.0, Technical Stack §2 — *"Centralized `config/odoo.conf` file and `.env.sample` template with **runtime secret injection**"*

---

## 1. Why a Renderer Exists

Odoo's INI parser performs **no** environment-variable interpolation. A line reading
`admin_passwd = ${ODOO_ADMIN_PASSWD}` is consumed as that literal 22-character string, so the master
password would be the text `${ODOO_ADMIN_PASSWD}` — technically functional, entirely accidental, and
identical on every checkout.

Substitution must therefore happen on the host, before the container reads the file. That yields a
three-artifact pipeline in which the only file containing a secret is untracked:

| Artifact | Tracked? | Contains a secret? |
| :--- | :--- | :--- |
| `config/odoo.conf.template` | ✅ Yes | ❌ No — carries the `${ODOO_ADMIN_PASSWD}` token |
| `.env` | ❌ No | ✅ Yes — the authoritative source |
| `config/odoo.conf` | ❌ No | ✅ Yes — generated output |

---

## 2. Token Surface

| Token | Source | Required | Failure Mode If Missing |
| :--- | :--- | :--- | :--- |
| `${ODOO_ADMIN_PASSWD}` | `.env` | **Yes** | Renderer exits non-zero with a Spanish diagnostic. It must **never** emit an empty `admin_passwd`, which would silently disable the database manager and make Acceptance Scenario 2 fail for the wrong reason. |

No other token is defined. The renderer is deliberately a single-purpose substitution and not a
general templating engine: every other configuration value is a non-secret that belongs in Git.

---

## 3. Behavioral Contract

| Property | Requirement |
| :--- | :--- |
| **Idempotent** | Running it N times with the same `.env` produces byte-identical output. Safe to call unconditionally on every start; no staleness heuristics. |
| **Always re-renders** | It never skips based on file timestamps. An `.env` edit must take effect on the next start without the operator remembering to delete anything. |
| **Fails loudly** | A missing template, a missing `.env`, or an unset/blank `ODOO_ADMIN_PASSWD` is a non-zero exit with a Spanish message. Never a partial or blank render. |
| **Leaves no residue** | On failure, any pre-existing `config/odoo.conf` is left untouched rather than replaced with a broken one. |
| **Never logs the secret** | Console output confirms *that* the password was injected, never its value. |
| **Encoding** | UTF-8 without BOM. A BOM on the first line breaks `configparser`'s parse of the `[options]` header. |
| **Line endings** | LF. The file is read inside a Linux container; CRLF leaves a trailing `\r` in every value, so `addons_path` would resolve to a nonexistent path ending in a carriage return. |
| **Verifies the addon mount** | Asserts `./Modulo_Odoo/__manifest__.py` exists before rendering, mitigating the `spec.md` §8 risk that the module directory is absent. |

> The **encoding and line-ending requirements are not cosmetic.** Both are silent, high-cost failure
> modes on a Windows host: PowerShell's `Out-File` and `>` default to UTF-16LE or add a BOM depending
> on version, and CRLF endings produce `addons_path` values that Odoo reports as "no such directory"
> with no hint as to why. Write the file with
> `[System.IO.File]::WriteAllText($path, $content, (New-Object System.Text.UTF8Encoding($false)))`
> after normalizing `"`r`n"` to `"`n"`.

---

## 4. Failure Matrix

| Condition | Exit Code | Operator Message (Spanish) |
| :--- | :--- | :--- |
| `config/odoo.conf.template` missing | `1` | `ERROR: No se encontró la plantilla config/odoo.conf.template` |
| `.env` missing | `1` | `ERROR: No existe .env. Ejecuta: Copy-Item .env.sample .env` |
| `ODOO_ADMIN_PASSWD` unset or blank | `1` | `ERROR: ODOO_ADMIN_PASSWD no está definida en .env` |
| `ODOO_ADMIN_PASSWD` still the placeholder `bakery_master_key_change_me` | `0` + warning | `ADVERTENCIA: ODOO_ADMIN_PASSWD conserva el valor de ejemplo. Cámbialo antes de la entrega.` |
| `./Modulo_Odoo/__manifest__.py` missing | `1` | `ERROR: No se encontró Modulo_Odoo/__manifest__.py. El módulo no se montará.` |
| Success | `0` | `[OK] config/odoo.conf generado (clave maestra inyectada desde .env)` |

The placeholder case is a **warning, not an error**: a fresh clone must still start with one command,
but the operator needs a visible reminder that the shipped credential is a sample value.

---

## 5. Integration Contract with `SPEC-0.3.1`

```text
scripts/docker-start.ps1
  │
  ├─ 1. .env missing?  → Copy-Item .env.sample .env        (SPEC-0.3.1)
  ├─ 2. render-odoo-conf.ps1                               (SPEC-0.1.2, this contract)
  │       └─ abort the whole start on non-zero exit
  ├─ 3. docker compose up -d                               (SPEC-0.1.1)
  └─ 4. healthcheck.ps1                                    (SPEC-0.3.1)
```

Ordering is normative: rendering happens **after** `.env` is guaranteed to exist and **before**
Compose starts, because Compose resolves the bind-mount at container creation and Odoo reads the file
once at boot. Rendering after `up -d` would leave the running server on the previous configuration.

A non-zero exit from step 2 must abort the start. Proceeding would boot Odoo against a stale or
absent `odoo.conf`, producing a confusing "module not found" symptom whose real cause is two steps
upstream.

---

## 6. `.gitignore` Contract

```gitignore
# Configuración de Odoo renderizada (contiene la clave maestra inyectada)
config/odoo.conf
!config/odoo.conf.template
```

The negation is defensive. `config/odoo.conf` does not glob-match `config/odoo.conf.template`, so the
`!` line is not strictly required today — but it documents the intent explicitly and protects the
template if the rule is ever broadened to `config/odoo.conf*`.

---

## 7. Verification Contract

| Assertion | Command | Expected |
| :--- | :--- | :--- |
| Renderer is idempotent | Run twice, hash both outputs | Identical `SHA256` |
| Token fully substituted | `Select-String '\$\{' ./config/odoo.conf` | No match |
| Secret present in output | `Select-String '^admin_passwd\s*=\s*\S+' ./config/odoo.conf` | Exactly one match, value non-empty |
| Secret absent from Git | `git check-ignore -v config/odoo.conf` | Prints the matching rule |
| Template still tracked | `git ls-files --error-unmatch config/odoo.conf.template` | Exit `0` |
| No BOM | `(Get-Content ./config/odoo.conf -Encoding Byte -TotalCount 3)` | Not `239 187 191` |
| LF line endings | `(Get-Content ./config/odoo.conf -Raw) -match "\r"` | `False` |
| Missing-variable guard | Blank `ODOO_ADMIN_PASSWD` in `.env`, run the renderer | Non-zero exit; existing `odoo.conf` unmodified |
| Container reads the render | `docker compose exec web cat /etc/odoo/odoo.conf \| Select-String admin_passwd` | Shows the injected value (or its pbkdf2 upgrade after first use) |
