# Quickstart & Verification Guide: Registro y Proceso de Ventas Esencial

**Feature**: `SPEC-2.1.1: Registro y Proceso de Ventas Esencial`  
**Target Module**: `Modulo_Odoo`  
**Related Spec**: [`specs/2-sales/2.1-sales-orders/2.1.1-order-management/spec.md`](file:///c:/Users/Inspiron/Desktop/des-panaderia-erp/specs/2-sales/2.1-sales-orders/2.1.1-order-management/spec.md)  
**Data Model**: [`data-model.md`](file:///c:/Users/Inspiron/Desktop/des-panaderia-erp/specs/2-sales/2.1-sales-orders/2.1.1-order-management/data-model.md)  
**ORM Contract**: [`contracts/venta-orm-contract.md`](file:///c:/Users/Inspiron/Desktop/des-panaderia-erp/specs/2-sales/2.1-sales-orders/2.1.1-order-management/contracts/venta-orm-contract.md)  
**Views Contract**: [`contracts/venta-views-contract.md`](file:///c:/Users/Inspiron/Desktop/des-panaderia-erp/specs/2-sales/2.1-sales-orders/2.1.1-order-management/contracts/venta-views-contract.md)  

---

## 1. Prerequisites

1. Docker Desktop en ejecución con soporte para Docker Compose v2.
2. Contenedores de la pila Panadería ERP activos y saludables (`panaderia_odoo_db` y `panaderia_odoo_web`).
3. Base de datos `panaderia_db` inicializada con catálogo de productos base (`SPEC-1.1.1`).

---

## 2. Environment Startup & Module Upgrade

### Step 1: Ensure Containers are Running
```powershell
.\scripts\docker-start.ps1
```

### Step 2: Apply Python & XML Changes (Upgrade Module)
```powershell
.\scripts\docker-restart.ps1 -Upgrade
```

---

## 3. Automated Verification (Python / Odoo ORM Test Suite)

Ejecutar la suite unitaria de ventas dentro del contenedor Odoo:

```powershell
docker compose exec web odoo -d panaderia_db -u panaderia --test-enable --test-tags=/panaderia --stop-after-init --http-port=8079
```

### Expected Output:
```text
...
INFO panaderia_db odoo.addons.panaderia.tests.test_venta: Starting PanaderiaVentaTestCase.test_01_create_sale_and_subtotals ...
INFO panaderia_db odoo.addons.panaderia.tests.test_venta: Starting PanaderiaVentaTestCase.test_02_action_confirm_sequence_and_stock ...
INFO panaderia_db odoo.addons.panaderia.tests.test_venta: Starting PanaderiaVentaTestCase.test_03_insufficient_stock_raises_error ...
INFO panaderia_db odoo.addons.panaderia.tests.test_venta: Starting PanaderiaVentaTestCase.test_04_immutability_on_confirmed_order ...
INFO panaderia_db odoo.addons.panaderia.tests.test_venta: Starting PanaderiaVentaTestCase.test_05_prevent_unlink_confirmed_order ...
INFO panaderia_db odoo.addons.panaderia.tests.test_venta: 5 tests ran in 0.350s, 0 failed, 0 errors.
```

---

## 4. Manual End-to-End Validation Flow

### Journey 1: Creación de Orden de Venta en Mostrador (Scenario 1)
1. Abrir navegador en `http://localhost:8069`.
2. Iniciar sesión con usuario administrador o cajero (`admin` / `admin`).
3. Ir al menú principal: **Panadería** $\to$ **Ventas** $\to$ **Órdenes de Venta**.
4. Hacer clic en el botón **"Nuevo"**.
5. Seleccionar un cliente (ej. *Cliente Mostrador* o *Carlos Mendoza*).
6. En la pestaña **Líneas de la Venta**, agregar:
   - Línea 1: Producto *"Pan Francés Tradicional"*, Cantidad: `10.00`.
     - *Verificación*: El precio unitario se llena automáticamente en `$0.10` y el subtotal calcula `$1.00`.
   - Línea 2: Producto *"Pastel Selva Negra"*, Cantidad: `1.00`.
     - *Verificación*: El precio unitario se llena automáticamente en `$15.00` y el subtotal calcula `$15.00`.
7. Observar el pie de totales:
   - *Verificación*: El campo **Total ($)** muestra exactamente `$16.00`.
8. Guardar la orden:
   - *Verificación*: El folio muestra `Nuevo` y el estado en el statusbar es `Borrador`.

---

### Journey 2: Confirmación de Venta y Descuento de Stock (Scenario 2)
1. Con la orden de venta anterior guardada en estado `Borrador`:
2. Hacer clic en el botón **"Confirmar Venta"**.
3. *Verificación de Resultados*:
   - El estado en la barra superior cambia a **Confirmada** (color verde).
   - El folio `name` cambia automáticamente de `Nuevo` a un código secuencial correlativo (ej. `VEN-0001`).
   - Aparece el botón inteligente o vínculo a la **Factura Asociada**.
4. Ir al menú **Panadería** $\to$ **Inventario** $\to$ **Productos**:
   - Abrir el producto *"Pan Francés Tradicional"*.
   - *Verificación*: Las existencias se redujeron exactamente en 10 unidades (de 50 a 40 unidades).

---

### Journey 3: Restricción de Edición tras Confirmación (Scenario 3)
1. Regresar a la orden de venta confirmada (`VEN-0001`).
2. Intentar hacer clic en el cliente, fecha o en las líneas de detalle:
   - *Verificación*: Todos los campos están en modo de solo lectura (`readonly`).
   - No aparece el botón "Agregar una línea" ni se permite editar cantidades o precios.
3. Intentar eliminar la orden desde el menú *Acción* $\to$ *Suprimir*:
   - *Verificación*: El sistema bloquea la acción con un mensaje de advertencia: *"No es posible eliminar la orden de venta confirmada"*.
