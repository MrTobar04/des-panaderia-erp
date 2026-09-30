# SPEC-4.1.1: Generación de Facturas Simples

## 1. Objective
Implementar el módulo de facturación simple en Odoo para la panadería "Delicias Dulces", permitiendo la emisión automática y manual de comprobantes de facturación vinculados a ventas, asignación de numeración correlativa automática (`FAC-XXXX`), gestión de ciclo de cobranza (`Pendiente` $\to$ `Pagada`), y registro del método de pago utilizado en caja.

## 2. Scope
### 2.1. Included
* Modelo Odoo `panaderia.factura` para la gestión de comprobantes:
  * Número de factura con secuencia automática correlativa (`FAC-XXXX`).
  * Vínculo directo a la orden de venta origen (`venta_id`).
  * Cliente receptor (`cliente_id`).
  * Fecha de emisión (`fecha_emision`) y fecha de pago (`fecha_pago`).
  * Desglose de importe total (`monto_total`).
  * Método de pago (`metodo_pago`: `efectivo`, `tarjeta`, `transferencia`).
  * Estado de la factura (`state`: `pending` / Pendiente, `paid` / Pagada, `cancelled` / Cancelada).
* Botón de acción rápida en venta "Ver Factura" y generación automática al confirmar la orden.
* Botón de acción "Registrar Pago" en el formulario de la factura que pasa el estado a `paid` y registra la fecha actual.
* Vistas: Árbol con estado de pago y monto, Formulario con diseño claro e imprimible.

### 2.2. Not Included (Out of Scope)
* Facturación Electrónica DTE (Ministerio de Hacienda / SAT) con firma digital y certificados criptográficos PKI.
* Integración bancaria con conciliación automática de extractos en línea.
* Facturación recurrente por suscripción o notas de débito complejas.

## 3. Context and Restrictions
* **Context:** Deriva directamente de la confirmación de la venta (`SPEC-2.1.1`) y alimenta el reporte de ingresos diarios (`SPEC-5.1.1`).
* **Restrictions:**
  * Cada venta confirmada debe tener exactamente una factura asociada principal.
  * Una factura en estado `paid` no puede modificarse ni revertirse sin autorización de administrador.

## 4. Design (Implementation Details)
* **Architecture:** Modelo `panaderia.factura` en `models/factura.py`, vistas en `views/factura_views.xml`, y secuencia en `data/factura_sequence.xml`.
* **Data Model:**
  ```python
  class PanaderiaFactura(models.Model):
      _name = 'panaderia.factura'
      _description = 'Factura Simple de Panadería'
      _order = 'fecha_emision desc, name desc'

      name = fields.Char(string='Número de Factura', required=True, copy=False, readonly=True, default='Borrador')
      venta_id = fields.Many2one('panaderia.venta', string='Orden de Venta Origen', readonly=True)
      cliente_id = fields.Many2one('res.partner', string='Cliente', required=True)
      fecha_emision = fields.Datetime(string='Fecha de Emisión', default=fields.Datetime.now, required=True)
      fecha_pago = fields.Datetime(string='Fecha de Pago', readonly=True)
      monto_total = fields.Float(string='Monto Total ($)', required=True)
      metodo_pago = fields.Selection([
          ('efectivo', 'Efectivo'),
          ('tarjeta', 'Tarjeta de Débito / Crédito'),
          ('transferencia', 'Transferencia')
      ], string='Método de Pago', default='efectivo', required=True)
      state = fields.Selection([
          ('pending', 'Pendiente'),
          ('paid', 'Pagada'),
          ('cancelled', 'Cancelada')
      ], string='Estado de Pago', default='pending', required=True, tracking=True)

      def action_register_payment(self):
          for rec in self:
              rec.write({
                  'state': 'paid',
                  'fecha_pago': fields.Datetime.now()
              })
  ```
* **UI/UX:**
  * Barra de estado interactiva (`statusbar`) con estados `pending` $\to$ `paid`.
  * Filtro rápido "Facturas Pendientes de Pago".
  * Botón Smart Button en el formulario de ventas que abre la factura asociada.

## 5. Acceptance Criteria
* **Scenario 1: Emisión automática de factura al confirmar venta**
  * **Given** una orden de venta de $16.00 que se encuentra en estado borrador.
  * **When** el cajero presiona "Confirmar Venta".
  * **Then** se crea una factura vinculada con número correlativo (ej. `FAC-0001`), monto `$16.00`, cliente asociado y estado inicial `pending`.

* **Scenario 2: Registro de pago en caja**
  * **Given** una factura en estado `pending`.
  * **When** el operador selecciona el método de pago "Efectivo" y presiona "Registrar Pago".
  * **Then** el estado de la factura cambia a `paid` y se graba la fecha y hora exacta del cobro.

* **Scenario 3: Navegación bidireccional entre Venta y Factura**
  * **Given** una factura creada desde una venta.
  * **When** el usuario hace clic en el enlace de la venta origen desde la factura (o viceversa mediante el Smart Button).
  * **Then** el sistema navega instantáneamente al documento correspondiente sin pérdida de contexto.

## 6. Verification Plan
* **Manual UI Testing:**
  1. Confirmar una venta y comprobar que el botón "Ver Factura" aparezca en el encabezado.
  2. Abrir la factura generada y validar que el número `FAC-XXXX` y el monto coincidan con la orden de venta.
  3. Ejecutar la acción "Registrar Pago" y comprobar la transición a estado `paid`.
  4. Filtrar por facturas pagadas y verificar que aparezca en el listado.
* **Automated ORM Testing:**
  * Test unitario verificando la creación de secuencia `FAC-XXXX` y el cambio de estado con `action_register_payment()`.

## 7. Security and Privacy
* **Access Control:**
  * Cajeros: Emisión de facturas y registro de pagos en caja.
  * Administradores: Modificación de series de numeración y cancelación de comprobantes.
* **PII & Privacy:** Datos fiscales básicos del cliente y montos monetarios.

## 8. Risks and Mitigation
* **Risk:** Emisión de múltiples facturas duplicadas para la misma orden de venta.
  * **Mitigation:** Validación a nivel de ORM impidiendo que una orden cree más de una factura activa.

## 9. Deliverables & Config as Code
* Modelo: `Modulo_Odoo/models/factura.py`.
* Vistas: `Modulo_Odoo/views/factura_views.xml`.
* Secuencia: `Modulo_Odoo/data/factura_sequence.xml`.
* Reglas de acceso en `Modulo_Odoo/security/ir.model.access.csv`.

## 10. Definition of Done (DoD)
* [ ] Modelo `panaderia.factura` implementado con secuencia automática `FAC-XXXX`.
* [ ] Flujo de transición `pending` $\to$ `paid` operativo mediante botón "Registrar Pago".
* [ ] Integración automática con el módulo de ventas (`SPEC-2.1.1`).
* [ ] Procedimiento de prueba `docs/test-procedures/test-procedure-4.1.1.md` completado y verificado.
