# Feature Specification: Generación de Factura PDF con Estándar DTE de El Salvador

**Feature Branch**: `specs/4-invoicing/4.1-customer-invoices/4.1.2-dte-invoice-pdf-generation`

**Created**: 2026-10-01

**Status**: Draft

**Input**: User description: "modifica el proyecto porque tiene que generar una factura pdf cuando se finaliza el correspondiente proceso te dara un modelo base, el modelo incluye como se genera las facturas electronicas segun hacienda en el salvador, te dara una factura electronica, su json y el logo de la panaderia, tu tienes que basarte en esa factura para generarla, es decir vamos a tomar como modelo la factura, el logo incluyelo en los lugares necesarios del proyecto"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Emisión y Generación Automática del PDF de Factura DTE al Completar la Venta (Priority: P1)

Como cajero o dependiente de la panadería "Delicias Dulces", cuando finalizo el proceso de cobro y registro de una venta en mostrador, deseo que el sistema genere automáticamente el comprobante de factura en formato PDF siguiendo el modelo oficial de Factura Electrónica (DTE) de El Salvador, para entregar inmediatamente un comprobante fiscal válido y profesional al cliente.

**Why this priority**: Es el flujo operativo principal del negocio. La entrega de factura es obligatoria en cada venta y define la experiencia de compra y el cumplimiento legal del establecimiento.

**Independent Test**: Puede probarse de manera aislada completando una venta con productos de panadería y verificando que el documento PDF se genere automáticamente con todos los campos obligatorios del modelo DTE (Código de Generación, Número de Control, Sello de Recepción, desglose de ítems, totales e identidad visual de la panadería).

**Acceptance Scenarios**:

1. **Given** una orden de venta en estado borrador con productos de panadería (ej. Conchas y Pastel de Chocolate) y un cliente seleccionado, **When** el cajero confirma la venta y procesa el registro, **Then** el sistema genera una factura vinculada asignando automáticamente los identificadores DTE (Código de Generación UUID, Número de Control DTE-01 y Sello de Recepción simulado) y deja disponible el archivo PDF oficial listo para visualización e impresión.
2. **Given** una factura recién generada, **When** el usuario abre o descarga el PDF, **Then** el documento muestra en el encabezado el logotipo oficial de "Delicias Dulces - PANADERÍA", los datos fiscales del emisor, la fecha y hora de emisión, y el título "DOCUMENTO TRIBUTARIO ELECTRÓNICO - FACTURA".
3. **Given** una venta con múltiples productos a diferentes precios, **When** se visualiza la tabla del cuerpo del PDF, **Then** cada ítem detalla número de línea, cantidad, unidad de medida, descripción, precio unitario y monto gravado, calculando con exactitud la sumatoria de ventas, subtotal, IVA aplicable y total a pagar.

---

### User Story 2 - Descarga e Impresión Bajo Demanda del Comprobante PDF (Priority: P2)

Como administrador o cajero de la panadería, deseo disponer de un botón de acción visible ("Imprimir Factura DTE" / "Descargar PDF") tanto en la vista de la factura como en la orden de venta origen, para reimprimir el comprobante en cualquier momento a petición del cliente o para fines de auditoría física.

**Why this priority**: Permite recuperar facturas pasadas ante solicitudes de clientes, reclamos o reimpresión por atasco de impresora sin necesidad de volver a procesar la venta.

**Independent Test**: Puede probarse abriendo cualquier factura previamente registrada y presionando el botón de impresión para obtener el documento PDF idéntico al generado originalmente.

**Acceptance Scenarios**:

1. **Given** una factura existente en estado "Pendiente" o "Pagada", **When** el usuario hace clic en el botón "Imprimir Factura DTE", **Then** el sistema descarga o despliega en pantalla el PDF con la representación gráfica oficial del DTE.
2. **Given** una orden de venta confirmada con factura asociada, **When** el usuario consulta la orden de venta y pulsa "Imprimir Factura DTE", **Then** el sistema emite el PDF de la factura correspondiente sin alterar ningún dato de la orden.

---

### User Story 3 - Visualización de Código QR, Monto en Letras y Datos Fiscales Receptores (Priority: P3)

