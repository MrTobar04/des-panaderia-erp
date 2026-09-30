# SPEC-5.1.1: Reportes Operativos Diarios y Alertas de Stock

## 1. Objective
Implementar el módulo de reportería ejecutiva y operativa en Odoo para la panadería "Delicias Dulces", permitiendo a los administradores y dueños del negocio visualizar métricas clave en tiempo real: resumen de ventas del día, ranking de productos más vendidos y listado de productos con stock bajo en estado de alerta.

## 2. Scope
### 2.1. Included
* Tres reportes e interfaces de consulta analítica esenciales:
  1. **Reporte de Ventas del Día:** Sumatoria total de ingresos, conteo de órdenes confirmadas y desglose de formas de pago en la jornada actual.
  2. **Reporte de Productos Más Vendidos:** Ranking ordenado por volumen de unidades vendidas y montos generados.
  3. **Reporte de Stock Bajo (Alerta de Reabastecimiento):** Listado inmediato de todos los productos donde `cantidad_disponible <= stock_minimo`.
* Formatos de visualización en Odoo:
  * Vistas pivote y gráficas interactivas (`graph`, `pivot`) para ventas.
  * Vista de lista pre-filtrada y reporte imprimible (QWeb PDF express).
* Menú centralizado: "Panadería $\to$ Reportes".

### 2.2. Not Included (Out of Scope)
* Cuadros de mando complejos con integración a PowerBI o Tableau externo.
* Proyecciones matemáticas de demanda con Machine Learning.
* Reportes fiscales y balances contables de pérdidas y ganancias.

## 3. Context and Restrictions
* **Context:** Agrega y sintetiza la información de todos los módulos anteriores: Inventario (`SPEC-1.1.1`, `SPEC-1.2.1`), Ventas (`SPEC-2.1.1`), Clientes (`SPEC-3.1.1`) y Facturación (`SPEC-4.1.1`).
* **Restrictions:**
  * Debe generar información actualizada al instante sin requerir procesos batch nocturnos pesados.
  * El reporte impreso en PDF debe caber en una sola página de resumen operativo.

## 4. Design (Implementation Details)
* **Architecture:** Vistas analíticas integradas en `views/reporte_views.xml`, modelo de reporte SQL / ORM en `models/reporte_panaderia.py`, y plantilla QWeb en `report/reporte_diario_template.xml`.
* **Data Model / Vistas SQL:**
  ```python
  class PanaderiaReporteVentas(models.Model):
      _name = 'panaderia.reporte.ventas'
      _description = 'Análisis de Ventas de Panadería'
      _auto = False
      _order = 'fecha desc'

      fecha = fields.Date(string='Fecha', readonly=True)
      producto_id = fields.Many2one('panaderia.producto', string='Producto', readonly=True)
      categoria_id = fields.Many2one('panaderia.categoria', string='Categoría', readonly=True)
      cantidad_vendida = fields.Float(string='Unidades Vendidas', readonly=True)
      total_ingresos = fields.Float(string='Total Ingresos ($)', readonly=True)

      def init(self):
          tools.drop_view_if_exists(self.env.cr, self._table)
          self.env.cr.execute("""
              CREATE OR REPLACE VIEW panaderia_reporte_ventas AS (
                  SELECT
                      min(l.id) AS id,
                      v.fecha::date AS fecha,
                      l.producto_id AS producto_id,
                      p.categoria_id AS categoria_id,
                      sum(l.cantidad) AS cantidad_vendida,
                      sum(l.subtotal) AS total_ingresos
                  FROM panaderia_venta_linea l
                  JOIN panaderia_venta v ON l.venta_id = v.id
                  JOIN panaderia_producto p ON l.producto_id = p.id
                  WHERE v.state = 'confirmed'
                  GROUP BY v.fecha::date, l.producto_id, p.categoria_id
              )
          """)
  ```
* **UI/UX:**
  * Vista Gráfica de Barras (`graph type="bar"`) con los Top 5 productos más vendidos.
  * Vista Pivote interactiva cruzando categorías con días del mes.
  * Botón de acción para imprimir PDF "Resumen Operativo Diario".

## 5. Acceptance Criteria
* **Scenario 1: Consulta de ventas del día actual**
  * **Given** que durante el día se confirmaron 5 ventas por un total acumulado de $85.00.
  * **When** el administrador accede a Panadería $\to$ Reportes $\to$ Ventas del Día.
  * **Then** la vista muestra el total consolidado de $85.00 y el desglose correspondiente a la fecha actual.

* **Scenario 2: Detección de productos más vendidos**
  * **Given** que se vendieron 100 "Pan Francés" y 10 "Pasteles Selva Negra".
  * **When** se consulta el ranking de productos más vendidos.
  * **Then** "Pan Francés" aparece en la primera posición con 100 unidades y barra destacada.

* **Scenario 3: Listado de alerta de stock bajo**
  * **Given** que 3 productos de panadería están por debajo de su stock mínimo.
  * **When** el encargado de panadería abre el reporte de "Stock Bajo / Alertas".
  * **Then** la grilla lista exactamente esos 3 productos con sus cantidades actuales, stock mínimo y diferencia faltante para reposición.

## 6. Verification Plan
* **Manual UI Testing:**
  1. Registrar ventas de varios productos en fechas controladas.
  2. Abrir la vista de análisis de ventas y alternar entre vista Gráfica y vista Pivote.
  3. Comprobar que los totales del reporte coincidan exactamente con la suma de ventas confirmadas.
  4. Abrir la vista de Stock Bajo y verificar que los productos mostrados coincidan con los que tienen alerta activa.
  5. Imprimir el reporte PDF y verificar formato y legibilidad.
* **Automated ORM Testing:**
  * Validación de la consulta de la vista SQL `panaderia_reporte_ventas` ante inserción de nuevas líneas de venta.

## 7. Security and Privacy
* **Access Control:**
  * Administradores y Gerencia: Acceso total a reportes y métricas financieras.
  * Operadores: Acceso restringido al reporte de stock bajo para reposición física.
* **PII & Privacy:** Datos agregados estadísticos sin exposición directa de PII de clientes.

## 8. Risks and Mitigation
* **Risk:** Rendimiento de agregación en bases de datos con alto volumen de ventas.
  * **Mitigation:** Uso de vistas indexadas y filtros por rango de fecha para acotar la consulta.

## 9. Deliverables & Config as Code
* Modelo analítico: `Modulo_Odoo/models/reporte_panaderia.py`.
* Vistas analíticas y gráficas: `Modulo_Odoo/views/reporte_views.xml`.
* Reporte imprimible QWeb: `Modulo_Odoo/report/reporte_diario_template.xml`.
* Reglas de acceso en `Modulo_Odoo/security/ir.model.access.csv`.

## 10. Definition of Done (DoD)
* [ ] Vista SQL / Modelo analítico `panaderia.reporte.ventas` creado y validado.
* [ ] Las 3 vistas requeridas (Ventas del Día, Más Vendidos, Stock Bajo) accesibles desde el menú.
* [ ] Plantilla de reporte QWeb PDF operativa.
* [ ] Procedimiento de prueba `docs/test-procedures/test-procedure-5.1.1.md` documentado y verificado.
