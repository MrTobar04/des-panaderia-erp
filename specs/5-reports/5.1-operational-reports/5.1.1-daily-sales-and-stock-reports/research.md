# Phase 0: Technical Research & Architecture Decisions (SPEC-5.1.1)

## Feature: Reportes Operativos Diarios y Alertas de Stock
**Module**: `Modulo_Odoo`  
**Spec**: [`specs/5-reports/5.1-operational-reports/5.1.1-daily-sales-and-stock-reports/spec.md`](spec.md)

---

## 1. Context & Business Requirements

Panadería "Delicias Dulces" requires real-time operational insights into daily sales volume, product demand rankings, and immediate inventory replenishment alerts. Business owners and managers need:
1. **Daily Sales Performance**: Aggregated revenue, total confirmed order count, and sales breakdown by product and category for the current business day.
2. **Top Selling Products (Demand Ranking)**: Instant visual ranking (bar charts and pivot tables) identifying high-volume vs high-revenue items to optimize baking schedules.
3. **Low Stock Alerts (Replenishment Warning)**: Immediate list of active products with stock levels $\le$ configured minimums (`cantidad_disponible <= stock_minimo`) with direct replenishment actions.
4. **Single-Page Printable Summary (QWeb PDF)**: Concise executive snapshot summarizing the day's KPIs, top sellers, and critical stock shortages.

---

## 2. Technical Evaluation & Decisions

### Decision 1: SQL View ORM Model (`_auto = False`) vs Stored Computational Tables
- **Alternative A**: Create standard PostgreSQL tables and populate them via nocturnal batch cron jobs or event triggers.
  - *Cons*: Stale data during the day, complex cache invalidation, unnecessary storage duplication.
- **Alternative B (Chosen)**: Use Odoo's SQL View model pattern (`_name = 'panaderia.reporte.ventas'`, `_auto = False`, `init()` method creating `CREATE OR REPLACE VIEW panaderia_reporte_ventas AS SELECT ...`).
  - *Pros*: Zero latency, real-time aggregation upon query execution, native support for Odoo Pivot and Graph views, strict filtering on `state = 'confirmed'`.

### Decision 2: Graph & Pivot Views Configuration
- Configured Odoo standard analytical views:
  - `pivot`: Categoría as row group, Producto as row sub-group, Fecha as column group, measuring `cantidad_vendida` and `total_ingresos`.
  - `graph`: Bar graph displaying Top products ranked by units sold.
  - `search`: Pre-configured filters for "Ventas de Hoy" (`fecha = today`) and "Este Mes".

### Decision 3: Low Stock Filter & Dedicated Action
- Reuses `panaderia.producto` model with domain `[('alerta_stock_bajo', '=', True), ('active', '=', True)]`.
- Displays dedicated tree view highlighting products in critical state (`estado_stock in ('bajo', 'agotado')`) with direct button to trigger inventory adjustment wizard.

### Decision 4: QWeb PDF Daily Summary Architecture
- Uses a lightweight transient wizard (`panaderia.reporte.diario.wizard`) and an `AbstractModel` parser (`report.Modulo_Odoo.reporte_diario_template`) to fetch and calculate:
  - Total daily revenue, order count, and sold pieces.
  - Top 10 selling products of the day.
  - Current low-stock products table with status badges.
- Fits neatly on a single-page landscape or portrait summary.

---

## 3. Performance & Scaling Considerations

- Indexed columns on source tables (`panaderia_venta.fecha`, `panaderia_venta.state`, `panaderia_venta_linea.producto_id`, `panaderia_producto.categoria_id`).
- View queries use `min(l.id) AS id` and standard aggregate functions (`sum`, `count(DISTINCT v.id)`).
- Execution times for typical daily volume (500–2,000 lines) $< 20\text{ms}$.
