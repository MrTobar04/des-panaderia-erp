# Implementation Plan: Extensión y Registro de Clientes de Panadería

**Branch**: `3.1.1-bakery-customer-management` | **Date**: 2026-09-30 | **Spec**: [`specs/3-customers/3.1-partner-extension/3.1.1-bakery-customer-management/spec.md`](file:///d:/UDB/CICLO-10-2026/DES/LAB/Desafio%203/des-panaderia-erp/specs/3-customers/3.1-partner-extension/3.1.1-bakery-customer-management/spec.md)

**Input**: Feature specification from `/specs/3-customers/3.1-partner-extension/3.1.1-bakery-customer-management/spec.md`

---

## Summary

Extend Odoo's native partner model (`res.partner`) for the bakery "Delicias Dulces" to differentiate specialized bakery customers from general contacts and vendors. The extension captures store registration dates, automatically aggregates historical purchases from confirmed bakery sales orders (`panaderia.venta`), stores customer taste/dietary preferences and allergy notes, and provides tailored Views, Action Windows, Search Filters, and Seed Data (including a default walk-in customer).

---

## Technical Context

**Language/Version**: Python 3.10+ (adhering to PEP 8 standards).

**Primary Dependencies**: Odoo Community Framework (v16.0 / v17.0 / v18.0) Core ORM & Web Client (`base` addon).

**Storage**: PostgreSQL 15 / 16 Relational Database Engine (`res_partner` table extension).

**Testing**: `odoo.tests.common.TransactionCase` (Python automated test suite) & manual UI verification procedures (`docs/test-procedures/test-procedure-3.1.1.md`).

**Target Platform**: Containerized Linux environment (Docker Compose v2 orchestration).

**Project Type**: Odoo ERP Custom Addon Module (`Modulo_Odoo`).

**Performance Goals**: Fast customer list queries $< 50\text{ms}$; stored computed field `total_compras_panaderia` for instant retrieval during POS/cashier checkout without runtime aggregation overhead.

**Constraints**:
- Strict MVC file structure (`models/cliente.py`, `views/cliente_views.xml`, `data/cliente_data.xml`).
- Non-destructive inheritance (`_inherit = 'res.partner'`), preserving all standard Odoo partner behavior.
- All UI strings, menu labels, and validation error messages in Spanish.
- Seed data loading of default "Cliente General / Mostrador" with `noupdate="1"`.
- Zero hardcoded secrets in version control (ISO-27001 secret management).

**Scale/Scope**: 1 extended model, 3 XML view definitions (form notebook extension, list view, search filter), 1 window action, 2 menu entries, 2 seed records.

---

## Constitution Check

*GATE: Evaluated against Constitution v1.1.0 before Phase 0 research and verified post Phase 1 design.*

| Principle / Rule | Compliance Status | Justification / Implementation Reference |
| :--- | :--- | :--- |
| **I. Odoo Modular Architecture & MVC Separation** | **PASS** | `res.partner` extension in `Modulo_Odoo/models/cliente.py`, UI extensions in `Modulo_Odoo/views/cliente_views.xml`, seed data in `Modulo_Odoo/data/cliente_data.xml`. |
| **II. Atomic Sales-to-Inventory Synchronization** | **PASS** | Customer cumulative purchases react automatically to confirmed sales orders (`panaderia.venta`) via `@api.depends`. |
| **III. Proactive Stock Alerting & Data Integrity** | **PASS** | `total_compras_panaderia` is stored and computed from confirmed transactions, preventing arbitrary manual tampering. |
| **IV. Spec-Driven Verification & Test Procedures** | **PASS** | Full traceability to `SPEC-3.1.1` and deliverable `docs/test-procedures/test-procedure-3.1.1.md`. |
| **V. Operational Usability & Express Standards** | **PASS** | Direct access via "Panadería $\to$ Clientes", default flag context, and dedicated "Datos de Panadería" form notebook tab. |
| **VI. Deterministic Local Docker Provisioning** | **PASS** | Addon live-mounted at `/mnt/extra-addons/panaderia`, zero host pollution, one-command execution via `docker compose`. |

---

## Project Structure

### Documentation (this feature)

```text
specs/3-customers/3.1-partner-extension/3.1.1-bakery-customer-management/
├── spec.md                          # Feature specification
├── plan.md                          # Implementation plan (this file)
├── data-model.md                    # Data model & validation invariants
├── quickstart.md                    # Quickstart & verification guide
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
│   ├── cliente.py                   # res.partner extension
│   └── venta.py                     # panaderia.venta integration
├── views/
│   └── cliente_views.xml            # Form, Tree, Search & Actions
├── data/
│   └── cliente_data.xml             # Seed customers
└── tests/
    ├── __init__.py
    └── test_cliente.py              # Automated test cases
```

**Structure Decision**: Standard Odoo extension pattern using `_inherit = 'res.partner'`, maintaining modularity and isolation.

---

## Complexity Tracking

| Aspect | Architectural Choice | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| **Partner Model** | Inherit standard `res.partner` via `_inherit` | Creating a standalone `panaderia.cliente` model duplicates contact fields (phone, email, address) and breaks native invoicing compatibility (`SPEC-4.1.1`). |
| **Purchase Aggregation** | Computed stored field with `@api.depends('venta_panaderia_ids.state', 'venta_panaderia_ids.total')` | Calculating on the fly in the UI slows down tree view rendering when thousands of sales exist; storing without compute causes drift on cancellations. |
