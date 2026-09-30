# Contract: Odoo XML Views & Menu Declarations Contract - `panaderia.producto`

**Feature**: `SPEC-1.1.1: Gestión de Catálogo de Productos`  
**Contract Type**: XML UI & Menu Hierarchy Contract  
**Target Module**: `Modulo_Odoo/views/producto_views.xml`  

---

## 1. Views Architecture

### 1.1. Tree / List View (`view_panaderia_producto_tree`)
* **XML ID**: `view_panaderia_producto_tree`
* **Model**: `panaderia.producto`
* **Layout Structure**:
  * `codigo` (SKU): Widget badge or mono text.
  * `name`: Principal bold column.
  * `categoria_id`: Tag/Many2one badge.
  * `costo`: Numeric format `$0.00`.
  * `precio_venta`: Numeric format `$0.00` with bold text.
  * `margen_bruto`: Numeric format `$0.00`.
  * `porcentaje_margen`: Numeric widget with `%`.
  * `active`: Widget boolean_toggle or badge.

### 1.2. Form View (`view_panaderia_producto_form`)
* **XML ID**: `view_panaderia_producto_form`
* **Model**: `panaderia.producto`
* **Layout Structure**:
  * **Header**: Contains archive/unarchive widget and alert ribbon if archived.
  * **Sheet**:
    * Widget `web_ribbon` for archived status (`title="Archivado" bg_color="bg-danger" invisible="active"`).
    * Title area with `name` (large font, placeholder "e.g. Pan Francés Tradicional").
    * Group 1 (Información General): `codigo`, `categoria_id`, `active`.
    * Group 2 (Precios y Costos): `costo`, `precio_venta`, `margen_bruto` (readonly), `porcentaje_margen` (readonly).
    * Notebook / Tabs:
      * Tab "Descripción y Notas": `descripcion` (Textarea).

### 1.3. Search & Filter View (`view_panaderia_producto_search`)
* **XML ID**: `view_panaderia_producto_search`
* **Model**: `panaderia.producto`
* **Filters**:
  * Search fields: `name`, `codigo`, `descripcion`.
  * Filters:
    * `filter_active`: `domain="[('active', '=', True)]"`, label "Activos" (default selected).
    * `filter_archived`: `domain="[('active', '=', False)]"`, label "Archivados".
  * Group By:
    * `group_by_categoria`: `context="{'group_by': 'categoria_id'}"`, label "Categoría".

---

## 2. Action & Menu Hierarchy Contract

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Action Definition -->
    <record id="action_panaderia_producto" model="ir.actions.act_window">
        <field name="name">Catálogo de Productos</field>
        <field name="res_model">panaderia.producto</field>
        <field name="view_mode">tree,form</field>
        <field name="search_view_id" ref="view_panaderia_producto_search"/>
        <field name="context">{'search_default_filter_active': 1}</field>
        <field name="help" type="html">
            <p class="o_view_nocontent_smiling_face">
                ¡Registra tu primer producto de panadería!
            </p>
            <p>
                Define los productos, categorías, costos de elaboración y precios de venta.
            </p>
        </field>
    </record>

    <!-- Menu Structure -->
    <!-- Top-level App Menu: Panadería -->
    <menuitem id="menu_panaderia_root" 
              name="Panadería" 
              sequence="10" 
              web_icon="Modulo_Odoo,static/description/icon.png"/>

    <!-- Category Menu: Inventario -->
    <menuitem id="menu_panaderia_inventario" 
              name="Inventario" 
              parent="menu_panaderia_root" 
              sequence="10"/>

    <!-- Action Menu: Productos -->
    <menuitem id="menu_panaderia_producto" 
              name="Productos" 
              parent="menu_panaderia_inventario" 
              action="action_panaderia_producto" 
              sequence="10"/>
</odoo>
```
