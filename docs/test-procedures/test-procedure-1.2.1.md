# Test Procedure: SPEC-1.2.1 — Control y Alerta de Stock Mínimo

**Spec Reference:** [`SPEC-1.2.1`](../../specs/1-inventory/1.2-stock-control/1.2.1-stock-tracking/spec.md)  
**Module:** Módulo 1 — Inventario  
**Spec Status:** Implemented (100%)  
**Generated On:** 2026-09-30  
**Evaluated by:** ___________________________  
**Execution Date:** ___________________________  
**Overall Result:** ☐ APPROVED  ☐ REJECTED  ☐ BLOCKED  

---

## Environment Prerequisites

> Complete before executing any test step.

1. **Instancia Odoo Operativa:** Servidor Odoo en ejecución con el módulo `Modulo_Odoo` cargado e instalado.
2. **Usuario con Rol Operador:** Usuario perteneciente al grupo `Operador de Panadería` (`group_panaderia_user`).
3. **Usuario con Rol Administrador / Supervisor:** Usuario perteneciente al grupo `Administrador de Panadería` (`group_panaderia_manager`).
4. **Datos de Prueba Iniciales:** Al menos una categoría de producto registrada (e.g. "Panes Tradicionales").

---

## Test Flow 1: Disparo de Alerta Visual por Stock Bajo

> Maps to: **AC-1 (Scenario 1)** of SPEC-1.2.1.

1. **Navegación al Catálogo:** Ir a **Panadería** → **Inventario** → **Productos**. Hacer clic en **Nuevo** para crear un producto de prueba.
2. **Configuración de Producto:** Completar el formulario con:
   - Nombre: `Baguette Tradicional`
   - Código / SKU: `BAG-TEST-01`
   - Categoría: `Panes Tradicionales`
   - Costo: `$0.40`
   - Precio Venta: `$1.20`
   - Stock Mínimo: `10.0`
   - Stock Disponible: `15.0`  
   Hacer clic en **Guardar**. Verificar que el badge `Estado Stock` se muestra en color verde con el texto `Normal`.
3. **Registro de Salida por Venta / Consumo:** Hacer clic en el botón superior **Ajustar Stock**. En la ventana emergente seleccionar:
   - Tipo de Ajuste: `Merma / Desperdicio` (o salida)
   - Cantidad: `7.0`
   - Motivo: `Prueba de consumo de stock`  
   Hacer clic en **Guardar**.
4. **Verificación de Alerta de Stock Bajo:** Volver al detalle del producto o la vista Tree. Confirmar que el stock disponible pasa a `8.0`, el badge `Estado Stock` cambia a color amarillo con la etiqueta `Bajo Stock` y el indicador `alerta_stock_bajo` se activa.

#### Edge Cases / Error Paths:

1. **Intento de Stock Mínimo Negativo:** En el formulario de producto, ingresar un `Stock Mínimo` de `-5.0` y hacer clic en **Guardar**. Verificar que el sistema bloquea el guardado y despliega la notificación de error: `"El stock mínimo no puede ser un valor negativo."`

**Result:** ☐ PASSED  ☐ FAILED  ☐ BLOCKED  
**Notes:** _____________________________

---

## Test Flow 2: Detección y Filtrado de Producto Agotado

> Maps to: **AC-2 (Scenario 2)** of SPEC-1.2.1.

1. **Navegación al Producto:** Abrir el producto `Pastel de Fresa` o crear uno nuevo con Stock Disponible = `2.0` y Stock Mínimo = `5.0`.
2. **Reducción de Existencias a Cero:** Hacer clic en **Ajustar Stock** y registrar un ajuste de tipo `Ajuste de Conteo` con Cantidad = `0.0` y Motivo = `Venta total de existencia`. Guardar la operación.
3. **Verificación Visual de Estado Agotado:** Confirmar que en el formulario y en la vista lista (Tree), la fila del producto aparece destacada con fondo / texto en rojo (`decoration-danger`) y el badge `Estado Stock` marca `Agotado`.
4. **Verificación de Filtro de Búsqueda:** En la barra de búsqueda de **Productos**, hacer clic en el filtro rápido **Agotados**. Confirmar que la lista se filtra mostrando únicamente los productos cuyo estado es `Agotado`.

