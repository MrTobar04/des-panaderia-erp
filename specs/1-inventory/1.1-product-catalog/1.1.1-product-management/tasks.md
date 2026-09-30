# Tasks: Gestión de Catálogo de Productos

**Feature**: `SPEC-1.1.1: Gestión de Catálogo de Productos`  
**Branch**: `1.1.1-product-management`  
**Spec**: [`specs/1-inventory/1.1-product-catalog/1.1.1-product-management/spec.md`](file:///d:/UDB/CICLO-10-2026/DES/LAB/Desafio%203/des-panaderia-erp/specs/1-inventory/1.1-product-catalog/1.1.1-product-management/spec.md)  
**Plan**: [`specs/1-inventory/1.1-product-catalog/1.1.1-product-management/plan.md`](file:///d:/UDB/CICLO-10-2026/DES/LAB/Desafio%203/des-panaderia-erp/specs/1-inventory/1.1-product-catalog/1.1.1-product-management/plan.md)  
**Data Model**: [`specs/1-inventory/1.1-product-catalog/1.1.1-product-management/data-model.md`](file:///d:/UDB/CICLO-10-2026/DES/LAB/Desafio%203/des-panaderia-erp/specs/1-inventory/1.1-product-catalog/1.1.1-product-management/data-model.md)  

---

## Phase 1: Setup (Shared Infrastructure & Module Skeleton)

**Purpose**: Initialize module folder structure, manifest declaration, and testing scaffolding.

- [X] T001 Initialize Odoo module directory structure at `Modulo_Odoo/models/`, `Modulo_Odoo/views/`, `Modulo_Odoo/security/`, `Modulo_Odoo/data/`, and `Modulo_Odoo/tests/`
- [X] T002 Configure Odoo module manifest in `Modulo_Odoo/__manifest__.py` declaring name `'Panadería Delicias Dulces'`, version `'1.0.0'`, category `'Sales/Inventory'`, dependencies `['base']`, and data loading order
- [X] T003 [P] Initialize Python package root in `Modulo_Odoo/__init__.py` and models loader in `Modulo_Odoo/models/__init__.py`
- [X] T004 [P] Initialize test package loader in `Modulo_Odoo/tests/__init__.py`

---

## Phase 2: Foundational (Security Groups & Category Prerequisite)

**Purpose**: Core security groups and baseline category model prerequisites that MUST be complete before product management can operate.

**⚠️ CRITICAL**: Product creation and security assignment depend on this foundation.

- [X] T005 Define security groups `group_panaderia_user` ("Operador de Panadería") and `group_panaderia_manager` ("Administrador de Panadería") in `Modulo_Odoo/security/security.xml`
- [X] T006 [P] Declare Category model `panaderia.categoria` with fields `name` (required, indexed), `codigo`, `descripcion`, and `active` in `Modulo_Odoo/models/categoria.py`
- [X] T007 [P] Create default bakery categories seed data in `Modulo_Odoo/data/categoria_data.xml` for `categoria_pan` ("Pan"), `categoria_pastel` ("Pastel"), `categoria_galleta` ("Galleta"), and `categoria_bebida` ("Bebida")
- [X] T008 Configure baseline Access Control Lists for categories and security groups in `Modulo_Odoo/security/ir.model.access.csv`

**Checkpoint**: Foundation ready — product catalog model and views implementation can proceed.

---

## Phase 3: User Story 1 - Creación y Consulta de Catálogo de Productos (Priority: P1) 🌟 MVP

**Goal**: Permitir al operador registrar productos de panadería con su información comercial básica (nombre, código SKU, categoría, costo, precio de venta, descripción) y visualizar el catálogo completo con cálculo automático de margen bruto en vistas de lista y formulario.

**Independent Test**: Registrar un producto ("Pan Francés Tradicional", SKU: "PAN-001", Categoría: "Pan", Costo: $0.05, Precio: $0.10) mediante interfaz web o prueba ORM; verificar que se almacena correctamente, calcula un margen de $0.05 (50.00%), y se muestra en la vista de lista.

### Tests for User Story 1
- [X] T009 [P] [US1] Create automated unit test case for valid product creation and margin computation in `Modulo_Odoo/tests/test_producto.py`

### Implementation for User Story 1
- [X] T010 [US1] Implement model `panaderia.producto` in `Modulo_Odoo/models/producto.py` with fields `name` (Char, required=True, index=True), `codigo` (Char, copy=False, index=True), `categoria_id` (Many2one='panaderia.categoria', required=True, ondelete='restrict'), `costo` (Float, digits=(10,2), default=0.0), `precio_venta` (Float, digits=(10,2), default=0.0), and `descripcion` (Text)
- [X] T011 [US1] Implement computed fields `margen_bruto` (`precio_venta - costo`, store=True) and `porcentaje_margen` (`(margen_bruto / precio_venta) * 100.0`, store=True) with `@api.depends('precio_venta', 'costo')` in `Modulo_Odoo/models/producto.py`
- [X] T012 [US1] Configure Access Control List permissions for `panaderia.producto` granting Read/Write/Create to `group_panaderia_user` and full CRUD to `group_panaderia_manager` in `Modulo_Odoo/security/ir.model.access.csv`
- [X] T013 [US1] Implement Tree / List view `view_panaderia_producto_tree` with columns `codigo`, `name`, `categoria_id`, `costo`, `precio_venta`, `margen_bruto`, `porcentaje_margen` in `Modulo_Odoo/views/producto_views.xml`
- [X] T014 [US1] Implement Form view `view_panaderia_producto_form` with structured headers, numeric cost/price groups, calculated margin fields, and description tabs in `Modulo_Odoo/views/producto_views.xml`
- [X] T015 [US1] Implement Search view `view_panaderia_producto_search` with search filters by `name`, `codigo`, and group-by `categoria_id` in `Modulo_Odoo/views/producto_views.xml`
- [X] T016 [US1] Declare window action `action_panaderia_producto` and top-level menu hierarchy (`Panadería` -> `Inventario` -> `Productos`) in `Modulo_Odoo/views/producto_views.xml`
- [X] T017 [P] [US1] Create initial seed products dataset (`producto_pan_frances`, `producto_selva_negra`, `producto_galleta_avena`, `producto_cafe_americano`) in `Modulo_Odoo/data/producto_data.xml`

**Checkpoint**: User Story 1 (MVP) is fully functional and testable independently.

---

## Phase 4: User Story 2 - Validación de Precios y Costos Comerciales (Priority: P2)

**Goal**: Garantizar la integridad comercial bloqueando el registro o actualización de productos con precio de venta menor o igual a cero (`precio_venta <= 0.0`) o costo negativo (`costo < 0.0`), mostrando mensajes de error amigables en español.

**Independent Test**: Intentar guardar un producto con `precio_venta = 0.0` o `costo = -1.00` desde el formulario web o ORM; verificar que se lanza un `ValidationError` bloqueando la transacción y mostrando el mensaje exacto estipulado.

### Tests for User Story 2
- [X] T018 [P] [US2] Create automated unit tests for negative cost and zero/negative sale price validation errors in `Modulo_Odoo/tests/test_producto.py`

### Implementation for User Story 2
- [X] T019 [US2] Implement `@api.constrains('precio_venta', 'costo')` validator `_check_precios_y_costos` in `Modulo_Odoo/models/producto.py` verifying `precio_venta > 0.0` (raising "El precio de venta debe ser un valor estrictamente mayor a $0.00.") and `costo >= 0.0` (raising "El costo de producción no puede ser un valor negativo.")

**Checkpoint**: User Stories 1 and 2 work independently with full business validation.

---

## Phase 5: User Story 3 - Restricción de Duplicidad y Unicidad de Catálogo (Priority: P3)

**Goal**: Prevenir la duplicidad accidental de nombres de productos y colisiones de códigos SKU en la base de datos de la panadería.

**Independent Test**: Intentar crear dos productos con el mismo nombre "Pan Francés Tradicional" o mismo código SKU; verificar que la base de datos y el ORM rechazan el segundo registro con un aviso de duplicidad.

### Tests for User Story 3
- [X] T020 [P] [US3] Create automated unit test for name and SKU uniqueness constraints in `Modulo_Odoo/tests/test_producto.py`

### Implementation for User Story 3
- [X] T021 [US3] Declare `_sql_constraints` in `Modulo_Odoo/models/producto.py` for `('name_unique', 'UNIQUE(name)', 'Ya existe un producto registrado con este nombre. El nombre debe ser único.')` and `('codigo_unique', 'UNIQUE(codigo)', 'Ya existe un producto registrado con este código / SKU.')`

**Checkpoint**: Uniqueness guarantees enforced at both database and application layers.

---

## Phase 6: User Story 4 - Ciclo de Vida, Archivado y Protección Histórica (Priority: P4)

**Goal**: Permitir el archivado lógico de productos descontinuados (`active = False`) manteniendo el histórico de ventas intacto, e impedir la eliminación física (`unlink`) si existen transacciones vinculadas.

**Independent Test**: Archivar un producto activo y verificar que se oculta de la vista por defecto pero aparece al filtrar por "Archivados"; verificar que intentar eliminar un producto con historial levanta una advertencia de usuario.

### Tests for User Story 4
- [X] T022 [P] [US4] Create automated unit test for active archival toggling and deletion prevention safeguards in `Modulo_Odoo/tests/test_producto.py`

### Implementation for User Story 4
- [X] T023 [US4] Add `active` field (Boolean, default=True) and override `unlink` method in `Modulo_Odoo/models/producto.py` to raise `UserError` when referenced by sale lines
- [X] T024 [US4] Add archived ribbon indicator widget (`web_ribbon`, bg_color="bg-danger") and active filters in `Modulo_Odoo/views/producto_views.xml`

**Checkpoint**: Complete product lifecycle and data retention policies verified.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end documentation, test procedure traceability, and containerized verification.

- [X] T025 [P] Create manual test procedure document `docs/test-procedures/test-procedure-1.1.1.md` mapping all acceptance criteria and test scenarios per Principle IV
- [X] T026 [P] Verify Python code styling against PEP 8 guidelines and Odoo coding conventions
- [X] T027 Execute containerized quickstart verification suite (`docker compose exec odoo ...`) per `specs/1-inventory/1.1-product-catalog/1.1.1-product-management/quickstart.md`
- [X] T028 Update requirements checklist at `specs/1-inventory/1.1-product-catalog/1.1.1-product-management/checklists/requirements.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) — BLOCKS all user stories.
- **User Story 1 (Phase 3 - MVP)**: Depends on Foundational (Phase 2).
- **User Story 2 (Phase 4)**: Depends on User Story 1 (Phase 3).
- **User Story 3 (Phase 5)**: Depends on User Story 1 (Phase 3).
- **User Story 4 (Phase 6)**: Depends on User Story 1 (Phase 3).
- **Polish (Phase 7)**: Depends on all User Story phases (Phases 3-6).

### Parallel Opportunities

- **Setup Phase**: T003 (`__init__.py`) and T004 (`tests/__init__.py`) can run in parallel.
- **Foundational Phase**: T006 (`categoria.py`) and T007 (`categoria_data.xml`) can run in parallel.
- **User Story 1 Phase**: T009 (unit test) and T017 (`producto_data.xml`) can be prepared in parallel with model/view definitions.
- **User Stories 2, 3, 4**: Can be developed in parallel once User Story 1 baseline is in place.
- **Polish Phase**: T025 (`test-procedure-1.1.1.md`) and T026 (PEP 8 linting) can run in parallel.

---

## Parallel Execution Example: User Story 1

```bash
# Launch test and seed data definitions in parallel:
Task: "Create automated unit test case for valid product creation in Modulo_Odoo/tests/test_producto.py"
Task: "Create initial seed products dataset in Modulo_Odoo/data/producto_data.xml"

# Launch model and view definitions sequentially or across developers:
Task: "Implement model panaderia.producto in Modulo_Odoo/models/producto.py"
Task: "Implement views in Modulo_Odoo/views/producto_views.xml"
```

---

## Implementation Strategy

### MVP Scope (Phases 1, 2, and 3)
1. Complete Phase 1 (Setup) and Phase 2 (Foundational).
2. Complete Phase 3 (User Story 1: Product model, computed margins, tree/form/search views, and seed data).
3. **STOP & VALIDATE**: Run `quickstart.md` Scenario 1 to verify product creation and display in Odoo.

### Incremental Delivery (Phases 4 through 7)
1. Layer on Price/Cost domain validations (Phase 4 - User Story 2).
2. Add Uniqueness constraints (Phase 5 - User Story 3).
3. Add Archival & Safe Unlink behavior (Phase 6 - User Story 4).
4. Finalize test procedures in `docs/test-procedures/test-procedure-1.1.1.md` and complete quickstart verification (Phase 7).
