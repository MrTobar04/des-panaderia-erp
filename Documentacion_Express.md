# Documentación Express - ERP Panadería "Delicias Dulces"

Este documento sintetiza de forma ejecutiva y técnica las funcionalidades principales de los **5 módulos** implementados en el sistema ERP Odoo para la gestión integral de la panadería.

---

## 1. Gestión de Inventario Básico

### Descripción General
Centraliza la administración del catálogo de productos y el control de existencias en almacén en tiempo real, garantizando la trazabilidad de los insumos y productos terminados.

### Funcionalidades Clave
* **Catálogo de Productos:** Registro detallado con atributos esenciales:
  * **Nombre del producto:** Identificador comercial único.
  * **Categoría:** Clasificación tipificada del producto.
  * **Precio de Venta y Costo:** Definición de costo unitario y precio al público, con cálculo automático del margen de ganancia.
* **Categorización Estructurada:** Organización predeterminada en 4 familias clave:
  * 🍞 **Pan**
  * 🎂 **Pastel**
  * 🍪 **Galleta**
  * 🥤 **Bebida**
* **Control de Stock Actual:** Monitoreo en tiempo real de las cantidades disponibles por producto.
* **Alerta Básica de Stock Mínimo:** Detección visual y lógica automática cuando el stock disponible es menor o igual al umbral mínimo establecido (`stock_minimo`), señalando la necesidad urgente de reposición.

---

## 2. Proceso de Ventas Esencial

### Descripción General
Gestiona el ciclo de vida de las transacciones comerciales de la panadería en mostrador o pedidos especiales, integrando la reserva y descuento inmediato de inventario.

### Funcionalidades Clave
* **Registro de Órdenes de Venta:** Creación ágil de pedidos vinculados a clientes con múltiples líneas de detalle (`lineas_ids`).
* **Cálculo Automático de Totales:**
  * Subtotal por línea (Cantidad × Precio Unitario).
  * Monto total acumulado de la venta calculado dinámicamente.
* **Actualización Automática de Stock:** Al confirmar la venta, se descuenta de forma automática e inmediata la cantidad vendida del inventario de cada producto.
* **Flujo de Estados:**
  * `Borrador`: Registro preliminar de la orden (permite modificaciones de cantidades y precios).
  * `Confirmada`: Aprobación final que bloquea la orden, descuenta el stock y habilita la facturación.

```mermaid
stateDiagram-v2
    [*] --> Borrador: Crear Venta
    Borrador --> Confirmada: Confirmar Venta (Descuenta Stock)
    Confirmada --> Facturada: Generar Factura
    Confirmada --> Cancelada: Cancelar (Restaura Stock)
```

---

## 3. Registro de Clientes

### Descripción General
Extiende el modelo nativo de contactos y socios comerciales de Odoo (`res.partner`) para adaptarlo a las necesidades analíticas y comerciales de la panadería.

### Funcionalidades Clave
* **Extensión de `res.partner`:** Incorporación de metadatos especializados sin alterar la compatibilidad del ecosistema base de Odoo.
* **Campos Adicionales Especializados:**
  * `es_cliente_panaderia`: Indicador booleano para segmentar clientes específicos del negocio.
  * `fecha_registro`: Fecha y hora de alta del cliente en el sistema.
  * `total_compras`: Monto monetario histórico acumulado calculado automáticamente a partir de las ventas confirmadas.
* **Filtro y Vistas Personalizadas:** Filtro predeterminado en vistas de lista y kanban para consultar exclusivamente clientes de la panadería.

---

## 4. Facturación Simple y Documento Tributario Electrónico (DTE)

### Descripción General
Provee un mecanismo integral de emisión, seguimiento y cobranza de comprobantes fiscales impresos y digitales bajo la normativa del **Documento Tributario Electrónico (DTE - Factura Tipo 01)** del Ministerio de Hacienda de El Salvador.

### Funcionalidades Clave
* **Generación Directa desde Venta:** Al confirmar la orden de venta, el sistema genera automáticamente la factura vinculada con desglose de productos y asignación inmediata de identificadores fiscales.
* **Secuencia y Numeración Oficial DTE:**
  * Folio interno correlativo (`FAC-XXXX`).
  * **Código de Generación:** Identificador universal único UUID v4 oficial en mayúsculas (ej. `4D042782-DC9B-4709-876C-11EC48CD3900`).
  * **Número de Control MH:** Formato legal salvadoreño `DTE-01-M001P001-` con correlativo de 15 dígitos.
  * **Sello de Recepción Fiscal:** Cadena de seguridad criptográfica de 40 caracteres.
* **Emisión de Factura PDF (QWeb Report):**
  * **Logotipo Oficial:** Encabezado con el isotipo e imagotipo de *"Delicias Dulces - PANADERÍA"*.
  * **Datos del Emisor:** Razón Social (DELICIAS DULCES S.A. DE C.V.), NIT, NRC, actividad económica y dirección comercial en San Salvador, El Salvador.
  * **Cuerpo de Ítems y Liquidación Fiscal:** Tabla detallada de productos, precios unitarios, ventas gravadas/exentas/no sujetas, subtotal e IVA.
  * **Código QR Escaneable:** Código bidimensional nativo con URL de consulta pública ante el Ministerio de Hacienda.
  * **Total en Letras:** Conversión automática a palabras en español (ej. *SETENTA Y NUEVE CON 00/100*).
* **Impresión Bajo Demanda:** Botones "Imprimir Factura DTE" disponibles en las vistas formulario tanto de la factura como de la orden de venta.
* **Flujo y Gestión de Estados:**
  * `Pendiente`: Comprobante emitido con DTE generado, a la espera del cobro en mostrador.
  * `Pagada`: Registro de pago conforme (efectivo, tarjeta o transferencia) con fecha/hora de cobro e inmutabilidad fiscal.
  * `Cancelada`: Anulación del comprobante protegida por permisos de administrador.

---

## 5. Reportes Básicos

### Descripción General
Módulo analítico y de inteligencia operativa que consolida métricas clave para la toma de decisiones diarias de la gerencia.

### Funcionalidades Clave
* **Ventas del Día:**
  * Reporte consolidado de transacciones efectuadas en la jornada actual.
  * Agrupación por método de pago, vendedor y balance total facturado.
* **Productos Más Vendidos:**
  * Ranking (Top N) de productos con mayor volumen de unidades colocadas e ingresos generados.
  * Análisis de rotación de inventario por categoría.
* **Alerta de Stock Bajo:**
  * Listado consolidado de productos cuyas existencias están en o por debajo del stock mínimo.
  * Sugerencia automática de cantidades a reponer/producir en panadería.

---

## Matriz Resumen de Módulos y Modelos Técnicos

| # | Módulo Funcional | Modelo Odoo Principal | Modelos Relacionados | Salidas / Vistas Principales |
|---|---|---|---|---|
| **1** | **Inventario Básico** | `panaderia.producto` | `panaderia.categoria` | Catálogo de productos, alertas de stock mínimo |
| **2** | **Ventas Esencial** | `panaderia.venta` | `panaderia.venta.linea` | Formulario de venta, órdenes confirmadas |
| **3** | **Registro de Clientes** | `res.partner` (extendido) | `panaderia.venta` | Vista de clientes de panadería, métrica total compras |
| **4** | **Facturación Simple** | `panaderia.factura` | `panaderia.factura.linea`, `panaderia.venta` | Comprobante de pago, historial de facturas |
| **5** | **Reportes Básicos** | `panaderia.reporte` / Wizard | Modelos de Venta, Producto e Inventario | Reporte PDF de ventas diarias, tablero de stock bajo |
