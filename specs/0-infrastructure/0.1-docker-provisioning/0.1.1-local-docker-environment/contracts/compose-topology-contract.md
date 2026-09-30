# Contract: Compose Topology — Services, Network, Volumes, Mounts

**Feature**: `SPEC-0.1.1: Aprovisionamiento de Entorno Local en Docker`
**Artifact under contract**: `docker-compose.yml` (repository root)
**Date**: 2026-09-29
**Consumers**: `SPEC-0.1.2` (config mount), `SPEC-0.2.1` (db container name, datadir), `SPEC-0.3.1` (container names, health status, HTTP endpoint), `SPEC-1.1.1`+ (module technical name)

> This is the **authoritative** source for container names, service names, internal paths, and the module technical name. Any sibling spec that hardcodes one of these values must match this table.

---

## 1. Identity Contract

| Identifier | Normative Value | Consumed By |
| :--- | :--- | :--- |
| Compose project name | `panaderia-erp` (via `COMPOSE_PROJECT_NAME`) | Volume/network prefixing |
| Application service name | `web` | `docker compose exec web ...`, `docker compose logs web` |
| Database service name | `db` | Odoo `HOST=db`; `docker compose logs db` |
| Application container name | `panaderia_odoo_web` | `SPEC-0.3.1` healthcheck & restart |
| Database container name | `panaderia_odoo_db` | `SPEC-0.2.1` `docker exec`; `SPEC-0.3.1` healthcheck |
| Private network name | `panaderia-net` | Internal DNS resolution of `db` |
| Odoo filestore volume | `panaderia_odoo_web_data` | `SPEC-0.1.1` DoD persistence check |
| PostgreSQL datadir volume | `panaderia_odoo_db_data` | `SPEC-0.1.1` DoD persistence check |
| **Module technical name** | **`panaderia`** | `-i panaderia`, `-u panaderia`, `odoo.addons.panaderia` logger |

---

## 2. Service Contract: `db`

| Attribute | Normative Value | Rationale |
| :--- | :--- | :--- |
| `image` | `postgres:15-alpine` | Official, unmodified |
| `container_name` | `panaderia_odoo_db` | Fixed so `docker exec` in `SPEC-0.2.1` needs no lookup |
| `restart` | `unless-stopped` | Constitution Technical Stack §2 |
| `ports` | **absent** | Acceptance Scenario 3 — no host exposure of `5432` |
| `networks` | `[panaderia-net]` | Sole network |
| `environment.POSTGRES_DB` | `${POSTGRES_DB:-postgres}` | Maintenance database; Odoo creates its own |
| `environment.POSTGRES_USER` | `${POSTGRES_USER:-odoo}` | Becomes the cluster superuser, so Odoo can `CREATEDB` |
| `environment.POSTGRES_PASSWORD` | `${POSTGRES_PASSWORD:-odoo_dev_password}` | Secret; supplied by `.env` |
| `environment.PGDATA` | `/var/lib/postgresql/data/pgdata` | Nested — see `research.md` Decision 3 |
| `volumes` | `odoo-db-data:/var/lib/postgresql/data/pgdata` | Mounted at the nested `PGDATA` |

### Healthcheck (normative)

| Field | Value |
| :--- | :--- |
| `test` | `["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-odoo} -d ${POSTGRES_DB:-postgres}"]` |
| `interval` | `5s` |
| `timeout` | `5s` |
| `retries` | `5` |

**Guarantee**: reaches `healthy` within 25 s on a warm volume. `SPEC-0.3.1` may read this via
`docker inspect --format='{{.State.Health.Status}}' panaderia_odoo_db` and MUST expect exactly `healthy`.

---

## 3. Service Contract: `web`

