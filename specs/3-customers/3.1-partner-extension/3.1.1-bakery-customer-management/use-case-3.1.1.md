# Test Procedure: SPEC-3.1.1 — Extensión y Registro de Clientes

**Spec Reference:** [`SPEC-3.1.1`](spec.md)  
**Module:** Module 3 — Customers & Partner Extension  
**Spec Status:** Built (100%)  
**Generated On:** 2026-09-30  
**Evaluated by:** Antigravity Automated QA Lead  
**Execution Date:** 2026-09-30  
**Overall Result:** ☑ APPROVED  ☐ REJECTED  ☐ BLOCKED  

---

## Environment Prerequisites

> Complete before executing any test step.

1. **Docker Services Running:** The containers `panaderia_odoo_web` and `panaderia_odoo_db` must be active (`docker compose up -d`).
2. **Database Initialized:** The `panaderia_db` database is loaded with base catalog products and categories.
3. **Module Upgraded:** The addon `Modulo_Odoo` contains all models and views (`Modulo_Odoo/models/cliente.py`, `Modulo_Odoo/views/cliente_views.xml`).
4. **Web Browser Session:** Authenticated as an administrative user or bakery cashier at `http://localhost:8069`.

---

## Test Flow 1: Registro de nuevo cliente de panadería con notas y fecha automática

> Maps to: **AC Scenario 1** of SPEC-3.1.1.

1. **[Navegación al menú de clientes]:** En la barra de navegación superior, hacer clic en la aplicación **Panadería** $\to$ en el menú superior o barra lateral seleccionar **Clientes** (o **Ventas** $\to$ **Clientes**). Se debe visualizar la vista de lista de clientes con el botón **Nuevo** disponible.
2. **[Creación de nuevo cliente]:** Hacer clic en **Nuevo** (o **Crear**), ingresar en el campo `Nombre`: `Carlos Mendoza`, en el campo `Teléfono`: `7123-4567`.
3. **[Verificación y captura en pestaña Datos de Panadería]:** En el formulario, hacer clic en la pestaña **Datos de Panadería**. Verificar visualmente que la casilla **Es Cliente de Panadería** esté marcada con un check azul y que el campo **Fecha de Registro en Panadería** muestre la fecha actual. En el campo **Notas y Preferencias de Consumo**, escribir: `Prefiere pan integral caliente por las tardes y repostería baja en azúcar.`
4. **[Guardado del registro]:** Hacer clic en el icono de la nube / botón **Guardar**. Se debe observar que la ficha queda guardada sin errores, el campo **Total en Compras ($)** se inicializa en `$0.00` y el Smart Button en la esquina superior derecha muestra `$0.00 Compras Panadería`.

#### Edge Cases / Error Paths:
1. **[Falta de fecha obligatoria]:** Si el usuario intenta borrar la fecha de registro en un cliente con el flag de panadería activo, el formulario muestra el campo resaltado en rojo impidiendo guardar el registro sin fecha.

**Result:** ☑ PASSED  ☐ FAILED  ☐ BLOCKED  
**Notes:** Registro validado con fecha automática y captura de preferencias.

---

## Test Flow 2: Actualización reactiva del total acumulado de compras

> Maps to: **AC Scenario 2** of SPEC-3.1.1.

1. **[Registro y confirmación de primera venta]:** Ir a **Panadería** $\to$ **Ventas** $\to$ **Órdenes de Venta**, hacer clic en **Nuevo**, seleccionar cliente `Carlos Mendoza`, agregar productos con subtotal de `$12.50` y hacer clic en **Confirmar Venta**. La orden pasa al estado verde `Confirmada`.
2. **[Registro y confirmación de segunda venta]:** Crear una segunda orden de venta para `Carlos Mendoza` con productos por un importe de `$7.50` y hacer clic en **Confirmar Venta**. La orden pasa al estado `Confirmada`.
3. **[Inspección del acumulado en la ficha del cliente]:** Regresar a **Panadería** $\to$ **Clientes** y abrir el registro de `Carlos Mendoza`. En la pestaña **Datos de Panadería** y en el Smart Button superior derecho, se debe visualizar inmediatamente el valor `$20.00` como Total en Compras acumulado.
4. **[Inspección de la sub-grilla histórica]:** En la parte inferior de la pestaña **Datos de Panadería**, verificar que la tabla **Historial de Ventas en Panadería** liste las 2 órdenes con sus respectivos folios (`VEN-XXXX`), fechas, importes y estado `Confirmada`.

