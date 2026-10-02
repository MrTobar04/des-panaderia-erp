# Phase 1: Quickstart & Verification Guide — Factura PDF DTE

**Feature**: `specs/4-invoicing/4.1-customer-invoices/4.1.2-dte-invoice-pdf-generation`  
**Date**: 2026-10-01  
**Status**: Ready for Verification

---

## 1. Prerrequisitos de Ejecución

1. Contenedores Docker de Odoo y PostgreSQL operativos (`docker compose up -d`).
2. Módulo de Panadería actualizado con las nuevas vistas y plantilla de reporte:
   ```powershell
   .\scripts\docker-restart.ps1 -Upgrade
   ```
3. Datos de prueba cargados (productos, clientes y categorías).

---

## 2. Escenario de Verificación 1: Flujo Extremo a Extremo en UI

### Paso 1: Crear y Confirmar una Orden de Venta
1. Iniciar sesión en Odoo (`http://localhost:8069`) como Administrador o Cajero.
2. Navegar al menú **Panadería $\to$ Órdenes de Venta $\to$ Crear**.
3. Seleccionar un cliente (ej. *"Alejandro Hernández"*).
4. Agregar productos a la orden:
   - 2x Baguette Tradicional ($1.25 c/u = $2.50)
   - 1x Pastel de Chocolate ($15.00)
   Total: `$17.50`.
5. Presionar **Confirmar Venta**.
   - *Resultado esperado:* La venta cambia a estado `Confirmada` y se genera automáticamente una factura en estado `Pendiente`.

### Paso 2: Imprimir Factura DTE desde la Orden de Venta
1. En la cabecera de la orden confirmada, presionar el botón **Imprimir Factura DTE**.
   - *Resultado esperado:* El navegador inicia la descarga o visualización del archivo PDF titulado `Factura_DTE_FAC-XXXX.pdf`.

### Paso 3: Validar Fidelidad Visual del PDF
Abrir el documento generado y comprobar los siguientes elementos:
1. **Encabezado**:
   - Logotipo oficial de **"Delicias Dulces - PANADERÍA"** nítido a la izquierda.
   - Datos del emisor a la derecha (Razón social, NIT, NRC, dirección en El Salvador, teléfono).
2. **Caja DTE y Código QR**:
   - Título: *DOCUMENTO TRIBUTARIO ELECTRÓNICO - FACTURA*.
   - Código de Generación (UUID en mayúsculas).
   - Número de Control (`DTE-01-M001P001-...`).
   - Sello de Recepción (cadena alfanumérica de 40 caracteres).
   - Código QR renderizado y legible con un lector estándar de smartphone.
3. **Bloque Emisor y Receptor**:
   - Información del emisor y receptor en cajas paralelas con bordes definidos.
4. **Tabla de Productos**:
   - Filas con número de ítem, cantidad, descripción, precio unitario y venta gravada.
5. **Totales y Monto en Letras**:
   - Subtotal: `$17.50`, Total a Pagar: `$17.50`.
   - Valor en Letras: `DIECISIETE CON 50/100 USD`.
   - Condición de la Operación: `CONTADO`.

---

## 3. Escenario de Verificación 2: Prueba Automatizada en Contenedor

Ejecutar la suite de pruebas unitarias automáticas desde PowerShell:

```powershell
docker compose exec -T odoo-web odoo --test-enable --stop-after-init -d panaderia_db -u panaderia_delicias_dulces --test-tags=/panaderia_delicias_dulces
```

**Resultado Esperado**:
- Todos los tests de generación de DTE, cálculo en letras y emisión de reporte PDF pasan con resultado `OK` sin trazas de error.
