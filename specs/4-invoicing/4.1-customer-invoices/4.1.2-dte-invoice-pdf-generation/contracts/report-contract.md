# Phase 1: Report & Interface Contracts — Factura PDF DTE

**Feature**: `specs/4-invoicing/4.1-customer-invoices/4.1.2-dte-invoice-pdf-generation`  
**Date**: 2026-10-01  
**Status**: Complete

---

## 1. Contrato de Acción de Reporte Odoo QWeb (`ir.actions.report`)

```xml
<record id="action_report_factura_dte" model="ir.actions.report">
    <field name="name">Factura Electrónica DTE (PDF)</field>
    <field name="model">panaderia.factura</field>
    <field name="report_type">qweb-pdf</field>
    <field name="report_name">panaderia.reporte_factura_dte</field>
    <field name="report_file">panaderia.reporte_factura_dte</field>
    <field name="print_report_name">'Factura_DTE_%s' % (object.name or 'Borrador')</field>
    <field name="binding_model_id" ref="model_panaderia_factura"/>
    <field name="binding_type">report</field>
</record>
```

---

## 2. Contrato de Datos del Documento (Payload DTE)

Cada factura expone al motor de renderizado QWeb la siguiente estructura canónica:

```json
{
  "identificacion": {
    "version": 1,
    "ambiente": "01",
    "tipoDte": "01",
    "numeroControl": "DTE-01-M001P001-000000000000001",
    "codigoGeneracion": "4D042782-DC9B-4709-876C-11EC48CD3900",
    "tipoModelo": 1,
    "tipoOperacion": 1,
    "fecEmi": "2026-10-01",
    "horEmi": "21:00:00",
    "tipoMoneda": "USD"
  },
  "emisor": {
    "nit": "06140803841010",
    "nrc": "1061224",
    "nombre": "DELICIAS DULCES S.A. DE C.V.",
    "codActividad": "10711",
    "descActividad": "ELABORACIÓN DE PRODUCTOS DE PANADERÍA",
    "nombreComercial": "PANADERÍA DELICIAS DULCES",
    "telefono": "2234-5678",
    "correo": "ventas@deliciasdulces.sv",
    "direccion": "Avenida Los Próceres #120, Local 4, San Salvador, El Salvador",
    "logo_path": "/panaderia/static/src/img/logo_delicias_dulces.png"
  },
  "receptor": {
    "nombre": "Alejandro Javier Hernández Orellana",
    "numDocumento": "06202964-6",
    "tipoDocumento": "DUI/NIT",
    "direccion": "Urb. El limon, pje 15, pol 30, casa # 3",
    "correo": "pedrada914@gmail.com"
  },
  "cuerpoDocumento": [
    {
      "numItem": 1,
      "cantidad": 1.0,
      "uniMedida": "Otra",
      "descripcion": "Pastel de Chocolate Fiesta",
      "precioUni": 15.50,
      "montoDescu": 0.0,
      "ventaNoSuj": 0.0,
      "ventaExenta": 0.0,
      "ventaGravada": 15.50
    }
  ],
  "resumen": {
    "totalNoSuj": 0.0,
    "totalExenta": 0.0,
    "totalGravada": 15.50,
    "subTotalVentas": 15.50,
    "ivaCalculado": 1.78,
    "subTotal": 15.50,
    "ivaRete1": 0.0,
    "reteRenta": 0.0,
    "montoTotalOperacion": 15.50,
    "totalPagar": 15.50,
    "totalLetras": "QUINCE CON 50/100 USD",
    "condicionOperacion": "CONTADO"
  }
}
```

---

## 3. Contratos de Interfaz de Usuario (UI Actions)

### 3.1. En Formulario de Factura (`views/factura_views.xml`)
- Botón en `<header>`:
  ```xml
  <button name="action_print_factura_dte" 
          string="Imprimir Factura DTE" 
          type="object" 
          class="btn-primary" 
          icon="fa-print"/>
  ```

### 3.2. En Formulario de Venta (`views/venta_views.xml`)
- Botón en `<header>`:
  ```xml
  <button name="action_print_factura_dte" 
          string="Imprimir Factura DTE" 
          type="object" 
          class="btn-secondary" 
          icon="fa-print" 
          attrs="{'invisible': [('factura_id', '=', False)]}"/>
  ```
