# Procedimiento de Prueba: SPEC-3.1.1 Extensión y Registro de Clientes de Panadería

**Documento ID**: `test-procedure-3.1.1.md`  
**Especificación Asociada**: [`specs/3-customers/3.1-partner-extension/3.1.1-bakery-customer-management/spec.md`](file:///d:/UDB/CICLO-10-2026/DES/LAB/Desafio%203/des-panaderia-erp/specs/3-customers/3.1-partner-extension/3.1.1-bakery-customer-management/spec.md)  
**Módulo Objetivo**: `Modulo_Odoo` (`res.partner`, extensión de clientes de panadería)  
**Versión**: 1.0.0  
**Fecha de Ejecución**: 2026-09-30  
**Evaluado por**: Antigravity Automated Verification Agent  
**Overall Result:** ☑ APPROVED  ☐ REJECTED  ☐ BLOCKED  

---

## 1. Resumen y Objetivos de Verificación

El presente procedimiento de prueba valida de forma exhaustiva y sin código la extensión del modelo de contactos (`res.partner`) para el ERP de Panadería "Delicias Dulces". Se evalúan la diferenciación de clientes de panadería frente a contactos generales/proveedores, la inicialización automática de la fecha de alta en tienda, el almacenamiento de notas y preferencias dietéticas/alergias, el cálculo acumulativo y reactivo del importe histórico de compras mediante órdenes de venta confirmadas, la reversión del importe ante cancelaciones, y la ergonomía de vistas (Lista, Formulario con pestaña dedicada, Filtros y Smart Buttons).

---

## 2. Prerrequisitos de Entorno

- [x] Contenedores `panaderia_odoo_db` y `panaderia_odoo_web` en ejecución y saludables (`docker compose up -d`).
- [x] Base de datos `panaderia_db` inicializada con catálogo de productos base (`SPEC-1.1.1`, `SPEC-1.1.2`).
- [x] Módulo `Modulo_Odoo` actualizado con el modelo de extensión `cliente.py`, datos semilla `cliente_data.xml` y vistas `cliente_views.xml`.
- [x] Interfaz web disponible en `http://localhost:8069`.

---

## 3. Casos de Prueba de Interfaz de Usuario y ORM

### Caso de Prueba 01: Registro de Nuevo Cliente de Panadería (Escenario 1)
* **Objetivo**: Verificar que al registrar un cliente desde el menú de panadería, se inicializa con el flag `es_cliente_panaderia = True`, fecha de registro de hoy y preferencias capturadas.
* **Pasos de Ejecución**:
  1. Ingresar a **Panadería** $\to$ **Clientes** (o **Panadería** $\to$ **Ventas** $\to$ **Clientes**).
  2. Hacer clic en el botón **Nuevo** / **Crear**.
  3. Completar los siguientes campos:
     - **Nombre**: `Carlos Mendoza`
     - **Teléfono**: `7123-4567`
     - En la pestaña **Datos de Panadería**:
       - Verificar que **Es Cliente de Panadería** esté marcado con checkbox activo.
       - Verificar que **Fecha de Registro en Panadería** contenga la fecha del día de hoy.
       - En **Notas y Preferencias de Consumo**, ingresar: `Prefiere pan integral caliente por las tardes y repostería baja en azúcar.`
  4. Guardar el registro.
* **Resultados Esperados**:
  - [x] El contacto queda guardado exitosamente.
  - [x] El campo `total_compras_panaderia` muestra `$0.00`.
  - [x] El contador de compras muestra `0`.
* **Result:** ☑ PASSED  ☐ FAILED  

---

### Caso de Prueba 02: Acumulación Automática del Historial de Compras (Escenario 2)
* **Objetivo**: Validar que al confirmar órdenes de venta a nombre del cliente, el total acumulado en compras aumenta de forma inmediata y automática ($12.50 + $7.50 = $20.00).
* **Pasos de Ejecución**:
  1. Ingresar a **Panadería** $\to$ **Ventas** $\to$ **Órdenes de Venta** y hacer clic en **Nuevo**.
  2. Seleccionar como cliente a `Carlos Mendoza`.
  3. Agregar líneas de venta con productos por un total de `$12.50`.
  4. Hacer clic en **Confirmar Venta**.
  5. Crear una segunda orden de venta a nombre de `Carlos Mendoza` por un importe de `$7.50`.
  6. Hacer clic en **Confirmar Venta**.
  7. Regresar a **Panadería** $\to$ **Clientes** y abrir el registro de `Carlos Mendoza`.
* **Resultados Esperados**:
  - [x] El campo `Total en Compras ($)` en la pestaña **Datos de Panadería** refleja exactamente `$20.00`.
  - [x] El Smart Button en la cabecera superior derecha muestra `$20.00 Compras Panadería`.
  - [x] En la sub-tabla **Historial de Ventas en Panadería** se visualizan las 2 órdenes con estado `Confirmada`.
* **Result:** ☑ PASSED  ☐ FAILED  

---

### Caso de Prueba 03: Filtrado Exclusivo de Clientes de Panadería (Escenario 3)
* **Objetivo**: Comprobar que en el menú de clientes de panadería se visualizan únicamente los contactos del giro comercial de panadería, omitiendo proveedores y contactos ajenos.
* **Pasos de Ejecución**:
  1. Ir a **Contactos** (menú general de Odoo) y crear un contacto de proveedor con nombre `Distribuidora de Harinas S.A.` (asegurándose de desmarcar el flag de panadería si aplica).
  2. Ingresar a **Panadería** $\to$ **Clientes**.
  3. Observar la lista de registros cargados en la vista árbol.
* **Resultados Esperados**:
  - [x] Aparecen los clientes de panadería (ej. `Cliente General / Mostrador`, `Carlos Mendoza`, `Ana López`).
  - [x] El proveedor `Distribuidora de Harinas S.A.` no se muestra en el listado por el dominio `[('es_cliente_panaderia', '=', True)]`.
* **Result:** ☑ PASSED  ☐ FAILED  

---

### Caso de Prueba 04: Reversión del Total Acumulado ante Cancelación de Venta
* **Objetivo**: Verificar que al cancelar una orden de venta confirmada, el total de compras del cliente se actualiza descontando el importe de la orden anulada.
* **Pasos de Ejecución**:
  1. Abrir la segunda orden de venta de `$7.50` asociada a `Carlos Mendoza`.
  2. Presionar el botón **Cancelar** y confirmar el diálogo.
  3. Regresar a la ficha de `Carlos Mendoza`.
* **Resultados Esperados**:
  - [x] El total acumulado de compras disminuye automáticamente a `$12.50`.
  - [x] La orden cancelada se marca con badge gris/rojo de `Cancelada`.
* **Result:** ☑ PASSED  ☐ FAILED  

---

### Caso de Prueba 05: Smart Button y Navegación Directa a Ventas
* **Objetivo**: Validar la navegación rápida a las ventas del cliente mediante el Smart Button.
* **Pasos de Ejecución**:
  1. Abrir la ficha de `Carlos Mendoza`.
  2. Hacer clic en el botón de estadísticas superior derecho **Compras Panadería**.
* **Resultados Esperados**:
  - [x] Odoo abre la vista de órdenes de venta pre-filtrada exclusivamente con las ventas de Carlos Mendoza.
* **Result:** ☑ PASSED  ☐ FAILED  

---

## 4. Trazabilidad de Requerimientos y Cobertura

| Requerimiento Spec | Caso de Prueba | Cobertura en Test Unitario | Estado |
| :--- | :--- | :--- | :--- |
| **Escenario 1 (Registro con valores por defecto)** | Caso 01 | `test_01_cliente_defaults_and_fields` | PASSED |
| **Escenario 2 (Acumulación de compras $20.00)** | Caso 02 | `test_03_cumulative_purchases_confirmed_sales` | PASSED |
| **Escenario 3 (Filtrado de clientes)** | Caso 03 | `test_05_bakery_customer_filtering_domain` | PASSED |
| **Datos Semilla (Cliente Mostrador)** | Datos Iniciales | `test_02_seed_data_validation` | PASSED |
| **Reversión de Compras (Cancelación)** | Caso 04 | `test_04_cancellation_reverts_accumulated_total` | PASSED |
| **Smart Button y Navegación** | Caso 05 | `test_06_action_view_panaderia_ventas` | PASSED |

---

## 5. Verificación de Definition of Done (DoD)

| # | Criterio de Aceptación (DoD) | Evidencia de Cumplimiento | Estado |
| :--- | :--- | :--- | :--- |
| 1 | Modelo `res.partner` extendido con campos de panadería | Implementado en `Modulo_Odoo/models/cliente.py` con `_inherit = 'res.partner'`. | ☑ Cumplido |
| 2 | Vistas Formulario y Lista personalizadas con filtros de panadería | Implementado en `Modulo_Odoo/views/cliente_views.xml`. | ☑ Cumplido |
| 3 | Conexión y cálculo automático de `total_compras_panaderia` probado con ventas confirmadas | Validado en `Modulo_Odoo/tests/test_cliente.py` (`test_03`). | ☑ Cumplido |
| 4 | Procedimiento de prueba `docs/test-procedures/test-procedure-3.1.1.md` completado y verificado | Documento generado y aprobado con 100% de trazabilidad. | ☑ Cumplido |
