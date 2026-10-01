# Tasks: Reportes Operativos Diarios y Alertas de Stock

**Feature**: `SPEC-5.1.1: Reportes Operativos Diarios y Alertas de Stock`  
**Branch**: `5.1.1-daily-sales-and-stock-reports`  
**Spec**: [`specs/5-reports/5.1-operational-reports/5.1.1-daily-sales-and-stock-reports/spec.md`](spec.md)  
**Plan**: [`specs/5-reports/5.1-operational-reports/5.1.1-daily-sales-and-stock-reports/plan.md`](plan.md)  
**Data Model**: [`specs/5-reports/5.1-operational-reports/5.1.1-daily-sales-and-stock-reports/data-model.md`](data-model.md)  
**ORM Contract**: [`specs/5-reports/5.1-operational-reports/5.1.1-daily-sales-and-stock-reports/contracts/reporte-orm-contract.md`](contracts/reporte-orm-contract.md)  
**Views Contract**: [`specs/5-reports/5.1-operational-reports/5.1.1-daily-sales-and-stock-reports/contracts/reporte-views-contract.md`](contracts/reporte-views-contract.md)  

---

## Phase 1: Setup (Module Manifest & Registration)

**Purpose**: Structural scaffolding, model imports, and manifest registrations for the reporting module.

- [X] T001 Register `views/reporte_views.xml` and `report/reporte_diario_template.xml` in `data` list of `Modulo_Odoo/__manifest__.py`
- [X] T002 [P] Register `from . import reporte_panaderia` in `Modulo_Odoo/models/__init__.py`
- [X] T003 [P] Register test suite import `from . import test_reporte` in `Modulo_Odoo/tests/__init__.py`

---

## Phase 2: Foundational (SQL View Model & Access Control)

**Purpose**: Core analytical SQL view definition and model access permissions.

- [X] T004 Implement SQL view model `PanaderiaReporteVentas` (`_name = 'panaderia.reporte.ventas'`, `_auto = False`) with `init()` creating PostgreSQL view `panaderia_reporte_ventas` in `Modulo_Odoo/models/reporte_panaderia.py`
- [X] T005 [P] Declare Access Control List entries `access_panaderia_reporte_ventas_user`, `access_panaderia_reporte_ventas_manager`, `access_panaderia_reporte_diario_wizard_user`, and `access_panaderia_reporte_diario_wizard_manager` in `Modulo_Odoo/security/ir.model.access.csv`

---

## Phase 3: User Story 1 - Consulta de Ventas del Día y Métricas Analíticas (Priority: P1) 🌟 MVP

**Goal**: Permitir al administrador consultar el total consolidado de ingresos, conteo de órdenes y desglose de ventas de la jornada actual mediante vistas pivote y listas analíticas.

**Independent Test**: Confirmar ventas en el día por $85.00; abrir Panadería $\to$ Reportes $\to$ Ventas del Día; verificar que la vista muestra el acumulado de $85.00 con desglose por categoría y producto.

### Tests for User Story 1 ⚠️
- [X] T006 [P] [US1] Create automated unit tests for SQL view aggregation, revenue sum, and draft/cancelled sale exclusion in `Modulo_Odoo/tests/test_reporte.py`

### Implementation for User Story 1
- [X] T007 [US1] Declare Pivot view `view_panaderia_reporte_ventas_pivot` in `Modulo_Odoo/views/reporte_views.xml` measuring `cantidad_vendida` and `total_ingresos` grouped by category, product, and date
- [X] T008 [US1] Declare Tree view `view_panaderia_reporte_ventas_tree` and Search view `view_panaderia_reporte_ventas_search` with filters "Ventas de Hoy" and "Este Mes" in `Modulo_Odoo/views/reporte_views.xml`
- [X] T009 [US1] Declare Window Action `action_panaderia_reporte_ventas_dia` and Menu `menu_panaderia_reporte_ventas_dia` in `Modulo_Odoo/views/reporte_views.xml`

---

## Phase 4: User Story 2 - Ranking de Productos Más Vendidos (Priority: P2)

**Goal**: Proveer una vista gráfica interactiva (diagrama de barras) y ranking de productos ordenados por volumen de piezas vendidas y montos generados.

