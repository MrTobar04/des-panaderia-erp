# SPEC-1.1.2: Categorías de Productos de Panadería

## 1. Objective
Implementar la estructura de clasificación y categorización de productos de panadería en Odoo para "Delicias Dulces", permitiendo agrupar ítems bajo las 4 categorías comerciales estándar (Pan, Pastel, Galleta, Bebida) con códigos, descripciones y conteo automático de productos asignados.

## 2. Scope
### 2.1. Included
* Modelo Odoo `panaderia.categoria` para la taxonomía de productos.
* Campos obligatorios: Nombre de la Categoría (`Char`), Código corto (`Char`), Descripción (`Text`), Secuencia de ordenamiento (`Integer`), y Campo computado de cantidad de productos asociados (`Integer` compute).
* Población automática (Data XML o Hooks de inicio) de las 4 categorías obligatorias:
  1. **Pan** (e.g. Francés, Baguette, Dulce)
  2. **Pastel** (e.g. Selva Negra, Tres Leches, Tartas)
  3. **Galleta** (e.g. Chispas, Avena, Mantequilla)
  4. **Bebida** (e.g. Café, Jugos, Refrescos)
* Vistas de usuario: Lista (`tree`) y Formulario (`form`) con listado embebido de productos pertenecientes a la categoría.
* Permisos de acceso en `ir.model.access.csv`.

### 2.2. Not Included (Out of Scope)
* Jerarquía infinita multinivel de subcategorías complejas (se mantiene plano para el MVP).
* Asignación de impuestos dinámicos a nivel de categoría (se maneja en producto directo).
* Permisos granulares de edición de categoría por usuario individual.

## 3. Context and Restrictions
* **Context:** Provee la base clasificatoria requerida por `SPEC-1.1.1` (Catálogo de Productos) y `SPEC-5.1.1` (Reportes de Ventas e Inventario agrupados por categoría).
* **Restrictions:**
  * Las 4 categorías iniciales deben cargarse automáticamente mediante un archivo XML de datos (`data/categoria_data.xml`).
  * El nombre de la categoría debe ser único e insensible a mayúsculas/minúsculas.

## 4. Design (Implementation Details)
* **Architecture:** Modelo MVC Odoo con lógica en `models/categoria.py`, vistas en `views/categoria_views.xml`, y datos semilla en `data/categoria_data.xml`.
* **Data Model:**
  ```python
  class PanaderiaCategoria(models.Model):
      _name = 'panaderia.categoria'
      _description = 'Categoría de Productos de Panadería'
      _order = 'sequence, name'

      name = fields.Char(string='Nombre de Categoría', required=True, index=True)
      codigo = fields.Char(string='Código Corto', size=10, required=True)
      sequence = fields.Integer(string='Secuencia', default=10)
      descripcion = fields.Text(string='Descripción')
      producto_ids = fields.One2many('panaderia.producto', 'categoria_id', string='Productos')
      total_productos = fields.Integer(string='Total Productos', compute='_compute_total_productos', store=True)

      @api.depends('producto_ids')
      def _compute_total_productos(self):
          for rec in self:
              rec.total_productos = len(rec.producto_ids)
  ```
* **API Contracts / ORM Methods:**
  * `_compute_total_productos`: Calcula y almacena en tiempo real el conteo de productos vinculados.
  * `_sql_constraints`: Unicidad en el campo `name` y `codigo`.
* **UI/UX:**
  * Formulario con vista de Smart Button o pestaña secundaria con la grilla de productos vinculados.
  * Vista de lista simplificada y ordenada visualmente.

## 5. Acceptance Criteria
* **Scenario 1: Carga inicial de categorías base**
  * **Given** que el módulo de panadería es instalado o actualizado en la base de datos de Odoo.
  * **When** el usuario navega a Panadería $\to$ Configuración $\to$ Categorías.
  * **Then** el sistema muestra exactamente las 4 categorías precargadas: Pan, Pastel, Galleta y Bebida.

* **Scenario 2: Cálculo dinámico de productos por categoría**
  * **Given** que la categoría "Pan" tiene 3 productos asociados.
  * **When** se crea un nuevo producto asignado a "Pan".
  * **Then** el campo `total_productos` de la categoría "Pan" se actualiza automáticamente a 4.

* **Scenario 3: Validación de código o nombre duplicado**
  * **Given** que existe la categoría "Bebida" con código "BEB".
  * **When** un usuario intenta registrar otra categoría con el mismo nombre "Bebida" o código "BEB".
  * **Then** el sistema arroja un error de restricción impidiendo la duplicidad.

## 6. Verification Plan
* **Manual UI Testing:**
  1. Verificar la presencia de las 4 categorías estándar en la vista de lista tras la instalación.
  2. Crear una categoría personalizada de prueba (e.g. "Postres Fríos").
  3. Asociar 2 productos a la nueva categoría y comprobar que el contador refleje el número 2.
  4. Validar la navegación directa desde la categoría a sus productos asociados.
* **Automated ORM Testing:**
  * Test unitario verificando la correcta ejecución de `_compute_total_productos` y unicidad de clave.

## 7. Security and Privacy
* **Access Control:**
  * Todos los usuarios del grupo `group_panaderia_user` tienen acceso de sólo lectura.
  * Los administradores del grupo `group_panaderia_manager` tienen permisos completos de edición y creación.
* **PII & Privacy:** Información pública operativa sin datos personales.

## 8. Risks and Mitigation
* **Risk:** Intentar borrar una categoría que ya contiene productos en inventario o ventas.
  * **Mitigation:** Implementar `ondelete='restrict'` en el campo `categoria_id` del producto para prevenir eliminaciones en cascada accidentales.

## 9. Deliverables & Config as Code
* Archivo de modelo: `Modulo_Odoo/models/categoria.py`.
* Archivo de datos semilla: `Modulo_Odoo/data/categoria_data.xml`.
* Archivo de vistas: `Modulo_Odoo/views/categoria_views.xml`.
* Reglas de acceso en `Modulo_Odoo/security/ir.model.access.csv`.

## 10. Definition of Done (DoD)
* [ ] Modelo `panaderia.categoria` implementado y cargado en `__init__.py`.
* [ ] Archivo `categoria_data.xml` declarado en `__manifest__.py` con las 4 categorías estándar.
* [ ] Vistas de lista y formulario operativas con el conteo de productos calculado.
* [ ] Procedimiento de prueba `docs/test-procedures/test-procedure-1.1.2.md` creado y validado.
* [ ] Pruebas unitarias de integridad y dependencias superadas con éxito.
