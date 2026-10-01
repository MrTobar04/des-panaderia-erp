# Procedimiento de Prueba: SPEC-5.1.1 Reportes Operativos Diarios y Alertas de Stock

**Documento ID**: `test-procedure-5.1.1.md`  
**Especificación Asociada**: [`specs/5-reports/5.1-operational-reports/5.1.1-daily-sales-and-stock-reports/spec.md`](../../specs/5-reports/5.1-operational-reports/5.1.1-daily-sales-and-stock-reports/spec.md)  
**Módulo Objetivo**: `Modulo_Odoo` (`panaderia.reporte.ventas`, `panaderia.reporte.diario.wizard`)  
**Versión**: 1.0.0  
**Fecha de Ejecución**: 2026-09-30  
**Evaluado por**: Automated Agent (Playwright MCP / Test Automation Runner)  
**Overall Result:** ☑ APPROVED  ☐ REJECTED  ☐ BLOCKED  

---

## 1. Resumen y Objetivos de Verificación

El presente procedimiento de prueba valida de extremo a extremo las capacidades analíticas y de reportería operativa del ERP de Panadería "Delicias Dulces". Se evalúan la agregación de ventas diarias en tiempo real mediante la vista SQL `panaderia_reporte_ventas`, la visualización en tablas pivote y gráficos de barras del ranking de productos más vendidos, la grilla de alertas de inventario para productos en nivel crítico de reabastecimiento, y la generación del resumen operativo diario en formato imprimible QWeb PDF.

---

## 2. Prerrequisitos de Entorno

- [x] Contenedores Docker `panaderia_odoo_db` y `panaderia_odoo_web` configurados para el entorno.
- [x] Base de datos `panaderia_db` inicializada con catálogo de productos y ventas (`SPEC-1.1.1`, `SPEC-2.1.1`, `SPEC-4.1.1`).
- [x] Módulo `Modulo_Odoo` actualizado con el modelo analítico `panaderia.reporte.ventas`, vistas de reportes y plantilla QWeb.
- [x] Interfaz web y modelos Odoo accesibles.

---

## 3. Casos de Prueba de Interfaz de Usuario y ORM

### Caso de Prueba 01: Consulta de Ventas del Día Actual (Escenario 1)
* **Objetivo**: Validar que las ventas confirmadas en la jornada actual se consolidan en tiempo real en la vista analítica con el total de ingresos y desglose.
* **Pasos de Ejecución**:
  1. Registrar y confirmar órdenes de venta en mostrador durante el día por un total acumulado de `$85.00`.
  2. Navegar a **Panadería** $\to$ **Reportes** $\to$ **Ventas del Día**.
  3. Observar los importes totales en la vista de lista y la tabla pivote.
* **Resultados Esperados**:
  - [x] La vista muestra el total consolidado de `$85.00` para la fecha actual.
  - [x] Se muestran los subtotales correctos desglosados por categoría y producto.
  - [x] Las ventas en estado borrador o canceladas no se computan.
* **Result:** ☑ PASSED  ☐ FAILED  ☐ BLOCKED  
* **Notes:** Verificado exitosamente mediante agregación SQL y suite automatizada `test_01` y `test_02`.

---

### Caso de Prueba 02: Detección y Gráfico de Productos Más Vendidos (Escenario 2)
* **Objetivo**: Comprobar que el ranking de productos ordena correctamente los artículos por volumen de unidades y despliega el gráfico de barras interactivo.
* **Pasos de Ejecución**:
  1. Confirmar ventas acumuladas de 100 unidades de *"Pan Francés"* y 10 unidades de *"Pasteles Selva Negra"*.
  2. Navegar a **Panadería** $\to$ **Reportes** $\to$ **Productos Más Vendidos**.
  3. Alternar entre la vista gráfica de barras y la vista pivote.
* **Resultados Esperados**:
  - [x] *"Pan Francés"* aparece en la primera posición con 100 unidades vendidas.
  - [x] El gráfico de barras resalta la barra más alta para el producto líder.
  - [x] La tabla pivote refleja las medidas agregadas correctamente.
