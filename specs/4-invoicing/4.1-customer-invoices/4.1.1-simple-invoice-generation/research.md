# Phase 0: Outline & Research - Generación de Facturas Simples

**Feature**: `SPEC-4.1.1: Generación de Facturas Simples`  
**Branch / Directory**: `specs/4-invoicing/4.1-customer-invoices/4.1.1-simple-invoice-generation`  
**Date**: 2026-09-30  
**Status**: Completed  

---

## 1. Executive Summary & Objective

This research document analyzes and establishes all architectural decisions, design invariants, data constraints, and UI integration patterns required to implement the Simple Invoice Generation module (`panaderia.factura`) for Panadería "Delicias Dulces" ERP. The module completes the core financial loop of the bakery operation by receiving transactions from Sales Orders (`SPEC-2.1.1`), producing official sequential numbering (`FAC-XXXX`), tracking the cashier collection lifecycle (`pending` $\to$ `paid`), and preparing data aggregates for daily income reporting (`SPEC-5.1.1`).

---

## 2. Research Findings & Technical Decisions

### Decision 1: Correlative Sequential Numbering Strategy (`FAC-XXXX`)
* **Decision**: Implement an Odoo sequence record (`ir.sequence`) with code `panaderia.factura.secuencia` in `Modulo_Odoo/data/factura_sequence.xml` and generate the numbering inside the `create()` method override of `panaderia.factura`:
  ```python
  @api.model
  def create(self, vals):
      if vals.get('name', 'Borrador') == 'Borrador' or not vals.get('name'):
          vals['name'] = self.env['ir.sequence'].next_by_code('panaderia.factura.secuencia') or 'FAC-0001'
      return super(PanaderiaFactura, self).create(vals)
  ```
  Sequence definition parameters:
  - `prefix`: `FAC-`
  - `padding`: 4 (e.g., `FAC-0001`, `FAC-0002`)
  - `implementation`: standard (`no_gap` or standard PostgreSQL sequence)
  - `number_next`: 1
  - `number_increment`: 1
* **Rationale**:
  * Guarantees strict gapless or monotonic invoice numbering without collisions during concurrent cashier checkouts.
  * Respects Odoo standard numbering lifecycle where draft records start with `'Borrador'` or `'Nuevo'` and are assigned definitive legal folios upon record instantiation or validation.
  * In the existing sales module (`SPEC-2.1.1`), `panaderia.venta.action_confirm()` calls `panaderia.factura.create({...})` passing `'name': 'Borrador'`. Overriding `create` ensures that any automated creation instantly receives its official `FAC-XXXX` folio seamlessly.
* **Alternatives Considered**:
  * *Option A: Assign sequence via SQL trigger or Python `@api.onchange`*: Rejected because `onchange` does not run in background ORM `create()` calls from sales orders, and SQL triggers bypass Odoo sequence metadata.
  * *Option B: Sequence assignment only when clicking a manual "Emitir" button*: Rejected because counter sales in a bakery require immediate invoice generation upon order confirmation.

---

### Decision 2: State Lifecycle & In-Form Cashier Payment Registration
* **Decision**: Adopt a clear, 3-state workflow (`pending` $\to$ `paid`, with `cancelled` available for annulments):
  * `pending` (Pendiente): Default state upon generation from sale or manual draft creation. Invoice reflects an outstanding account receivable at the counter.
  * `paid` (Pagada): Transition triggered by cashier clicking the button `action_register_payment()`. Sets `state = 'paid'` and automatically records current timestamp in `fecha_pago = fields.Datetime.now()`.
  * `cancelled` (Cancelada): Transition triggered by `action_cancel()` or automatically when the linked sales order is cancelled.
* **Rationale**:
  * Cashiers operate in high-turnover retail environments where counter payments are completed immediately after sales confirmation.
  * A direct, one-click action `action_register_payment()` on the invoice form view provides optimal cashier ergonomics without forcing cumbersome multi-step bank reconciliation wizards.
  * Complies fully with Principle V (Operational Usability & Express Deployment Standards) and Acceptance Criteria Scenario 2.
* **Alternatives Considered**:
  * *Option A: Full Odoo `account.payment.register` wizard*: Rejected because standard Odoo accounting introduces journal entries, analytic accounts, reconciliation widgets, and multi-currency exchange rates that exceed the scope of "Facturación Simple" and complicate testing.
  * *Option B: Two-state model (`draft` and `paid`)*: Rejected because bakery orders may be prepared before cashier payment is completed (e.g., telephone orders or custom pastry pickup), requiring a distinct `pending` state.

---

### Decision 3: Payment Method Management & Financial Integrity
* **Decision**: Provide standard payment method selection (`metodo_pago`) with the following values:
  * `efectivo`: "Efectivo" (Default)
  * `tarjeta`: "Tarjeta de Débito / Crédito"
  * `transferencia`: "Transferencia"
  Enforce validation on `monto_total` to guarantee non-negative values (`monto_total >= 0.0`) via `@api.constrains('monto_total')`.
