# UI & XML Views Contract: Registro y Proceso de Ventas Esencial

**Feature**: `SPEC-2.1.1: Registro y Proceso de Ventas Esencial`  
**Target File**: `Modulo_Odoo/views/venta_views.xml`  

---

## 1. Views Hierarchy & Structure

### 1.1. Form View (`view_panaderia_venta_form`)
* **Target Record ID**: `view_panaderia_venta_form`
* **Model**: `panaderia.venta`
* **Layout Requirements**:
  * **Header**:
    * Action button: "Confirmar Venta" (`type="object"`, `name="action_confirm"`, `class="oe_highlight"`, visible only in `state == 'draft'`).
    * Action button: "Cancelar" (`type="object"`, `name="action_cancel"`, visible in `state in ('draft', 'confirmed')`).
    * Action button: "Cambiar a Borrador" (`type="object"`, `name="action_draft"`, visible in `state == 'cancelled'`).
    * Statusbar widget: `statusbar_visible="draft,confirmed,cancelled"`, `widget="statusbar"`.
  * **Sheet**:
    * Smart Button Box (`oe_button_box`):
      * Stat Button for Factura: Links to `factura_id`, icon `fa-pencil-square-o`, visible when `factura_id != False`.
    * Title Area:
      * `<h1>` with `field name="name"` (Folio).
    * Group with 2 columns:
      * Left: `cliente_id` (context to show name), `fecha` (datetime).
      * Right: `state` (readonly), `factura_id` (readonly).
    * Notebook / Page:
      * Page "Líneas de la Orden":
        * Field `linea_ids` with nested `<tree editable="bottom">`:
          * `producto_id`: required, domain `[('active', '=', True)]`.
          * `cantidad`: numeric input.
          * `precio_unitario`: numeric input with monetary format.
          * `subtotal`: readonly computed subtotal with monetary format.
      * Page "Otras Informaciones":
        * Audit fields (`create_uid`, `create_date`, `write_uid`, `write_date`).
    * Summary Group / Footer:
      * Right-aligned `group class="oe_subtotal_footer oe_right"`:
        * Field `total`: prominent monetary widget `widget="monetary"`, large font.

```xml
<record id="view_panaderia_venta_form" model="ir.ui.view">
    <field name="name">panaderia.venta.form</field>
    <field name="model">panaderia.venta</field>
    <field name="arch" type="xml">
        <form string="Orden de Venta de Panadería">
            <header>
                <button name="action_confirm" string="Confirmar Venta" type="object"
                        class="oe_highlight" states="draft"/>
                <button name="action_cancel" string="Cancelar" type="object"
                        states="draft,confirmed" confirm="¿Está seguro de que desea cancelar esta venta?"/>
                <button name="action_draft" string="Volver a Borrador" type="object"
                        states="cancelled"/>
                <field name="state" widget="statusbar" statusbar_visible="draft,confirmed,cancelled"/>
            </header>
            <sheet>
                <div class="oe_button_box" name="button_box">
                    <button name="action_view_factura" type="object" class="oe_stat_button"
                            icon="fa-pencil-square-o" attrs="{'invisible': [('factura_id', '=', False)]}">
                        <div class="o_stat_info">
                            <span class="o_stat_text">Factura</span>
                        </div>
                    </button>
                </div>
                <div class="oe_title">
                    <span class="o_form_label">Orden de Venta</span>
                    <h1>
                        <field name="name" readonly="1"/>
                    </h1>
                </div>
                <group>
                    <group>
                        <field name="cliente_id" attrs="{'readonly': [('state', '!=', 'draft')]}"/>
                        <field name="fecha" attrs="{'readonly': [('state', '!=', 'draft')]}"/>
                    </group>
                    <group>
                        <field name="factura_id" readonly="1" attrs="{'invisible': [('factura_id', '=', False)]}"/>
                    </group>
                </group>
                <notebook>
                    <page string="Líneas de la Venta" name="lineas_venta">
                        <field name="linea_ids" attrs="{'readonly': [('state', '!=', 'draft')]}">
                            <tree string="Detalle de Venta" editable="bottom">
                                <field name="producto_id"/>
                                <field name="cantidad"/>
                                <field name="precio_unitario"/>
                                <field name="subtotal" sum="Total de Líneas"/>
                            </tree>
                        </field>
                        <group class="oe_subtotal_footer oe_right">
                            <field name="total" class="oe_subtotal_footer_separator" widget="monetary"/>
                        </group>
                    </page>
                </notebook>
            </sheet>
        </form>
    </field>
</record>
```

---

### 1.2. Tree View (`view_panaderia_venta_tree`)
* **Target Record ID**: `view_panaderia_venta_tree`
* **Model**: `panaderia.venta`
* **Decorators**:
  * `decoration-info="state == 'draft'"`
  * `decoration-success="state == 'confirmed'"`
  * `decoration-muted="state == 'cancelled'"`

```xml
<record id="view_panaderia_venta_tree" model="ir.ui.view">
    <field name="name">panaderia.venta.tree</field>
    <field name="model">panaderia.venta</field>
    <field name="arch" type="xml">
        <tree string="Órdenes de Venta"
              decoration-info="state == 'draft'"
              decoration-success="state == 'confirmed'"
              decoration-muted="state == 'cancelled'">
            <field name="name"/>
            <field name="fecha"/>
            <field name="cliente_id"/>
            <field name="total" sum="Total Ventas" widget="monetary"/>
            <field name="state" widget="badge"
                   decoration-info="state == 'draft'"
                   decoration-success="state == 'confirmed'"
                   decoration-danger="state == 'cancelled'"/>
        </tree>
    </field>
</record>
```

---

### 1.3. Search View (`view_panaderia_venta_search`)
* **Filters**:
  * "Borrador": `domain="[('state', '=', 'draft')]"`
  * "Confirmadas": `domain="[('state', '=', 'confirmed')]"`
  * "Canceladas": `domain="[('state', '=', 'cancelled')]"`
  * "Hoy": `domain="[('fecha', '&gt;=', datetime.datetime.now().strftime('%Y-%m-%d 00:00:00'))]"`
* **Group By**:
  * Agrupar por Cliente: `context="{'group_by': 'cliente_id'}"`
  * Agrupar por Estado: `context="{'group_by': 'state'}"`
  * Agrupar por Fecha: `context="{'group_by': 'fecha:day'}"`

---

### 1.4. Window Action & Menu Hierarchy

```xml
<!-- Window Action -->
<record id="action_panaderia_venta" model="ir.actions.act_window">
    <field name="name">Órdenes de Venta</field>
    <field name="res_model">panaderia.venta</field>
    <field name="view_mode">tree,form</field>
    <field name="search_view_id" ref="view_panaderia_venta_search"/>
    <field name="help" type="html">
        <p class="o_view_nocontent_smiling_face">
            ¡Registra tu primera orden de venta de panadería!
        </p>
    </field>
</record>

<!-- Menú: Panadería > Ventas > Órdenes de Venta -->
<menuitem id="menu_panaderia_ventas_root"
          name="Ventas"
          parent="menu_panaderia_root"
          sequence="20"/>

<menuitem id="menu_panaderia_venta_ordenes"
          name="Órdenes de Venta"
          parent="menu_panaderia_ventas_root"
          action="action_panaderia_venta"
          sequence="10"/>
```
