# Implementation Plan: Gestión de Catálogo de Productos

**Branch**: `1.1.1-product-management` | **Date**: 2026-09-29 | **Spec**: [`specs/1-inventory/1.1-product-catalog/1.1.1-product-management/spec.md`](file:///d:/UDB/CICLO-10-2026/DES/LAB/Desafio%203/des-panaderia-erp/specs/1-inventory/1.1-product-catalog/1.1.1-product-management/spec.md)

**Input**: Feature specification from `/specs/1-inventory/1.1-product-catalog/1.1.1-product-management/spec.md`

---

## Summary

Implement the foundational Product Catalog Management module (`panaderia.producto`) for Panadería "Delicias Dulces" ERP. The module encapsulates commercial product records (name, SKU, category, cost, sale price, margin, active status, description) within an idiomatic Odoo Model-View-Controller architecture. It enforces dual-layer validation (`_sql_constraints` and `@api.constrains`), provides structured Tree/Form/Search XML views, configures granular Role-Based Access Control (RBAC), and provides seed data for instant verification.

---

## Technical Context

**Language/Version**: Python 3.10+ (adhering to PEP 8 standards).

**Primary Dependencies**: Odoo Community Framework (v16.0 / v17.0 / v18.0) Core ORM & Web Client.

**Storage**: PostgreSQL 15 / 16 Relational Database Engine.

**Testing**: `odoo.tests.common.TransactionCase` (Python automated test suite) & manual UI verification procedures (`docs/test-procedures/test-procedure-1.1.1.md`).

**Target Platform**: Containerized Linux environment (Docker Compose v2 orchestration).

**Project Type**: Odoo ERP Custom Addon Module (`Modulo_Odoo`).

**Performance Goals**: Catalog listing and search response times $< 100\text{ms}$ for standard bakery catalog operations; zero unindexed queries on `name` or `codigo`.

**Constraints**:
- Strict MVC file structure (`models/producto.py`, `views/producto_views.xml`, `security/ir.model.access.csv`).
- All UI strings, menu labels, and validation error messages must be in Spanish.
- Non-negative costs (`costo >= 0.0`), positive sale prices (`precio_venta > 0.0`), unique product names.
- Zero hardcoded secrets in version control (ISO-27001 secret management).

**Scale/Scope**: 1 Odoo model, 3 XML view definitions, 1 window action, 3 menu items, 2 security group permissions, 4 seed products.

---

## Constitution Check

*GATE: Evaluated against Constitution v1.1.0 before Phase 0 research and verified post Phase 1 design.*

| Principle / Rule | Compliance Status | Justification / Implementation Reference |
| :--- | :--- | :--- |
| **I. Odoo Modular Architecture & MVC Separation** | **PASS** | `panaderia.producto` is isolated in `Modulo_Odoo/models/producto.py`, UI in `Modulo_Odoo/views/producto_views.xml`, and access rules in `Modulo_Odoo/security/ir.model.access.csv`. |
| **II. Atomic Sales-to-Inventory Synchronization** | **PASS** | Provides master product entity with unit prices and costs required for sales lines (`SPEC-2.1.1`) and stock movements (`SPEC-1.2.1`). |
| **III. Proactive Stock Alerting & Data Integrity** | **PASS** | Enforces `@api.constrains` for `precio_venta > 0` and `costo >= 0`, plus SQL unique constraint on `name`. |
| **IV. Spec-Driven Verification & Test Procedures** | **PASS** | Full traceability to `SPEC-1.1.1` and requirement for `docs/test-procedures/test-procedure-1.1.1.md`. |
| **V. Operational Usability & Express Standards** | **PASS** | Form and Tree views include calculated margins, monetary formatting, and clear search filters in Spanish. |
| **VI. Deterministic Local Docker Provisioning** | **PASS** | Addon live-mounted at `/mnt/extra-addons/panaderia`, zero host pollution, one-command execution via `docker compose`. |

---

## Project Structure

### Documentation (this feature)

```text
specs/1-inventory/1.1-product-catalog/1.1.1-product-management/
├── spec.md                          # Feature specification
├── plan.md                          # Implementation plan (this file)
├── research.md                      # Phase 0 research findings & technical decisions
├── data-model.md                    # Phase 1 data model & validation invariants
├── quickstart.md                    # Phase 1 quickstart & verification guide
├── contracts/                       # Phase 1 contracts
│   ├── producto-orm-contract.md     # ORM methods, decorators, and security permissions
│   └── producto-views-contract.md   # XML views, window actions, and menu hierarchy
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
│   └── producto.py
├── views/
│   └── producto_views.xml
├── data/
│   └── producto_data.xml
├── security/
│   └── ir.model.access.csv
└── tests/
    ├── __init__.py
    └── test_producto.py
```

**Structure Decision**: Adopts the standardized Odoo modular structure specified in Constitution Section 5, placing all product management logic inside `Modulo_Odoo/` with zero modifications to base Odoo core modules.

---

## Complexity Tracking

> **Constitution Check passed with zero violations. No unjustified complexity introduced.**

| Aspect | Architectural Choice | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| **Model Selection** | Standalone `panaderia.producto` | `product.template` is overly bloated for basic bakery POS requirements. |
| **Validation** | Dual `@api.constrains` + `_sql_constraints` | Client-only validation allows corrupt data through RPC; SQL-only gives unfriendly error traces. |
