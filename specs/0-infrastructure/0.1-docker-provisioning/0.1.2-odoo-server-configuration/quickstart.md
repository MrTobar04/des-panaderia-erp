# Quickstart & Verification Guide — Configuración del Servidor Odoo y Modos de Desarrollo

**Feature**: `SPEC-0.1.2: Configuración del Servidor Odoo y Modos de Desarrollo`
**Related Spec**: [`spec.md`](./spec.md)
**Config Contract**: [`contracts/odoo-conf-contract.md`](./contracts/odoo-conf-contract.md)
**Rendering Contract**: [`contracts/config-rendering-contract.md`](./contracts/config-rendering-contract.md)
**Depends On**: [`SPEC-0.1.1`](../0.1.1-local-docker-environment/spec.md) — the stack, the `./config` mount, and `.env`

All commands assume **PowerShell** executed from the repository root (`des-panaderia-erp/`).

---

## 1. Prerequisites

| Requirement | Verify With | Expected |
| :--- | :--- | :--- |
| `SPEC-0.1.1` stack defined | `Test-Path ./docker-compose.yml` | `True` |
| `.env` exists with the master password | `Select-String "^ODOO_ADMIN_PASSWD=" ./.env` | One match, non-empty value |
| Config template present | `Test-Path ./config/odoo.conf.template` | `True` |
| Addon present | `Test-Path ./Modulo_Odoo/__manifest__.py` | `True` |

---

## 2. Render the Configuration

```powershell
./scripts/render-odoo-conf.ps1
```

**Expected**: `[OK] config/odoo.conf generado (clave maestra inyectada desde .env)`.

If `ODOO_ADMIN_PASSWD` is still the shipped sample value, the script also prints
`ADVERTENCIA: ODOO_ADMIN_PASSWD conserva el valor de ejemplo.` — the render still succeeds, but change
the value in `.env` and re-run before the final delivery.

### Confirm the render is clean

```powershell
# No unsubstituted tokens
Select-String '\$\{' ./config/odoo.conf
# Exactly one non-empty master password line
Select-String '^admin_passwd\s*=\s*\S+' ./config/odoo.conf
# LF endings only — a CRLF here corrupts every path value inside the Linux container
(Get-Content ./config/odoo.conf -Raw) -match "`r"
```

**Expected**: no output from the first command; one match from the second; `False` from the third.

---

## 3. Verify the Critical Values Before Starting

This is the cheapest possible catch for the single most defect-prone setting in the project.

```powershell
Select-String -Path ./config/odoo.conf -Pattern "^addons_path|^data_dir|^dev_mode|^log_handler"
```

**Expected**:

```text
addons_path = /mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons
data_dir = /var/lib/odoo
dev_mode = reload,qweb,xml
log_handler = :INFO,odoo.addons.panaderia:DEBUG
```

⚠️ If `addons_path` reads `/mnt/extra-addons/panaderia`, **stop and fix it**. Odoo enumerates the
*children* of each path entry, so it would scan inside the module and find `models/`, `views/`,
`security/` — none with a `__manifest__.py`. The module would never appear in **Aplicaciones**.
See `research.md` Decision 1.

⚠️ If the core path `/usr/lib/python3/dist-packages/odoo/addons` is absent, the `base` module cannot
load and the server aborts at startup.

---

## 4. Acceptance Scenario 1 — Automatic bakery module detection

### Step 1 — Start the stack and confirm the file is in place

```powershell
docker compose up -d
docker compose exec web printenv ODOO_RC
docker compose exec web cat /etc/odoo/odoo.conf | Select-String "^addons_path"
```

**Expected**: `ODOO_RC` is `/etc/odoo/odoo.conf`, and the `addons_path` line matches §3. This proves
Odoo is reading *your* file and not the image's default.

### Step 2 — Confirm the mount resolves to a real module

```powershell
docker compose exec web ls -la /mnt/extra-addons/
docker compose exec web cat /mnt/extra-addons/panaderia/__manifest__.py | Select-String "'name'"
```

**Expected**: `/mnt/extra-addons/` lists a `panaderia` directory, and the manifest prints
`'name': 'Panadería Delicias Dulces - Gestión ERP'`.

### Step 3 — Confirm Odoo agrees

```powershell
docker compose logs web | Select-String "addons paths|addons_path"
```

**Expected**: the startup banner lists `/mnt/extra-addons` among the addons paths.

### Step 4 — Confirm discovery in the UI

1. Open `http://localhost:8069` and log in as `admin`.
2. Go to **Aplicaciones**.
3. Remove the default **Aplicaciones** filter from the search box.
4. Click **Actualizar lista de aplicaciones** and confirm.
5. Search for `Panadería`.

