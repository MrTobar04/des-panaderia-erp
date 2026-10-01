# Quickstart & Verification Guide: Reportes Operativos Diarios y Alertas de Stock

**Spec**: [`specs/5-reports/5.1-operational-reports/5.1.1-daily-sales-and-stock-reports/spec.md`](spec.md)  
**Module**: `Modulo_Odoo`  
**Feature**: `SPEC-5.1.1`

---

## 1. Quick Verification Commands

### Upgrade Module and Run Tests in Docker:
```powershell
docker compose exec web odoo -d panaderia_db -u Modulo_Odoo --test-enable --test-tags=/Modulo_Odoo --stop-after-init --http-port=8079
```

---

## 2. Manual User Verification Journeys

### Journey 1: Visualizar Ventas del Día
1. Ingresar a Odoo (`http://localhost:8069`) e identificarse como Administrador.
2. Navegar a **Panadería** $\to$ **Reportes** $\to$ **Ventas del Día**.
3. Verificar que la vista pivote y de lista muestran los totales agregados de ingresos y unidades vendidas de hoy.

### Journey 2: Ranking de Productos Más Vendidos
1. Navegar a **Panadería** $\to$ **Reportes** $\to$ **Productos Más Vendidos**.
2. Observar el gráfico de barras interactivo con los productos con mayor demanda.
3. Alternar a vista pivote o lista para auditar las unidades y montos monetarios.

### Journey 3: Revisión de Alertas de Stock Bajo
1. Navegar a **Panadería** $\to$ **Reportes** $\to$ **Stock Bajo / Alertas**.
2. Verificar que se despliegan únicamente los productos con existencias $\le$ stock mínimo.
3. Presionar el botón **Reabastecer / Ajustar** en una línea para ingresar un ajuste de inventario rápido.

### Journey 4: Imprimir Resumen Diario en PDF
1. Navegar a **Panadería** $\to$ **Reportes** $\to$ **Imprimir Resumen Diario (PDF)**.
2. Seleccionar la fecha del día y presionar **Generar PDF**.
3. Comprobar que se descarga el PDF con el encabezado de "Delicias Dulces", KPIs del día, ranking de productos y tabla de alertas.