| Attribute | Normative Value | Rationale |
| :--- | :--- | :--- |
| `image` | `odoo:16.0` | Official, unmodified — no `Dockerfile` in this project |
| `container_name` | `panaderia_odoo_web` | Fixed for `SPEC-0.3.1` restart/log targeting |
| `restart` | `unless-stopped` | Constitution Technical Stack §2 |
| `depends_on` | `db: { condition: service_healthy }` | Prevents Odoo starting against an uninitialized cluster |
| `ports[0]` | `"${ODOO_HTTP_PORT:-8069}:8069"` | Host port reassignable via `.env` only |
| `ports[1]` | `"${ODOO_CHAT_PORT:-8072}:8072"` | Longpolling / chat |
| `networks` | `[panaderia-net]` | Sole network |
| `environment.HOST` | `db` | Resolved by the bridge network's embedded DNS |
| `environment.PORT` | `5432` | Container-internal port |
| `environment.USER` | `${POSTGRES_USER:-odoo}` | Must equal `db`'s `POSTGRES_USER` |
| `environment.PASSWORD` | `${POSTGRES_PASSWORD:-odoo_dev_password}` | Must equal `db`'s `POSTGRES_PASSWORD` |

### Mount Contract (normative — consumed by other specs)

| Host Source | Container Target | Mode | Owner Spec |
| :--- | :--- | :--- | :--- |
| `odoo-web-data` (named volume) | `/var/lib/odoo` | rw | `SPEC-0.1.1` |
| `./config` | `/etc/odoo` | rw | `SPEC-0.1.2` authors the contents |
| `./Modulo_Odoo` | `/mnt/extra-addons/panaderia` | rw | `SPEC-1.1.1`+ author the contents |

> **Critical invariant.** The addon is mounted at `/mnt/extra-addons/panaderia`, therefore
> `addons_path` in `config/odoo.conf` MUST reference the **parent** `/mnt/extra-addons` — never
> `/mnt/extra-addons/panaderia`. See `research.md` Decision 2. Violating this makes the module
> undiscoverable.

### Healthcheck (normative, additive to `spec.md`)

| Field | Value |
| :--- | :--- |
| `test` | `["CMD-SHELL", "python3 -c \"import urllib.request; urllib.request.urlopen('http://localhost:8069/web/login', timeout=5)\""]` |
| `interval` | `10s` |
| `timeout` | `10s` |
| `retries` | `6` |
| `start_period` | `60s` |

**Guarantee**: `python3` is present in `odoo:16.0`; `curl` and `wget` are **not**. `/web/login`
answers `200` even with no Odoo database created, so the probe is valid on a cold stack.

---

## 4. Network Contract

| Attribute | Value |
| :--- | :--- |
| Key | `panaderia-net` |
| `name` | `panaderia-net` (explicit, so it is not prefixed with the project name) |
| `driver` | `bridge` |
| `internal` | `false` — `web` needs outbound access |

**Guarantees**: `db` is resolvable from `web` as the hostname `db` on port `5432`. No service on this network is reachable from the host except through an explicit published port.

---

## 5. Volume Contract

| Compose Key | `name` (actual Docker volume) | Mounted At | Survives |
| :--- | :--- | :--- | :--- |
| `odoo-web-data` | `panaderia_odoo_web_data` | `web:/var/lib/odoo` | `down`, `up -d`, container recreation, image update |
| `odoo-db-data` | `panaderia_odoo_db_data` | `db:/var/lib/postgresql/data/pgdata` | same |

**Destroyed only by** an explicit `docker compose down -v` or `docker volume rm`. No Capa 0 script may issue either without interactive confirmation (`SPEC-0.3.1` §3).

---

## 6. Verification Contract

| Assertion | Command | Expected |
| :--- | :--- | :--- |
| File is syntactically valid | `docker compose config` | Exit `0`, no `WARN` lines |
| Both services running | `docker compose ps` | `db` and `web` listed, `db` `(healthy)` |
| DB healthy | `docker inspect --format='{{.State.Health.Status}}' panaderia_odoo_db` | `healthy` |
| Web healthy | `docker inspect --format='{{.State.Health.Status}}' panaderia_odoo_web` | `healthy` |
| HTTP reachable | `Invoke-WebRequest http://localhost:8069/web/login -UseBasicParsing` | `StatusCode` `200` |
| `5432` not published | `Test-NetConnection localhost -Port 5432` | `TcpTestSucceeded : False` |
| DB reachable in-network | `docker compose exec web python3 -c "import socket; socket.create_connection(('db',5432),3)"` | Exit `0`, no output |
| Addon discoverable | `docker compose logs web \| Select-String "addons_path"` | Contains `/mnt/extra-addons` |
| Volumes persist | `docker volume ls` after `down` | Both `panaderia_odoo_*_data` still listed |
