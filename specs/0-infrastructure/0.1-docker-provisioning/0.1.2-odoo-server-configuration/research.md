# Phase 0: Outline & Research — Configuración del Servidor Odoo y Modos de Desarrollo

**Feature**: `SPEC-0.1.2: Configuración del Servidor Odoo y Modos de Desarrollo`
**Branch / Directory**: `specs/0-infrastructure/0.1-docker-provisioning/0.1.2-odoo-server-configuration`
**Date**: 2026-09-29
**Status**: Completed

---

## 1. Executive Summary & Objective

This research establishes how the `odoo:16.0` image actually consumes `/etc/odoo/odoo.conf`, so the delivered configuration satisfies every acceptance scenario in `spec.md` §5 rather than merely resembling a plausible Odoo config. Six decisions were required. Three of them correct defects in the literal snippet given in `spec.md` §4 — one of which (`addons_path`) would deterministically fail that spec's own Acceptance Scenario 1, and another (`admin_passwd`) would produce a server error instead of an authentication prompt.

---

## 2. Research Findings & Technical Decisions

### Decision 1: `addons_path` must name the parent directory, not the module

* **Decision**: `addons_path = /mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons`.
* **Rationale**:
  * Odoo's module loader treats each `addons_path` entry as a *container of modules*: it lists the immediate child directories of the entry and accepts those containing a `__manifest__.py`.
  * `SPEC-0.1.1` bind-mounts `./Modulo_Odoo` to `/mnt/extra-addons/panaderia`. Setting `addons_path` to `/mnt/extra-addons/panaderia` — the value in `spec.md` §4 — makes Odoo enumerate `models/`, `views/`, `data/`, `security/`, `tests/`. None has a manifest, so **no module is discovered**, the addon never appears in **Aplicaciones**, and Acceptance Scenario 1 of this spec fails every single time.
  * Naming the parent makes `panaderia` the one discovered module. Its technical name becomes `panaderia`, which is also exactly the logger namespace that Acceptance Scenario 3 asserts (`odoo.addons.panaderia`). The correction therefore reconciles this spec with itself — its §4 snippet writes `odoo.addons.Modulo_Odoo`, contradicting its own Scenario 3.
  * The core path is listed explicitly because supplying `addons_path` replaces the parser's default. Omitting the core directory prevents the `base` module from loading and the server aborts at startup. In the Debian-packaged official image the standard addons live at `/usr/lib/python3/dist-packages/odoo/addons`.
  * Custom path first preserves the override precedence stated in `spec.md` §2.1.
* **Alternatives Considered**:
  * *Change the mount target to `/mnt/extra-addons/Modulo_Odoo` and keep `addons_path` deep*: Rejected — yields the technical name `Modulo_Odoo`. Odoo module names are Python package identifiers by convention (lower snake_case); a leading capital is awkward in `-i`/`-u`, `--test-tags`, and the `odoo.addons.*` logger hierarchy, and it would leave Scenario 3's asserted prefix wrong.
  * *Rely on the image's built-in default `addons_path = /mnt/extra-addons`*: Rejected — it works, but leaving the key implicit makes the single most defect-prone setting invisible to reviewers, and `spec.md` §2.1 requires it declared.

### Decision 2: Omit `db_host`, `db_user`, and `db_password` from the config file

* **Decision**: Do not declare any database connection key in `odoo.conf`. Let `SPEC-0.1.1`'s Compose environment (`HOST`, `PORT`, `USER`, `PASSWORD`) remain authoritative.
* **Rationale**:
  * The official image's entrypoint builds its `--db_*` argument list conditionally: for each of `db_host`, `db_port`, `db_user`, `db_password` it first greps `ODOO_RC`, and **if the key is present in the file, the file's value is used instead of the environment variable**. Declaring them in `odoo.conf` therefore silently overrides `.env`.
  * Omitting them keeps one source of truth for database credentials (`.env` → Compose → container environment) and leaves `admin_passwd` as the only secret the config file ever contains. That is what makes the single-token template of Decision 4 viable.
  * It also prevents a class of confusing failure where `.env` is updated, the stack is recreated, and Odoo still authenticates with a stale password baked into a tracked file.
* **Alternatives Considered**:
  * *Declare `db_host = db` and friends for explicitness*: Rejected — duplicates the credential surface into a second file for documentation value only, and introduces a real drift hazard against `.env`.

### Decision 3: How Odoo actually validates `admin_passwd` — the pseudo-hash defect

* **Decision**: Render `admin_passwd` as **plaintext**, sourced from `ODOO_ADMIN_PASSWD` in `.env`. Do not write a hash.
* **Rationale**:
  * Odoo 16 verifies the master password through a passlib `CryptContext` configured for `pbkdf2_sha512`, with a plaintext comparison path retained for backward compatibility. When a plaintext value verifies successfully, Odoo **re-hashes it and writes the hash back into the config file**, upgrading the credential in place.
  * The value in `spec.md` §4 — `$pbkdf2-sha512$25000$local_bakery_erp_master_pwd` — is not a valid pbkdf2-sha512 hash: the modular-crypt format requires `$pbkdf2-sha512$<rounds>$<salt>$<checksum>`, and here the salt and checksum fields are simply missing. Because the string carries the recognized `$pbkdf2-sha512$` prefix, Odoo routes it to passlib rather than the plaintext path, and passlib raises on the malformed payload. The operator sees a `500` in the database manager instead of a password prompt — a failure that is actively misleading under demo pressure.
  * Plaintext-in-a-gitignored-file is the correct posture here: the threat model is "credential in Git history", not "attacker with local filesystem read access to the developer's own machine".
