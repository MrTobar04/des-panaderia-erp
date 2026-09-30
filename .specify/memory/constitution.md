<!--
SYNC IMPACT REPORT
- Version change: 1.0.0 -> 1.1.0
- List of modified principles:
  - Added Principle VI: Deterministic Local Docker Provisioning & Environment Parity
  - Maintained Principles I through V unchanged
- Added sections: Local Docker Orchestration & Provisioning Standards in Technical Stack
- Removed sections: None
- Follow-up TODOs: None
-->

# Panadería "Delicias Dulces" ERP Constitution

## Core Principles

### I. Odoo Modular Architecture & MVC Separation
Every feature must adhere strictly to Odoo's Model-View-Controller paradigm and modular file structure (`__init__.py`, `__manifest__.py`, `models/`, `views/`, `security/`). Extensions to standard Odoo models (such as `res.partner`) must inherit cleanly without mutating core base behaviors. Business logic, model fields, XML views (form/tree/search), and access control lists (`ir.model.access.csv`) must remain isolated and self-contained within dedicated module subdirectories.

### II. Atomic Sales-to-Inventory Synchronization
Transaction lifecycle transitions (such as moving a sale order from `draft` / Borrador to `confirmed` / Confirmada) must guarantee atomic execution. Confirming a sale must calculate line totals, update customer metrics, trigger automated invoice generation, and instantaneously decrement available product stock to prevent inventory discrepancies.

### III. Proactive Stock Alerting & Data Integrity
All financial, quantity, and cost fields must enforce strict domain validations (non-negative unit costs, positive unit prices, valid category assignments: Pan, Pastel, Galleta, Bebida). The inventory system must proactively monitor stock thresholds against configured minimum limits and flag low-stock warnings across inventory listings and reporting dashboards.

### IV. Spec-Driven Verification & Traceable Test Procedures
Every deliverable module must strictly derive its implementation from formal specifications and maintain a manual/automated test procedure document (`docs/test-procedures/`) mapping directly to Acceptance Criteria. No feature is marked complete without passing end-to-end user journey verification (from product configuration to point-of-sale confirmation and invoicing).

### V. Operational Usability & Express Deployment Standards
User interfaces must prioritize speed, ergonomic navigation, and intuitive status bar workflows tailored for bakery shop personnel. Every release must include clear, turnkey installation documentation (`Instrucciones_Instalacion.txt`) and executive project documentation (`Documentacion_Express.pdf`) ensuring zero-barrier deployment and verification.

### VI. Deterministic Local Docker Provisioning & Environment Parity
Local development, automated evaluation, and live demonstration must be fully containerized using Docker and Docker Compose (`docker-compose.yml`). The provisioning layer must decouple the application service (Odoo), the relational database (PostgreSQL), and persistent named volumes (`odoo-web-data`, `odoo-db-data`). Custom bakery addons (`Modulo_Odoo/`) must be mounted dynamically (`/mnt/extra-addons/`) to support rapid iteration, zero host-polluting dependency installs, and single-command startup (`docker compose up -d`). In compliance with ISO-27001 secret management, database passwords and master keys must be parameterized through `.env` and excluded from version control via `.gitignore`.

## Technical Stack & Architectural Constraints

1. **Framework & Platform:** Odoo ERP Framework (Python 3.10+, XML UI declarations, QWeb reporting engine).
2. **Container & Local Provisioning Tier:**
   - **Docker Engine & Docker Compose:** Standard v2 compose configuration with healthcheck triggers and restart policies (`unless-stopped`).
   - **Odoo Service:** Official Odoo container image (v16/v17/v18) mapped on host port `8069:8069` (and `8072:8072` for chat/longpolling).
   - **PostgreSQL Service:** Official PostgreSQL 15/16 Alpine image configured on private internal bridge network (`panaderia-network`).
   - **Persistent Volumes:** Named volumes for PostgreSQL datadir and Odoo filestore (`web_data`, `db_data`).
   - **Live Addon Mount:** Bind-mount `./Modulo_Odoo` $\to$ `/mnt/extra-addons/panaderia` for instant module hot-reloading.
   - **Configuration & Secrets:** Centralized `config/odoo.conf` file and `.env.sample` template with runtime secret injection.
3. **Persistence & Data Tier:** PostgreSQL backend utilizing Odoo ORM methods; raw SQL queries are prohibited unless required for complex aggregation reports.
4. **Security & Permissions:** Mandatory role-based access controls defined via `security/ir.model.access.csv` and security XML groups for bakery operators and managers.
5. **Delivery Directory Layout:**
   ```text
   Panaderia_DeliciasDulces/
   ├── docker-compose.yml
   ├── .env.sample
   ├── .gitignore
   ├── config/
   │   └── odoo.conf
   ├── Documentacion_Express.pdf
   ├── Modulo_Odoo/
   │   ├── __init__.py
   │   ├── __manifest__.py
   │   ├── models/
   │   │   ├── __init__.py
   │   │   ├── producto.py
   │   │   ├── venta.py
   │   │   ├── cliente.py
   │   │   └── factura.py
   │   ├── views/
   │   │   ├── producto_views.xml
   │   │   ├── venta_views.xml
   │   │   ├── cliente_views.xml
   │   │   ├── factura_views.xml
   │   │   └── reporte_views.xml
   │   ├── data/
   │   │   ├── categoria_data.xml
   │   │   ├── cliente_data.xml
   │   │   ├── venta_sequence.xml
   │   │   └── factura_sequence.xml
   │   └── security/
   │       └── ir.model.access.csv
   └── Instrucciones_Instalacion.txt
   ```

## Quality Gates & Delivery Rubric Standards

All deliverables must comply with the Academic & Professional Excellence Rubric (Score 4.5 - 5.0 / Destacado):
- **Core Functionality:** Full implementation of 5 core modules (Inventario Básico, Proceso de Ventas Esencial, Registro y Extensión de Clientes, Facturación Simple, Reportes de Operación Diaria) with seamless interconnection.
- **Technical Quality:** Modular, idiomatic Odoo code adhering to PEP 8, clean view inheritance, and zero critical unhandled exceptions.
- **Usability:** Intuitive state workflows (`Borrador` $\to$ `Confirmada`, `Pendiente` $\to$ `Pagada`), custom bakery partner filtering, and prominent stock warnings.
- **Demonstration Readiness:** Prepared execution scripts, sample bakery seed data, containerized one-command launch (`docker compose up`), and a 10–12 minute live demonstration path covering end-to-end bakery workflows.

## Governance

- **Supremacy & Compliance:** This Constitution establishes the non-negotiable architectural and engineering baseline for Panadería "Delicias Dulces" ERP. All specifications (`specs/`), plans (`plan.md`), and tasks (`tasks.md`) must strictly comply.
- **Amendment Procedure:** Any change or evolution in scope requires proposing an updated Constitution with explicit justification and a version increment.
- **Semantic Versioning Policy:**
  - **MAJOR:** Structural overhaul of core architecture, breaking data model migrations, or removal of core modules.
  - **MINOR:** Addition of new operational modules, provisioning layers (e.g. Docker containerization), extended reporting, or new business rules.
  - **PATCH:** Refinements to UI views, field label corrections, or documentation adjustments.

**Version**: 1.1.0 | **Ratified**: 2026-09-29 | **Last Amended**: 2026-09-29
