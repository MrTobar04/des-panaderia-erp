# SPEC-1.2.1: Control y Alerta de Stock Mínimo

## 1. Objective
Implementar el sistema de control de existencias en tiempo real y alertas de reabastecimiento en Odoo para la panadería "Delicias Dulces", permitiendo monitorear las cantidades físicas disponibles por producto, configurar niveles mínimos de reserva, emitir alertas visuales automáticas cuando el inventario caiga por debajo del umbral de seguridad, y ajustar existencias de forma auditable.

## 2. Scope
### 2.1. Included
* Extensión del modelo `panaderia.producto` con campos de inventario:
  * `cantidad_disponible` (`Float` o `Integer`, cantidad actual en panadería).
  * `stock_minimo` (`Float` o `Integer`, umbral mínimo configurable).
  * `alerta_stock_bajo` (`Boolean` compute/stored, indicador binario de advertencia).
  * `estado_stock` (`Selection`: `normal`, `bajo`, `agotado`).
* Modelo de movimientos o bitácora de ajuste manual: `panaderia.inventario.ajuste` para registrar ingresos de producción o mermas con fecha, motivo y cantidad.
* Filtros predefinidos en vistas: "Stock Bajo" y "Agotados".
* Indicadores visuales en la vista lista (badges de color: verde para normal, amarillo para stock bajo, rojo para agotado).

### 2.2. Not Included (Out of Scope)
* Multi-almacén o ubicaciones físicas geolocalizadas complejas (se maneja un único inventario de tienda).
* Reglas automáticas de reabastecimiento con compras a proveedores automáticas (se limita a alerta visual).
* Valoración de inventario perpetuo FIFO/LIFO contable avanzado.

## 3. Context and Restrictions
* **Context:** Este módulo interactúa directamente con el catálogo (`SPEC-1.1.1`), el flujo de ventas (`SPEC-2.1.1` decrementa stock) y el módulo de reportes (`SPEC-5.1.1` genera el reporte de productos con stock crítico).
* **Restrictions:**
  * El stock disponible no debe permitir valores negativos a menos que se configure una venta bajo pedido express con advertencia.
  * Los ajustes manuales deben registrar el usuario responsable y la justificación.

## 4. Design (Implementation Details)
* **Architecture:** Lógica computada en `models/producto.py` y `models/inventario_ajuste.py`, vistas con decoradores de color en `views/producto_views.xml` y `views/inventario_views.xml`.
* **Data Model:**
  ```python
  class PanaderiaProducto(models.Model):
      _inherit = 'panaderia.producto'

      cantidad_disponible = fields.Float(string='Stock Disponible', default=0.0, required=True)
      stock_minimo = fields.Float(string='Stock Mínimo de Alerta', default=5.0, required=True)
      alerta_stock_bajo = fields.Boolean(string='Alerta Stock Bajo', compute='_compute_estado_stock', store=True)
      estado_stock = fields.Selection([
          ('normal', 'Normal'),
          ('bajo', 'Bajo Stock'),
          ('agotado', 'Agotado')
      ], string='Estado de Stock', compute='_compute_estado_stock', store=True, default='agotado')

      @api.depends('cantidad_disponible', 'stock_minimo')
      def _compute_estado_stock(self):
          for rec in self:
              if rec.cantidad_disponible <= 0:
                  rec.estado_stock = 'agotado'
                  rec.alerta_stock_bajo = True
              elif rec.cantidad_disponible <= rec.stock_minimo:
                  rec.estado_stock = 'bajo'
                  rec.alerta_stock_bajo = True
              else:
                  rec.estado_stock = 'normal'
                  rec.alerta_stock_bajo = False
  ```
