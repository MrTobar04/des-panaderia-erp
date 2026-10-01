# Quickstart: Categorías de Productos de Panadería

**Feature**: `SPEC-1.1.2: Categorías de Productos de Panadería`  
**Target Environment**: Odoo 16.0 / 17.0 / 18.0 Community with Docker Compose  

---

## 1. Verificación Inicial

### Paso 1: Comprobar Datos Semilla Cargados
Navega en Odoo a:
**Panadería** $\to$ **Inventario** $\to$ **Categorías**

Verifica que las 4 categorías base se encuentren presentes:
1. **Pan** (`PAN`)
2. **Pastel** (`PAS`)
3. **Galleta** (`GAL`)
4. **Bebida** (`BEB`)

---

## 2. Flujo Operativo: Registro de Categoría Personalizada

### Paso 1: Crear Categoría
1. En la vista de lista de **Categorías de Panadería**, haz clic en el botón **Nuevo** / **Crear**.
2. Ingresa los datos:
   - **Nombre de la Categoría**: `Postres Especiales`
   - **Código Corto**: `POS`
   - **Secuencia**: `50`
   - **Descripción**: `Postres de temporada, gelatinas y flanes artesanales.`
3. Haz clic en **Guardar**.

### Paso 2: Asociar Productos y Comprobar Conteo Automático
1. Navega a **Panadería** $\to$ **Inventario** $\to$ **Productos**.
2. Crea un nuevo producto:
   - **Nombre**: `Flan Napolitano Individual`
   - **Código**: `POS-001`
   - **Categoría**: `Postres Especiales`
   - **Costo**: `0.75`
   - **Precio Venta**: `2.00`
3. Guarda el producto.
4. Regresa a la categoría `Postres Especiales`:
   - Observa que el **Smart Button** de "Productos" muestra `1`.
   - La pestaña **Productos Asociados** lista el producto `Flan Napolitano Individual`.

---

## 3. Validación de Errores de Negocio

### Intento de Duplicidad de Nombre o Código
1. Intenta crear una categoría con nombre `pan` (en minúsculas o con espacios).
2. El sistema bloqueará el guardado con un mensaje de `ValidationError` indicando que ya existe una categoría con ese nombre.