**Independent Test**: Registrar venta de 100 Pan Francés y 10 Pasteles Selva Negra; abrir Panadería $\to$ Reportes $\to$ Productos Más Vendidos; verificar que Pan Francés encabeza el ranking con la barra más alta.

### Tests for User Story 2 ⚠️
- [X] T010 [P] [US2] Create automated unit test verifying top selling products ranking sorting order in `Modulo_Odoo/tests/test_reporte.py`

### Implementation for User Story 2
- [X] T011 [US2] Declare Graph view `view_panaderia_reporte_ventas_graph` (type bar) measuring `cantidad_vendida` by `producto_id` in `Modulo_Odoo/views/reporte_views.xml`
- [X] T012 [US2] Declare Window Action `action_panaderia_reporte_top_productos` and Menu `menu_panaderia_reporte_top_productos` in `Modulo_Odoo/views/reporte_views.xml`

---

## Phase 5: User Story 3 - Alertas de Stock Bajo y Reabastecimiento (Priority: P3)

**Goal**: Brindar un listado pre-filtrado inmediato de todos los productos donde `cantidad_disponible <= stock_minimo` con botón de ajuste rápido para reposición física.

**Independent Test**: Configurar 3 productos con existencias por debajo del mínimo; abrir Panadería $\to$ Reportes $\to$ Stock Bajo / Alertas; verificar que aparecen exactamente esos 3 productos con badges y botón de ajuste.

### Tests for User Story 3 ⚠️
- [X] T013 [P] [US3] Create automated unit test verifying low stock alert domain filtering and critical status detection in `Modulo_Odoo/tests/test_reporte.py`

### Implementation for User Story 5
- [X] T014 [US3] Declare specialized Tree view `view_panaderia_producto_stock_bajo_tree` in `Modulo_Odoo/views/reporte_views.xml` displaying SKU, name, available stock, minimum stock, alert badge, and quick action button `action_ajustar_stock`
- [X] T015 [US3] Declare Window Action `action_panaderia_reporte_stock_bajo` and Menu `menu_panaderia_reporte_stock_bajo` in `Modulo_Odoo/views/reporte_views.xml`

---

## Phase 6: User Story 4 - Resumen Operativo Diario Imprimible (QWeb PDF) (Priority: P4)

**Goal**: Permitir la impresión de un documento PDF de una sola página que resume las métricas clave de ventas del día, el ranking de productos y la tabla de alertas de inventario.

**Independent Test**: Ejecutar acción "Imprimir Resumen Diario (PDF)", seleccionar fecha actual y verificar que se genera el documento PDF con diseño profesional, indicadores clave y alertas.

### Tests for User Story 4 ⚠️
- [X] T016 [P] [US4] Create automated unit test verifying QWeb report parser `_get_report_values()` and PDF action in `Modulo_Odoo/tests/test_reporte.py`

### Implementation for User Story 4
- [X] T017 [US4] Implement TransientModel `PanaderiaReporteDiarioWizard` and AbstractModel `ReporteDiarioParser` in `Modulo_Odoo/models/reporte_panaderia.py`
- [X] T018 [US4] Declare QWeb report action `action_report_resumen_diario` and QWeb template `reporte_diario_template` in `Modulo_Odoo/report/reporte_diario_template.xml`
- [X] T019 [US4] Declare wizard form view `view_panaderia_reporte_diario_wizard_form`, window action, and menu item `menu_panaderia_reporte_diario_pdf` in `Modulo_Odoo/views/reporte_views.xml`

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Test procedure documentation, quality checks, and end-to-end test execution.

- [X] T020 [P] Create manual test procedure document `docs/test-procedures/test-procedure-5.1.1.md` mapping 1:1 to Acceptance Criteria Scenarios 1, 2, and 3
- [X] T021 [P] Create quickstart documentation `specs/5-reports/5.1-operational-reports/5.1.1-daily-sales-and-stock-reports/quickstart.md`
- [X] T022 [P] Create use case specification `specs/5-reports/5.1-operational-reports/5.1.1-daily-sales-and-stock-reports/use-case-5.1.1.md`
