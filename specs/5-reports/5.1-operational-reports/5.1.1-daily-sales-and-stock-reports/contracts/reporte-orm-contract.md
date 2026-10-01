# Contract: Reportes ORM Model & Security Interface (SPEC-5.1.1)

## Feature: Reportes Operativos Diarios y Alertas de Stock
**Module**: `Modulo_Odoo`  
**File**: `Modulo_Odoo/models/reporte_panaderia.py`

---

## 1. ORM Model Contract: `panaderia.reporte.ventas`

```python
class PanaderiaReporteVentas(models.Model):
    _name = 'panaderia.reporte.ventas'
    _description = 'Análisis de Ventas de Panadería'
    _auto = False
    _order = 'fecha desc, total_ingresos desc, id desc'

    fecha = fields.Date(string='Fecha', readonly=True)
    producto_id = fields.Many2one('panaderia.producto', string='Producto', readonly=True)
    categoria_id = fields.Many2one('panaderia.categoria', string='Categoría', readonly=True)
    cantidad_vendida = fields.Float(string='Unidades Vendidas', readonly=True, digits=(10, 2))
    total_ingresos = fields.Float(string='Total Ingresos ($)', readonly=True, digits=(10, 2))
    precio_promedio = fields.Float(string='Precio Promedio ($)', readonly=True, digits=(10, 2))
    ordenes_count = fields.Integer(string='Órdenes', readonly=True)

    def init(self):
        """Creates or replaces the SQL view in PostgreSQL."""
        ...
```

### Invariants & Preconditions:
1. `_auto = False`: The table is maintained solely as a PostgreSQL view; Odoo ORM will not create table columns or execute DDL updates automatically.
2. Only confirmed sales (`v.state = 'confirmed'`) are included in aggregations.
3. Read-only model: `create`, `write`, and `unlink` are not supported on this model.

---

## 2. ORM Wizard Contract: `panaderia.reporte.diario.wizard`

```python
class PanaderiaReporteDiarioWizard(models.TransientModel):
    _name = 'panaderia.reporte.diario.wizard'
    _description = 'Asistente de Resumen Operativo Diario'

    fecha = fields.Date(string='Fecha del Reporte', default=fields.Date.context_today, required=True)

    def action_print_pdf(self):
        """Returns the report action dictionary for Modulo_Odoo.action_report_resumen_diario."""
        ...
```

---

## 3. Access Control List Contract (`ir.model.access.csv`)

| Model | Group | Read | Write | Create | Unlink |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `model_panaderia_reporte_ventas` | `group_panaderia_user` | 1 | 0 | 0 | 0 |
| `model_panaderia_reporte_ventas` | `group_panaderia_manager` | 1 | 0 | 0 | 0 |
| `model_panaderia_reporte_diario_wizard` | `group_panaderia_user` | 1 | 1 | 1 | 1 |
| `model_panaderia_reporte_diario_wizard` | `group_panaderia_manager` | 1 | 1 | 1 | 1 |
