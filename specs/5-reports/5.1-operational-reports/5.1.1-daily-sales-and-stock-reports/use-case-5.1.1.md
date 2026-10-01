# Use Case: Reportes Operativos Diarios y Alertas de Stock (SPEC-5.1.1)

**Actor Principal**: Administrador de Panadería / Encargado de Producción  
**Objetivo**: Obtener visibilidad en tiempo real de ingresos, demanda de productos y necesidad de reposición física.

---

## Escenario 1: Consulta de Ventas del Día
- **Precondición**: Se han confirmado 5 órdenes de venta durante el día por un total acumulado de $85.00.
- **Acción**: El usuario hace clic en el menú **Panadería** $\to$ **Reportes** $\to$ **Ventas del Día**.
- **Resultado Esperado**:
  - La grilla muestra el resumen analítico con el total consolidado de $85.00.
  - La vista pivote permite cruzar las categorías y los productos.

---

## Escenario 2: Detección de Productos Más Vendidos
- **Precondición**: Se vendieron 100 unidades de "Pan Francés" y 10 unidades de "Pastel Selva Negra".
- **Acción**: El usuario ingresa a **Panadería** $\to$ **Reportes** $\to$ **Productos Más Vendidos**.
- **Resultado Esperado**:
  - El gráfico de barras muestra en la primera posición a "Pan Francés" con 100 unidades.
  - Se visualiza claramente la proporción de ventas entre categorías.

---

## Escenario 3: Alertas de Stock Bajo y Reabastecimiento
- **Precondición**: Existen 3 productos cuyo stock disponible es menor o igual al umbral mínimo (`stock_minimo`).
- **Acción**: El encargado de panadería ingresa a **Panadería** $\to$ **Reportes** $\to$ **Stock Bajo / Alertas**.
- **Resultado Esperado**:
  - Se listan exactamente esos 3 productos con etiquetas de advertencia "Bajo Stock" o "Agotado".
  - El botón "Reabastecer / Ajustar" permite registrar un ajuste de entrada en mostrador inmediatamente.

---

## Escenario 4: Impresión del Resumen Diario en PDF
- **Precondición**: Jornada comercial con ventas y existencias registradas.
- **Acción**: El usuario selecciona **Panadería** $\to$ **Reportes** $\to$ **Imprimir Resumen Diario (PDF)** y confirma la fecha.
- **Resultado Esperado**:
  - Odoo genera un archivo PDF de 1 página con diseño ejecutivo que incluye las métricas clave del día, ranking de productos y la tabla de alertas de reabastecimiento.
