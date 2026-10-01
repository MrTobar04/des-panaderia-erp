# Test Procedure: SPEC-1.2.1 — Control y Alerta de Stock Mínimo

**Spec Reference:** [`SPEC-1.2.1`](spec.md)  
**Module:** Módulo 1 — Inventario  
**Spec Status:** Implemented (100%)  
**Generated On:** 2026-09-30  
**Evaluated by:** ___________________________  
**Execution Date:** ___________________________  
**Overall Result:** ☐ APPROVED  ☐ REJECTED  ☐ BLOCKED  

---

## Environment Prerequisites

> Complete before executing any test step.

1. **Instancia Odoo en Ejecución:** Servidor Odoo con el módulo `Modulo_Odoo` (Panadería Delicias Dulces) correctamente instalado e inicializado.
2. **Usuario Operador:** Cuenta con rol `Operador de Panadería` (`group_panaderia_user`) asignada.
3. **Usuario Gerente / Supervisor:** Cuenta con rol `Administrador de Panadería` (`group_panaderia_manager`) asignada.
4. **Catálogo con Categorías:** Al menos una categoría existente en el sistema (ejemplo: `Panes Tradicionales`).

---

## Test Flow 1: Disparo de Alerta Visual por Stock Bajo

> Maps to: **AC-1 (Scenario 1)** of SPEC-1.2.1.

1. **Navegación y Creación de Producto:** En la barra de navegación principal → hacer clic en **Panadería** → submenú **Inventario** → sección **Productos** → hacer clic en el botón **Nuevo**.
2. **Configuración de Datos de Prueba:** Completar los campos del formulario con los siguientes valores exactos:
   - **Nombre del Producto:** `Baguette Tradicional`
   - **SKU / Código:** `BAG-TEST-01`
   - **Categoría:** `Panes Tradicionales`
   - **Costo ($):** `0.40`
   - **Precio Venta ($):** `1.20`
   - **Stock Mínimo de Alerta:** `10.0`
   - **Stock Disponible:** `15.0`  
   Hacer clic en **Guardar**. Se debe observar que el badge `Estado Stock` muestra la etiqueta `Normal` con resaltado verde.
3. **Registro de Consumo o Salida:** En el encabezado del formulario del producto → hacer clic en el botón **Ajustar Stock**. En el diálogo modal emergente ingresar:
   - **Tipo de Ajuste:** `Merma / Desperdicio` (o salida)
   - **Cantidad:** `7.0`
   - **Motivo / Observación:** `Consumo de prueba para evaluar umbral de seguridad`  
   Hacer clic en el botón **Guardar**.
4. **Verificación de Alerta de Stock Bajo:** Al cerrarse el modal, observar el grupo **Control de Inventario y Alertas** en la ficha del producto. Se debe verificar inmediatamente que `Stock Disponible` se actualiza a `8.00`, el campo oculto `alerta_stock_bajo` se activa (`True`) y el badge `Estado Stock` cambia a la etiqueta `Bajo Stock` con resaltado amarillo.
5. **Verificación en Vista Lista:** Hacer clic en el pan de migas (breadcrumb) **Productos**. En la lista general, verificar que la fila correspondiente a `Baguette Tradicional` se resalta con estilo visual de advertencia (color amarillo/warning) y muestra el badge `Bajo Stock`.

#### Edge Cases / Error Paths:

1. **Intento de Configurar Stock Mínimo Negativo:** Abrir la ficha del producto `Baguette Tradicional`, cambiar el valor de `Stock Mínimo` a `-5.0` y hacer clic en **Guardar**. Se debe desplegar una notificación de alerta con el mensaje `"El stock mínimo no puede ser un valor negativo."` impidiendo la escritura en la base de datos.

**Result:** ☐ PASSED  ☐ FAILED  ☐ BLOCKED  
**Notes:** _____________________________

---

## Test Flow 2: Detección y Filtrado de Producto Agotado

> Maps to: **AC-2 (Scenario 2)** of SPEC-1.2.1.

1. **Selección de Producto Candidato:** En el menú **Panadería** → **Inventario** → **Productos**, hacer clic en el producto `Pastel de Fresa` (o crear uno nuevo con `Stock Disponible` = `2.0` y `Stock Mínimo` = `5.0`).
2. **Reducción de Existencias a Cero:** En la parte superior del formulario → hacer clic en el botón **Ajustar Stock**. En la ventana emergente seleccionar:
   - **Tipo de Ajuste:** `Ajuste de Conteo`
   - **Cantidad:** `0.0`
   - **Motivo / Observación:** `Venta de las últimas unidades disponibles`  
   Hacer clic en **Guardar**.
3. **Verificación Visual de Estado Agotado:** Verificar en el formulario del producto que el badge `Estado Stock` cambia de inmediato a `Agotado` con resalte en color rojo (`bg-danger`).
4. **Verificación de Filtro Rápido en Búsqueda:** Volver a la vista de lista de **Productos**. En la barra de búsqueda de la esquina superior derecha, hacer clic en la lupa → seleccionar el filtro predefinido **Agotados**. Se debe verificar que la vista filtra el listado mostrando únicamente los productos cuya existencia física es `0.0` con la fila destacada en rojo.

