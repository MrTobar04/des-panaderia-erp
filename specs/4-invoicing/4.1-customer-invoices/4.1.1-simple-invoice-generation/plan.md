# Implementation Plan: Generación de Facturas Simples

**Branch**: `4.1.1-simple-invoice-generation` | **Date**: 2026-09-30 | **Spec**: [`specs/4-invoicing/4.1-customer-invoices/4.1.1-simple-invoice-generation/spec.md`](spec.md)

**Input**: Feature specification from `/specs/4-invoicing/4.1-customer-invoices/4.1.1-simple-invoice-generation/spec.md`

---

## Summary

Implement the Simple Invoice Generation module (`panaderia.factura`) for Panadería "Delicias Dulces" ERP. The module completes the core financial and retail billing lifecycle by automatically generating receipts from confirmed sales orders (`SPEC-2.1.1`), assigning gapless correlative numbering (`FAC-XXXX`) through an Odoo sequence, providing single-click cashier payment settlement (`pending` $\to$ `paid`) with automatic payment timestamp recording, supporting multiple payment methods (cash, card, transfer), enforcing financial immutability on paid receipts, enabling seamless bidirectional navigation with sales orders, and exposing intuitive tree/form/search views with status badges and daily filters.

---

## Technical Context

**Language/Version**: Python 3.10+ (adhering strictly to PEP 8 standards).

**Primary Dependencies**: Odoo Community Framework (v16.0) Core ORM & Web Client.

**Storage**: PostgreSQL 15 Relational Database Engine.

**Testing**: `odoo.tests.common.TransactionCase` (Python automated test suite `tests/test_factura.py`) & manual UI verification procedure (`docs/test-procedures/test-procedure-4.1.1.md`).

**Target Platform**: Containerized Linux environment (Docker Compose v2 orchestration, `panaderia_odoo_web` & `panaderia_odoo_db`).

**Project Type**: Odoo ERP Custom Addon Module (`Modulo_Odoo`).

**Performance Goals**: Sequence assignment $< 15\text{ms}$; payment registration transaction $< 50\text{ms}$; invoice list view loading $< 100\text{ms}$; zero unindexed queries on `name`, `cliente_id`, `venta_id`, and `state`.

**Constraints**:
- Strict MVC file structure (`models/factura.py`, `views/factura_views.xml`, `data/factura_sequence.xml`, `security/ir.model.access.csv`).
- All UI strings, menu labels, field descriptions, and validation messages in Spanish.
- Non-negative financial amounts (`monto_total >= 0.0`).
- Strict post-payment immutability: paid invoices cannot have financial amounts, customer, or sales links altered (`UserError` on tampering).
- Deletion protection: invoices in `paid` state cannot be deleted (`UserError` on `unlink`).
- Exactly one active invoice per sales order.

**Scale/Scope**: 1 Odoo model (`panaderia.factura`), 1 sequential numbering record (`FAC-XXXX`), 3 XML view definitions (form, tree, search), 1 window action, 2 menu entries, 2 security group permissions.

---

## Constitution Check

*GATE: Evaluated against Constitution v1.1.0 before Phase 0 research and verified post Phase 1 design.*