* **Result:** ☑ PASSED  ☐ FAILED  ☐ BLOCKED  
* **Notes:** Verificado exitosamente mediante `view_panaderia_reporte_ventas_graph` y suite automatizada `test_03`.

---

## Caso de Prueba 03: Listado de Alertas de Stock Bajo (Escenario 3)
* **Objetivo**: Verificar que los productos cuyas existencias físicas son $\le$ stock mínimo se listan inmediatamente en la grilla de alertas.
* **Pasos de Ejecución**:
  1. Configurar productos con stock disponible menor o igual a su umbral mínimo (`stock_minimo`).
  2. Navegar a **Panadería** $\to$ **Reportes** $\to$ **Stock Bajo / Alertas**.
  3. Comprobar las columnas de stock actual, stock mínimo y estado de alerta.
  4. Probar el botón de acción rápida **Reabastecer / Ajustar**.
* **Resultados Esperados**:
  - [x] Se listan únicamente los productos que cumplen la condición de stock bajo o agotado.
  - [x] Las insignias de advertencia (`badge`) indican *"Bajo Stock"* (amarillo) o *"Agotado"* (rojo).
  - [x] El botón abre el asistente emergente para registrar un ajuste de entrada rápido.
* **Result:** ☑ PASSED  ☐ FAILED  ☐ BLOCKED  
* **Notes:** Verificado exitosamente mediante dominio `[('alerta_stock_bajo', '=', True)]` y suite automatizada `test_04`.

---

### Caso de Prueba 04: Impresión del Resumen Operativo Diario (QWeb PDF) (Escenario 4)
* **Objetivo**: Validar la generación y descarga del comprobante PDF de resumen operativo en una sola página.
* **Pasos de Ejecución**:
  1. Navegar a **Panadería** $\to$ **Reportes** $\to$ **Imprimir Resumen Diario (PDF)**.
  2. Seleccionar la fecha actual y presionar **Generar PDF**.
  3. Abrir el documento PDF generado.
* **Resultados Esperados**:
  - [x] Se genera el archivo PDF con formato limpio y membrete de la panadería.
  - [x] Muestra las tarjetas KPI con el total de ingresos, órdenes confirmadas y piezas vendidas.
  - [x] Incluye la tabla del Top de productos más vendidos y la tabla de alertas de stock.
* **Result:** ☑ PASSED  ☐ FAILED  ☐ BLOCKED  
* **Notes:** Verificado exitosamente mediante `action_report_resumen_diario`, parser `_get_report_values()` y suite automatizada `test_05`.

---

## 4. Matriz de Cobertura y Trazabilidad

| Caso de Prueba | Requisito Spec | Criterio de Aceptación | Estado |
| :--- | :--- | :--- | :---: |
| CP-01 | SPEC-5.1.1 Sec. 2.1 | Escenario 1: Consulta de ventas del día actual | **APROBADO** |
| CP-02 | SPEC-5.1.1 Sec. 2.1 | Escenario 2: Detección y ranking de productos más vendidos | **APROBADO** |
| CP-03 | SPEC-5.1.1 Sec. 2.1 | Escenario 3: Listado y acción de stock bajo | **APROBADO** |
| CP-04 | SPEC-5.1.1 Sec. 2.1 & 4 | Escenario 4: Reporte imprimible QWeb PDF de una página | **APROBADO** |

---

## 5. Resumen de Ejecución y Veredicto Final

| Métrica | Valor |
| :--- | :---: |
| Total de casos ejecutados | 4 |
| Casos aprobados | 4 |
| Casos fallidos | 0 |
| Casos bloqueados | 0 |
| Cobertura de Criterios de Aceptación (AC) | 100% |
| Criterios de DoD Verificados | 4 / 4 |

**Veredicto Final**: ☑ APPROVED  ☐ REJECTED  ☐ BLOCKED  
**Dictamen**: La especificación **SPEC-5.1.1** ha completado y superado satisfactoriamente todas las pruebas unitarias automatizadas, de vistas analíticas y de generación QWeb PDF conforme a la Constitución del Proyecto.
