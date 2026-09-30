# Contract: Odoo ORM & Model Interface Specification - `panaderia.producto`

**Feature**: `SPEC-1.1.1: Gestión de Catálogo de Productos`  
**Contract Type**: ORM API & Access Control Contract  
**Target Module**: `Modulo_Odoo/models/producto.py`, `Modulo_Odoo/security/ir.model.access.csv`  

---

## 1. ORM Methods & Interface Signature

### 1.1. Model Definition Contract

```python
class PanaderiaProducto(models.Model):
    _name = 'panaderia.producto'
    _description = 'Producto de Panadería'
    _order = 'name asc, id desc'
```

### 1.2. Method Contracts

#### A. `_compute_margenes`
* **Decorator**: `@api.depends('precio_venta', 'costo')`
* **Signature**: `def _compute_margenes(self) -> None`
* **Preconditions**: `self` contains one or more `panaderia.producto` records.
* **Postconditions**:
  * Sets `record.margen_bruto = record.precio_venta - record.costo`
  * Sets `record.porcentaje_margen = (record.margen_bruto / record.precio_venta) * 100.0` if `record.precio_venta > 0` else `0.0`.

#### B. `_check_precios_y_costos`
* **Decorator**: `@api.constrains('precio_venta', 'costo')`
* **Signature**: `def _check_precios_y_costos(self) -> None`
* **Exceptions Raised**: `odoo.exceptions.ValidationError`
  * Message when `precio_venta <= 0.0`: `"El precio de venta debe ser un valor estrictamente mayor a $0.00."`
  * Message when `costo < 0.0`: `"El costo de producción no puede ser un valor negativo."`

#### C. `unlink` (Deletion Safeguard)
* **Signature**: `def unlink(self) -> bool`
* **Behavior**:
  * Checks if any record in `self` is referenced by existing sale lines (`panaderia.venta.linea`).
  * If referenced: Raises `odoo.exceptions.UserError("No puede eliminar un producto que ya cuenta con historial de ventas. En su lugar, utilice la opción de archivar.")`.
  * If not referenced: Calls `super(PanaderiaProducto, self).unlink()`.

---

## 2. Security & Access Control Contract (`ir.model.access.csv`)

| id | name | model_id:id | group_id:id | perm_read | perm_write | perm_create | perm_unlink |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `access_panaderia_producto_user` | `panaderia.producto.user` | `model_panaderia_producto` | `Modulo_Odoo.group_panaderia_user` | 1 | 1 | 1 | 0 |
| `access_panaderia_producto_manager` | `panaderia.producto.manager` | `model_panaderia_producto` | `Modulo_Odoo.group_panaderia_manager` | 1 | 1 | 1 | 1 |

---

## 3. Seed Data Contract (`data/producto_data.xml`)

The module must ship with default seed products to ensure turnkey verification:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
        <record id="producto_pan_frances" model="panaderia.producto">
            <field name="name">Pan Francés Tradicional</field>
            <field name="codigo">PAN-001</field>
            <field name="categoria_id" ref="categoria_pan"/>
            <field name="costo">0.05</field>
            <field name="precio_venta">0.10</field>
            <field name="descripcion">Pieza de pan francés crujiente horneado diariamente.</field>
            <field name="active">True</field>
        </record>

        <record id="producto_selva_negra" model="panaderia.producto">
            <field name="name">Pastel Selva Negra</field>
            <field name="codigo">PAS-001</field>
            <field name="categoria_id" ref="categoria_pastel"/>
            <field name="costo">8.50</field>
            <field name="precio_venta">16.00</field>
            <field name="descripcion">Pastel de chocolate con relleno de cerezas y crema chantilly.</field>
            <field name="active">True</field>
        </record>

        <record id="producto_galleta_avena" model="panaderia.producto">
            <field name="name">Galleta de Avena y Miel</field>
            <field name="codigo">GAL-001</field>
            <field name="categoria_id" ref="categoria_galleta"/>
            <field name="costo">0.35</field>
            <field name="precio_venta">0.75</field>
            <field name="descripcion">Galleta artesanal de avena integral endulzada con miel natural.</field>
            <field name="active">True</field>
        </record>

        <record id="producto_cafe_americano" model="panaderia.producto">
            <field name="name">Café Americano 12oz</field>
            <field name="codigo">BEB-001</field>
            <field name="categoria_id" ref="categoria_bebida"/>
            <field name="costo">0.40</field>
            <field name="precio_venta">1.50</field>
            <field name="descripcion">Café recién pasado elaborado con granos selectos de altura.</field>
            <field name="active">True</field>
        </record>
    </data>
</odoo>
```