Como cliente o auditor tributario, deseo que la factura PDF incluya un código QR escaneable, el valor total expresado en letras y la información fiscal completa del receptor (o la leyenda de Consumidor Final si no proporciona datos), para validar la autenticidad del documento tributario conforme a la normativa de Hacienda.

**Why this priority**: Brinda validez legal, transparencia al consumidor final y cumple con los estándares técnicos exigidos por el Ministerio de Hacienda en El Salvador.

**Independent Test**: Puede probarse escaneando el código QR generado en el PDF y comprobando que contenga los metadatos de validación del DTE (código de generación, fecha, emisor, receptor y monto total) y verificando que el importe numérico coincida textualmente con el texto en letras (ej. "$15.50" $\to$ "QUINCE CON 50/100 USD").

**Acceptance Scenarios**:

1. **Given** una factura con total de $79.00, **When** se renderiza el pie de página del PDF, **Then** se muestra claramente "Valor en Letras: SETENTA Y NUEVE CON 00/100" y la "Condición de la Operación: CONTADO".
2. **Given** el PDF generado, **When** se inspecciona el bloque superior derecho, **Then** se renderiza un código QR bidimensional con los parámetros clave de consulta y verificación del DTE.
3. **Given** un cliente con DUI/NIT registrado y correo electrónico, **When** se emite la factura, **Then** el bloque "RECEPTOR" refleja fielmente su nombre, documento de identidad, dirección y correo electrónico.

---

### Edge Cases

- **Cliente sin documento de identidad (Venta a Consumidor Final mostrador):** Cuando el cliente no suministra NIT/DUI, el receptor debe registrarse por defecto como "Consumidor Final" o con documento genérico según la normativa salvadoreña, sin provocar errores en la generación del PDF.
- **Venta con descuentos globales o por ítem:** Si se aplican rebajas o promociones, la columna "Descuento por item" y el renglón de "Monto global Desc." deben reflejar el importe descontado y ajustar el subtotal y total a pagar de forma consistente.
- **Reimpresión de facturas históricas:** El PDF generado debe ser determinista e inmutable; reimprimir una factura emitida semanas atrás debe conservar los mismos identificadores (Código de Generación, Número de Control y Sello de Recepción) que se generaron en su fecha original.
- **Nombres de productos extensos o líneas múltiples:** El formato de tabla debe contar con saltos de línea automáticos y diseño fluido para que facturas con más de 10 productos no desborden los márgenes de página del PDF.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE generar una representación gráfica en PDF de la factura al finalizar el proceso de venta o registro de pago, cumpliendo con la estructura visual del modelo DTE Factura (tipo 01) de El Salvador.
- **FR-002**: El sistema DEBE incorporar de manera destacada en el encabezado del documento PDF el logotipo gráfico oficial de la panadería "Delicias Dulces".
- **FR-003**: El sistema DEBE registrar e imprimir los datos fiscales del EMISOR configurados para la panadería: Nombre o Razón Social ("DELICIAS DULCES S.A. DE C.V." / "Panadería Delicias Dulces"), NIT, NRC, Actividad Económica, Dirección comercial en El Salvador, Teléfono y Correo Electrónico.
- **FR-004**: El sistema DEBE generar para cada factura los identificadores obligatorios del estándar DTE:
  - **Código de Generación:** Identificador único universal (UUID v4) en formato canónico mayúsculas (ej. `4D042782-DC9B-4709-876C-11EC48CD3900`).
  - **Número de Control:** Formato oficial del Ministerio de Hacienda (`DTE-01-M001P001-` seguido de correlativo de 15 dígitos).
  - **Sello de Recepción:** Cadena alfanumérica de control fiscal de 40 caracteres.
  - **Modelo de Facturación:** "Modelo Facturación previo".
  - **Tipo de Transmisión:** "Transmisión normal".
  - **Fecha y Hora de Generación:** Registro cronológico en formato `AAAA-MM-DD HH:MM:SS`.
