# Quickstart & Verification Guide: Generación de Facturas Simples

**Feature**: `SPEC-4.1.1: Generación de Facturas Simples`  
**Target Module**: `Modulo_Odoo`  
**Related Spec**: [`specs/4-invoicing/4.1-customer-invoices/4.1.1-simple-invoice-generation/spec.md`](spec.md)  
**Data Model**: [`data-model.md`](data-model.md)  
**ORM Contract**: [`contracts/factura-orm-contract.md`](contracts/factura-orm-contract.md)  
**Views Contract**: [`contracts/factura-views-contract.md`](contracts/factura-views-contract.md)  

---

## 1. Prerequisites

1. Docker Desktop en ejecución con soporte para Docker Compose v2.
2. Contenedores de la pila Panadería ERP activos y saludables (`panaderia_odoo_db` y `panaderia_odoo_web`).
3. Módulos base de inventario (`SPEC-1.1.1`) y ventas (`SPEC-2.1.1`) instalados.

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

Ejecutar la suite unitaria de facturación dentro del contenedor Odoo:

```powershell
docker compose exec web odoo -d panaderia_db -u panaderia --test-enable --test-tags=/panaderia --stop-after-init --http-port=8079
```

### Expected Output:
```text
INFO panaderia_db odoo.addons.panaderia.tests.test_factura: Starting PanaderiaFacturaTestCase.test_01_auto_invoice_generation_from_sale ...
INFO panaderia_db odoo.addons.panaderia.tests.test_factura: Starting PanaderiaFacturaTestCase.test_02_register_payment_lifecycle ...
INFO panaderia_db odoo.addons.panaderia.tests.test_factura: Starting PanaderiaFacturaTestCase.test_03_bidirectional_navigation ...
INFO panaderia_db odoo.addons.panaderia.tests.test_factura: Starting PanaderiaFacturaTestCase.test_04_immutability_on_paid_invoice ...
INFO panaderia_db odoo.addons.panaderia.tests.test_factura: Starting PanaderiaFacturaTestCase.test_05_prevent_unlink_paid_invoice ...
INFO panaderia_db odoo.addons.panaderia.tests.test_factura: 5 tests ran in 0.320s, 0 failed, 0 errors.
```

---

## 4. Manual End-to-End Validation Flow

### Journey 1: Emisión Automática de Factura al Confirmar Venta (BDD Scenario 1)
1. Abrir navegador en `http://localhost:8069`.
2. Iniciar sesión con credenciales de administrador o cajero (`admin` / `admin`).
3. Ir a **Panadería** $\to$ **Ventas** $\to$ **Órdenes de Venta**.
4. Crear una nueva orden para el cliente "Cliente Frecuente Mostrador", agregar productos por un total de `$16.00`.
5. Hacer clic en **Confirmar Venta**.
6. **Verificación**:
   * Aparece el Smart Button **Factura** en la parte superior derecha con el texto "1 Factura".
   * En el pie del formulario o en el smart button se constata que la factura fue creada automáticamente.

### Journey 2: Registro de Pago en Caja (BDD Scenario 2)
1. Desde la orden de venta confirmada, hacer clic en el Smart Button **Factura** (o ir al menú **Panadería** $\to$ **Facturación** $\to$ **Facturas de Clientes**).
2. Abrir la factura correspondiente.
3. Constatar que:
   * El folio tiene numeración oficial correlativa (ej. `FAC-0001`).
   * El monto total refleja `$16.00`.
   * El estado actual es **Pendiente** (`pending`).
4. Seleccionar el método de pago (ej. `Efectivo` o `Tarjeta de Débito / Crédito`).
5. Presionar el botón **Registrar Pago**.
6. **Verificación**:
   * La barra de estado cambia a **Pagada** (`paid`).
   * El campo **Fecha de Pago** se llena automáticamente con la fecha y hora actual.
   * El botón "Registrar Pago" desaparece del encabezado.

### Journey 3: Navegación Bidireccional entre Venta y Factura (BDD Scenario 3)
1. En el formulario de la factura pagada, hacer clic en el Smart Button **Ver Orden de Venta** (o sobre el enlace del campo `Orden de Venta Origen`).
2. El sistema navega instantáneamente al formulario de la orden de venta origen (`VEN-XXXX`).
3. Desde la orden de venta, hacer clic nuevamente en el Smart Button **Factura**.
4. El sistema regresa sin error a la factura `FAC-XXXX`.

### Journey 4: Validación de Inmutabilidad y Auditoría Fiscal
1. Estando en la factura con estado **Pagada**:
   * Intentar editar el cliente o el monto total desde la interfaz: los campos están en modo solo lectura (`readonly`).
   * Intentar eliminar la factura desde el menú Acción $\to$ Suprimir: el sistema arroja una alerta bloqueando la eliminación por motivos de auditoría contable.