* **Ajustes de Inventario:**
  ```python
  class PanaderiaInventarioAjuste(models.Model):
      _name = 'panaderia.inventario.ajuste'
      _description = 'Ajuste Manual de Inventario'
      _order = 'fecha desc'

      producto_id = fields.Many2one('panaderia.producto', string='Producto', required=True)
      fecha = fields.Datetime(string='Fecha', default=fields.Datetime.now, required=True)
      tipo = fields.Selection([('entrada', 'Entrada de Producción'), ('salida', 'Merma / Desperdicio'), ('conteo', 'Ajuste de Conteo')], required=True, default='entrada')
      cantidad = fields.Float(string='Cantidad', required=True)
      motivo = fields.Char(string='Motivo / Observación', required=True)
      user_id = fields.Many2one('res.users', string='Responsable', default=lambda self: self.env.user)
  ```
* **UI/UX:**
  * Vista Tree con decoradores: `decoration-danger="estado_stock == 'agotado'"` y `decoration-warning="estado_stock == 'bajo'"`.
  * Filtro rápido en la barra de búsqueda `name="filter_stock_bajo"` con domain `[('alerta_stock_bajo', '=', True)]`.
  * Botón de acción rápida "Ajustar Stock" desde el formulario del producto.

## 5. Acceptance Criteria
* **Scenario 1: Disparo de alerta por stock bajo**
  * **Given** que un producto "Baguette Tradicional" tiene configurado un stock mínimo de 10 unidades.
  * **When** su cantidad disponible pasa de 15 a 8 unidades tras una venta o ajuste.
  * **Then** el campo `alerta_stock_bajo` se vuelve `True`, `estado_stock` cambia a `bajo` y el registro se resalta en amarillo en la vista lista.

* **Scenario 2: Detección de producto agotado**
  * **Given** que un producto "Pastel de Fresa" tiene 2 unidades disponibles.
  * **When** se confirma una venta de 2 unidades reduciendo el stock a 0.
  * **Then** el `estado_stock` cambia a `agotado`, se resalta en rojo y aparece en el filtro de productos agotados.

* **Scenario 3: Registro de entrada de producción diaria**
  * **Given** que la cocina de la panadería hornea 50 unidades de Pan Francés.
  * **When** el operador registra un ajuste de tipo "Entrada de Producción" por +50 unidades.
  * **Then** el stock disponible del producto se incrementa en 50 y queda registrado el movimiento en la bitácora histórica.

## 6. Verification Plan
* **Manual UI Testing:**
  1. Configurar un producto con stock inicial 20 y stock mínimo 5.
  2. Aplicar un ajuste de salida por 16 unidades (quedando en 4).
  3. Comprobar que se activa el filtro de "Stock Bajo" y la alerta visual.
  4. Reducir las 4 unidades restantes y comprobar que el estado pasa a "Agotado" con badge rojo.
* **Automated ORM Testing:**
  * Pruebas unitarias de los métodos compute y validación de aplicación de ajustes de inventario.

## 7. Security and Privacy
* **Access Control:**
  * Operadores pueden consultar stock y registrar entradas ordinarias de producción.
  * Solo los supervisores/administradores pueden registrar mermas o ajustes directos de conteo.
* **PII & Privacy:** Registra únicamente el ID de usuario interno responsable del ajuste.

## 8. Risks and Mitigation
* **Risk:** Venta de productos con stock cero que provoque inconsistencia física.
  * **Mitigation:** Validación en la orden de venta que advierta al operador cuando la cantidad solicitada excede el stock disponible.

## 9. Deliverables & Config as Code
* Modelo extendido de producto en `Modulo_Odoo/models/producto.py`.
* Modelo de ajuste en `Modulo_Odoo/models/inventario_ajuste.py`.
* Vistas y filtros en `Modulo_Odoo/views/producto_views.xml` y `Modulo_Odoo/views/inventario_views.xml`.
* Permisos en `Modulo_Odoo/security/ir.model.access.csv`.

## 10. Definition of Done (DoD)
* [x] Campos de stock y cálculo reactivo `_compute_estado_stock` operativos.
* [x] Filtros de Stock Bajo y Agotado funcionando en la vista de búsqueda.
* [x] Decoradores visuales de color verificados en la vista Tree.
* [x] Formulario de ajustes de inventario probado con entradas y salidas.
* [x] Procedimiento de prueba `docs/test-procedures/test-procedure-1.2.1.md` completado y validado.

