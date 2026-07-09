# Phase 7: Backend Core (Nested Data & Case-Insensitive Matching) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-09
**Phase:** 07-backend-core-nested-data-case-insensitive-matching
**Areas discussed:** Representación en BD de campos complejos, Preservación de casing en base de datos, Validación de listas vacías/ausentes, Formato de error de colisiones de casing

---

## Representación en BD de campos complejos

| Option | Description | Selected |
|--------|-------------|----------|
| Opción A | Solo registrar hojas terminales (e.g. `cliente.direccion.calle`). Estructura anidada inferida en runtime. | ✓ |
| Opción B | Registrar todos los niveles de jerarquía recursivamente (e.g., `cliente`, `cliente.direccion` como filas separadas). | |

**User's choice:** Opción A (Solo Hojas)
**Notes:** Decidido usar notación de corchetes en los nombres de campo para listas de objetos, manteniendo el esquema de BD plano.

---

## Preservación de casing en base de datos

| Option | Description | Selected |
|--------|-------------|----------|
| Opción A | Preservar casing original enviado por el integrador en `document_issuances.input_data`, resolviendo case-insensitivity dinámicamente en memoria. | ✓ |
| Opción B | Normalizar todas las llaves a minúsculas antes de persistir en la base de datos. | |

**User's choice:** Opción A (Preservar Original)
**Notes:** Mantiene el valor de auditoría del payload de datos tal como llegó del sistema externo.

---

## Validación de listas vacías/ausentes

| Option | Description | Selected |
|--------|-------------|----------|
| Opción A | Permisiva: Listas vacías `[]` o ausentes no generan error 400. Jinja2 itera 0 veces o renderiza vacío. | ✓ |
| Opción B | Estricta: Listas vacías o ausentes disparan error 400 Bad Request asumiendo que falta información. | |

**User's choice:** Opción A (Permisiva)
**Notes:** Otorga flexibilidad ante casos de negocio donde un cliente no posea elementos en la lista.

---

## Formato de error de colisiones de casing

| Option | Description | Selected |
|--------|-------------|----------|
| Opción A | Estructurado: JSON con formato estándar de FastAPI/Pydantic indicando `loc`, `type` (`casing_collision`) y `msg` con llaves conflictivas. | ✓ |
| Opción B | Texto Plano: Mensaje de error plano en un string simple bajo la llave `detail`. | |

**User's choice:** Opción A (Estructurado)
**Notes:** Ideal para mapeos en frontend y robustez en la integración API.

---

## the agent's Discretion

- Diseño e implementación exacta de las clases de mapeo dinámico de casing (`RecursiveCaseInsensitiveDict` / custom proxies).
- Estructura de pruebas de integración para escenarios con colisiones y listas vacías.

## Deferred Ideas

- Representación visual e interfaz de campos complejos en el menú de Document Types y el Diseñador — diferido a la Fase 10.

---

*Phase: 07-backend-core-nested-data-case-insensitive-matching*
*Discussion log generated: 2026-07-09*
