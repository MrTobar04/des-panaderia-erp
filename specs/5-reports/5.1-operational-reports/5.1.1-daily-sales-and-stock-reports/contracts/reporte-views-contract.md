# Contract: Reportes Views, Actions and Menus (SPEC-5.1.1)

## Feature: Reportes Operativos Diarios y Alertas de Stock
**Module**: `Modulo_Odoo`  
**File**: `Modulo_Odoo/views/reporte_views.xml` and `Modulo_Odoo/report/reporte_diario_template.xml`

---

## 1. Views Contract

1. **Pivot View (`view_panaderia_reporte_ventas_pivot`)**:
   - Model: `panaderia.reporte.ventas`
   - Rows: `categoria_id`, `producto_id`
   - Columns: `fecha` (interval: `day`)
   - Measures: `cantidad_vendida`, `total_ingresos`

2. **Graph View (`view_panaderia_reporte_ventas_graph`)**:
   - Model: `panaderia.reporte.ventas`
   - Type: `bar`
   - Dimension: `producto_id`
   - Measure: `cantidad_vendida`

3. **Tree View (`view_panaderia_reporte_ventas_tree`)**:
   - Model: `panaderia.reporte.ventas`
   - Columns: `fecha`, `producto_id`, `categoria_id`, `cantidad_vendida` (sum), `total_ingresos` (sum, widget monetary), `precio_promedio` (monetary), `ordenes_count` (sum)
   - Attributes: `create="false"`, `edit="false"`, `delete="false"`

4. **Search View (`view_panaderia_reporte_ventas_search`)**:
   - Fields: `producto_id`, `categoria_id`
   - Filters: `filter_today` (`fecha = context_today`), `filter_this_month`
   - Group by: `group_by_producto`, `group_by_categoria`, `group_by_fecha_day`, `group_by_fecha_month`

5. **Stock Bajo Tree View (`view_panaderia_producto_stock_bajo_tree`)**:
   - Model: `panaderia.producto`
   - Columns: `codigo`, `name`, `categoria_id`, `cantidad_disponible`, `stock_minimo`, `estado_stock` (badge)
   - Action Button: `action_ajustar_stock` (Reabastecer)

---

## 2. Window Actions Contract

| Action ID | Name | Model | View Mode | Context / Domain |
| :--- | :--- | :--- | :--- | :--- |
| `action_panaderia_reporte_ventas_dia` | Ventas del Día | `panaderia.reporte.ventas` | `pivot,graph,tree` | Default filter: `filter_today`, Default group: `categoria_id` |
| `action_panaderia_reporte_top_productos` | Productos Más Vendidos | `panaderia.reporte.ventas` | `graph,pivot,tree` | Default group: `producto_id` |
| `action_panaderia_reporte_stock_bajo` | Alertas de Stock Bajo | `panaderia.producto` | `tree,form` | Domain: `[('alerta_stock_bajo', '=', True), ('active', '=', True)]` |
| `action_panaderia_reporte_diario_wizard` | Imprimir Resumen Diario (PDF) | `panaderia.reporte.diario.wizard` | `form` | Target: `new` (modal dialog) |

---

## 3. Menu Structure Contract

```text
Panadería (menu_panaderia_root, sequence=10)
 ├── Inventario (sequence=10)
 ├── Ventas (sequence=20)
 ├── Facturación (sequence=30)
 └── Reportes (menu_panaderia_reportes_root, sequence=40)
      ├── Ventas del Día (menu_panaderia_reporte_ventas_dia, sequence=10)
      ├── Productos Más Vendidos (menu_panaderia_reporte_top_productos, sequence=20)
      ├── Stock Bajo / Alertas (menu_panaderia_reporte_stock_bajo, sequence=30)
      └── Imprimir Resumen Diario (PDF) (menu_panaderia_reporte_diario_pdf, sequence=40)
```
