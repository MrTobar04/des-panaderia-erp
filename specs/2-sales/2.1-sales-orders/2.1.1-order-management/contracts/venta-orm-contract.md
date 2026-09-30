# ORM & Business Logic Contract: Registro y Proceso de Ventas Esencial

**Feature**: `SPEC-2.1.1: Registro y Proceso de Ventas Esencial`  
**Target File**: `Modulo_Odoo/models/venta.py`  
**Target Sequence**: `Modulo_Odoo/data/venta_sequence.xml`  
**Target Access**: `Modulo_Odoo/security/ir.model.access.csv`  

---

## 1. Model Definitions & Method Signatures

### 1.1. `PanaderiaVenta` (`panaderia.venta`)

```python
class PanaderiaVenta(models.Model):
    _name = 'panaderia.venta'
    _description = 'Orden de Venta de Panadería'
    _order = 'fecha desc, name desc, id desc'

    name = fields.Char(string='Folio', required=True, copy=False, readonly=True, default='Nuevo', index=True)
    cliente_id = fields.Many2one('res.partner', string='Cliente', required=True, index=True)
    fecha = fields.Datetime(string='Fecha de Venta', default=fields.Datetime.now, required=True, index=True)
    linea_ids = fields.One2many('panaderia.venta.linea', 'venta_id', string='Líneas de Venta')
    total = fields.Float(string='Total ($)', compute='_compute_total', store=True, digits=(10, 2))
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmada'),
        ('cancelled', 'Cancelada')
    ], string='Estado', default='draft', required=True, tracking=True, index=True)
    factura_id = fields.Many2one('panaderia.factura', string='Factura Asociada', readonly=True, copy=False)
```

### 1.2. Public API Action Methods

#### `action_confirm(self)`
* **Preconditions**:
  * Record must be in `state == 'draft'`.
  * `linea_ids` must not be empty.
* **Execution Steps**:
  1. Sequence assignment: If `name == 'Nuevo'`, fetch next value from sequence code `'panaderia.venta.secuencia'`.
  2. Inventory stock validation and reduction:
     ```python
     for line in self.linea_ids:
         if hasattr(line.producto_id, 'cantidad_disponible'):
             if line.producto_id.cantidad_disponible < line.cantidad:
                 raise ValidationError(
                     f"Stock insuficiente para el producto '{line.producto_id.name}'. "
                     f"Disponible: {line.producto_id.cantidad_disponible}, Requerido: {line.cantidad}."
                 )
             line.producto_id.cantidad_disponible -= line.cantidad
     ```
  3. Customer metric update: If `cliente_id` has `total_compras_panaderia`, update it.
  4. Invoice creation: If model `'panaderia.factura'` is in `self.env`, create invoice:
     ```python
     factura = self.env['panaderia.factura'].create({
         'venta_id': self.id,
         'cliente_id': self.cliente_id.id,
         'monto_total': self.total,
         'state': 'pending',
     })
     self.factura_id = factura.id
     ```
  5. State transition: Update `state = 'confirmed'`.
* **Postconditions**:
  * Order is locked against further line edits.
  * Stock of each product in lines is reduced.
  * `factura_id` is populated.

#### `action_cancel(self)`
* **Preconditions**:
  * Record state is `draft` (or `confirmed` if manager).
* **Execution Steps**:
  * If cancelling a `confirmed` order, reverse the stock decrement (`producto_id.cantidad_disponible += line.cantidad`).
  * Cancel associated invoice if present (`factura_id.state = 'cancelled'`).
  * Set `state = 'cancelled'`.

#### `action_draft(self)`
* **Preconditions**:
  * Record state is `cancelled`.
* **Execution Steps**:
  * Set `state = 'draft'`.

---

## 2. Immutability & Lifecycle Guardrails

### 2.1. Override `write(self, vals)`
```python
def write(self, vals):
    for order in self:
        if order.state == 'confirmed':
            # Bloquear cambios en datos esenciales de la venta confirmada
            forbidden_fields = {'cliente_id', 'linea_ids', 'fecha', 'total'}
            if any(f in vals for f in forbidden_fields):
                raise UserError("No se pueden alterar líneas, clientes ni importes de una orden de venta ya confirmada.")
    return super(PanaderiaVenta, self).write(vals)
```

### 2.2. Override `unlink(self)`
```python
def unlink(self):
    for order in self:
        if order.state == 'confirmed':
            raise UserError(f"No es posible eliminar la orden de venta confirmada '{order.name}'. Cancele la orden primero.")
    return super(PanaderiaVenta, self).unlink()
```

---

## 3. Sequence Definition Contract (`data/venta_sequence.xml`)

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
        <record id="seq_panaderia_venta" model="ir.sequence">
            <field name="name">Secuencia de Ventas Panadería</field>
            <field name="code">panaderia.venta.secuencia</field>
            <field name="prefix">VEN-</field>
            <field name="padding">4</field>
            <field name="number_next">1</field>
            <field name="number_increment">1</field>
        </record>
    </data>
</odoo>
```

---

## 4. Line Detail API Contract (`panaderia.venta.linea`)

```python
class PanaderiaVentaLinea(models.Model):
    _name = 'panaderia.venta.linea'
    _description = 'Línea de Venta de Panadería'
    _order = 'id asc'

    venta_id = fields.Many2one('panaderia.venta', string='Orden de Venta', required=True, ondelete='cascade', index=True)
    producto_id = fields.Many2one('panaderia.producto', string='Producto', required=True, ondelete='restrict', index=True)
    cantidad = fields.Float(string='Cantidad', required=True, default=1.0, digits=(10, 2))
    precio_unitario = fields.Float(string='Precio Unitario ($)', required=True, digits=(10, 2))
    subtotal = fields.Float(string='Subtotal ($)', compute='_compute_subtotal', store=True, digits=(10, 2))

    @api.onchange('producto_id')
    def _onchange_producto_id(self):
        if self.producto_id:
            self.precio_unitario = self.producto_id.precio_venta

    @api.depends('cantidad', 'precio_unitario')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = round(line.cantidad * line.precio_unitario, 2)

    @api.constrains('cantidad', 'precio_unitario')
    def _check_valores_linea(self):
        for line in self:
            if line.cantidad <= 0.0:
                raise ValidationError("La cantidad vendida debe ser mayor a 0.")
            if line.precio_unitario < 0.0:
                raise ValidationError("El precio unitario no puede ser negativo.")
```