* **Rationale**:
  * Matches the daily settlement needs of bakery retail where cash and debit card POS terminals dominate sales.
  * Feeds the operational reporting engine (`SPEC-5.1.1`) to group daily revenue by payment channel.
  * Prevents erratic negative totals from corrupting financial audit trails.
* **Alternatives Considered**:
  * *Option A: Free-text payment method string*: Rejected because free-text inputs prevent reliable aggregation, filtering, and reporting.

---

### Decision 4: Financial Immutability & Anti-Tampering Rules on Paid Invoices
* **Decision**: Implement dual-tier immutability protection:
  1. **UI Layer**: Form view fields (`cliente_id`, `monto_total`, `metodo_pago`, `venta_id`, `fecha_emision`) become `readonly` when `state in ('paid', 'cancelled')`.
  2. **ORM Layer**: Override `write()` and `unlink()` on `panaderia.factura`:
     - If `state == 'paid'` and the update attempts to modify monetary (`monto_total`), client (`cliente_id`), or sales link (`venta_id`), raise `UserError(_("No se pueden modificar los datos financieros de una factura que ya ha sido pagada."))`.
     - Prevent `unlink()` (deletion) of any invoice in `paid` state: raise `UserError(_("No se pueden eliminar facturas en estado Pagada por motivos de auditoría fiscal."))`.
* **Rationale**:
  * Complies with Principle III (Proactive Stock Alerting & Data Integrity) and strict fiscal audit standards.
  * Prevents accidental modification or malicious alteration of completed transactions.
* **Alternatives Considered**:
  * *Option A: UI-only readonly*: Rejected because RPC API calls or Odoo developer mode can bypass XML view constraints.

---

### Decision 5: Bidirectional Navigation & Smart Button Integration
* **Decision**:
  1. On `panaderia.factura`: Add a smart button or header button "Ver Orden de Venta" calling `action_view_venta()`.
  2. On `panaderia.venta`: Utilize the existing smart button "Ver Factura" calling `action_view_factura()`.
  3. Relational Foreign Key: `venta_id = fields.Many2one('panaderia.venta', string='Orden de Venta Origen', readonly=True, ondelete='set null')`.
* **Rationale**:
  * Ensures seamless bidirectional navigation between customer orders and their fiscal receipts.
  * Fulfills Acceptance Criteria Scenario 3 directly.
* **Alternatives Considered**:
  * *Option A: Relying only on standard many2one field clickable link*: Less prominent and harder for non-technical retail users to spot during counter rush hours.

---

### Decision 6: View Architecture, Filters, Group By & Menu Hierarchy
* **Decision**:
  1. **Views**: Declare Form, Tree, and Search views in `Modulo_Odoo/views/factura_views.xml`.
  2. **Tree View**: Display `name`, `fecha_emision`, `cliente_id`, `venta_id`, `metodo_pago`, `monto_total` (with `sum="Total"`), and `state` with visual badges (`decoration-warning="state == 'pending'"`, `decoration-success="state == 'paid'"`, `decoration-danger="state == 'cancelled'"`).
  3. **Search View**: Provide instant search by `name`, `cliente_id`, `venta_id`, filters for "Pendientes de Pago", "Pagadas", "Canceladas", "Emitidas Hoy", and groupings by Cliente, Estado, Método de Pago, and Fecha.
  4. **Menu Integration**: Add menu entry under `menu_panaderia_root` or `menu_panaderia_ventas_root` titled "Facturación" / "Facturas de Clientes".
* **Rationale**:
  * Delivers immediate operational visibility for cashiers managing pending collections and daily cash closing.
* **Alternatives Considered**:
  * *Option A: Generic uncustomized Odoo tree view*: Lacks totals sum and color badges, hindering quick visual assessment.

---

## 3. Risk Assessment & Mitigations

| Risk | Impact | Likelihood | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **R-1: Duplicate Invoice Generation** | Multiple invoices created for a single sales order. | Medium | Add `@api.constrains('venta_id')` or check in `action_confirm()` of `panaderia.venta` to ensure a sale cannot have more than one non-cancelled invoice. |
| **R-2: Tampering with Paid Invoices** | Corrupted fiscal records and mismatched cash reports. | High | Enforce ORM-level `write()` and `unlink()` restrictions preventing modifications to paid invoices. |
| **R-3: Sequence Collisions** | Duplicate invoice numbers during concurrent transactions. | Low | Utilize standard Odoo `ir.sequence` with transactional isolation to ensure monotonic unique sequence generation. |

---

## 4. Conclusion & Next Steps

All technical aspects of `SPEC-4.1.1` have been researched and resolved without ambiguity. We proceed to Phase 1: Data Model, Interface Contracts, and Quickstart Validation Guide.
