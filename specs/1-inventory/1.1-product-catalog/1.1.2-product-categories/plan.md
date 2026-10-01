# Implementation Plan: Categorías de Productos de Panadería

**Branch**: `1.1.2-product-categories` | **Date**: 2026-09-30 | **Spec**: [`specs/1-inventory/1.1-product-catalog/1.1.2-product-categories/spec.md`](file:///d:/UDB/CICLO-10-2026/DES/LAB/Desafio%203/des-panaderia-erp/specs/1-inventory/1.1-product-catalog/1.1.2-product-categories/spec.md)

**Input**: Feature specification from `/specs/1-inventory/1.1-product-catalog/1.1.2-product-categories/spec.md`

---

## Summary

Implement the Product Categories taxonomy model (`panaderia.categoria`) for Panadería "Delicias Dulces" ERP. The module classifies commercial products into 4 standard commercial categories (Pan, Pastel, Galleta, Bebida) with sequence ordering, short codes, descriptions, and real-time computed product counts. It incorporates dual-layer validation (`_sql_constraints` and `@api.constrains` for case-insensitive uniqueness), provides ergonomic Tree/Form/Search views with embedded product sub-grids and stat-button navigation, configures Role-Based Access Control (RBAC), and loads immutable seed categories.

---

## Technical Context

**Language/Version**: Python 3.10+ (adhering to PEP 8 standards).

**Primary Dependencies**: Odoo Community Framework (v16.0 / v17.0 / v18.0) Core ORM & Web Client.

**Storage**: PostgreSQL 15 / 16 Relational Database Engine.

**Testing**: `odoo.tests.common.TransactionCase` (Python automated test suite) & manual UI verification procedures (`docs/test-procedures/test-procedure-1.1.2.md`).

**Target Platform**: Containerized Linux environment (Docker Compose v2 orchestration).

**Project Type**: Odoo ERP Custom Addon Module (`Modulo_Odoo`).

**Performance Goals**: Category listings and computed product counting $< 50\text{ms}$; indexed search on `name` and `codigo`.

**Constraints**:
- Strict MVC file structure (`models/categoria.py`, `views/categoria_views.xml`, `data/categoria_data.xml`, `security/ir.model.access.csv`).
- All UI strings, menu labels, and validation error messages in Spanish.
- Seed data loading of 4 base categories (Pan, Pastel, Galleta, Bebida) with `noupdate="1"`.
- Cascading deletion protection (`ondelete='restrict'`) on related products.
- Zero hardcoded secrets in version control (ISO-27001 secret management).

**Scale/Scope**: 1 Odoo model, 3 XML view definitions, 1 window action, 1 menu item, 2 security group permissions, 4 seed categories.

---

## Constitution Check

*GATE: Evaluated against Constitution v1.1.0 before Phase 0 research and verified post Phase 1 design.*

| Principle / Rule | Compliance Status | Justification / Implementation Reference |
| :--- | :--- | :--- |
| **I. Odoo Modular Architecture & MVC Separation** | **PASS** | `panaderia.categoria` is isolated in `Modulo_Odoo/models/categoria.py`, UI in `Modulo_Odoo/views/categoria_views.xml`, and access rules in `Modulo_Odoo/security/ir.model.access.csv`. |
| **II. Atomic Sales-to-Inventory Synchronization** | **PASS** | Supplies classification metadata required for product catalog (`SPEC-1.1.1`), inventory alerts (`SPEC-1.2.1`), and grouped sales reports (`SPEC-5.1.1`). |
| **III. Proactive Stock Alerting & Data Integrity** | **PASS** | Enforces `@api.constrains` for case-insensitive uniqueness and `_sql_constraints` on `name` and `codigo`. |
| **IV. Spec-Driven Verification & Test Procedures** | **PASS** | Full traceability to `SPEC-1.1.2` and requirement for `docs/test-procedures/test-procedure-1.1.2.md`. |
| **V. Operational Usability & Express Standards** | **PASS** | Tree and Form views include computed product counters, smart button navigation, sequence handles, and clear search filters in Spanish. |
| **VI. Deterministic Local Docker Provisioning** | **PASS** | Addon live-mounted at `/mnt/extra-addons/panaderia`, zero host pollution, one-command execution via `docker compose`. |

---

## Project Structure

### Documentation (this feature)

```text
specs/1-inventory/1.1-product-catalog/1.1.2-product-categories/
├── spec.md                          # Feature specification
├── plan.md                          # Implementation plan (this file)
├── data-model.md                    # Phase 1 data model & validation invariants
├── quickstart.md                    # Phase 1 quickstart & verification guide
├── tasks.md                         # Task breakdown & progress tracking
└── checklists/
    └── requirements.md              # Quality & requirements checklist
```

### Source Code (repository root layout)

```text
Modulo_Odoo/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── categoria.py
│   └── producto.py
├── views/
│   ├── categoria_views.xml
│   └── producto_views.xml
├── data/
│   └── categoria_data.xml
├── security/
│   └── ir.model.access.csv
└── tests/
    ├── __init__.py
    └── test_categoria.py
```

**Structure Decision**: Standard Odoo module architecture, keeping category logic cleanly separated in `categoria.py`, `categoria_views.xml`, `categoria_data.xml`, and `test_categoria.py`.

---

## Complexity Tracking

| Aspect | Architectural Choice | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| **Taxonomy Structure** | Flat 1-level category model | Deep hierarchical parent-child trees add unnecessary navigational friction for basic bakery retail operations. |
| **Validation** | Dual `@api.constrains` (case-insensitive) + `_sql_constraints` | SQL-only allows subtle case duplicate discrepancies ('pan' vs 'Pan'); UI-only fails during RPC imports. |
