# Implementation Plan: Reportes Operativos Diarios y Alertas de Stock

**Branch**: `5.1.1-daily-sales-and-stock-reports` | **Date**: 2026-09-30 | **Spec**: [`specs/5-reports/5.1-operational-reports/5.1.1-daily-sales-and-stock-reports/spec.md`](spec.md)

**Input**: Feature specification from `specs/5-reports/5.1-operational-reports/5.1.1-daily-sales-and-stock-reports/spec.md`

---

## Summary

Implement the executive and operational reporting module (`panaderia.reporte.ventas`, `panaderia.reporte.diario.wizard`) for Panadería "Delicias Dulces" ERP. The module aggregates and synthesizes information from Inventory (`SPEC-1.1.1`, `SPEC-1.2.1`), Sales (`SPEC-2.1.1`), Customers (`SPEC-3.1.1`), and Invoicing (`SPEC-4.1.1`) to deliver 3 critical operational capabilities:
1. **Daily Sales Analytics**: Real-time sales metrics (total revenue, confirmed order count, category breakdown) via interactive Pivot, Graph, and List views.
2. **Top Selling Products (Demand Ranking)**: Visual bar charts and ranking tables sorting products by units sold and dollar amounts.
3. **Low Stock Replenishment Alerts**: Filtered grid listing all products where `cantidad_disponible <= stock_minimo` with direct replenishment shortcut.
4. **QWeb PDF Daily Operational Summary**: Single-page printable document summarizing day KPIs, top products, and low stock warnings.

---

## Technical Context

**Language/Version**: Python 3.10+ (PEP 8).  
**Primary Dependencies**: Odoo Community Framework (v16.0) Core ORM, Graph, Pivot & QWeb.  
**Storage**: PostgreSQL 15 Relational Database Engine (SQL View pattern).  
**Testing**: `odoo.tests.common.TransactionCase` (`tests/test_reporte.py`) & manual procedure (`docs/test-procedures/test-procedure-5.1.1.md`).  
**Target Platform**: Containerized Linux environment (`panaderia_odoo_web`, `panaderia_odoo_db`).  
**Project Type**: Odoo ERP Custom Addon Module (`Modulo_Odoo`).

---

## Constitution Check

*GATE: Evaluated against Constitution v1.1.0.*

| Principle / Rule | Compliance Status | Justification / Implementation Reference |
| :--- | :--- | :--- |
| **I. Odoo Modular Architecture & MVC Separation** | **PASS** | `panaderia.reporte.ventas` in `models/reporte_panaderia.py`, views in `views/reporte_views.xml`, PDF template in `report/reporte_diario_template.xml`, ACL in `security/ir.model.access.csv`. |
| **II. Atomic Sales-to-Inventory Synchronization** | **PASS** | View strictly aggregates confirmed sales (`v.state = 'confirmed'`), reflecting current inventory transactions accurately. |
| **III. Proactive Stock Alerting & Data Integrity** | **PASS** | Proactive low stock alerts surface products with `cantidad_disponible <= stock_minimo` in real-time. |
| **IV. Spec-Driven Verification & Traceable Test Procedures** | **PASS** | Mapped 1:1 to Acceptance Criteria Scenarios 1, 2, and 3; backed by automated test suite (`tests/test_reporte.py`) and test procedure (`docs/test-procedures/test-procedure-5.1.1.md`). |
| **V. Operational Usability & Express Standards** | **PASS** | Intuitive menus under "Panadería $\to$ Reportes", pre-filtered views for today's sales, clear warning badges for low stock, and one-click PDF printing. |
| **VI. Deterministic Local Docker Provisioning** | **PASS** | Fully executable and verified inside Docker test environment. |

---

## Project Structure

```text
specs/5-reports/5.1-operational-reports/5.1.1-daily-sales-and-stock-reports/
├── spec.md                         # Feature specification (SPEC-5.1.1)
├── plan.md                         # Implementation plan (this file)
├── research.md                     # Phase 0 research findings & technical decisions
├── data-model.md                   # Phase 1 data model & relational specifications
├── quickstart.md                   # Phase 1 quickstart & verification guide
├── use-case-5.1.1.md               # Phase 1 use case scenarios
├── contracts/                      # Formal contracts
│   ├── reporte-orm-contract.md     # ORM schema, SQL view definition & ACL
│   └── reporte-views-contract.md   # Views, actions and menu declarations
└── checklists/
    └── requirements.md             # Specification quality checklist
```

```text
Modulo_Odoo/
├── __manifest__.py                 # Updated: Registers views/reporte_views.xml & report/reporte_diario_template.xml
├── models/
│   ├── __init__.py                 # Updated: imports reporte_panaderia
│   └── reporte_panaderia.py        # New: panaderia.reporte.ventas, wizard & QWeb parser
├── views/
│   └── reporte_views.xml           # New: Pivot, Graph, Tree & Search views + menus
├── report/
│   └── reporte_diario_template.xml # New: QWeb report action & PDF template
├── security/
│   └── ir.model.access.csv         # Updated: ACL for report view & wizard
└── tests/
    ├── __init__.py                 # Updated: imports test_reporte
    └── test_reporte.py             # New: Automated unit tests for reports & stock alerts
```
