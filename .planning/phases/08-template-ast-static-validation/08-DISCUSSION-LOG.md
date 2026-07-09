# Phase 8: Template AST & Static Validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-09
**Phase:** 08-template-ast-static-validation
**Areas discussed:** Severidad del bloqueo ante variables no declaradas, Rigurosidad del Analizador AST para variables locales de Loops, Tratamiento de variables globales del sistema

---

## Severidad del bloqueo ante variables no declaradas

| Option | Description | Selected |
|--------|-------------|----------|
| Opción A | Flexible en Borrador, Estricta en Activación: Permitir guardar borradores con `warnings`. Bloquear con error 400 al activar/publicar diseños. | ✓ |
| Opción B | Estricto Siempre: Bloquear con error 400 cualquier guardado de plantilla si contiene variables no declaradas. | |

**User's choice:** Opción A (Flexible en Borrador, Estricta en Activación)
**Notes:** Otorga una mejor experiencia de usuario al permitir guardar trabajo inconcluso y resolver advertencias antes de publicar.

---

## Rigurosidad del Analizador AST para variables locales de Loops

| Option | Description | Selected |
|--------|-------------|----------|
| Opción A | Análisis AST Completo: Visitor del AST que rastrea el ámbito de los loops para mapear aliases (ej: `item.nombre` a `cliente.contactos[].nombre`). | ✓ |
| Opción B | Validación Parcial: Mapeo difuso de hojas de variables sin rastreo de ámbito. | |

**User's choice:** Opción A (Análisis AST Completo y Preciso)
**Notes:** Garantiza la máxima fiabilidad en la validación estática de variables iterativas, previniendo errores en producción.

---

## Tratamiento de variables globales del sistema

| Option | Description | Selected |
|--------|-------------|----------|
| Opción A | Dinámica: Inspeccionar `env.globals` en runtime para ignorar de forma dinámica las variables globales y funciones configuradas. | ✓ |
| Opción B | Lista Blanca Estática: Usar un conjunto constante hardcodeado en el backend. | |

**User's choice:** Opción A (Dinámica)
**Notes:** Ideal para mantenibilidad; las nuevas globales inyectadas en Jinja se eximen automáticamente de validación sin cambiar el validador estático.

---

## the agent's Discretion

- Algoritmo exacto de resolución del AST para loops anidados y scopes.
- Formato estructurado del campo `warnings` devuelto en las respuestas JSON de guardado.

## Deferred Ideas

- Validación en tiempo real (asíncrona) desde el editor HTML en el navegador — diferido a la Fase 10.

---

*Phase: 08-template-ast-static-validation*
*Discussion log generated: 2026-07-09*
