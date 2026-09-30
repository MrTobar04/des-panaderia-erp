# Tasks: Registro y Proceso de Ventas Esencial

**Feature**: `SPEC-2.1.1: Registro y Proceso de Ventas Esencial`  
**Branch**: `2.1.1-order-management`  
**Spec**: [`specs/2-sales/2.1-sales-orders/2.1.1-order-management/spec.md`](file:///c:/Users/Inspiron/Desktop/des-panaderia-erp/specs/2-sales/2.1-sales-orders/2.1.1-order-management/spec.md)  
**Plan**: [`specs/2-sales/2.1-sales-orders/2.1.1-order-management/plan.md`](file:///c:/Users/Inspiron/Desktop/des-panaderia-erp/specs/2-sales/2.1-sales-orders/2.1.1-order-management/plan.md)  
**Data Model**: [`specs/2-sales/2.1-sales-orders/2.1.1-order-management/data-model.md`](file:///c:/Users/Inspiron/Desktop/des-panaderia-erp/specs/2-sales/2.1-sales-orders/2.1.1-order-management/data-model.md)  

---

## Phase 1: Setup (Module Manifest & Model Skeleton)

**Purpose**: Module declarations, loader imports, and baseline structural scaffolding for the sales feature.

- [X] T001 Register `venta.py` in `Modulo_Odoo/models/__init__.py` and declare `data/venta_sequence.xml` and `views/venta_views.xml` in `Modulo_Odoo/__manifest__.py`
- [X] T002 [P] Register minimal invoice comodel `panaderia.factura` in `Modulo_Odoo/models/factura.py` and `Modulo_Odoo/models/__init__.py` to support `factura_id = fields.Many2one('panaderia.factura')` comodel resolution
- [X] T003 [P] Initialize sales test case suite loader in `Modulo_Odoo/tests/__init__.py`

---

## Phase 2: Foundational (Access Control & Inventory Stock Support)

**Purpose**: Core sequence numbering, security access controls, and inventory field prerequisites that MUST be complete before sales order processing can operate.

**⚠️ CRITICAL**: Order numbering, access permissions, and stock decrement depend on this foundation.

- [X] T004 Define sequence record `seq_panaderia_venta` in `Modulo_Odoo/data/venta_sequence.xml` with `name="Secuencia de Ventas Panadería"`, `code="panaderia.venta.secuencia"`, `prefix="VEN-"`, and `padding="4"`
- [X] T005 [P] Configure Access Control Lists for `panaderia.venta`, `panaderia.venta.linea`, and `panaderia.factura` granting permissions to `group_panaderia_user` and `group_panaderia_manager` in `Modulo_Odoo/security/ir.model.access.csv`
- [X] T006 [P] Ensure inventory stock field `cantidad_disponible = fields.Float(string='Stock Disponible', default=0.0, required=True)` is declared on `panaderia.producto` in `Modulo_Odoo/models/producto.py`

**Checkpoint**: Foundation ready — Sales order models, reactive computations, and view implementation can now begin.

---

## Phase 3: User Story 1 - Creación y Cálculo de Órdenes de Venta en Mostrador (Priority: P1) 🌟 MVP

**Goal**: Permitir al cajero de panadería abrir órdenes de venta de mostrador, seleccionar cliente, agregar múltiples líneas de productos con autocompletado de precio unitario, y calcular reactivamente los subtotales de línea y el total general de la venta.

**Independent Test**: Abrir nueva venta para "Cliente Mostrador", agregar 10 unidades de "Pan Francés Tradicional" ($0.10) y 1 unidad de "Pastel Selva Negra" ($15.00); verificar que los precios se autocompletan, los subtotales calculan $1.00 y $15.00, y el total general computa exactamente $16.00 en estado borrador.

### Tests for User Story 1 ⚠️

- [X] T007 [P] [US1] Create automated unit tests for order line subtotal computation, order total computation, and `_onchange_producto_id` price assignment in `Modulo_Odoo/tests/test_venta.py`

### Implementation for User Story 1

- [X] T008 [US1] Implement header model `panaderia.venta` in `Modulo_Odoo/models/venta.py` with fields `name` (`default='Nuevo'`, `readonly=True`), `cliente_id` (`Many2one='res.partner'`, `required=True`), `fecha` (`Datetime`, `default=fields.Datetime.now`, `required=True`), `state` (`Selection`, `default='draft'`, `required=True`), and `total` (`Float`, `compute='_compute_total'`, `store=True`, `digits=(10, 2)`)
- [X] T009 [US1] Implement detail model `panaderia.venta.linea` in `Modulo_Odoo/models/venta.py` with fields `venta_id` (`Many2one='panaderia.venta'`, `required=True`, `ondelete='cascade'`), `producto_id` (`Many2one='panaderia.producto'`, `required=True`, `ondelete='restrict'`), `cantidad` (`Float`, `default=1.0`, `required=True`), `precio_unitario` (`Float`, `required=True`, `digits=(10, 2)`), and `subtotal` (`Float`, `compute='_compute_subtotal'`, `store=True`, `digits=(10, 2)`)
- [X] T010 [US1] Implement `@api.onchange('producto_id')` on `panaderia.venta.linea` to copy `producto_id.precio_venta` into `precio_unitario` in `Modulo_Odoo/models/venta.py`
- [X] T011 [US1] Implement `@api.constrains('cantidad', 'precio_unitario')` on `panaderia.venta.linea` verifying `cantidad > 0.0` ("La cantidad vendida debe ser estrictamente mayor a 0.00.") and `precio_unitario >= 0.0` ("El precio unitario no puede ser un valor negativo.") in `Modulo_Odoo/models/venta.py`
- [X] T012 [US1] Implement Tree view `view_panaderia_venta_tree` with columns `name`, `fecha`, `cliente_id`, `total` (`sum="Total Ventas"`), and `state` (`widget="badge"`) in `Modulo_Odoo/views/venta_views.xml`
- [X] T013 [US1] Implement Form view `view_panaderia_venta_form` with customer/date inputs, inline editable lines grid (`<tree editable="bottom">`), and right-aligned monetary total footer (`oe_subtotal_footer`) in `Modulo_Odoo/views/venta_views.xml`
- [X] T014 [US1] Implement Search view `view_panaderia_venta_search` with filters by `state` ('draft', 'confirmed', 'cancelled'), date, and group-by customer in `Modulo_Odoo/views/venta_views.xml`
- [X] T015 [US1] Declare window action `action_panaderia_venta` and menu items (`Panadería` -> `Ventas` -> `Órdenes de Venta`) in `Modulo_Odoo/views/venta_views.xml`

**Checkpoint**: User Story 1 (MVP) is fully functional and testable independently.

---

## Phase 4: User Story 2 - Confirmación de Venta y Descuento Atómico de Existencias (Priority: P2)

**Goal**: Permitir al cajero confirmar la orden de venta mediante el botón "Confirmar Venta", asignando un folio secuencial automático (`VEN-XXXX`), validando y decrementando en tiempo real las existencias de inventario, actualizando el volumen de compras del cliente y generando la factura correspondiente.

**Independent Test**: Crear una orden en borrador de 10 unidades de "Pan Francés Tradicional" (con 50 unidades disponibles en stock); presionar "Confirmar Venta"; verificar que el estado cambia a `confirmed`, se asigna un folio correlativo (ej. `VEN-0001`), el stock en catálogo disminuye a 40 unidades y se crea el comprobante de factura vinculado en estado pendiente.

### Tests for User Story 2 ⚠️

- [X] T016 [P] [US2] Create automated unit tests for `action_confirm()` verifying sequence numbering generation, inventory stock decrement, and insufficient stock `ValidationError` in `Modulo_Odoo/tests/test_venta.py`

### Implementation for User Story 2

- [X] T017 [US2] Implement sequence generation logic in `action_confirm()` using `self.env['ir.sequence'].next_by_code('panaderia.venta.secuencia')` when `name == 'Nuevo'` in `Modulo_Odoo/models/venta.py`
- [X] T018 [US2] Implement stock availability validation and atomic decrement loop in `action_confirm()` raising `ValidationError` if `line.producto_id.cantidad_disponible < line.cantidad` in `Modulo_Odoo/models/venta.py`
- [X] T019 [US2] Implement automatic invoice creation (`panaderia.factura` with `state='pending'`) and link assignment to `factura_id` inside `action_confirm()` in `Modulo_Odoo/models/venta.py`
- [X] T020 [US2] Update customer historical purchase total `cliente_id.total_compras_panaderia` upon confirmation in `Modulo_Odoo/models/venta.py`
- [X] T021 [US2] Add action button "Confirmar Venta" (`name="action_confirm"`, `states="draft"`, `class="oe_highlight"`) and invoice smart button (`name="action_view_factura"`, icon `fa-pencil-square-o`) in `Modulo_Odoo/views/venta_views.xml`

**Checkpoint**: User Stories 1 and 2 work together, completing counter sale confirmation to inventory deduction.

---

## Phase 5: User Story 3 - Restricción de Edición e Inmutabilidad Post-Confirmación (Priority: P3)

**Goal**: Garantizar la integridad fiscal y de auditoría bloqueando cualquier modificación en líneas de productos, cantidades, precios o cliente una vez que la orden de venta ha pasado al estado confirmada (`confirmed`).

**Independent Test**: Tomar una orden de venta en estado `confirmed`; intentar editar productos o cantidades desde la vista formulario; verificar que los campos se encuentran en modo solo lectura (`readonly`). Intentar modificar o eliminar la orden vía ORM y verificar que se emite un `UserError` impidiendo la alteración o supresión.

### Tests for User Story 3 ⚠️

- [X] T022 [P] [US3] Create automated unit tests for post-confirmation immutability verifying `write()` and `unlink()` restrictions raise `UserError` on confirmed sales in `Modulo_Odoo/tests/test_venta.py`

### Implementation for User Story 3

- [X] T023 [US3] Override `write(self, vals)` in `Modulo_Odoo/models/venta.py` to raise `UserError("No se pueden alterar líneas, clientes ni importes de una orden de venta ya confirmada.")` if modifying confirmed records
- [X] T024 [US3] Override `unlink(self)` in `Modulo_Odoo/models/venta.py` to raise `UserError("No es posible eliminar la orden de venta confirmada. Cancele la orden primero.")`
- [X] T025 [US3] Configure XML readonly attributes `attrs="{'readonly': [('state', '!=', 'draft')]}"` on `cliente_id`, `fecha`, and `linea_ids` in `Modulo_Odoo/views/venta_views.xml`

**Checkpoint**: Immutability safeguards enforced at both application layer and user interface.

---

## Phase 6: User Story 4 - Ciclo de Vida, Cancelación y Reversión de Existencias (Priority: P4)

**Goal**: Permitir la cancelación de órdenes de venta en borrador o confirmadas (por usuarios autorizados), restituyendo automáticamente las cantidades al inventario disponible si la venta confirmada es cancelada.

**Independent Test**: Cancelar una venta confirmada de 10 unidades de pan; verificar que el estado cambia a `cancelled`, la factura asociada se marca como cancelada y las 10 unidades se devuelven al stock disponible del producto.

### Tests for User Story 4 ⚠️

- [X] T026 [P] [US4] Create automated unit tests for `action_cancel()` and inventory stock reversion in `Modulo_Odoo/tests/test_venta.py`

### Implementation for User Story 4

- [X] T027 [US4] Implement `action_cancel()` in `Modulo_Odoo/models/venta.py` checking if previous state was `confirmed` to restore `producto_id.cantidad_disponible += line.cantidad` and cancel associated invoice
- [X] T028 [US4] Implement `action_draft()` in `Modulo_Odoo/models/venta.py` allowing reset from `cancelled` back to `draft`
- [X] T029 [US4] Add header action buttons "Cancelar" (`states="draft,confirmed"`) and "Volver a Borrador" (`states="cancelled"`) in `Modulo_Odoo/views/venta_views.xml`

**Checkpoint**: Complete sales order lifecycle and stock recovery verified.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Traceability documentation, PEP 8 compliance, and containerized test execution.

- [X] T030 [P] Create manual test procedure document `docs/test-procedures/test-procedure-2.1.1.md` mapping all acceptance criteria and test scenarios per Principle IV
- [X] T031 [P] Verify Python code formatting and PEP 8 guidelines across `models/venta.py` and `tests/test_venta.py`
- [X] T032 Execute containerized test suite (`docker compose exec web odoo ...`) per `specs/2-sales/2.1-sales-orders/2.1.1-order-management/quickstart.md`
- [X] T033 Update requirements checklist at `specs/2-sales/2.1-sales-orders/2.1.1-order-management/checklists/requirements.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) — BLOCKS all user stories.
- **User Story 1 (Phase 3 - MVP)**: Depends on Foundational (Phase 2).
- **User Story 2 (Phase 4)**: Depends on User Story 1 (Phase 3).
- **User Story 3 (Phase 5)**: Depends on User Story 2 (Phase 4).
- **User Story 4 (Phase 6)**: Depends on User Story 2 (Phase 4).
- **Polish (Phase 7)**: Depends on all User Story phases (Phases 3-6).

### User Story Dependencies

- **User Story 1 (P1)**: Independent foundation for sales order lines and totals.
- **User Story 2 (P2)**: Builds upon US1 order structure to add confirmation and stock reduction.
- **User Story 3 (P3)**: Guards confirmed orders produced by US2.
- **User Story 4 (P4)**: Provides reversal workflow for orders confirmed in US2.

### Parallel Opportunities

- **Setup Phase**: T002 (`factura.py`) and T003 (`tests/__init__.py`) can run in parallel.
- **Foundational Phase**: T005 (`ir.model.access.csv`) and T006 (`producto.py`) can run in parallel.
- **User Story 1**: T007 (unit tests) can be written in parallel with model/view definitions.
- **User Story 2**: T016 (confirmation tests) can be written in parallel with action implementation.
- **Polish Phase**: T030 (`test-procedure-2.1.1.md`) and T031 (PEP 8 review) can run in parallel.

---

## Implementation Strategy

### MVP Scope (Phases 1, 2, and 3)
1. Complete Phase 1 (Setup) and Phase 2 (Foundational).
2. Complete Phase 3 (User Story 1: Header/Line models, reactive total calculations, onchange price lookup, and Form/Tree/Search views).
3. **STOP & VALIDATE**: Run `quickstart.md` Scenario 1 to verify sales order creation and math calculations in Odoo.

### Incremental Delivery (Phases 4 through 7)
1. Implement Confirmation and Stock Decrement (Phase 4 - User Story 2).
2. Enforce Post-Confirmation Immutability (Phase 5 - User Story 3).
3. Add Cancellation and Stock Reversal (Phase 6 - User Story 4).
4. Document test procedures in `docs/test-procedures/test-procedure-2.1.1.md` and validate test suite in Docker (Phase 7).
