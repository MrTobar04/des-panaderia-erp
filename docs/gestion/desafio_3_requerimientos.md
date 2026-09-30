# Desafío 3: Sistema para Panadería "Delicias Dulces"
**Desarrollo de Software Empresarial** | **Unidad III: Prototipado de producto**

---

### Instrucciones
* **Fecha de Entrega:** Semana 15
* **Modalidad:** Defensa Presencial
* **Duración de la Defensa:** 10-12 minutos por equipo

---

### Objetivo
Desarrollar un sistema mínimo viable en Odoo para la panadería "Delicias Dulces" que cubra los procesos empresariales esenciales.

La panadería necesita urgentemente un sistema básico para controlar inventario, ventas y clientes. El tiempo es limitado, por lo que se priorizarán funcionalidades core.

---

### Módulos Mínimos Viables

#### 1. Gestión de Inventario Básico
* Catálogo de productos (nombre, categoría, precio, costo)
* Control de stock actual
* Alerta básica de stock mínimo
* Categorías: Pan, Pastel, Galleta, Bebida

#### 2. Proceso de Ventas Esencial
* Registro de ventas con líneas de productos
* Cálculo automático de totales
* Actualización de stock al confirmar venta
* Estados: Borrador $\to$ Confirmada

#### 3. Registro de Clientes
* Extender modelo estándar de partners
* Campos adicionales: fecha registro, total compras
* Filtro para clientes de panadería

#### 4. Facturación Simple
* Generar factura desde venta
* Número de factura automático
* Estados: Pendiente $\to$ Pagada

#### 5. Reportes Básicos
* Ventas del día
* Productos más vendidos
* Stock bajo (alerta)

---

### Estructura Mínima de Entrega

```text
Proyecto Panaderia_5Dias_GrupoX/
├── Documentacion_Express.pdf (2-3 páginas)
├── Modulo Odoo/
│   ├── __init__.py
│   ├── __manifest__.py
│   ├── models/ (producto, venta, cliente, factura)
│   ├── views/ (vistas básicas tree/form)
│   └── security/ (permisos básicos)
└── Instrucciones_Instalacion.txt
```

---

### Cronograma como Sugerencia

| Día | Enfoque Principal | Entregable Diario |
| :--- | :--- | :--- |
| **Día 1** | Inventario + Configuración | CRUD productos funcionando |
| **Día 2** | Módulo Ventas | Flujo venta básico operativo |
| **Día 3** | Clientes + Facturación | Clientes extendidos + facturas |
| **Día 4** | Reportes + Dashboard | 3 reportes básicos |
| **Día 5** | Integración + Demo | Sistema integrado + presentación |

---

### Criterios

**Mínimo Aceptable:**
* 3 módulos core funcionando.
* Demo que muestre flujo principal.
* Código que compile sin errores críticos.
* Poder explicar lo desarrollado.

*¡Éxitos!*

---

### Rúbrica de Evaluación

| Criterio | Destacado (4.5 - 5.0) | Competente (4.0 - 4.4) | Básico (3.0 - 3.9) | Insuficiente (< 3.0) |
| :--- | :--- | :--- | :--- | :--- |
| **Funcionalidad Core** | 4-5 módulos funcionando perfectamente + 1 extra | 3-4 módulos operativos, errores menores | 2-3 módulos funcionando con ayuda | Menos de 2 módulos operativos |
| **Calidad Técnica** | Código limpio, lógica clara, buen uso de Odoo | Código funcional, alguna deuda técnica | Código funciona pero desorganizado | Código con errores críticos |
| **Usabilidad** | Flujo intuitivo, navegación clara, fácil de usar | Funcional pero requiere mínima explicación | Confuso, necesita guía constante | Inusable sin ayuda experta |
| **Demo y Presentación** | Demo fluida, archivos y pdf, explica decisiones, maneja bien el tiempo | Demo funciona, explica lo básico | Demo con problemas, explicación superficial | Demo no funcional o sin preparación |
| **Integración** | Módulos perfectamente integrados, flujo completo | Módulos conectados, flujo mayormente funcional | Módulos aislados, integración básica | Módulos desconectados |