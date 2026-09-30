# Phase 0: Outline & Research - Registro y Proceso de Ventas Esencial

**Feature**: `SPEC-2.1.1: Registro y Proceso de Ventas Esencial`  
**Branch / Directory**: `specs/2-sales/2.1-sales-orders/2.1.1-order-management`  
**Date**: 2026-09-30  
**Status**: Completed  

---

## 1. Executive Summary & Objective

This research document resolves all architectural decisions, design invariants, and technical trade-offs required to implement the Sales Order Management module (`panaderia.venta` and `panaderia.venta.linea`) for Panadería "Delicias Dulces" ERP. The module serves as the operational transaction engine connecting customer checkout (`SPEC-3.1.1`), product catalog pricing (`SPEC-1.1.1`), real-time stock decrement (`SPEC-1.2.1`), and simple invoice generation (`SPEC-4.1.1`).

---

## 2. Research Findings & Technical Decisions

### Decision 1: Relational Model Architecture & Header/Detail Decomposition
* **Decision**: Implement two decoupled, dedicated custom models inheriting directly from `models.Model`:
  1. `panaderia.venta`: Header model capturing order folio (`name`), customer (`cliente_id`), date (`fecha`), state (`state`), total amount (`total`), and invoice reference (`factura_id`).
  2. `panaderia.venta.linea`: Detail line model capturing product (`producto_id`), quantity (`cantidad`), unit price (`precio_unitario`), and computed line subtotal (`subtotal`).
  Linked via `linea_ids = fields.One2many('panaderia.venta.linea', 'venta_id', string='Líneas de Venta')` with `ondelete='cascade'` on the foreign key.
* **Rationale**:
  * Employs standard Odoo Header-Lines composite design pattern without the unnecessary overhead of standard `sale.order` / `sale.order.line` (which drag quotation expirations, tax matrices, shipping grids, analytic distributions, and multi-currency pricing).
  * Guarantees 100% compliance with Principle I (Odoo Modular Architecture & MVC Separation) and Principle V (Operational Usability & Express Standards for bakery counter checkout).
* **Alternatives Considered**:
  * *Option A: Extend core `sale.order` / `sale.order.line`*: Rejected because it activates complex delivery pipelines, procurement groups, and multiple configuration tiers that slow counter POS transactions and hinder automated evaluation.
  * *Option B: Single flat model with JSON/Text line storage*: Rejected because it violates relational database normalization, impedes SQL index lookups, and breaks Odoo ORM `@api.depends` aggregation.

---

### Decision 2: Inter-Module Integration & Dependency Decoupling Strategy
* **Decision**: 
  1. **Stock Decrement (`panaderia.producto`)**: In `action_confirm()`, verify and decrement `cantidad_disponible` on `producto_id`. To ensure cross-spec compatibility, define `cantidad_disponible` on `panaderia.producto` with default `0.0` if not already present, ensuring Scenario 2 BDD tests execute deterministically.
  2. **Customer Purchase History (`res.partner`)**: In `action_confirm()`, update `cliente_id.total_compras_panaderia` (or calculate via ORM search) to feed customer loyalty and operational reports (`SPEC-3.1.1`).
  3. **Automated Invoicing (`panaderia.factura`)**: Because Odoo's model registry validates `comodel_name` at startup, provide a baseline definition of `panaderia.factura` in `models/factura.py` (or ensure graceful creation of invoice records) to support `factura_id = fields.Many2one('panaderia.factura')` without causing `KeyError` runtime crashes.
* **Rationale**:
  * Principle II (Atomic Sales-to-Inventory Synchronization) mandates that confirming a sale must atomically deduct stock, update customer metrics, and generate an invoice.
  * Registering the comodel prevents registry load failure while establishing the exact schema contract needed for `SPEC-4.1.1`.
* **Alternatives Considered**:
  * *Option A: Soft foreign keys (storing invoice ID as integer)*: Rejected because it breaks Odoo form smart-buttons, relational integrity, and search navigation.
  * *Option B: Delaying invoice creation to an external cron*: Rejected because counter sales in a bakery require immediate invoice/ticket generation.

---

### Decision 3: Atomic Lifecycle State Machine & Immutability Rules
* **Decision**: Implement a 3-state workflow (`draft` $\to$ `confirmed`, with `cancelled` available from draft or manager authorization):
  * `draft` (Borrador): Default state upon creation. Fully editable. Allows adding, editing, and deleting order lines. Folio displays `Nuevo`.
  * `confirmed` (Confirmada): Triggered by button `action_confirm()`. Generates sequence `VEN-XXXX`, decrements product stock, creates invoice, updates customer metrics, and locks all order fields and lines as `readonly`.
  * `cancelled` (Cancelada): Triggered by button `action_cancel()`. Reverses stock decrement if previously confirmed, or simply archives/cancels the order.
