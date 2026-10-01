# Tasks: SPEC-1.1.2 Categorías de Productos de Panadería

**Branch**: `1.1.2-product-categories` | **Date**: 2026-09-30 | **Spec**: [`specs/1-inventory/1.1-product-catalog/1.1.2-product-categories/spec.md`](file:///d:/UDB/CICLO-10-2026/DES/LAB/Desafio%203/des-panaderia-erp/specs/1-inventory/1.1-product-catalog/1.1.2-product-categories/spec.md)

---

## Task Breakdown

### Phase 1: Setup & Data Model Configuration
- [x] **T001**: Implement `panaderia.categoria` model in `Modulo_Odoo/models/categoria.py` with fields (`name`, `codigo`, `sequence`, `descripcion`, `active`, `producto_ids`, `total_productos`), computed product counter, `_order`, `_sql_constraints`, and case-insensitive validations.
- [x] **T002**: Verify export and import of `categoria` in `Modulo_Odoo/models/__init__.py`.

### Phase 2: Seed Data & Security Configuration
- [x] **T003**: Populate seed data for 4 core bakery categories (Pan, Pastel, Galleta, Bebida) in `Modulo_Odoo/data/categoria_data.xml`.
- [x] **T004**: Enforce RBAC security permissions in `Modulo_Odoo/security/ir.model.access.csv` (read-only for standard users, full CRUD for bakery managers).
- [x] **T005**: Ensure `categoria_data.xml`, `categoria_views.xml`, and access rules are registered in `Modulo_Odoo/__manifest__.py`.

### Phase 3: Views & User Interface
- [x] **T006**: Implement Tree, Form, Search views, and Window Action in `Modulo_Odoo/views/categoria_views.xml` including sequence handle, computed total badge, stat-button navigation, and embedded product list.
- [x] **T007**: Ensure category menu item is accessible under Panadería / Inventario.

### Phase 4: Automated Testing & Verification
- [x] **T008**: Implement automated test suite in `Modulo_Odoo/tests/test_categoria.py` verifying seed data loading, computed counts, uniqueness constraints, deletion restriction, and archiving.
- [x] **T009**: Register `test_categoria` in `Modulo_Odoo/tests/__init__.py`.

### Phase 5: Test Procedure Documentation
- [x] **T010**: Generate manual test procedure document in `docs/test-procedures/test-procedure-1.1.2.md`.
