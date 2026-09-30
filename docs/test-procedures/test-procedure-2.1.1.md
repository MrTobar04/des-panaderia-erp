# Procedimiento de Prueba: SPEC-2.1.1 Registro y Proceso de Ventas Esencial

**Documento ID**: `test-procedure-2.1.1.md`  
**Especificación Asociada**: [`specs/2-sales/2.1-sales-orders/2.1.1-order-management/spec.md`](file:///c:/Users/Inspiron/Desktop/des-panaderia-erp/specs/2-sales/2.1-sales-orders/2.1.1-order-management/spec.md)  
**Módulo Objetivo**: `Modulo_Odoo` (`panaderia.venta`, `panaderia.venta.linea`)  
**Versión**: 1.0.0  
**Fecha de Ejecución**: 2026-09-30  
**Evaluado por**: Antigravity Automated Verification Agent  
**Overall Result:** ☑ APPROVED  ☐ REJECTED  ☐ BLOCKED  

---

## 1. Resumen y Objetivos de Verificación

El presente procedimiento de prueba valida de extremo a extremo el flujo operativo de registro y confirmación de ventas en el ERP de Panadería "Delicias Dulces". Se evalúan la creación de órdenes de venta en mostrador, el autocompletado de precios de venta desde el catálogo, el cálculo reactivo de subtotales por línea y total general, la confirmación de venta con generación secuencial (`VEN-XXXX`), la validación y decremento atómico de existencias en catálogo, la emisión automática de factura simple vinculada, y las restricciones de inmutabilidad y cancelación.

---

## 2. Prerrequisitos de Entorno

- [x] Contenedores `panaderia_odoo_db` y `panaderia_odoo_web` en ejecución y saludables (`docker compose up -d`).
- [x] Base de datos `panaderia_db` inicializada con catálogo de productos base (`SPEC-1.1.1`).
- [x] Módulo `Modulo_Odoo` actualizado con los modelos `panaderia.venta` y `panaderia.venta.linea`.
- [x] Interfaz web disponible en `http://localhost:8069`.

---

## 3. Casos de Prueba de Interfaz de Usuario y ORM

### Caso de Prueba 01: Creación de Venta en Mostrador y Cálculo de Totales (Escenario 1)
* **Objetivo**: Confirmar que un cajero puede registrar una venta, seleccionar cliente y agregar productos, con cálculo automático de subtotales y total.
* **Pasos de Ejecución**:
  1. Ingresar a **Panadería** $\to$ **Ventas** $\to$ **Órdenes de Venta**.
  2. Hacer clic en **Nuevo**.
  3. Seleccionar cliente *"Cliente Mostrador"* o crear un contacto.
  4. En la grilla de líneas agregar:
     - 10 unidades de *"Pan Francés Tradicional"* ($0.10 c/u).
     - 1 unidad de *"Pastel Selva Negra"* ($15.00 c/u).
  5. Guardar la orden.
* **Resultados Esperados**:
  - [x] Subtotal línea 1 calcula `$1.00`.
  - [x] Subtotal línea 2 calcula `$15.00`.
  - [x] Total de la venta calcula `$16.00`.
  - [x] Folio inicial muestra `Nuevo` y estado es `Borrador`.
* **Result:** ☑ PASSED  ☐ FAILED  

---

### Caso de Prueba 02: Confirmación de Venta y Descuento de Stock (Escenario 2)
* **Objetivo**: Validar que al presionar "Confirmar Venta" se asigna folio correlativo `VEN-XXXX`, se decrementa el stock en inventario y se crea la factura.
* **Pasos de Ejecución**:
  1. Con la orden de venta anterior en estado `Borrador`, verificar existencias iniciales del producto (50 unidades).
  2. Hacer clic en el botón de cabecera **Confirmar Venta**.
  3. Observar el estado y el folio generado.
  4. Revisar la vista de Productos en **Inventario** $\to$ **Productos**.
* **Resultados Esperados**:
  - [x] Estado de la orden pasa a `Confirmada`.
  - [x] Folio cambia a secuencia `VEN-XXXX` (ej. `VEN-0001`).
  - [x] Existencias de *"Pan Francés Tradicional"* bajan de 50 a 40 unidades.
  - [x] Se genera la factura asociada con estado `Pendiente` y monto `$16.00`.
* **Result:** ☑ PASSED  ☐ FAILED  

---

### Caso de Prueba 03: Restricción de Edición e Inmutabilidad (Escenario 3)
* **Objetivo**: Validar que una orden confirmada no permita modificaciones ni eliminación.
* **Pasos de Ejecución**:
  1. Abrir la orden confirmada `VEN-0001`.
  2. Intentar editar el cliente, fecha o cantidades en las líneas.
  3. Intentar suprimir la orden.
* **Resultados Esperados**:
  - [x] Campos de la vista en modo solo lectura (`readonly`).
  - [x] El ORM rechaza intentos de modificación (`write`) o eliminación (`unlink`) emitiendo `UserError`.
* **Result:** ☑ PASSED  ☐ FAILED  

---

### Caso de Prueba 04: Cancelación y Reversión de Stock
* **Objetivo**: Validar que al cancelar una orden confirmada, se restablecen las cantidades de stock del catálogo.
* **Pasos de Ejecución**:
  1. En la orden confirmada, hacer clic en **Cancelar**.
  2. Confirmar el diálogo de advertencia.
  3. Consultar las existencias del producto en catálogo.
* **Resultados Esperados**:
  - [x] Estado pasa a `Cancelada`.
  - [x] El stock previamente descontado se reintegra al catálogo.
  - [x] La factura asociada pasa a estado `Cancelada`.
* **Result:** ☑ PASSED  ☐ FAILED  

---

## 4. Trazabilidad de Requerimientos

| Requerimiento Spec | Caso de Prueba | Cobertura en Test Unitario | Estado |
| :--- | :--- | :--- | :--- |
| **Escenario 1 (Totales y Subtotales)** | Caso 01 | `test_01_create_sale_and_subtotals` | PASSED |
| **Escenario 2 (Confirmación y Stock)** | Caso 02 | `test_03_action_confirm_sequence_and_stock` | PASSED |
| **Escenario 3 (Inmutabilidad)** | Caso 03 | `test_05_immutability_on_confirmed_order` | PASSED |
| **Validación Cantidades/Precios** | Reglas de negocio | `test_02_invalid_line_values_raise_error` | PASSED |
| **Stock Insuficiente** | Reglas de negocio | `test_04_insufficient_stock_raises_validation_error` | PASSED |
| **Cancelación y Reversión** | Ciclo de vida | `test_06_action_cancel_and_stock_reversion` | PASSED |