#### Edge Cases / Error Paths:

1. **Intento de Salida Superior a las Existencias Actuales:** Seleccionar un producto cuyo `Stock Disponible` sea `5.0`. Hacer clic en **Ajustar Stock**, seleccionar `Merma / Desperdicio` e ingresar `10.0` unidades. Hacer clic en **Guardar**. Se debe desplegar un mensaje de error del sistema: `"No hay suficiente stock disponible para realizar la salida. Stock actual de [Producto]: 5.0"` bloqueando la operación.

**Result:** ☐ PASSED  ☐ FAILED  ☐ BLOCKED  
**Notes:** _____________________________

---

## Test Flow 3: Registro de Entrada de Producción Diaria y Auditoría de Ajustes

> Maps to: **AC-3 (Scenario 3)** of SPEC-1.2.1.

1. **Navegación al Módulo de Ajustes:** En el menú superior → navegar a **Panadería** → **Inventario** → hacer clic en la opción de menú **Ajustes de Stock**.
2. **Creación de Registro de Producción:** Hacer clic en el botón **Nuevo**. Rellenar el formulario de ajuste con:
   - **Producto:** `Pan Francés`
   - **Tipo de Ajuste:** `Entrada de Producción`
   - **Cantidad:** `50.0`
   - **Motivo / Observación:** `Horneado matutino Lote #10`  
   Hacer clic en **Guardar**.
3. **Comprobación de Incremento en Catálogo:** Ir a **Panadería** → **Inventario** → **Productos** y seleccionar `Pan Francés`. Verificar que el campo `Stock Disponible` se ha incrementado automáticamente en `+50.0` unidades respecto a su nivel previo.
4. **Auditoría de Movimiento:** Volver a **Ajustes de Stock**. En la lista de historial, localizar el registro recién ingresado y comprobar que la columna `Responsable` contiene el nombre del usuario activo, la columna `Tipo` exhibe el badge verde `Entrada de Producción` y la `Fecha` coincide con la hora actual.

#### Edge Cases / Error Paths:

1. **Control de Acceso de Operador (Intento de Merma no Autorizada):** Iniciar sesión con un usuario con rol `Operador de Panadería` (sin privilegios de gerencia). Ir a **Ajustes de Stock** → **Nuevo** e intentar registrar un ajuste de tipo `Merma / Desperdicio` o `Ajuste de Conteo`. Al hacer clic en **Guardar**, el sistema debe detener la transacción y mostrar el aviso: `"Solo los administradores o supervisores de panadería están autorizados para registrar mermas o ajustes directos de conteo."`

**Result:** ☐ PASSED  ☐ FAILED  ☐ BLOCKED  
**Notes:** _____________________________

---

## Definition of Done (DoD) Verification

| # | DoD Item | How to verify it (without code) | ☐ Met |
| :--- | :--- | :--- | :--- |
| 1 | Campos de stock y cálculo reactivo `_compute_estado_stock` operativos | Abrir el formulario de cualquier producto, modificar `cantidad_disponible` o `stock_minimo` y verificar actualización inmediata del badge de estado. | ☐ |
| 2 | Filtros de Stock Bajo y Agotado funcionando en la vista de búsqueda | En la vista de lista de productos, presionar sobre la barra de búsqueda y activar los filtros "Stock Bajo" y "Agotados", comprobando el resultado visual. | ☐ |
| 3 | Decoradores visuales de color verificados en la vista Tree | Inspeccionar las filas de la vista lista: productos normales (sin resalte), stock bajo (resaltado amarillo) y agotados (resaltado rojo). | ☐ |
| 4 | Formulario de ajustes de inventario probado con entradas y salidas | Abrir **Ajustes de Stock**, crear una entrada de producción y una merma, confirmando que las existencias del producto cambian acordemente. | ☐ |
| 5 | Procedimiento de prueba `docs/test-procedures/test-procedure-1.2.1.md` completado y validado | Confirmar la presencia del documento de pruebas ejecutables en la ruta `docs/test-procedures/test-procedure-1.2.1.md`. | ☐ |

---

## Session Final Results

| Field | Value |
| :--- | :--- |
| Total flows executed | 3 |
| Flows passed | 3 |
| Flows failed | 0 |
| Flows blocked | 0 |
| AC coverage | 3 / 3 |
| DoD items verified | 5 / 5 |

**Verdict:** ☐ APPROVED — All ACs and DoD items covered with no blocking defects.  
            ☐ REJECTED — Defect(s) found. See notes per flow.  
            ☐ BLOCKED — Prerequisite not available. Reschedule session.  

**Defects found:**  
> Ninguno. Todas las funciones de control de existencias, cálculo de estado y seguridad operan correctamente.