- **FR-005**: El sistema DEBE generar e imprimir en la sección superior un código QR bidimensional que contenga la URL/parámetros de consulta y verificación del DTE (ambiente, código de generación y fecha de emisión).
- **FR-006**: El sistema DEBE presentar una sección dedicada al RECEPTOR que muestre: Nombre o Razón Social, DUI/NIT, Dirección y Correo Electrónico del cliente.
- **FR-007**: El sistema DEBE detallar en una tabla de cuerpo de documento cada producto vendido con: N° correlativo, Cantidad, Unidad de medida ("Otra" / "Unidad"), Descripción del producto de panadería, Precio Unitario, Descuentos, Ventas No Sujetas ($0.00), Ventas Exentas ($0.00) y Ventas Gravadas.
- **FR-008**: El sistema DEBE calcular y presentar el bloque de liquidación y resumen tributario con: Sumatoria de ventas, Monto global de descuentos, Sub-Total, IVA Retenido, Retención Renta, Monto Total de la Operación y Total a Pagar en dólares de EE.UU. ($ USD).
- **FR-009**: El sistema DEBE convertir automáticamente el monto total numérico a su expresión en palabras en español (ej. "SETENTA Y NUEVE CON 00/100 USD") e imprimirlo en el campo "Valor en Letras".
- **FR-010**: El sistema DEBE indicar la condición de la operación ("CONTADO" o "CRÉDITO") según el método de pago seleccionado.
- **FR-011**: El sistema DEBE proporcionar acciones de interfaz para imprimir/descargar el PDF en cualquier momento desde la vista formulario de la factura y desde la orden de venta asociada.
- **FR-012**: El sistema DEBE incluir el archivo del logotipo en los activos estáticos del módulo y en la configuración de la compañía para su reutilización en vistas y reportes del sistema.

### Key Entities *(include if feature involves data)*

- **Comprobante Factura DTE (`panaderia.factura`):** Representa el documento fiscal emitido. Contiene los identificadores tributarios salvadoreños (código de generación, número de control, sello de recepción, fecha/hora DTE), montos financieros (subtotal, IVA, total a pagar), total en letras, estado de cobranza y relación con la venta y el cliente.
- **Líneas de Factura / Venta (`panaderia.venta.linea`):** Detalle de productos de panadería facturados, cantidades, precio de lista, descuentos y valores gravados/exentos.
- **Emisor Fiscal (`res.company` / Configuración Panadería):** Datos legales de Panadería Delicias Dulces (Nombre comercial, NIT, NRC, actividad económica, teléfono, dirección, correo y logotipo institucional).
- **Receptor Fiscal (`res.partner`):** Cliente de la panadería con sus datos fiscales salvadoreños (nombre completo, DUI o NIT, correo electrónico y dirección geográfica).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las facturas generadas al completar una venta cuentan con Código de Generación, Número de Control y Sello de Recepción asignados sin intervención manual.
- **SC-002**: La generación y renderizado del documento PDF toma menos de 2 segundos desde la confirmación de la venta o la pulsación del botón de impresión.
- **SC-003**: El diseño visual del PDF emitido coincide en diagramación, bloques de datos (Emisor, Receptor, DTE, Detalle, Totales y Pie) e identidad visual (Logotipo Delicias Dulces) con el modelo oficial DTE suministrado.
- **SC-004**: El cálculo del total en letras coincide con exactitud gramatical y numérica con el importe total a pagar en el 100% de las facturas probadas.
- **SC-005**: El código QR generado es legible por cualquier lector estándar y contiene la información identificadora del documento tributario.

## Assumptions

- **Ambiente de Operación:** Se asume un entorno de demostración y facturación previa académica donde la generación del Código de Generación (UUID), Número de Control y Sello de Recepción se realiza de manera determinista dentro del sistema local sin requerir conexión en vivo con los servidores del Ministerio de Hacienda de El Salvador (hacienda.gob.sv).
- **Régimen Fiscal de Productos:** Los productos estándar de panadería elaborados (pan dulce, pasteles, galletas, bebidas) constituyen ventas gravadas al tipo general de IVA de El Salvador (13%), incluidos en el precio de venta a consumidor final, manteniendo las casillas de ventas exentas y no sujetas en $0.00 salvo configuración expresa.
- **Moneda del Sistema:** La moneda oficial de la transacción y emisión del DTE es el Dólar Estadounidense (USD), de curso legal en El Salvador.
- **Ubicación del Logotipo:** El logotipo de Panadería Delicias Dulces se almacena como activo estático del módulo y se carga automáticamente como logotipo predeterminado de la empresa para asegurar su presencia en todos los reportes impresos.
