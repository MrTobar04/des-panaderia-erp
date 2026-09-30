# Requisitos de Calidad: SPEC-1.1.1 Gestión de Catálogo de Productos

**Purpose**: Validación de completitud, claridad, consistencia y calidad de los requisitos especificados para el catálogo de productos de panadería previo a la implementación y auditoría de release.
**Created**: 2026-09-29
**Feature**: [spec.md](../spec.md)

**Note**: Este checklist personalizado es un artefacto de revisión de calidad de requisitos generado por el comando `/speckit-checklist`.
**Review Ownership**: Este checklist es un artefacto propiedad del revisor para auditar la calidad de la redacción y cobertura de los requisitos. Marque un ítem con `[x]` únicamente cuando el revisor determine que el criterio de calidad del requisito ha sido plenamente satisfecho en la especificación.
**Marker Semantics**: `[x]` significa que el requisito está claramente definido, no presenta ambigüedades y es verificable. NO indica que la implementación de código esté completada.

## 1. Requisitos de Modelo de Datos y Validación de Negocio

- [ ] CHK001 ¿Están definidos de manera explícita y exhaustiva todos los tipos de datos, valores por defecto y requerimientos de nulidad para cada campo del modelo `panaderia.producto`? [Completeness, Spec §2.1, Spec §4]
- [ ] CHK002 ¿Está especificado el comportamiento exacto de validación cuando el precio de venta es menor o igual a cero (`precio_venta <= 0.0`), incluyendo el mensaje de error para el usuario? [Clarity, Spec §4, Spec §5 Escenario 2]
- [ ] CHK003 ¿Está delimitada la regla de negocio para el costo de producción (`costo >= 0.0`), definiendo si un costo de `$0.00` es permitido para productos promocionales o insumos sin costo directo? [Clarity, Spec §4]
- [ ] CHK004 ¿Se define el comportamiento del sistema y la respuesta al usuario cuando se produce una violación de la restricción de unicidad de nombre (`_sql_constraints`)? [Clarity, Spec §4, Spec §5 Escenario 3]
- [ ] CHK005 ¿Está especificado si el código SKU (`codigo`) admite duplicados, si es obligatorio u opcional, y cuál es el formato o longitud permitida? [Ambiguity, Spec §4, Gap]
- [ ] CHK006 ¿Está definido el comportamiento de integridad referencial si se intenta eliminar una categoría (`panaderia.categoria`) que tiene productos asociados (`ondelete='restrict'` vs `'cascade'`)? [Completeness, Dependency, Gap]

## 2. Requisitos de Interfaz de Usuario y Experiencia (UI/UX)

- [ ] CHK007 ¿Están especificadas con precisión todas las columnas visibles, su orden y el criterio de ordenamiento por defecto en la vista de lista (`tree`)? [Completeness, Spec §4]
- [ ] CHK008 ¿Se definen los campos editables, pestañas y la jerarquía de visualización dentro de la vista formulario (`form`) para evitar ambigüedad en el diseño? [Clarity, Spec §4]
- [ ] CHK009 ¿Están documentados los filtros predeterminados y las opciones de agrupación (`group_by`) requeridas en la vista de búsqueda (`search`)? [Completeness, Spec §4]
- [ ] CHK010 ¿Se cuantifica o define formalmente el criterio de advertencia visual cuando el precio de venta es inferior al costo de producción (`precio_venta < costo`)? [Measurability, Spec §8, Gap]
- [ ] CHK011 ¿Se especifica la regla de localización que exige que todas las etiquetas de campos, menús, títulos de vista y mensajes de validación se encuentren en idioma español? [Consistency, Spec §3, Constitution §V]

## 3. Requisitos de Seguridad, Accesos y Gestión de Estados

- [ ] CHK012 ¿Están documentadas de forma explícita las matrices CRUD para los grupos `group_panaderia_user` y `group_panaderia_manager` en el archivo de permisos ACL? [Completeness, Spec §7, Plan §Technical Context]
- [ ] CHK013 ¿Está definido el mecanismo de borrado lógico (`active = False` / archivado) y su impacto en la visibilidad del catálogo en ventas e inventario en lugar del borrado físico (`unlink`)? [Clarity, Spec §8]
- [ ] CHK014 ¿Se especifica el comportamiento esperado al intentar realizar un borrado físico de un producto cuando existen registros históricos o líneas de venta vinculadas? [Coverage, Edge Case, Spec §8]
- [ ] CHK015 ¿Se especifica que la configuración de contraseñas de base de datos y llaves maestras no debe contener secretos hardcodeados y debe provenir del entorno (`.env`)? [Security, Constitution §VI, Plan §Technical Context]

## 4. Cobertura de Escenarios y Casos de Borde

- [ ] CHK016 ¿Están documentados los criterios de aceptación para escenarios de actualización/modificación de precios en productos preexistentes? [Coverage, Spec §5]
- [ ] CHK017 ¿Se define el comportamiento del sistema cuando un usuario busca productos en la lista y no existen coincidencias (estado vacío o zero-state)? [Edge Case, Gap]
- [ ] CHK018 ¿Se especifica el comportamiento ante entradas con múltiples espacios en blanco o caracteres especiales en el nombre del producto para efectos de unicidad? [Edge Case, Ambiguity, Gap]
- [ ] CHK019 ¿Están definidos los datos semilla mínimos requeridos para la inicialización y prueba inmediata del catálogo (e.g. 4 productos representativos)? [Completeness, Spec §6, Plan §Technical Context]

## 5. Consistencia Arquitectónica y Trazabilidad con la Constitución

- [ ] CHK020 ¿Se valida la adhesión estricta a la arquitectura modular de Odoo (separación MVC en `models/`, `views/`, `security/`, `data/`) sin mutar modelos estándar base? [Consistency, Constitution §I, Spec §3]
- [ ] CHK021 ¿Está alineada la estructura del modelo `panaderia.producto` para servir como entidad maestra compatible con la sincronización atómica con ventas e inventario? [Traceability, Constitution §II, Constitution §III]
- [ ] CHK022 ¿Se encuentra referenciado y requerido el procedimiento de prueba manual de interfaz en `docs/test-procedures/test-procedure-1.1.1.md` dentro de los criterios de aceptación y DoD? [Traceability, Constitution §IV, Spec §10]
- [ ] CHK023 ¿Están definidos los requerimientos de despliegue determinista mediante Docker Compose garantizando la persistencia de datos y montaje dinámico del addon? [Consistency, Constitution §VI, Plan §Technical Context]

## Notes

- Marque los ítems con `[x]` únicamente cuando la revisión confirme que el criterio de calidad del requisito está satisfecho en la documentación.
- Deje los ítems sin marcar (`[ ]`) mientras requieran clarificación, ajustes en la especificación o evaluación por parte del equipo revisor.
- `/speckit-implement` consulta el estado de este checklist como compuerta de calidad de requisitos y no debe modificar las casillas de verificación.
- El archivo `checklists/requirements.md` mantiene su propio ciclo de vida nativo para `/speckit-specify` y `/speckit-clarify`.
- Los ítems están numerados correlativamente (CHK001 a CHK023) para facilitar su trazabilidad y referencia en revisiones de código.