#### Edge Cases / Error Paths:
1. **[Ventas en borrador no suman]:** Crear una tercera orden de venta para el cliente por `$50.00` pero dejarla en estado `Borrador`. Consultar la ficha del cliente; el total acumulado debe permanecer invariablemente en `$20.00`.

**Result:** ☑ PASSED  ☐ FAILED  ☐ BLOCKED  
**Notes:** Suma acumulada $12.50 + $7.50 = $20.00 confirmada con total exactitud.

---

## Test Flow 3: Filtrado estricto de contactos en la vista de panadería

> Maps to: **AC Scenario 3** of SPEC-3.1.1.

1. **[Consulta del listado de clientes]:** Ingresar al menú **Panadería** $\to$ **Clientes**.
2. **[Verificación de filtro activo]:** En la barra de búsqueda superior, observar la etiqueta de filtro azul `Clientes de Panadería` activada por defecto.
3. **[Comprobación de aislamiento de contactos]:** Verificar que en la lista aparezcan únicamente clientes de panadería (como `Cliente General / Mostrador`, `Carlos Mendoza` y `Ana López`), excluyendo a proveedores generales, contactos de empresas externas y usuarios del sistema sin el flag `es_cliente_panaderia`.

#### Edge Cases / Error Paths:
1. **[Eliminación manual del filtro]:** Si el operador hace clic en la (X) del filtro en la barra de búsqueda, puede explorar todos los contactos y volver a aplicarlo haciendo clic en **Filtros** $\to$ **Clientes de Panadería**.

**Result:** ☑ PASSED  ☐ FAILED  ☐ BLOCKED  
**Notes:** El aislamiento y domain predeterminado funcionan según especificación.

---

## Test Flow 4: Reversión de compras ante cancelación de orden

> Maps to: **DoD y Robustez de Datos** of SPEC-3.1.1.

1. **[Cancelación de una venta confirmada]:** Abrir la orden de venta de `$7.50` asociada a `Carlos Mendoza` y hacer clic en el botón de cabecera **Cancelar**, confirmando el modal.
2. **[Verificación del recálculo]:** Regresar a la ficha de `Carlos Mendoza`. Visualizar el campo **Total en Compras ($)**; este debe disminuir automáticamente de `$20.00` a `$12.50`.

**Result:** ☑ PASSED  ☐ FAILED  ☐ BLOCKED  
**Notes:** Reversión reactiva confirmada.

---

## Definition of Done (DoD) Verification

| # | DoD Item | How to verify it (without code) | ☑ Met |
| :--- | :--- | :--- | :--- |
| 1 | Modelo `res.partner` extendido con los campos de panadería | Abrir la vista formulario de cualquier cliente en Panadería $\to$ Clientes y verificar la presencia de la pestaña "Datos de Panadería" con fecha de registro, flag y notas. | ☑ |
| 2 | Vistas Formulario y Lista personalizadas con filtros de clientes de panadería | Consultar la vista lista de Clientes y verificar las columnas Nombre, Teléfono, Fecha de Alta, Órdenes y Total Compras ($) con filtro por defecto. | ☑ |
| 3 | Conexión y cálculo automático de `total_compras_panaderia` probado con ventas confirmadas | Confirmar dos ventas ($12.50 y $7.50) y verificar visualmente en la ficha del cliente que el total muestre $20.00. | ☑ |
| 4 | Procedimiento de prueba `docs/test-procedures/test-procedure-3.1.1.md` completado y verificado | Comprobar la existencia y aprobación del documento en `docs/test-procedures/test-procedure-3.1.1.md`. | ☑ |

---

## Session Final Results

| Field | Value |
| :--- | :--- |
| Total flows executed | 4 |
| Flows passed | 4 |
| Flows failed | 0 |
| Flows blocked | 0 |
| AC coverage | 3 / 3 (100%) |
| DoD items verified | 4 / 4 (100%) |

**Verdict:** ☑ APPROVED — Todos los criterios de aceptación y requerimientos del DoD están cumplidos con cero defectos.
