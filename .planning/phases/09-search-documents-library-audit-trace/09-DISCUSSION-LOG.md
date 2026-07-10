# Phase 9: Search Documents Library & Audit Trace - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-09
**Phase:** 09-search-documents-library-audit-trace
**Areas discussed:** Modelo de datos para Tracelogs, Seguridad y Estructura del Enlace de Compartición, Navegación de la Biblioteca de Documentos en la UI

---

## Modelo de datos para Tracelogs (Historial de Auditoría)

| Option | Description | Selected |
|--------|-------------|----------|
| Opción A | Tabla Dedicada `document_tracelogs`: Una nueva tabla en la base de datos vinculada a `document_issuances`. | ✓ |
| Opción B | Campo JSON en `document_issuances`: Columna `tracelogs: JSON` con arreglo de eventos. | |

**User's choice:** Opción A (Tabla Dedicada `document_tracelogs`)
**Notes:** Asegura que los registros de auditoría sigan las mejores prácticas de normalización, permitiendo consultas estructuradas por evento o marcas temporales.

---

## Seguridad y Estructura del Enlace de Compartición (Share)

| Option | Description | Selected |
|--------|-------------|----------|
| Opción A | Endpoint Público Directo: Descarga directa por ID sin firmas ni autenticación. | |
| Opción B | Acceso de Solo Lectura Firmado: Validar un parámetro query `signature` usando HMAC con `SECRET_KEY` para evitar scraping por UUID. | ✓ |

**User's choice:** Opción B (Acceso de Solo Lectura Firmado)
**Notes:** Otorga una capa de seguridad básica pero fundamental para evitar que usuarios no autorizados descarguen documentos adivinando UUIDs.

---

## Navegación de la Biblioteca de Documentos en la UI

| Option | Description | Selected |
|--------|-------------|----------|
| Opción A | Sección Principal "Documents Library": Elemento independiente en el menú lateral. | ✓ |
| Opción B | Pestaña dentro de "Content Library": Agregar pestaña junto a Templates y Static PDFs. | |

**User's choice:** Opción A (Sección Principal "Documents Library")
**Notes:** Mantiene aisladas las emisiones transaccionales operativas de los activos estáticos que conforman el diseño.

---

## the agent's Discretion

- Diseño visual específico de la línea de tiempo del tracelog.
- Estructura y formato del enlace público generado en el frontend.

## Deferred Ideas

- Restricciones avanzadas de acceso o expiración configurable en enlaces públicos de descarga — diferido para versiones post-MVP.

---

*Phase: 09-search-documents-library-audit-trace*
*Discussion log generated: 2026-07-09*