* **Rationale**:
  * Guarantees fiscal and stock auditability. Once confirmed, cashiers cannot tamper with quantities, prices, or customer assignments.
  * Enforced at both UI level (`attrs="{'readonly': [('state', '!=', 'draft')]}"`) and ORM level (override `write()` and `unlink()` to block modifications when `state == 'confirmed'`).
* **Alternatives Considered**:
  * *Option A: UI-only readonly attributes*: Rejected because XML view attributes can be bypassed via RPC calls or developer mode.

---

### Decision 4: Reactive Calculation Architecture & UX Autocompletion
* **Decision**:
  1. Line subtotal: `@api.depends('cantidad', 'precio_unitario')` computes `subtotal = cantidad * precio_unitario` with `store=True`.
  2. Order total: `@api.depends('linea_ids.subtotal')` computes `total = sum(order.linea_ids.mapped('subtotal'))` with `store=True`.
  3. Price autocompletion: `@api.onchange('producto_id')` copies `producto_id.precio_venta` into `precio_unitario` immediately upon product selection in the web client, while allowing cashier price overrides if authorized.
* **Rationale**:
  * Storing computed fields in PostgreSQL enables instant tree view summing, SQL filtering (`total > 50`), and high-speed aggregation reports (`SPEC-5.1.1`).
  * `@api.onchange` provides snappy client-side responsiveness without round-trip database commits until the form is saved.
* **Alternatives Considered**:
  * *Option A: Non-stored compute fields*: Rejected because they prevent sorting and filtering in tree views and degrade performance during large sales list queries.

---

### Decision 5: Sequential Folio Generation (`ir.sequence`)
* **Decision**: Define a dedicated sequence record in `data/venta_sequence.xml`:
  * Code: `panaderia.venta.secuencia`
  * Name: `Secuencia de Ventas Panadería`
  * Prefix: `VEN-`
  * Padding: `4` (`VEN-0001`, `VEN-0002`, ...)
  * Implementation: Generated in `action_confirm()` using `self.env['ir.sequence'].next_by_code('panaderia.venta.secuencia')` when `name == 'Nuevo'`.
* **Rationale**:
  * Preserves continuous, gap-free numbering. If a draft order is discarded or cancelled before confirmation, no sequence number is burned or wasted.
* **Alternatives Considered**:
  * *Option A: Generate folio on `create()`*: Rejected because abandoned draft sales would create gaps in legal sales sequence numbers.

---

### Decision 6: Role-Based Access Control (RBAC) & Security
* **Decision**: Configure access permissions in `security/ir.model.access.csv`:
  * `group_panaderia_user` (Cajeros / Operadores):
    * `panaderia.venta`: Read (1), Write (1), Create (1), Unlink (0)
    * `panaderia.venta.linea`: Read (1), Write (1), Create (1), Unlink (1 - to delete lines in draft)
  * `group_panaderia_manager` (Administradores):
    * `panaderia.venta`: Read (1), Write (1), Create (1), Unlink (1)
    * `panaderia.venta.linea`: Read (1), Write (1), Create (1), Unlink (1)
  * Record-level Python enforcement: Override `unlink()` on `panaderia.venta` to forbid deleting any record where `state == 'confirmed'`.
* **Rationale**:
  * Adheres strictly to the Principle of Least Privilege. Front-desk personnel can create and confirm transactions but cannot destroy sales records.

---

## 3. Technology Matrix

| Component | Choice | Specification / Standard |
| :--- | :--- | :--- |
| **Runtime & Language** | Python 3.10+ | PEP 8 compliant, Odoo 16.0 framework standards |
| **Database** | PostgreSQL 15 | Relational integrity, foreign keys with CASCADE / RESTRICT |
| **Sequence Provider** | `ir.sequence` | XML data record with `noupdate="1"`, prefix `VEN-`, padding 4 |
| **Testing Engine** | `odoo.tests.common.TransactionCase` | Automated transactional test execution inside Docker container |
| **UI Framework** | Odoo Web Client (OWL & XML) | Statusbar widget, editable tree in form, monetary formatting |
| **Localization** | Spanish (`es_ES` / `es_SV`) | All field labels, button strings, states, and exception messages |

---

## 4. Risks and Mitigations

| Risk | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Stock Out-of-Stock / Negative Inventory** | Operational inconsistency | In `action_confirm()`, check if `line.cantidad > line.producto_id.cantidad_disponible`. Raise explicit localized `ValidationError` blocking confirmation if stock is insufficient. |
| **Concurrent Checkout of Same Product** | Race condition | Execute `action_confirm()` within an atomic ORM transaction; re-read product stock with row lock (`FOR UPDATE` or fresh search) before decrementing. |
| **Post-Confirmation Data Alteration** | Audit & Financial corruption | Enforce immutability via both XML view attributes and Python ORM `write()` / `unlink()` checks that raise `UserError` on confirmed orders. |
| **Line Deletion Causing Total Desync** | Math discrepancy | One2many relationship with `ondelete='cascade'` and `@api.depends('linea_ids.subtotal')` ensures total is recalculated upon line removal. |