* **Consequence for the mount mode**: the self-upgrade writes to `/etc/odoo/odoo.conf`, so the `./config` bind-mount is deliberately left read-write (consistent with `SPEC-0.1.1` `research.md` Decision 6). Mounting `:ro` is a valid hardening step; the only effect is a warning on the write attempt while authentication still succeeds.
* **Alternatives Considered**:
  * *Generate a genuine pbkdf2 hash and commit it*: Rejected — still commits a credential derivative, and adds a hashing step to first-time setup for no gain on a local-only stack.
  * *Leave `admin_passwd` empty*: Rejected — an empty master password makes Odoo refuse all database-manager operations, so Acceptance Scenario 2 could not be demonstrated at all (it would fail for the wrong reason).
  * *`admin_passwd = admin`*: Explicitly forbidden by `spec.md` §3.

### Decision 4: Runtime secret injection via a tracked template

* **Decision**: Commit `config/odoo.conf.template` containing the token `${ODOO_ADMIN_PASSWD}`. Render it to the untracked `config/odoo.conf` with `scripts/render-odoo-conf.ps1`, invoked by `SPEC-0.3.1`'s `docker-start.ps1` before `docker compose up -d`. Add `config/odoo.conf` to `.gitignore`.
* **Rationale**:
  * Odoo's INI parser performs **no** environment-variable interpolation, so `admin_passwd = ${ODOO_ADMIN_PASSWD}` inside the file would be read as that literal string. Substitution must happen before the container reads the file.
  * Constitution Technical Stack §2 names the target design directly: "Centralized `config/odoo.conf` file and `.env.sample` template with **runtime secret injection**." The template pipeline is the literal implementation of that clause.
  * Config-as-code survives intact: every non-secret key is reviewable in Git, and a diff on the template is a diff on the real configuration.
  * Rendering is idempotent and cheap, so it can run unconditionally on every start — no staleness logic, no "is the file newer than the template" heuristics.
* **Alternatives Considered**:
  * *Commit `odoo.conf` directly, as `spec.md` §9 lists*: Rejected — either it leaks a credential or it ships broken.
  * *Set the master password through the Odoo UI on first run*: Rejected — Odoo writes the hash into a *tracked* file, so `git status` is permanently dirty and the credential lands in the next commit by accident.
  * *Docker secrets / `secrets:` in Compose*: Rejected as disproportionate. Docker secrets outside Swarm are file bind-mounts, and Odoo cannot read `admin_passwd` from a separate file — it would still need rendering.

### Decision 5: Effective `dev_mode` flags — and the `reload` caveat

* **Decision**: `dev_mode = reload,qweb,xml`.
* **Rationale**:
  * `xml` is the flag that makes Odoo re-read view definitions from the XML files on the filesystem instead of serving the database-stored copy. It is what actually delivers the §4 UI/UX promise that "vistas modificadas en el código fuente XML se actualizan en el navegador al recargar la página (F5)". `spec.md` omits it from both of its own lists, which is why the promise would not have been met.
  * `qweb` surfaces QWeb template rendering diagnostics, needed later by the reporting module (`SPEC-5.1.1`).
  * `werkzeug` is **excluded deliberately**, despite appearing in `spec.md` §2.1. It renders full Python tracebacks into HTTP responses — an information-disclosure surface with no benefit over reading the container log, which the operator already has via `docker compose logs web`.
  * **`reload` caveat**: auto-restart on Python file change depends on the `watchdog` package, which is not part of Odoo 16's dependency set and is not installed in the official image. When it is absent Odoo logs a warning and the flag is inert — non-fatal, but the operator must not expect Python changes to apply by themselves. The documented path for model changes remains an explicit module upgrade (`-u panaderia`) or `docker-restart.ps1` from `SPEC-0.3.1`.
* **Alternatives Considered**:
  * *`dev_mode = all`*: Rejected — `all` implies `werkzeug`, reintroducing the traceback exposure.
  * *No `dev_mode` at all*: Rejected — every view tweak would require a container restart, defeating Principle VI's "rapid iteration" requirement.

### Decision 6: Logging granularity, and the inert resource limits

