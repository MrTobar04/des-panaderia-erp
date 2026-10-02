# Phase 0: Research & Technical Decisions — Factura PDF DTE El Salvador

**Feature**: `specs/4-invoicing/4.1-customer-invoices/4.1.2-dte-invoice-pdf-generation`  
**Date**: 2026-10-01  
**Author**: Antigravity Assistant

---

## 1. Decisiones Técnicas y Arquitectura de Reportes

### Decisión 1: Motor de Generación de PDF en Odoo (QWeb Report)
- **Decisión**: Implementar el reporte PDF utilizando el motor nativo **QWeb Report** de Odoo (`ir.actions.report` con `report_type="qweb-pdf"`).
- **Racional**:
  - Es el estándar nativo de Odoo v16/v17/v18, compatible directamente con `wkhtmltopdf` ya configurado en el contenedor Docker oficial.
  - Permite diseñar la plantilla en HTML/CSS (`web.html_container` con estilos CSS en línea y tipografía moderna), reproduciendo con precisión milimétrica la diagramación del Ministerio de Hacienda de El Salvador.
  - No requiere bibliotecas pesadas externas ni procesos desacoplados fuera de Odoo.
- **Alternativas consideradas**:
  - *ReportLab en Python puro*: Descartado por requerir código imperativo excesivo, curvas de diseño rígidas y dificultad para mantener la estética idéntica al modelo PDF provisto.
  - *Generación vía Headless Chrome / Node microservice*: Descartado por violar el principio de simplicidad modular y autosuficiencia del contenedor Odoo.

---

### Decisión 2: Generación del Código QR en el PDF
- **Decisión**: Utilizar el controlador y servicio nativo de códigos de barra y QR de Odoo (`/report/barcode/?barcode_type=QR&value=...`) o renderizado de imagen QR vectorial/base64 embebida.
- **Racional**:
  - Odoo incorpora nativamente soporte para generar códigos QR a través de su helper de reportes y controller `/report/barcode`.
  - El QR codifica la URL oficial de consulta pública del Ministerio de Hacienda de El Salvador con los parámetros de la factura: `https://admin.factura.gob.sv/consultaPublica?ambiente=01&codGen={codigo_generacion}&fechaEmi={fecha_emision}` o el payload JSON condensado de identificación.
  - No requiere instalar dependencias adicionales en tiempo de ejecución.
- **Alternativas consideradas**:
  - *Imagen estática fija de QR*: Descartada por violar la regla de no usar placeholders y no corresponder al código de generación real de cada factura.

---

### Decisión 3: Algoritmo de Conversión de Importes a Palabras ("Total en Letras")
- **Decisión**: Implementar un método utilitario en Python dentro del modelo `panaderia.factura` (`_monto_en_palabras(monto)`) que transforme de forma determinista importes numéricos a su representación textual en español (ej. `79.00` $\to$ `"SETENTA Y NUEVE CON 00/100 USD"`).
- **Racional**:
  - Evita la dependencia de librerías externas no incluidas en Odoo core como `num2words`.
  - Garantiza un formato estandarizado para El Salvador: números en mayúsculas seguidos del conector "CON XX/100 USD".
- **Alternativas consideradas**:
  - *Librería externa `num2words`*: Descartada para evitar rotura de compatibilidad o necesidad de recompilar imágenes Docker sin conexión a Internet.

---

### Decisión 4: Generación y Asignación de Campos DTE Oficiales
- **Decisión**: Generar automáticamente los identificadores DTE al crear la factura o al confirmarla:
  - **Código de Generación**: `str(uuid.uuid4()).upper()` (UUID v4 canónico de 36 caracteres en mayúsculas).
  - **Número de Control**: Formato oficial MH `DTE-01-M001P001-{correlativo:015d}` respaldado por una secuencia Odoo dedicada.
  - **Sello de Recepción**: Cadena hash alfanumérica de 40 caracteres generada a partir de la firma de los metadatos de la factura.
  - **Modelo de Facturación**: Constante `'Modelo Facturación previo'` (tipo 1).
  - **Tipo de Transmisión**: Constante `'Transmisión normal'` (tipo 1).
  - **Fecha y Hora de Generación**: Fecha y hora exacta de emisión en formato `YYYY-MM-DD HH:MM:SS`.
- **Racional**:
  - Reproduce fielmente el esquema JSON y la representación gráfica del modelo oficial entregado por el usuario.
  - Permite pruebas offline completas sin depender de credenciales reales ni certificados PKI del Ministerio de Hacienda.

---

### Decisión 5: Inclusión y Visualización del Logotipo de la Panadería
- **Decisión**:
  - El logotipo proporcionado por el usuario (`Delicias Dulces - PANADERÍA`) se guarda en `Modulo_Odoo/static/src/img/logo_delicias_dulces.png`.
  - En la plantilla QWeb, se enlaza directamente mediante ruta estática `/panaderia/static/src/img/logo_delicias_dulces.png` o mediante `image_data_uri` / base64 embebido para asegurar renderizado infalible tanto en visualización web como al compilar con `wkhtmltopdf`.
  - Se actualiza la compañía por defecto de la panadería para asociar dicho logotipo.
- **Racional**:
  - Garantiza que el logotipo aparezca con la más alta nitidez en el PDF y en la interfaz de Odoo sin dependencias de red.

---

### Decisión 6: Interacción y Botones de Acción en UI
- **Decisión**:
  - En el formulario de `panaderia.factura`: Botón `"Imprimir Factura DTE"` (`action_print_factura_dte()`) en la cabecera.
  - En el formulario de `panaderia.venta`: Botón `"Imprimir Factura DTE"` (`action_print_factura_dte()`) disponible en cuanto la venta esté confirmada y tenga factura asociada.
  - Acción de reporte vinculada en el menú "Imprimir" nativo de Odoo.
- **Racional**:
  - Cumple el requerimiento del usuario de emitir el comprobante cuando se finaliza el proceso correspondiente de venta o cobro, con máxima agilidad para el cajero.