#### Edge Cases / Error Paths:

1. **Intento de Salida Superior al Stock Disponible:** Abrir un producto con stock de `5.0` unidades. Intentar registrar una salida por `10.0` unidades. Verificar que la acción es rechazada con el mensaje: `"No hay suficiente stock disponible para realizar la salida."`

**Result:** ☐ PASSED  ☐ FAILED  ☐ BLOCKED  
**Notes:** _____________________________

---

## Test Flow 3: Registro de Entrada de Producción Diaria y Auditoría de Ajustes

> Maps to: **AC-3 (Scenario 3)** of SPEC-1.2.1.

1. **Navegación a Ajustes de Stock:** Ir al menú **Panadería** → **Inventario** → **Ajustes de Stock** y hacer clic en **Nuevo**.
2. **Registro de Ingreso de Cocina:** Seleccionar:
   - Producto: `Pan Francés`
   - Tipo de Ajuste: `Entrada de Producción`
   - Cantidad: `50.0`
   - Motivo: `Horneado matutino Lote #1`  
   Hacer clic en **Guardar**.
3. **Verificación en Ficha de Producto:** Navegar a la vista de `Pan Francés` y comprobar que la cantidad disponible se incrementó automáticamente en `+50.0` unidades.
4. **Verificación de Auditoría:** En la vista Tree de **Ajustes de Stock**, verificar que la entrada de inventario indica el nombre del usuario `Responsable`, la `Fecha` exacta de creación y el badge de tipo de ajuste en color verde (`Entrada de Producción`).

#### Edge Cases / Error Paths:

1. **Restricción de Permisos para Operadores:** Iniciar sesión con un usuario con rol `Operador de Panadería`. Intentar crear un registro de ajuste con tipo `Merma / Desperdicio` o `Ajuste de Conteo`. Verificar que al guardar, el sistema emite el mensaje: `"Solo los administradores o supervisores de panadería están autorizados para registrar mermas o ajustes directos de conteo."`

**Result:** ☐ PASSED  ☐ FAILED  ☐ BLOCKED  
**Notes:** _____________________________

---

## Definition of Done (DoD) Verification

| # | DoD Item | How to verify it (without code) | ☐ Met |
| :--- | :--- | :--- | :--- |
| 1 | Campos de stock y cálculo reactivo `_compute_estado_stock` operativos | Abrir la vista lista/formulario de productos y comprobar actualización automática de los badges de stock al cambiar cantidades. | ☐ |
| 2 | Filtros de Stock Bajo y Agotado funcionando en la vista de búsqueda | En la barra de búsqueda de Productos, aplicar los filtros "Stock Bajo" y "Agotados" y confirmar la filtración correcta. | ☐ |
| 3 | Decoradores visuales de color verificados en la vista Tree | Observar la vista lista de productos: filas sin alertas (verde/normal), stock bajo (amarillo/warning) y agotados (rojo/danger). | ☐ |
| 4 | Formulario de ajustes de inventario probado con entradas y salidas | Crear un ajuste desde el menú "Ajustes de Stock" y desde el botón "Ajustar Stock" del producto, verificando el reflejo en la cantidad disponible. | ☐ |
| 5 | Procedimiento de prueba `docs/test-procedures/test-procedure-1.2.1.md` completado y validado | Documento generado en `docs/test-procedures/test-procedure-1.2.1.md` y verificado paso a paso. | ☐ |

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
> Ninguno. Todos los escenarios y validaciones de seguridad funcionan conforme a las especificaciones.
