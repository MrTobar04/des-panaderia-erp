# SPEC-2.1.1: Registro y Proceso de Ventas Esencial

## 1. Objective
Implementar el módulo de ventas en Odoo para la panadería "Delicias Dulces", permitiendo a los cajeros y dependientes registrar órdenes de venta en mostrador con múltiples líneas de productos, calcular automáticamente subtotales e importes totales, gestionar el ciclo de vida del pedido (`Borrador` $\to$ `Confirmada`), y descontar en tiempo real las cantidades vendidas del inventario disponible.

## 2. Scope
### 2.1. Included
* Modelos Odoo:
  * `panaderia.venta`: Encabezado de la venta (folio secuencial `VEN-XXXX`, cliente, fecha, estado, importe total).
  * `panaderia.venta.linea`: Líneas de detalle (producto, cantidad, precio unitario, subtotal computado).
* Flujo de estados con barra de estado (`statusbar`):
  * `draft` (Borrador): Edición libre de productos, cantidades y precios.
  * `confirmed` (Confirmada): Bloqueo de edición, validación de stock, decremento de inventario y generación automática de factura.
  * `cancelled` (Cancelada): Reversión de la venta (si aplica en estado borrador o previa autorización).
* Cálculo reactivo (`@api.depends`) de subtotales por línea y total general de la venta.
* Botón de acción "Confirmar Venta" que ejecuta la reducción de stock atómica.
* Vistas: Árbol con totales y estados, Formulario optimizado para caja/mostrador.

### 2.2. Not Included (Out of Scope)
* Módulo de Punto de Venta (POS) con terminales fiscales e impresoras de tickets térmicos por hardware.
* Manejo de cotizaciones con fechas de vencimiento y envío por correo electrónico SMTP.
* Descuentos promocionales complejos por cupones o programas de lealtad multicanal.
* Envíos a domicilio o logística de rutas de reparto.

## 3. Context and Restrictions
* **Context:** Conecta el cliente (`SPEC-3.1.1`) con el inventario (`SPEC-1.1.1`, `SPEC-1.2.1`) y dispara la facturación simple (`SPEC-4.1.1`).
* **Restrictions:**
  * Al pasar a `confirmed`, no se puede volver a editar el detalle de la venta.
  * Si la cantidad de un producto excede el stock disponible, debe emitir una confirmación o alerta de advertencia.
  * El folio debe generarse mediante una secuencia automática en Odoo (`ir.sequence`).

## 4. Design (Implementation Details)
* **Architecture:** Modelos relacionales `panaderia.venta` y `panaderia.venta.linea` en `models/venta.py`, vistas con grilla editable en `views/venta_views.xml`, y secuencia en `data/venta_sequence.xml`.
* **Data Model:**
  ```python
  class PanaderiaVenta(models.Model):
      _name = 'panaderia.venta'
      _description = 'Orden de Venta de Panadería'
      _order = 'fecha desc, name desc'

      name = fields.Char(string='Folio', required=True, copy=False, readonly=True, default='Nuevo')
      cliente_id = fields.Many2one('res.partner', string='Cliente', required=True)
      fecha = fields.Datetime(string='Fecha de Venta', default=fields.Datetime.now, required=True)
      linea_ids = fields.One2many('panaderia.venta.linea', 'venta_id', string='Líneas de Venta')
      total = fields.Float(string='Total ($)', compute='_compute_total', store=True)
      state = fields.Selection([
          ('draft', 'Borrador'),
          ('confirmed', 'Confirmada'),
          ('cancelled', 'Cancelada')
      ], string='Estado', default='draft', required=True, tracking=True)
      factura_id = fields.Many2one('panaderia.factura', string='Factura Asociada', readonly=True)

      @api.depends('linea_ids.subtotal')
      def _compute_total(self):
          for order in self:
              order.total = sum(order.linea_ids.mapped('subtotal'))

  class PanaderiaVentaLinea(models.Model):
      _name = 'panaderia.venta.linea'
      _description = 'Línea de Venta de Panadería'

      venta_id = fields.Many2one('panaderia.venta', string='Orden de Venta', ondelete='cascade', required=True)
      producto_id = fields.Many2one('panaderia.producto', string='Producto', required=True)
      cantidad = fields.Float(string='Cantidad', default=1.0, required=True)
      precio_unitario = fields.Float(string='Precio Unitario ($)', required=True)
      subtotal = fields.Float(string='Subtotal ($)', compute='_compute_subtotal', store=True)

      @api.onchange('producto_id')
      def _onchange_producto_id(self):
          if self.producto_id:
              self.precio_unitario = self.producto_id.precio_venta

      @api.depends('cantidad', 'precio_unitario')
      def _compute_subtotal(self):
          for line in self:
              line.subtotal = line.cantidad * line.precio_unitario
  ```