**Expected**: **Panadería Delicias Dulces - Gestión ERP** appears and offers **Activar** / **Instalar**.

### Step 5 — Install and confirm the technical name

```powershell
docker compose exec web odoo -d panaderia_db -i panaderia --stop-after-init
docker compose restart web
```

**Expected**: the log shows `module panaderia: loading ...` with no traceback. The technical name is
`panaderia` — a direct consequence of `addons_path` naming the parent directory.

✅ **Scenario 1 satisfied**: the module is listed and installable from `/mnt/extra-addons/panaderia`.

---

## 5. Acceptance Scenario 2 — Database manager protection

### Step 1 — Reach the manager

Navigate to `http://localhost:8069/web/database/manager`.

**Expected**: the manager loads and lists the existing databases (`list_db = True`).

### Step 2 — Attempt a backup with no master key

Click **Backup** on `panaderia_db`, leave **Master Password** empty, and submit.

**Expected**: the operation is rejected with an access-denied message. Critically, it must **not** be
an HTTP `500` — a `500` here means `admin_passwd` holds a malformed pseudo-hash and passlib raised
while parsing it (see `research.md` Decision 3).

### Step 3 — Attempt with a wrong master key

Repeat with `clave_incorrecta`.

**Expected**: rejected again, same clean error.

### Step 4 — Confirm the correct key works

Repeat with the value of `ODOO_ADMIN_PASSWD` from `.env`.

**Expected**: the `.zip` backup downloads.

### Step 5 — Observe the automatic hash upgrade

```powershell
docker compose exec web cat /etc/odoo/odoo.conf | Select-String "^admin_passwd"
```

**Expected**: the value now begins with `$pbkdf2-sha512$`. Odoo re-hashed the plaintext on first
successful verification and wrote it back — which is exactly why the `./config` mount is read-write.
The local `./config/odoo.conf` reflects the same change through the bind-mount, and it is `.gitignore`d,
so nothing leaks.

✅ **Scenario 2 satisfied**: destructive database-manager operations require the configured master key.

---

## 6. Acceptance Scenario 3 — Custom debug log visibility

### Step 1 — Confirm the handler is active

```powershell
docker compose logs web | Select-String "log_handler|odoo.addons.panaderia"
```

### Step 2 — Generate bakery module activity

In the UI, go to **Panadería → Inventario → Productos** and create or edit a product.

### Step 3 — Follow the module's own log namespace

```powershell
docker compose logs --tail 80 web | Select-String "odoo.addons.panaderia"
```

**Expected**: `DEBUG` lines appear under the `odoo.addons.panaderia` prefix while unrelated
subsystems stay at `INFO`. The namespace follows directly from the technical name `panaderia`; had the
`addons_path` defect shipped, this prefix would not exist at all.

✅ **Scenario 3 satisfied**: detailed debug messages surface under `odoo.addons.panaderia`.

---

## 7. `dev_mode` — Hot Reload Behavior

### XML views: reload the browser, nothing else

1. Edit a label in `Modulo_Odoo/views/producto_views.xml` and save.
2. Press `F5` in the browser on the affected view.