* **Decision**: `log_level = info` with `log_handler = :INFO,odoo.addons.panaderia:DEBUG`. Retain `limit_memory_hard`, `limit_memory_soft`, `limit_time_cpu`, `limit_time_real` and `db_maxconn` as specified, documented as non-enforcing.
* **Rationale**:
  * The two-part handler keeps the global floor at INFO — so the boot log stays readable during a timed defense — while raising only the bakery module to DEBUG. This is exactly what Acceptance Scenario 3 asserts, and the namespace `odoo.addons.panaderia` follows from the technical name established in Decision 1.
  * Setting a global `log_level = debug` instead would bury the bakery messages under ORM, werkzeug, and asset-bundling chatter.
  * The four resource limits are enforced by Odoo's **prefork** (multi-worker) server only. This stack runs threaded, because `workers` is left at its default of `0` and `spec.md` §2.2 explicitly places multi-worker configuration out of scope. The keys are therefore inert. They are kept rather than deleted so the declared intent survives into any future production profile, and this plan documents them as non-enforcing so no one later mistakes them for an active memory guard.
  * `db_maxconn = 32` sits comfortably under PostgreSQL's default `max_connections = 100`, leaving headroom for the `psql` and `pg_dump` sessions that `SPEC-0.2.1` opens.
  * `list_db = True` is already the parser default; it is declared explicitly because Acceptance Scenario 2 depends on the database manager being reachable, and an implicit dependency on a default is exactly the kind of thing a later hardening pass breaks silently.
* **Alternatives Considered**:
  * *`log_level = debug` globally*: Rejected for signal-to-noise during the defense.
  * *Delete the inert limit keys*: Rejected — `spec.md` §2.1 requires performance parameters; documenting them as non-enforcing is more honest than removing them, and costs nothing.
  * *`list_db = False`*: Rejected — it hides the database manager, making Acceptance Scenario 2 undemonstrable.

---

## 3. Technology Matrix

| Parameter | Specification |
| :--- | :--- |
| **Config Format** | INI, single `[options]` section, parsed by Python `configparser` |
| **Config Path (container)** | `/etc/odoo/odoo.conf`, located via the image's `ODOO_RC` environment variable |
| **Config Path (host)** | `./config/odoo.conf`, rendered from `./config/odoo.conf.template` |
| **Core Addons Path** | `/usr/lib/python3/dist-packages/odoo/addons` (Debian-packaged official image) |
| **Custom Addons Path** | `/mnt/extra-addons` (parent of the bind-mount target `/mnt/extra-addons/panaderia`) |
| **Module Technical Name** | `panaderia` |
| **Logger Namespace** | `odoo.addons.panaderia` |
| **Filestore** | `/var/lib/odoo`, on the `panaderia_odoo_web_data` named volume |
| **Server Mode** | Threaded (`workers = 0`, the default) — multi-worker is out of scope per `spec.md` §2.2 |
| **Renderer** | PowerShell 5.1+ (`scripts/render-odoo-conf.ps1`) |

---

## 4. Risks and Mitigations

| Risk | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| `addons_path` points into the module directory | **Blocking** — module never discovered; Scenario 1 fails and no Capa 1–5 feature is demonstrable | Decision 1. Asserted in `quickstart.md` §4 by grepping the startup log for `/mnt/extra-addons` and confirming the module is listed in **Aplicaciones** |
| Core addons path omitted from `addons_path` | **Blocking** — `base` cannot load, server aborts at startup | Both paths declared explicitly; `quickstart.md` §4 verifies the rendered value before starting |
| Malformed pbkdf2 pseudo-hash in `admin_passwd` | Database manager returns `500` instead of prompting; looks like a broken stack | Decision 3 — plaintext, self-upgraded by Odoo. Scenario 2 verified in `quickstart.md` §5 |
| `config/odoo.conf` committed with a real master password | **Credential leak**; Principle VI and ISO-27001 violation | `.gitignore` excludes the rendered file; `quickstart.md` §8 verifies with `git check-ignore -v config/odoo.conf` |
| `.env` lacks `ODOO_ADMIN_PASSWD`, rendering an empty value | Database manager silently refuses every operation | Renderer fails loudly with a non-zero exit and a Spanish diagnostic rather than emitting a blank key (`config-rendering-contract.md` §4) |
| `Modulo_Odoo` absent or not mounted (`spec.md` §8 risk) | Odoo boots with an empty extra-addons root; module missing with no obvious cause | `docker-start.ps1` and the renderer assert `./Modulo_Odoo/__manifest__.py` exists before `up -d` |
| `reload` assumed to hot-apply Python changes | Developer edits a model, sees no effect, and misdiagnoses the code | `watchdog` absence documented in Decision 5; `quickstart.md` §7 gives the explicit `-u panaderia` upgrade path for Python changes |
| Resource limits mistaken for an active memory guard | False confidence; no protection against a runaway request | Documented as inert under `workers = 0` in Decision 6 and in `contracts/odoo-conf-contract.md` |
| `:ro` added to the config mount as a "hardening" tweak | Odoo cannot persist the pbkdf2 upgrade; a warning appears on every master-password use | Trade-off documented in Decision 3; the default stays read-write |

---

## 5. Open Questions

None blocking. The four artifact-level contradictions this research uncovered (`addons_path` versus mount target, `dev_mode` §2.1 versus §4, `log_handler` namespace versus Scenario 3, and `config/odoo.conf` as a tracked deliverable versus the no-committed-secrets rule) are all resolved above and recorded in `plan.md` → *Known Cross-Artifact Inconsistencies* for `/speckit-analyze`.
