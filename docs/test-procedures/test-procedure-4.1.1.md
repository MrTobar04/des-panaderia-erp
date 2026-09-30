# Procedimiento de Prueba: SPEC-4.1.1 Generación de Facturas Simples

**Documento ID**: `test-procedure-4.1.1.md`  
**Especificación Asociada**: [`specs/4-invoicing/4.1-customer-invoices/4.1.1-simple-invoice-generation/spec.md`](../../specs/4-invoicing/4.1-customer-invoices/4.1.1-simple-invoice-generation/spec.md)  
**Módulo Objetivo**: `Modulo_Odoo` (`panaderia.factura`)  
**Versión**: 1.0.0  
**Fecha de Ejecución**: 2026-09-30  
**Evaluado por**: Antigravity Automated Verification Agent  
**Overall Result:** ☑ APPROVED  ☐ REJECTED  ☐ BLOCKED  

---

## 1. Resumen y Objetivos de Verificación

El presente procedimiento de prueba valida de extremo a extremo el flujo operativo de emisión, numeración y cobro de facturas simples en el ERP de Panadería "Delicias Dulces". Se evalúan la asignación correlativa automática (`FAC-XXXX`) mediante secuencia Odoo, la emisión automática vinculada tras la confirmación de ventas en mostrador (`SPEC-2.1.1`), el registro ágil de pagos en caja (`pending` $\to$ `paid`) con fecha exacta, la navegación bidireccional mediante Smart Buttons, y las políticas de inmutabilidad fiscal y auditoría contable.

---

## 2. Prerrequisitos de Entorno

- [x] Contenedores `panaderia_odoo_db` y `panaderia_odoo_web` en ejecución y saludables (`docker compose up -d`).
- [x] Base de datos `panaderia_db` inicializada con catálogo de productos y ventas (`SPEC-1.1.1` y `SPEC-2.1.1`).
- [x] Módulo `Modulo_Odoo` actualizado con el modelo `panaderia.factura`, secuencia `FAC-` y vistas XML.
- [x] Interfaz web disponible en `http://localhost:8069`.

---

## 3. Casos de Prueba de Interfaz de Usuario y ORM

### Caso de Prueba 01: Emisión Automática de Factura al Confirmar Venta (Escenario 1)
* **Objetivo**: Confirmar que al confirmar una orden de venta de mostrador se crea una factura vinculada con numeración `FAC-XXXX`, monto exacto y estado inicial `pending`.
* **Pasos de Ejecución**:
  1. Ingresar a **Panadería** $\to$ **Ventas** $\to$ **Órdenes de Venta**.
  2. Crear o abrir una orden de venta en borrador para *"Cliente Mostrador"* con un importe total de `$16.00`.
  3. Hacer clic en **Confirmar Venta**.
  4. Observar la cabecera de la orden de venta y hacer clic en el Smart Button **Factura**.
* **Resultados Esperados**:
  - [x] Se genera automáticamente un comprobante en `panaderia.factura`.
  - [x] El número de factura tiene formato `FAC-XXXX` (ej. `FAC-0001`).
  - [x] El cliente asociado y el monto total (`$16.00`) coinciden exactamente con la orden.
  - [x] El estado inicial del comprobante es `Pendiente` (`pending`).
* **Result:** ☑ PASSED  ☐ FAILED  

---

### Caso de Prueba 02: Registro de Pago en Caja y Fecha de Cobro (Escenario 2)
* **Objetivo**: Validar que el cajero puede registrar el pago de la factura en mostrador, pasando el estado a `paid` y registrando el timestamp del cobro.
* **Pasos de Ejecución**:
  1. Abrir la factura generada (`FAC-0001`) en estado `Pendiente`.
  2. Verificar que el campo **Fecha de Pago** se encuentra vacío o invisible.
  3. Seleccionar el método de pago *"Efectivo"* o *"Tarjeta de Débito / Crédito"*.
  4. Presionar el botón de cabecera **Registrar Pago**.
* **Resultados Esperados**:
  - [x] El estado de la factura cambia a `Pagada` (`paid`).
  - [x] El campo **Fecha de Pago** registra automáticamente la fecha y hora actual del cobro.
  - [x] El botón **Registrar Pago** desaparece del encabezado.
* **Result:** ☑ PASSED  ☐ FAILED  

---

### Caso de Prueba 03: Navegación Bidireccional entre Venta y Factura (Escenario 3)
* **Objetivo**: Validar la navegación fluida y bidireccional entre la orden de venta y su factura asociada sin pérdida de contexto.
* **Pasos de Ejecución**:
  1. En el formulario de la factura `FAC-0001`, hacer clic en el Smart Button **Ver Orden de Venta**.
  2. Verificar que se despliega la orden de venta origen `VEN-XXXX`.
  3. En la orden de venta, hacer clic en el Smart Button **Factura**.
  4. Comprobar que se regresa a la factura correspondiente.
* **Resultados Esperados**:
  - [x] Navegación instantánea de Factura $\to$ Venta mediante acción de ventana `ir.actions.act_window`.
  - [x] Navegación instantánea de Venta $\to$ Factura mediante smart button.
* **Result:** ☑ PASSED  ☐ FAILED  

---

### Caso de Prueba 04: Inmutabilidad Financiera y Protección Fiscal (Escenario 4)
* **Objetivo**: Garantizar que una factura pagada no puede ser modificada en sus valores fiscales ni suprimida de la base de datos.
* **Pasos de Ejecución**:
  1. En la factura en estado `Pagada`, comprobar el modo de edición visual.
  2. Intentar modificar el cliente o monto total vía API / ORM `write()`.
  3. Intentar eliminar la factura pagada vía `unlink()`.
* **Resultados Esperados**:
  - [x] Campos de cliente, fecha, monto y método de pago en modo solo lectura (`readonly`).
  - [x] Intento de `write()` sobre campos protegidos bloqueado con `UserError`.
  - [x] Intento de `unlink()` bloqueado con `UserError` por motivos de auditoría fiscal.
* **Result:** ☑ PASSED  ☐ FAILED  

---

## 4. Matriz de Cobertura y Trazabilidad

| Caso de Prueba | Requisito Spec | Criterio de Aceptación | Estado |
| :--- | :--- | :--- | :---: |
| CP-01 | SPEC-4.1.1 Sec. 2.1 | Escenario 1: Emisión automática y correlativo `FAC-XXXX` | **APROBADO** |
| CP-02 | SPEC-4.1.1 Sec. 2.1 | Escenario 2: Registro de pago en caja `pending` $\to$ `paid` | **APROBADO** |
| CP-03 | SPEC-4.1.1 Sec. 2.1 | Escenario 3: Navegación bidireccional Venta $\leftrightarrow$ Factura | **APROBADO** |
| CP-04 | SPEC-4.1.1 Sec. 3 | Restricción: Inmutabilidad fiscal y protección contra borrado | **APROBADO** |

---

## 5. Dictamen Final

La especificación **SPEC-4.1.1** ha completado y superado satisfactoriamente todas las pruebas funcionales, de interfaz y de integridad fiscal conforme a la Constitución del Proyecto.
