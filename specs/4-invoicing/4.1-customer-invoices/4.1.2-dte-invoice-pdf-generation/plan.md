# Implementation Plan: Generación de Factura PDF DTE El Salvador

**Branch**: `4.1.2-dte-invoice-pdf-generation` | **Date**: 2026-10-01 | **Spec**: [`specs/4-invoicing/4.1-customer-invoices/4.1.2-dte-invoice-pdf-generation/spec.md`](spec.md)

**Input**: Feature specification from `/specs/4-invoicing/4.1-customer-invoices/4.1.2-dte-invoice-pdf-generation/spec.md`

---

## Summary

Implement the official Electronic Tax Invoice PDF generation (Documento Tributario Electrónico - DTE Factura Tipo 01 El Salvador) inside Odoo using the native QWeb Report Engine. The feature incorporates the bakery's official visual identity ("Delicias Dulces - PANADERÍA" logo), populates official Ministry of Hacienda identifiers (canonical UUID v4 generation code, DTE-01 control number, 40-character reception stamp, dynamic QR validation barcode), computes amounts in Spanish words, and exposes immediate print actions from both invoice and sales order views upon process completion.

---

## Technical Context

**Language/Version**: Python 3.10+ (PEP 8 compliant, Odoo ORM methods).

**Primary Dependencies**: Odoo Community Framework (v16.0/v17.0) QWeb Report Engine & `wkhtmltopdf` (integrated in container).

**Storage**: PostgreSQL 15 Relational Database (`panaderia.factura` extended fields, `res.partner` fiscal fields).

**Testing**: `odoo.tests.common.TransactionCase` automated unit tests (`tests/test_factura_dte.py`) & manual UI verification guide (`quickstart.md`).

**Target Platform**: Containerized Linux environment (Docker Compose v2 orchestration: `panaderia_odoo_web` & `panaderia_odoo_db`).

**Project Type**: Odoo ERP Custom Addon Module (`Modulo_Odoo`).

**Performance Goals**:
- PDF report rendering and stream output $< 2.0\text{s}$.
- Automatic DTE identifier generation on invoice creation $< 20\text{ms}$.
- Pure Python amount-to-words conversion $< 5\text{ms}$.

**Constraints**:
- Strictly native Odoo QWeb report (`report_type="qweb-pdf"`).
- Zero external Python pip dependencies; zero host machine pollution.
- Static assets stored under `Modulo_Odoo/static/src/img/logo_delicias_dulces.png`.
- Visual layout must replicate the exact box layout, tables, and typography of the El Salvador Hacienda DTE standard provided in the sample PDF.
- All monetary amounts displayed in USD with proper currency symbol ($) and cents formatting.

**Scale/Scope**:
- 1 extended Odoo model (`panaderia.factura`).
- 1 extended customer model (`res.partner`).
- 1 new QWeb XML report template (`Modulo_Odoo/report/reporte_factura_dte_template.xml`).
- 1 report action declaration (`ir.actions.report`).
- 2 updated view declarations (`views/factura_views.xml`, `views/venta_views.xml`).
- 1 static logo asset (`static/src/img/logo_delicias_dulces.png`).

---

## Constitution Check

*GATE: Evaluated against Constitution v1.1.0 before Phase 0 research and verified post Phase 1 design.*

| Principle / Rule | Compliance Status | Justification / Implementation Reference |
| :--- | :--- | :--- |
| **I. Odoo Modular Architecture & MVC Separation** | **PASS** | Logic in `models/factura.py`, views in `views/factura_views.xml` & `views/venta_views.xml`, report definitions in `report/reporte_factura_dte_template.xml`, assets in `static/src/img/`. |
| **II. Atomic Sales-to-Inventory Synchronization** | **PASS** | When sales order confirms, it creates the invoice with pre-populated DTE keys ready for immediate rendering without altering inventory deduction atomicity. |
| **III. Proactive Stock Alerting & Data Integrity** | **PASS** | DTE identifiers (`codigo_generacion`, `numero_control`) are immutable once written; calculations strictly rounded to 2 decimal places. |
| **IV. Spec-Driven Verification & Traceable Test Procedures** | **PASS** | Directly derives from `SPEC-4.1.2`, documented with `quickstart.md` and automated tests. |
| **V. Operational Usability & Express Standards** | **PASS** | Direct single-click "Imprimir Factura DTE" action on sales order and invoice form headers. |
| **VI. Deterministic Local Docker Provisioning & Environment Parity** | **PASS** | Operates inside the existing container stack using `wkhtmltopdf` native binaries. No new container layers or packages required. |

---

## Project Structure

### Documentation (this feature)

```text
specs/4-invoicing/4.1-customer-invoices/4.1.2-dte-invoice-pdf-generation/
├── spec.md              # Feature specification
├── plan.md              # This implementation plan
├── research.md          # Phase 0 architectural & technical decisions
├── data-model.md        # Phase 1 data model extensions
├── quickstart.md        # Phase 1 verification and testing guide
├── contracts/           # Phase 1 interface and QWeb contracts
│   └── report-contract.md
├── samples/             # User-provided sample assets and JSON
│   ├── factura_dte_ejemplo.pdf
│   ├── factura_dte_ejemplo.json
│   └── logo_delicias_dulces.png
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
Modulo_Odoo/
├── __manifest__.py                                # Updated with new report template
├── models/
│   ├── factura.py                                # Extended with DTE fields & helpers
│   ├── venta.py                                  # Extended with print invoice DTE action
│   └── cliente.py                                # Extended with DUI / NIT
├── views/
│   ├── factura_views.xml                         # Added print button and DTE fields
│   └── venta_views.xml                           # Added print DTE button
├── report/
│   ├── reporte_diario_template.xml               # Existing daily report
│   └── reporte_factura_dte_template.xml          # NEW QWeb DTE PDF template & action
├── static/
│   └── src/
│       └── img/
│           └── logo_delicias_dulces.png          # Bakery logo asset
└── tests/
    └── test_factura_dte.py                       # Automated unit tests for DTE & PDF
```

**Structure Decision**: Fully encapsulated within existing `Modulo_Odoo` addon following the established modular convention, registering the QWeb report in `report/` and the asset in `static/src/img/`.

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| *None* | No constitutional violations. Solution adheres strictly to native Odoo conventions. | N/A |
