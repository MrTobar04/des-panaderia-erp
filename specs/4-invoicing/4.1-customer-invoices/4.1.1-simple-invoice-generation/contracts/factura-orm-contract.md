# ORM & Business Logic Contract: Generación de Facturas Simples

**Feature**: `SPEC-4.1.1: Generación de Facturas Simples`  
**Target File**: `Modulo_Odoo/models/factura.py`  
**Target Sequence**: `Modulo_Odoo/data/factura_sequence.xml`  
**Target Access**: `Modulo_Odoo/security/ir.model.access.csv`  

---

## 1. Model Definition & Method Signatures

### 1.1. `PanaderiaFactura` (`panaderia.factura`)

```python
class PanaderiaFactura(models.Model):
    _name = 'panaderia.factura'
    _description = 'Factura Simple de Panadería'
    _order = 'fecha_emision desc, name desc, id desc'

    name = fields.Char(string='Número de Factura', required=True, copy=False, readonly=True, default='Borrador', index=True)
    venta_id = fields.Many2one('panaderia.venta', string='Orden de Venta Origen', readonly=True, ondelete='set null', index=True)
    cliente_id = fields.Many2one('res.partner', string='Cliente', required=True, index=True)
    fecha_emision = fields.Datetime(string='Fecha de Emisión', default=fields.Datetime.now, required=True, index=True)
    fecha_pago = fields.Datetime(string='Fecha de Pago', readonly=True)
    monto_total = fields.Float(string='Monto Total ($)', required=True, digits=(10, 2))
    metodo_pago = fields.Selection([
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta de Débito / Crédito'),
        ('transferencia', 'Transferencia')
    ], string='Método de Pago', default='efectivo', required=True)
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('paid', 'Pagada'),
        ('cancelled', 'Cancelada')
    ], string='Estado de Pago', default='pending', required=True, index=True)
```

---

## 2. Public API Action Methods

### 2.1. `action_register_payment(self)`
* **Preconditions**:
  * Record must be in `state == 'pending'`.
  * If already `paid`, the method either performs a no-op or raises a warning.
* **Execution Steps**:
  1. Iterate over `self`.
  2. Write `state = 'paid'` and `fecha_pago = fields.Datetime.now()`.
* **Postconditions**:
  * `state == 'paid'`.
  * `fecha_pago` contains the timestamp of when the action was executed.
* **Exceptions**:
  * `UserError` if attempted on a `cancelled` invoice.

### 2.2. `action_cancel(self)`
* **Preconditions**:
  * Record must be in `state == 'pending'`.
* **Execution Steps**:
  1. Iterate over `self`.
  2. Write `state = 'cancelled'`.
* **Postconditions**:
  * `state == 'cancelled'`.
* **Exceptions**:
  * `UserError` if attempted on a `paid` invoice without manager overrides.

### 2.3. `action_view_venta(self)`
* **Preconditions**:
  * Record must have `venta_id` populated.
* **Execution Steps**:
  1. Ensure single record (`self.ensure_one()`).
  2. Return window action dict opening `panaderia.venta` in form view for `res_id = self.venta_id.id`.
* **Postconditions**:
  * Web client redirects user to the corresponding sale order form view.
* **Exceptions**:
  * `UserError` if `venta_id` is not set (e.g. invoice created manually).

---

## 3. ORM Lifecycle Hooks & Overrides

### 3.1. `@api.model create(self, vals)`
* If `vals.get('name', 'Borrador') == 'Borrador'` or not `vals.get('name')`:
  * Fetch next number from sequence: `self.env['ir.sequence'].next_by_code('panaderia.factura.secuencia') or 'FAC-0001'`.
* Delegate to `super(PanaderiaFactura, self).create(vals)`.

### 3.2. `write(self, vals)`
* Check if record is currently `state == 'paid'`.
* If true and any field in `{'monto_total', 'cliente_id', 'venta_id', 'fecha_emision'}` is present in `vals`:
  * Raise `UserError("No se pueden modificar los datos financieros de una factura que ya ha sido pagada.")`.
* Delegate to `super(PanaderiaFactura, self).write(vals)`.

### 3.3. `unlink(self)`
* Check if any record in `self` has `state == 'paid'`.
* If true:
  * Raise `UserError("No se pueden eliminar facturas en estado Pagada por motivos de auditoría contable.")`.
* Delegate to `super(PanaderiaFactura, self).unlink()`.

---

## 4. Model Constraints (`@api.constrains`)

### 4.1. `_check_monto_total(self)`
* Triggered on changes to `monto_total`.
* Raise `ValidationError` if `monto_total < 0.0`.

### 4.2. `_check_unique_active_invoice_per_sale(self)`
* Triggered on changes to `venta_id`.
* Raise `ValidationError` if another invoice with `state != 'cancelled'` already references the same `venta_id`.