| Principle / Rule | Compliance Status | Justification / Implementation Reference |
| :--- | :--- | :--- |
| **I. Odoo Modular Architecture & MVC Separation** | **PASS** | `panaderia.factura` encapsulated in `Modulo_Odoo/models/factura.py`, views in `Modulo_Odoo/views/factura_views.xml`, sequence in `Modulo_Odoo/data/factura_sequence.xml`, and security access in `Modulo_Odoo/security/ir.model.access.csv`. |
| **II. Atomic Sales-to-Inventory Synchronization** | **PASS** | Tightly coupled with `SPEC-2.1.1`: when sales order confirms, it automatically creates a linked `panaderia.factura` in `pending` state with sequence `FAC-XXXX`. |
| **III. Proactive Stock Alerting & Data Integrity** | **PASS** | Financial integrity guaranteed via `@api.constrains('monto_total')` ($\ge 0.0$), anti-tampering guards on `write()` for paid records, deletion blocking in `unlink()`, and duplicate invoice prevention for sales orders. |
| **IV. Spec-Driven Verification & Traceable Test Procedures** | **PASS** | Derived 1:1 from `SPEC-4.1.1` Acceptance Criteria; accompanied by automated ORM test suite (`tests/test_factura.py`) and manual verification guide (`quickstart.md` / `docs/test-procedures/test-procedure-4.1.1.md`). |
| **V. Operational Usability & Express Standards** | **PASS** | Ergonomic cashier UI with prominent "Registrar Pago" button, statusbar workflow (`pending` $\to$ `paid`), Smart Button for instant navigation to sales order, and tree badges. |
| **VI. Deterministic Local Docker Provisioning & Environment Parity** | **PASS** | Addon live-mounted at `/mnt/extra-addons/panaderia`, hot-reloaded via `scripts/docker-restart.ps1 -Upgrade`, and evaluated inside containerized test runner with zero host footprint. |

---

## Project Structure

### Documentation (this feature)

```text
specs/4-invoicing/4.1-customer-invoices/4.1.1-simple-invoice-generation/
├── spec.md                         # Feature specification (SPEC-4.1.1)
├── plan.md                         # Implementation plan (this file)
├── research.md                     # Phase 0 research findings & architectural decisions
├── data-model.md                   # Phase 1 data model & relational specifications
├── quickstart.md                   # Phase 1 quickstart & manual validation scenarios
├── contracts/                      # Phase 1 formal contracts
│   ├── factura-orm-contract.md     # ORM methods, decorators, and security permissions
│   └── factura-views-contract.md   # XML views, actions, and menu declarations
└── checklists/
    └── requirements.md             # Specification quality checklist
```

### Source Code (repository root layout)

```text
Modulo_Odoo/
├── __init__.py
├── __manifest__.py                 # Updated: Registers data/factura_sequence.xml and views/factura_views.xml
├── models/
│   ├── __init__.py
│   ├── categoria.py
│   ├── producto.py
│   ├── venta.py
│   └── factura.py                  # Updated: panaderia.factura with sequence, constraints & immutability
├── views/
│   ├── categoria_views.xml
│   ├── producto_views.xml
│   ├── venta_views.xml
│   └── factura_views.xml           # New: Form, Tree & Search views for facturas
├── data/
│   ├── categoria_data.xml
│   ├── producto_data.xml
│   ├── venta_sequence.xml
│   └── factura_sequence.xml        # New: ir.sequence for FAC-XXXX numbering
├── security/
│   ├── security.xml
│   └── ir.model.access.csv         # Verified: Access rights for panaderia.factura
└── tests/
    ├── __init__.py                 # Updated: imports test_factura
    ├── test_producto.py
    ├── test_venta.py
    └── test_factura.py             # New: Unit tests for invoice lifecycle & payment
```

**Structure Decision**: The implementation follows the standard single-module Odoo Addon layout (`Modulo_Odoo/`). It adheres strictly to MVC separation by encapsulating Python logic in `models/factura.py`, sequence definitions in `data/factura_sequence.xml`, UI definitions in `views/factura_views.xml`, and automated test coverage in `tests/test_factura.py`.

---

## Complexity Tracking

> **Evaluated against Constitution Check: No architectural violations identified.**

| Violation | Why Needed | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| *None* | N/A | N/A |

---

## Post-Design Verification

All design artifacts (Phases 0 and 1) have been compiled:
- [research.md](research.md): Clarified sequence numbering, payment registration, and immutability rules.
- [data-model.md](data-model.md): Detailed schema for `panaderia.factura`, constraints, state machine, and sequence.
- [contracts/factura-orm-contract.md](contracts/factura-orm-contract.md): Defined signatures, pre/postconditions, and security permissions.
- [contracts/factura-views-contract.md](contracts/factura-views-contract.md): Specified XML form/tree/search views and menu items.
- [quickstart.md](quickstart.md): Defined verification commands and manual cashier journeys.
