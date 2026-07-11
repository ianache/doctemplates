# Phase 10: Complex Schema UI & Nested Data Previsualization - Context

**Gathered:** 2026-07-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Enhance the frontend application to support the visual configuration of complex nested schemas (objects and lists) in the Document Types UI form, and support previsualizing designs using custom nested mock JSON payloads in the visual editor.

</domain>

<decisions>
## Implementation Decisions

### Document Type Schema Fields UI (COMPUI-01)
- **D-01 (Visual Tree Builder):** The Document Types UI form will introduce an interactive tree builder node editor where users can visually add parent objects/lists and leaf fields, which automatically compiles and submits as flat dot-notation paths (e.g. `cliente.direccion.calle`, `cliente.contactos[].nombre`) to match the backend contract.
- **D-02 (Collapsible Tree Layout):** The Document Type Detail page will display the schema fields grouped under nested collapsible folders/lists to match the configured hierarchy, making it highly readable.

### Designer Mock Data Editor UI (COMPUI-02)
- **D-03 (Raw JSON Code Editor Panel):** The designer will include a panel displaying a syntax-checking raw JSON text area pre-filled with correctly structured mock data matching the Document Type schema, allowing users to quickly edit values or copy-paste preview payloads.
- **D-04 (Interactive Preview Toggle Mode):** A toolbar toggle in the designer to switch the page canvas sheet into a full-height PDF viewer. When toggled, the UI posts the custom mock JSON payload to the backend `/preview` API and renders the returned PDF Blob URL in an iframe.

### Mock Data Persistence
- **D-05 (Local Browser Storage Persistence):** The custom mock JSON payload edited in the designer will be persisted locally in the user's browser `localStorage` keyed by design ID, avoiding backend migrations.

### the agent's Discretion
- The exact UI layout of the tree builder add/remove buttons, collapsible state animations, and the JSON syntax highlighting or error indicator style.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Requirements & Specifications
- `.planning/ROADMAP.md` — Phase 10 goals and dependencies.
- `.planning/REQUIREMENTS.md` — UI/UX Improvements for Complex Fields (COMPUI-01 and COMPUI-02).
- `.design/mvp2/plantilla_objetos_campos_complejos_previsualiazcion.html` — HTML design reference for the nested object fields tree sidebar.
- `.planning/phases/10-complex-schema-ui-nested-data-previsualization/10-RESEARCH.md` — Technical research on Vite/React/FastAPI preview API contract and schema adapters.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/pages/document-types/DocumentTypeCreatePage.tsx` — Current Document Types form using `react-hook-form` + `useFieldArray` to extend.
- `frontend/src/pages/document-types/DocumentTypeDetailPage.tsx` — Detail view to display tree hierarchy.
- `frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx` — Designer detail view to add mock panel and PDF preview frame toggle.
- `frontend/src/pages/document-issuances/DocumentIssuanceDetailPage.tsx` — Reference page for fetching and displaying generated PDFs inside an iframe using Blob URLs.

### Established Patterns
- Form array registration with React Hook Form.
- Tailored color tokens and Material Icons styling from `.design/mvp2/plantilla_objetos_campos_complejos_previsualiazcion.html`.

### Integration Points
- `frontend/src/lib/documentDesigns.ts` — Define/expose `previewDocumentDesign(id, mockJSON)` client function.
- `frontend/src/lib/schemaFields.ts` — Create helper module to convert flat dot/bracket paths to/from recursive tree structures, generate mock payloads, and detect case-insensitive collisions.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-complex-schema-ui-nested-data-previsualization*
*Context gathered: 2026-07-10*