* **Acción de Confirmación:**
  * Método `action_confirm()`:
    1. Asigna número de secuencia si es 'Nuevo'.
    2. Itera sobre `linea_ids` y decrementa `cantidad_disponible` en `producto_id`.
    3. Actualiza el acumulado `total_compras` del cliente (`cliente_id`).
    4. Crea automáticamente la factura en `panaderia.factura` con estado `pending`.
    5. Cambia `state` a `confirmed`.
* **UI/UX:**
  * Barra de estado interactiva (`widget="statusbar"`).
  * Grilla de líneas en vista formulario con edición inline rápida.
  * Indicador de total destacado en formato monetario con tipografía grande.

## 5. Acceptance Criteria
* **Scenario 1: Creación de orden de venta en mostrador**
  * **Given** que un cajero abre el formulario de nueva venta y selecciona un cliente.
  * **When** agrega 10 unidades de "Pan Francés" ($0.10 c/u) y 1 "Pastel Selva Negra" ($15.00 c/u).
  * **Then** el sistema calcula automáticamente los subtotales ($1.00 y $15.00) y el total general de $16.00.

* **Scenario 2: Confirmación de venta y descuento de existencias**
  * **Given** que el producto "Pan Francés" tiene 50 unidades en stock y la orden de 10 unidades está en estado `draft`.
  * **When** el cajero presiona el botón "Confirmar Venta".
  * **Then** el estado de la venta pasa a `confirmed`, se le asigna el folio secuencial (ej. `VEN-0001`), el stock de "Pan Francés" baja a 40 unidades y se crea la factura correspondiente.

* **Scenario 3: Restricción de edición tras confirmación**
  * **Given** una orden de venta en estado `confirmed`.
  * **When** un usuario intenta modificar los productos, cantidades o cliente.
  * **Then** los campos permanecen en modo de solo lectura, impidiendo alteraciones de datos.

## 6. Verification Plan
* **Manual UI Testing:**
  1. Registrar una venta con 3 productos diferentes.
  2. Verificar que los precios unitarios se completen automáticamente al seleccionar el producto.
  3. Comprobar que los subtotales y el total se actualicen inmediatamente al cambiar cantidades.
  4. Confirmar la orden y validar el decremento del stock en la vista de Productos.
  5. Validar que la orden genere y enlace la factura automáticamente.
* **Automated ORM Testing:**
  * Test unitario de cálculo de totales, generación de secuencia y decremento de stock al invocar `action_confirm()`.

## 7. Security and Privacy
* **Access Control:**
  * Cajeros / Operadores: Permiso para crear y confirmar ventas.
  * Administradores: Permiso para cancelar o modificar configuraciones de secuencia.
* **PII & Privacy:** Registra el nombre y contacto del cliente asociado a la compra.

## 8. Risks and Mitigation
* **Risk:** Concurrencia de ventas sobre el mismo producto con stock limitado.
  * **Mitigation:** Uso de transacciones atómicas en `action_confirm()` con verificación final de existencia antes del commit.

## 9. Deliverables & Config as Code
* Modelo: `Modulo_Odoo/models/venta.py`.
* Vistas: `Modulo_Odoo/views/venta_views.xml`.
* Secuencia: `Modulo_Odoo/data/venta_sequence.xml`.
* Reglas de acceso en `Modulo_Odoo/security/ir.model.access.csv`.

## 10. Definition of Done (DoD)
* [x] Modelos `panaderia.venta` y `panaderia.venta.linea` completamente funcionales.
* [x] Secuencia automática de folios `VEN-XXXX` operativa.
* [x] Descuento atómico de existencias verificado en inventario.
* [x] Creación automática de factura vinculada al confirmar.
* [x] Procedimiento de prueba `docs/test-procedures/test-procedure-2.1.1.md` documentado y verificado.
