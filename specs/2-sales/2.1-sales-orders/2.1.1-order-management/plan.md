# Implementation Plan: Registro y Proceso de Ventas Esencial

**Branch**: `2.1.1-order-management` | **Date**: 2026-09-30 | **Spec**: [`specs/2-sales/2.1-sales-orders/2.1.1-order-management/spec.md`](file:///c:/Users/Inspiron/Desktop/des-panaderia-erp/specs/2-sales/2.1-sales-orders/2.1.1-order-management/spec.md)

**Input**: Feature specification from `/specs/2-sales/2.1-sales-orders/2.1.1-order-management/spec.md`

---

## Summary

Implement the Sales Order Management module (`panaderia.venta` and `panaderia.venta.linea`) for Panadería "Delicias Dulces" ERP. The module enables shop cashiers to create counter sales orders with multiple product line items, dynamically autocompletes list prices, reactively computes line subtotals and overall order totals, manages the order lifecycle (`draft` $\to$ `confirmed` / `cancelled`), atomically validates and decrements physical inventory stock from `panaderia.producto`, updates historical customer purchase volume on `res.partner`, and automatically issues a linked pending invoice (`panaderia.factura`).

---

## Technical Context

**Language/Version**: Python 3.10+ (adhering strictly to PEP 8 standards).

**Primary Dependencies**: Odoo Community Framework (v16.0) Core ORM & Web Client.

**Storage**: PostgreSQL 15 Relational Database Engine.

**Testing**: `odoo.tests.common.TransactionCase` (Python automated test suite) & manual UI verification procedure (`docs/test-procedures/test-procedure-2.1.1.md`).

**Target Platform**: Containerized Linux environment (Docker Compose v2 orchestration, `panaderia_odoo_web` & `panaderia_odoo_db`).

**Project Type**: Odoo ERP Custom Addon Module (`Modulo_Odoo`).

**Performance Goals**: Subtotal/Total computation latency $< 50\text{ms}$; atomic order confirmation transaction execution $< 200\text{ms}$; zero unindexed queries on `name`, `cliente_id`, and `fecha`.

**Constraints**:
- Strict MVC file structure (`models/venta.py`, `views/venta_views.xml`, `data/venta_sequence.xml`, `security/ir.model.access.csv`).
- All UI strings, menu labels, and validation error messages must be in Spanish.
- Domain rules: positive quantities (`cantidad > 0.0`), non-negative prices (`precio_unitario >= 0.0`).
- Strict post-confirmation immutability: confirmed orders cannot have lines, quantities, or clients altered (`UserError` on tampering).
- Atomic stock reduction: insufficient stock aborts the confirmation transaction completely.

**Scale/Scope**: 2 Odoo models (`panaderia.venta`, `panaderia.venta.linea`), 1 sequential numbering record (`VEN-XXXX`), 3 XML view definitions (form, tree, search), 1 window action, 2 menu entries, 4 security group permissions.

---

## Constitution Check

*GATE: Evaluated against Constitution v1.1.0 before Phase 0 research and verified post Phase 1 design.*

| Principle / Rule | Compliance Status | Justification / Implementation Reference |
| :--- | :--- | :--- |
| **I. Odoo Modular Architecture & MVC Separation** | **PASS** | `panaderia.venta` and `panaderia.venta.linea` encapsulated cleanly in `Modulo_Odoo/models/venta.py`, UI declarations in `Modulo_Odoo/views/venta_views.xml`, sequence in `Modulo_Odoo/data/venta_sequence.xml`, and security access in `Modulo_Odoo/security/ir.model.access.csv`. |
| **II. Atomic Sales-to-Inventory Synchronization** | **PASS** | `action_confirm()` executes as a single atomic transaction: checks and decrements `cantidad_disponible` on `producto_id`, updates `total_compras_panaderia` on `cliente_id`, generates linked `panaderia.factura`, and locks state to `confirmed`. Insufficient stock triggers `ValidationError` and rolls back all changes. |
| **III. Proactive Stock Alerting & Data Integrity** | **PASS** | Validates inventory availability before confirmation; enforces `@api.constrains` for positive quantities and non-negative prices; cascades line deletions on draft orders. |
| **IV. Spec-Driven Verification & Traceable Test Procedures** | **PASS** | Derived 1:1 from `SPEC-2.1.1` Acceptance Criteria; accompanied by automated ORM test suite (`tests/test_venta.py`) and manual verification guide (`quickstart.md` / `docs/test-procedures/test-procedure-2.1.1.md`). |
| **V. Operational Usability & Express Standards** | **PASS** | Form view optimized for counter cashiers with inline editable line grid, automatic price lookup (`@api.onchange`), prominent monetary total footer, and intuitive statusbar workflow. |
| **VI. Deterministic Local Docker Provisioning & Environment Parity** | **PASS** | Addon live-mounted at `/mnt/extra-addons/panaderia`, hot-reloaded via `scripts/docker-restart.ps1 -Upgrade`, and evaluated inside containerized test runner with zero host footprint. |

---

## Project Structure

### Documentation (this feature)

```text
specs/2-sales/2.1-sales-orders/2.1.1-order-management/
├── spec.md                       # Feature specification (SPEC-2.1.1)
├── plan.md                       # Implementation plan (this file)
├── research.md                   # Phase 0 research findings & architectural decisions
├── data-model.md                 # Phase 1 data model & relational specifications
├── quickstart.md                 # Phase 1 quickstart & manual validation scenarios
├── contracts/                    # Phase 1 formal contracts
│   ├── venta-orm-contract.md     # ORM methods, decorators, and security permissions
│   └── venta-views-contract.md   # XML views, actions, and menu declarations
└── checklists/
    └── requirements.md           # Specification quality checklist
```

### Source Code (repository root layout)

```text
Modulo_Odoo/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── categoria.py
│   ├── producto.py
│   └── venta.py                  # New: panaderia.venta & panaderia.venta.linea
├── views/
│   ├── categoria_views.xml
│   ├── producto_views.xml
│   └── venta_views.xml           # New: Tree, Form & Search views for sales
├── data/
│   ├── categoria_data.xml
│   ├── producto_data.xml
│   └── venta_sequence.xml        # New: ir.sequence for VEN-XXXX numbering
├── security/
│   ├── security.xml
│   └── ir.model.access.csv       # Updated: Access rights for sales models
└── tests/
    ├── __init__.py
    ├── test_producto.py
    └── test_venta.py             # New: Unit tests for sales operations
```

**Structure Decision**: Fully adheres to Constitution Section 5 by implementing all sales logic, views, sequences, and security rules inside `Modulo_Odoo/` without modifying core Odoo modules.

---

## Complexity Tracking

> **Constitution Check passed with zero violations. No unjustified complexity introduced.**

| Aspect | Architectural Choice | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| **Model Scope** | Custom `panaderia.venta` / `linea` | Extending Odoo core `sale.order` brings bloated dependencies (quotation expirations, complex tax engines, multi-currency, shipping logistics) that clutter bakery counter operations. |
| **Sequence Timing** | Generated on `action_confirm()` | Generating on `create()` burns sequence numbers for abandoned or draft sales, violating sequential fiscal integrity. |
| **Immutability** | Dual ORM (`write`/`unlink`) + XML readonly | XML-only attributes can be bypassed via RPC/script calls; ORM-only lacks intuitive visual cues in the web client. |
| **Cross-Module Link** | Atomic ORM confirmation handler | Asynchronous or background workers risk race conditions and delay immediate ticket generation required at bakery cash registers. |