**Expected**: the change is visible with **no** container restart and **no** module upgrade. This is
the `xml` flag at work.

### Python models: an explicit upgrade is required

```powershell
docker compose exec web odoo -d panaderia_db -u panaderia --stop-after-init
docker compose restart web
```

> The `reload` flag is present in `dev_mode`, but auto-restart on Python change depends on the
> `watchdog` package, which is **not installed in `odoo:16.0`**. Odoo logs a warning and the flag is
> inert. Do not wait for a Python change to apply by itself — run the upgrade above, or use
> `./scripts/docker-restart.ps1` from `SPEC-0.3.1`. See `research.md` Decision 5.

### Confirm `werkzeug` is absent

```powershell
Select-String "^dev_mode" ./config/odoo.conf
```

**Expected**: `reload,qweb,xml` — no `werkzeug`, which would render full Python tracebacks into HTTP
responses.

---

## 8. Security Verification (`spec.md` §7)

| Check | Command | Expected |
| :--- | :--- | :--- |
| Rendered config ignored | `git check-ignore -v config/odoo.conf` | Prints the matching rule |
| Rendered config untracked | `git ls-files --error-unmatch config/odoo.conf` | Exit non-zero |
| Template tracked | `git ls-files --error-unmatch config/odoo.conf.template` | Exit `0` |
| No secret in the template | `git grep -n "admin_passwd" -- config/odoo.conf.template` | Only the `${ODOO_ADMIN_PASSWD}` token |
| Master key is not the weak default | `Select-String "^admin_passwd\s*=\s*admin$" ./config/odoo.conf` | No match (`spec.md` §3) |
| Nothing leaked historically | `git log --all --oneline -- config/odoo.conf` | No commits |
| Host file permissions | `Get-Acl ./config/odoo.conf \| Format-List` | Readable by the current user; not world-writable |

---

## 9. Definition of Done Mapping

| `spec.md` §10 DoD Item | Verified In |
| :--- | :--- |
| `config/odoo.conf` created with all development parameters | §2, §3 |
| Mount to `/etc/odoo/odoo.conf` verified in the `web` container | §4 Step 1 |
| Addons path recognizing `Modulo_Odoo/` at startup | §3, §4 Steps 2–5 |
| `docs/test-procedures/test-procedure-0.1.2.md` documented | Authored from this guide during `/speckit-implement` |

> The DoD says "`config/odoo.conf` created". It is created — by the renderer, from the tracked
> `config/odoo.conf.template`. The tracked deliverable is the template, because the rendered file
> holds the master password. Rationale in `plan.md` → Complexity Tracking #2.

---

## 10. Troubleshooting

| Symptom | Likely Cause | Fix |
| :--- | :--- | :--- |
| Module absent from **Aplicaciones** after refreshing the list | `addons_path` points at `/mnt/extra-addons/panaderia` | Correct it to `/mnt/extra-addons`, re-render, `docker compose up -d` |
| Server exits at startup with a `base` module error | Core addons path missing from `addons_path` | Re-add `/usr/lib/python3/dist-packages/odoo/addons` |
| `500` on any database-manager action | `admin_passwd` holds a malformed `$pbkdf2-sha512$...` string | Render plaintext from `.env`; let Odoo hash it |
| `admin_passwd = ${ODOO_ADMIN_PASSWD}` literally in the file | Renderer never ran, or ran before `.env` existed | Run `./scripts/render-odoo-conf.ps1`, then `docker compose up -d` |
| Odoo reports a nonexistent addons directory | CRLF line endings in `odoo.conf` leave a trailing `\r` in the path | Re-render with LF endings and no BOM (`config-rendering-contract.md` §3) |
| XML edits need a restart to appear | `xml` missing from `dev_mode` | Set `dev_mode = reload,qweb,xml`, re-render, recreate the container |
| Config changes have no effect | Edited `config/odoo.conf` instead of the template, then re-rendered over it | Edit `config/odoo.conf.template`; the rendered file is disposable output |
