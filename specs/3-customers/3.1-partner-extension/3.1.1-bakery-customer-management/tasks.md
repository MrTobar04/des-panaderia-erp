# Tasks: SPEC-3.1.1 Extensión y Registro de Clientes

**Branch**: `3.1.1-bakery-customer-management` | **Date**: 2026-09-30 | **Spec**: [`specs/3-customers/3.1-partner-extension/3.1.1-bakery-customer-management/spec.md`](file:///d:/UDB/CICLO-10-2026/DES/LAB/Desafio%203/des-panaderia-erp/specs/3-customers/3.1-partner-extension/3.1.1-bakery-customer-management/spec.md)

---

## Task Breakdown

### Phase 1: Model Extension & Backend Logic
- [x] **T001**: Implement `res.partner` extension in `Modulo_Odoo/models/cliente.py` with fields `es_cliente_panaderia`, `fecha_registro_panaderia`, `total_compras_panaderia`, `notas_preferencias`, `venta_panaderia_ids`, and computed method `_compute_total_compras_panaderia`.
- [x] **T002**: Import `cliente` module in `Modulo_Odoo/models/__init__.py`.

### Phase 2: Seed Data & Manifest Registration
- [x] **T003**: Create seed customers in `Modulo_Odoo/data/cliente_data.xml` ("Cliente General / Mostrador" and initial sample clients).
- [x] **T004**: Register `data/cliente_data.xml` and `views/cliente_views.xml` in `Modulo_Odoo/__manifest__.py`.

### Phase 3: Views, Actions & UI Navigation
- [x] **T005**: Create `Modulo_Odoo/views/cliente_views.xml` with:
  - Form view extension adding "Datos de Panadería" notebook tab with fields and sales order history.
  - Dedicated tree view displaying name, phone, email, registration date, and total purchases.
  - Search view extension with "Clientes de Panadería" filter and custom group by.
  - Window Action `action_panaderia_cliente` with domain `[('es_cliente_panaderia', '=', True)]` and default context `{'default_es_cliente_panaderia': True}`.
  - Menu items under Panadería top level and Panadería / Ventas submenu.

### Phase 4: Automated Testing & Verification
- [x] **T006**: Implement automated test suite in `Modulo_Odoo/tests/test_cliente.py` covering partner extension, seed data verification, computed total purchase calculation, sales confirmation & cancellation synchronization, and list domain filtering.
- [x] **T007**: Register `test_cliente` in `Modulo_Odoo/tests/__init__.py`.

### Phase 5: Test Procedure Documentation & Closure
- [x] **T008**: Generate manual test procedure document in `docs/test-procedures/test-procedure-3.1.1.md`.
- [x] **T009**: Update `specs/3-customers/3.1-partner-extension/3.1.1-bakery-customer-management/spec.md` Definition of Done.
