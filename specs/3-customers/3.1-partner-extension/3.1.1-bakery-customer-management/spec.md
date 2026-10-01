# SPEC-3.1.1: Extensión y Registro de Clientes

## 1. Objective
Extender el modelo estándar de contactos y clientes de Odoo (`res.partner`) para la panadería "Delicias Dulces", permitiendo registrar clientes específicos del negocio, capturar su fecha de registro en tienda, acumular automáticamente el importe histórico de sus compras, y proporcionar vistas y filtros dedicados para la gestión comercial de panadería.

## 2. Scope
### 2.1. Included
* Herencia y extensión del modelo estándar `res.partner`:
  * `es_cliente_panaderia` (`Boolean`, flag para diferenciar clientes de panadería de otros contactos generales).
  * `fecha_registro_panaderia` (`Date`, fecha en que se dio de alta el cliente en la panadería, por defecto hoy).
  * `total_compras_panaderia` (`Float` compute/store, sumatoria de ventas confirmadas asociadas al cliente).
  * `notas_preferencias` (`Text`, notas sobre alergias o productos preferidos).
* Filtro predeterminado en Odoo para mostrar únicamente clientes de panadería (`[('es_cliente_panaderia', '=', True)]`).
* Vistas adaptadas: Formulario con pestaña "Datos de Panadería" y Vista Árbol con columnas de fecha de registro y total acumulado de compras.
* Datos semilla con al menos un cliente "Cliente General / Mostrador" precargado.

### 2.2. Not Included (Out of Scope)
* Programas complejos de puntos de lealtad o monedero electrónico canjeable.
* Integración con burós de crédito o límites de crédito financiero.
* Portales de autoservicio web para clientes.

## 3. Context and Restrictions
* **Context:** Los clientes registrados aquí son seleccionados en las órdenes de venta (`SPEC-2.1.1`) y en las facturas (`SPEC-4.1.1`).
* **Restrictions:**
  * No debe sobreescribir ni romper la lógica base del modelo estándar `res.partner` de Odoo.
  * Debe existir siempre un registro "Cliente Mostrador / Venta Rápida" para ventas anónimas de mostrador.

## 4. Design (Implementation Details)
* **Architecture:** Extensión de modelo mediante herencia `_inherit = 'res.partner'` en `models/cliente.py` y extensión de vistas mediante `inherit_id` en `views/cliente_views.xml`.
* **Data Model:**
  ```python
  class ResPartner(models.Model):
      _inherit = 'res.partner'

      es_cliente_panaderia = fields.Boolean(string='Es Cliente de Panadería', default=True)
      fecha_registro_panaderia = fields.Date(string='Fecha de Registro', default=fields.Date.context_today)
      total_compras_panaderia = fields.Float(string='Total en Compras ($)', compute='_compute_total_compras_panaderia', store=True)
      notas_preferencias = fields.Text(string='Preferencias / Notas de Panadería')
      venta_panaderia_ids = fields.One2many('panaderia.venta', 'cliente_id', string='Ventas de Panadería')

      @api.depends('venta_panaderia_ids.state', 'venta_panaderia_ids.total')
      def _compute_total_compras_panaderia(self):
          for partner in self:
              ventas_confirmadas = partner.venta_panaderia_ids.filtered(lambda v: v.state == 'confirmed')
              partner.total_compras_panaderia = sum(ventas_confirmadas.mapped('total'))
  ```
* **UI/UX:**
  * Vista de menú directo: "Panadería $\to$ Clientes" con acción de ventana (`ir.actions.act_window`) pre-filtrada con `context={'default_es_cliente_panaderia': True}` y domain `[('es_cliente_panaderia', '=', True)]`.
  * Vista Formulario con bloque de estadísticas de compras y notas especiales.

## 5. Acceptance Criteria
* **Scenario 1: Registro de nuevo cliente de panadería**
  * **Given** que el usuario ingresa al menú Panadería $\to$ Clientes y hace clic en "Crear".
  * **When** registra el nombre "Carlos Mendoza", teléfono "7123-4567" y notas "Prefiere pan integral".
  * **Then** el sistema guarda el cliente con el flag `es_cliente_panaderia = True` y la fecha de hoy establecida automáticamente.

* **Scenario 2: Actualización automática del total acumulado de compras**
  * **Given** un cliente registrado con `total_compras_panaderia = $0.00`.
  * **When** se confirman dos ventas a su nombre por $12.50 y $7.50 respectivamente.
  * **Then** el campo `total_compras_panaderia` del cliente muestra automáticamente `$20.00`.

* **Scenario 3: Filtrado de contactos en la vista de panadería**
  * **Given** que existen contactos de proveedores y clientes en la base de datos de Odoo.
  * **When** el operador consulta el menú Panadería $\to$ Clientes.
  * **Then** la lista muestra únicamente aquellos contactos con `es_cliente_panaderia = True`.

## 6. Verification Plan
* **Manual UI Testing:**
  1. Crear un cliente regular y verificar que la fecha de registro se asigne automáticamente.
  2. Ejecutar una venta a dicho cliente y verificar que el total acumulado en compras aumente tras la confirmación.
  3. Comprobar que en el menú general de Panadería $\to$ Clientes se aplique el filtro correcto.
* **Automated ORM Testing:**
  * Test unitario de cálculo de `_compute_total_compras_panaderia` tras la confirmación de múltiples órdenes de venta.

## 7. Security and Privacy
* **Access Control:**
  * Cajeros y operadores: Permiso de lectura y creación de clientes.
  * Administradores: Permiso completo de edición y eliminación.
* **PII & Privacy:** Manejo de datos de contacto (nombre, teléfono, correo) almacenados de forma segura bajo los estándares nativos de Odoo.

## 8. Risks and Mitigation
* **Risk:** Confusión entre clientes generales de Odoo y clientes de panadería.
  * **Mitigation:** Uso de acción de ventana con dominio explícito y valor predeterminado por contexto.

## 9. Deliverables & Config as Code
* Modelo de extensión: `Modulo_Odoo/models/cliente.py`.
* Vistas heredadas: `Modulo_Odoo/views/cliente_views.xml`.
* Datos semilla (Cliente Mostrador): `Modulo_Odoo/data/cliente_data.xml`.

## 10. Definition of Done (DoD)
* [x] Modelo `res.partner` extendido con los campos de panadería.
* [x] Vistas Formulario y Lista personalizadas con filtros de clientes de panadería.
* [x] Conexión y cálculo automático de `total_compras_panaderia` probado con ventas confirmadas.
* [x] Procedimiento de prueba `docs/test-procedures/test-procedure-3.1.1.md` completado y verificado.
