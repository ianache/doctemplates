# Phase 4: Visual Designer - Discussion Log

> **Audit trail only.** Do not use as input for planning, research, or execution agents. Decisions captured in CONTEXT.md are canonical.

**Date:** 2026-07-07
**Phase:** 04-visual-designer
**Areas discussed:** Modelo del diseno, Canvas y ordenamiento, Seleccion de contenido, Reglas de persistencia, Validacion y estados vacios, Experiencia visual del diseñador

---

## Modelo del diseno

| Option | Description | Selected |
|--------|-------------|----------|
| 1A | Nombre + document type solamente | |
| 1B | Nombre + descripcion + document type | |
| 1C | Nombre + descripcion + document type + created_by/created_at visible | yes |
| 2A | Crear, listar y ver disenos; edicion queda para Phase 5 con versionado | yes |
| 2B | Crear y editar el diseno actual sin versionado todavia | |
| 2C | Crear unicamente; list/detail basico | |
| 3A | Un diseno pertenece a exactamente un document type y no se puede cambiar despues de creado | |
| 3B | Se puede cambiar mientras no tenga paginas | yes |
| 3C | Se puede cambiar siempre, revalidando paginas | |
| 4A | Sin estado, todo diseno guardado es usable | |
| 4B | Estado simple draft solamente | |
| 4C | draft / active, pero sin versionado todavia | yes |

**User's choice:** `1C, 2A, 3B, 4C`

---

## Canvas y ordenamiento

| Option | Description | Selected |
|--------|-------------|----------|
| 1A | Lista vertical de paginas ordenadas tipo page stack | yes |
| 1B | Canvas libre con tarjetas posicionables | |
| 1C | Dos paneles: biblioteca izquierda + stack ordenado central | |
| 2A | Drag-and-drop obligatorio | yes |
| 2B | Botones subir/bajar como control principal | |
| 2C | Drag-and-drop + botones subir/bajar como fallback accesible | |
| 3A | Tarjeta compacta con tipo, nombre y posicion | yes |
| 3B | Bloque tipo hoja/pagina con altura visual mayor | |
| 3C | Fila densa estilo tabla | |
| 4A | El orden se guarda explicitamente al presionar Save | |
| 4B | Cada reorder se persiste automaticamente | yes |
| 4C | Reorder local primero, autosave despues de breve delay | |

**User's choice:** `1A, 2A, 3A, 4B`

---

## Seleccion de contenido

| Option | Description | Selected |
|--------|-------------|----------|
| 1A | Botones separados Add Template y Add PDF que abren un modal | yes |
| 1B | Biblioteca lateral siempre visible | |
| 1C | Selector inline dentro del stack | |
| 2A | Templates solo del document type del diseno; PDFs disponibles para todos | |
| 2B | Templates y PDFs filtrados por document type | initially |
| 2C | Mostrar todo, pero bloquear al guardar si algo no corresponde | |
| 3A | PDFs estaticos son globales y reutilizables en cualquier document type | initially |
| 3B | PDFs quedan asociados al document type elegido al subirlos | |
| 3C | El usuario elige al agregarlos si aplican o no | |
| 4A | Mostrar empty state con link a crear template/subir PDF | yes |
| 4B | Permitir crear contenido desde el modal | |
| 4C | Solo mostrar mensaje; creacion queda en Content Library | |

**User's choice:** `1A, 2B, 3A, 4A`

**Clarification:** The PDF rules conflicted, so the user selected final rule `2`: PDFs may be associated optionally. Designer selectors show global PDFs plus PDFs associated with the design's document type.

---

## Reglas de persistencia

| Option | Description | Selected |
|--------|-------------|----------|
| 1A | Tipo de bloque + id de contenido + posicion | |
| 1B | Tipo + id + posicion + titulo opcional | |
| 1C | Tipo + id + posicion + titulo opcional + notas internas | yes |
| 2A | Permitir usar el mismo template/PDF varias veces en el mismo diseno | |
| 2B | Bloquear duplicados dentro del mismo diseno | |
| 2C | Permitir duplicados solo para templates, no PDFs | yes |
| 3A | Remover inmediatamente sin confirmacion | |
| 3B | Confirmacion simple antes de remover | |
| 3C | Remover con undo local mientras no salgas de la pantalla | yes |
| 4A | El diseno siempre apunta al template/PDF actual por ID | |
| 4B | Guardar snapshot basico del nombre al momento de agregarlo | |
| 4C | Guardar snapshot completo del HTML/PDF metadata para aislar el diseno de cambios futuros | yes |

**User's choice:** `1C, 2C, 3C, 4C`

---

## Validacion y estados vacios

| Option | Description | Selected |
|--------|-------------|----------|
| 1A | Permitir guardar draft vacio, bloquear active vacio | yes |
| 1B | Bloquear cualquier diseno sin paginas | |
| 1C | Permitir siempre, incluso active vacio | |
| 2A | Solo requiere nombre, document type y al menos una pagina | yes |
| 2B | Ademas requiere que todos los templates sigan siendo compatibles con el schema actual | |
| 2C | Ademas requiere que todos los PDFs referenciados existan fisicamente en storage | |
| 3A | Bloquear activacion y mostrar tokens invalidos | yes |
| 3B | Permitir activacion con warning | |
| 3C | No revisar en Phase 4 | |
| 4A | Mostrar panel con dos acciones: Add Template / Add PDF | yes |
| 4B | Mostrar guia paso-a-paso | |
| 4C | Mostrar solo lista vacia y botones en toolbar | |

**User's choice:** `1A, 2A, 3A, 4A`

---

## Experiencia visual del disenador

| Option | Description | Selected |
|--------|-------------|----------|
| 1A | Admin funcional: cards compactas, sin preview visual real | |
| 1B | Mini-preview textual para HTML y metadata PDF | yes |
| 1C | Representacion tipo pagina con preview parcial, sin render PDF final | |
| 2A | Header metadata, toolbar, stack | |
| 2B | Dos columnas: stack principal + inspector lateral | |
| 2C | Biblioteca/modal para agregar, stack central, inspector lateral para pagina seleccionada | yes |
| 3A | No inspector; editar detalles en modal | |
| 3B | Inspector lateral para titulo/notas/configuracion de pagina seleccionada | yes |
| 3C | Inline editing dentro de cada card | |
| 4A | Solo texto Template / PDF | |
| 4B | Icono + color discreto por tipo | |
| 4C | Icono + metadata especifica: tokens para template, page count/range para PDF | yes |

**User's choice:** `1B, 2C, 3B, 4C`

---

## Agent's Discretion

- Exact drag-and-drop library and implementation details.
- Exact database schema for snapshots and page configuration.
- Exact UI spacing and card visual styling within the existing admin design language.
- Whether activation is implemented as a dedicated endpoint or state update.

## Deferred Ideas

- Versioned editing of document designs.
- Final PDF rendering and preview.
- Full page-fidelity rendering inside the designer.
- Platform-side data resolution.
