# SPEC-1.1.1: Gestión de Catálogo de Productos

## 1. Objective
Implementar el módulo de catálogo de productos en Odoo para la panadería "Delicias Dulces", permitiendo a los operadores registrar, consultar, actualizar y descontinuar productos de panadería con su información comercial básica (nombre, categoría, precio de venta, costo de producción y código de referencia), garantizando consistencia en los precios y soporte para los flujos de inventario y ventas.

## 2. Scope
### 2.1. Included
* Modelo Odoo `panaderia.producto` para gestión integral de ítems.
* Campos esenciales: Nombre del producto, Categoría (`Many2one` a `panaderia.categoria`), Precio de Venta (`Float`), Costo de Producción (`Float`), Código de Referencia / SKU (`Char`), y Estado Activo (`Boolean`).
* Vistas de usuario en Odoo: Vista Árbol/Lista (`tree`), Vista Formulario (`form`) y Vista de Búsqueda/Filtro (`search`).
* Reglas de validación a nivel de modelo: Costo $\ge 0$, Precio de Venta $> 0$, y unicidad de nombre de producto.
* Permisos de acceso básicos (`security/ir.model.access.csv`) para operadores y administradores de panadería.

### 2.2. Not Included (Out of Scope)
* Gestión de variantes complejas de producto (tallas, sabores dinámicos con matriz de atributos).
* Impuestos avanzados desglosados multicurrency o regímenes fiscales especiales.
* Trazabilidad de lotes o fechas de caducidad por unidad individual (diferido a fases futuras).
* Catálogo web / e-commerce público.

## 3. Context and Restrictions
* **Context:** Este módulo constituye la entidad base de datos para todo el ERP. Las órdenes de venta (`panaderia.venta.linea`) y el control de inventario (`panaderia.producto`) dependen directamente de la existencia y validez de estos registros.
* **Restrictions:**
  * Debe implementarse como un modelo nativo o extensión limpia en Odoo 16/17/18.
  * No debe modificar modelos estándar de Odoo que no pertenezcan al alcance del Desafío 3.
  * Todo texto y etiquetas de la interfaz de usuario deben estar en español.

## 4. Design (Implementation Details)
* **Architecture:** Modelo MVC Odoo con lógica encapsulada en Python (`models/producto.py`), vistas declarativas en XML (`views/producto_views.xml`), y control de acceso (`security/ir.model.access.csv`).
* **Data Model:**
  ```python
  class PanaderiaProducto(models.Model):
      _name = 'panaderia.producto'
      _description = 'Producto de Panadería'

      name = fields.Char(string='Nombre del Producto', required=True, index=True)
      codigo = fields.Char(string='Código / SKU', copy=False)
      categoria_id = fields.Many2one('panaderia.categoria', string='Categoría', required=True)
      precio_venta = fields.Float(string='Precio de Venta ($)', required=True, default=0.0)
      costo = fields.Float(string='Costo de Producción ($)', required=True, default=0.0)
      active = fields.Boolean(string='Activo', default=True)
      descripcion = fields.Text(string='Descripción')
  ```
* **API Contracts / ORM Methods:**
  * `@api.constrains('precio_venta', 'costo')`: Valida que `precio_venta > 0` y `costo >= 0`. En caso contrario, lanza `ValidationError`.
  * `_sql_constraints`: Unicidad en el campo `name` para evitar productos duplicados con el mismo nombre.
* **UI/UX:**
  * Vista Formulario con pestañas organizadas, campos numéricos con formato monetario `$`, y selector desplegable de categoría.
  * Vista Lista con columnas claras (Nombre, Código, Categoría, Costo, Precio de Venta, Estado) y badges visuales.
  * Filtros de búsqueda agrupados por Categoría y estado Activo.

## 5. Acceptance Criteria
* **Scenario 1: Creación exitosa de un producto de panadería**
  * **Given** que el usuario tiene permisos de operador de panadería y abre el formulario de nuevo producto.
  * **When** ingresa "Pan Francés Clásico", selecciona la categoría "Pan", define costo `$0.05` y precio de venta `$0.10`.
  * **Then** el sistema guarda el producto exitosamente, genera el registro y lo muestra en la lista general de productos.

* **Scenario 2: Validación de precio de venta inválido**
  * **Given** que el operador está creando o editando un producto.
  * **When** ingresa un precio de venta igual o menor a cero (`$0.00` o `-$1.00`).
  * **Then** el sistema bloquea el guardado y muestra un mensaje de error claro: "El precio de venta debe ser mayor a 0".

* **Scenario 3: Restricción de duplicidad de nombres**
  * **Given** que existe un producto registrado con nombre "Pastel de Chocolate".
  * **When** el usuario intenta crear otro producto con el mismo nombre "Pastel de Chocolate".
  * **Then** el sistema levanta una advertencia impidiendo el registro redundante.

## 6. Verification Plan
* **Manual UI Testing:**
  1. Ingresar a la aplicación Odoo $\to$ Panadería $\to$ Productos.
  2. Crear los 4 productos semilla requeridos (e.g. Baguette, Selva Negra, Galleta de Avena, Café Americano).
  3. Probar la edición de precios y verificar el refresco inmediato en la vista de lista.
  4. Intentar guardar valores negativos para verificar el diálogo de error de validación.
* **Automated ORM Testing:**
  * Ejecutar suite de pruebas unitarias en Python (`tests/test_producto.py`) verificando restricciones `precio_venta` y `_sql_constraints`.

## 7. Security and Privacy
* **Access Control:**
  * Grupo `group_panaderia_user`: Permisos de lectura y escritura en catálogo de productos.
  * Grupo `group_panaderia_manager`: Permisos completos (CRUD) incluyendo desvinculación y configuración.
* **PII & Privacy:** No contiene datos sensibles de usuarios ni clientes; únicamente información operativa de catálogo.

## 8. Risks and Mitigation
* **Risk:** Inconsistencia de márgenes si el costo supera el precio de venta.
  * **Mitigation:** Agregar advertencia visual en formulario cuando `precio_venta < costo`.
* **Risk:** Eliminación accidental de productos vinculados a ventas pasadas.
  * **Mitigation:** Uso de borrado lógico (`active = False`) en lugar de `unlink()` físico cuando existan líneas de venta asociadas.

## 9. Deliverables & Config as Code
* Archivo de modelo: `Modulo_Odoo/models/producto.py`.
* Archivo de vistas: `Modulo_Odoo/views/producto_views.xml`.
* Archivo de seguridad: `Modulo_Odoo/security/ir.model.access.csv`.
* Menús y acciones en Odoo declarados en XML.

## 10. Definition of Done (DoD)
* [ ] Modelo `panaderia.producto` implementado con todos los campos especificados.
* [ ] Vistas Tree, Form y Search funcionales y visibles en el menú principal de Panadería.
* [ ] Validaciones de precio y costo probadas y operativas sin errores de servidor.
* [ ] Procedimiento de prueba `docs/test-procedures/test-procedure-1.1.1.md` documentado y verificado.
* [ ] Código validado con PEP 8 y cargado sin advertencias en los logs de Odoo.
