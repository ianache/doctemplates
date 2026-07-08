# Phase 4: Visual Designer - Context

**Gathered:** 2026-07-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 4 delivers the visual document designer: authenticated users can create a document design scoped to a document type, compose it from the Phase 3 content primitives, and persist the ordered page sequence that downstream generation will use. This phase covers `DESIGN-01` and `DESIGN-02`.

Out of scope for this phase:
- Version history and revision workflows, which belong to Phase 5.
- Final PDF generation, preview rendering, and mock/sample data substitution, which belong to Phase 6.
- Platform-side resolution of external operational data.
- Editing an existing design after creation; Phase 4 supports create/list/detail and activation decisions only.

</domain>

<decisions>
## Implementation Decisions

### Design Metadata and Lifecycle
- **D-01:** A document design records and displays name, description, document type, created-by, and created-at metadata.
- **D-02:** Phase 4 supports creating, listing, and viewing designs. Editing existing designs is deferred to Phase 5 so edits can be handled together with versioning.
- **D-03:** A design belongs to exactly one document type. The document type can be changed only while the design has no pages.
- **D-04:** Designs have a simple `draft` / `active` lifecycle in Phase 4, without version history.

### Canvas and Ordering
- **D-05:** The primary designer surface is a vertical ordered page stack, not a freeform canvas.
- **D-06:** Reordering is drag-and-drop first. No button-based reorder fallback was requested for MVP1.
- **D-07:** Each page is represented as a compact card showing type, content identity, position, and relevant metadata.
- **D-08:** Page order persists automatically after each drag-and-drop reorder.

### Content Selection
- **D-09:** Users add content through separate `Add Template` and `Add PDF` actions that open selection modals.
- **D-10:** Templates shown in the selector must be scoped to the design's document type.
- **D-11:** Static PDFs may be global or associated with a document type. The designer should show PDFs that are global plus PDFs associated with the design's document type.
- **D-12:** When no compatible content exists, the designer empty state should include direct actions or links to create a template or upload a PDF.

### Page Persistence
- **D-13:** Each design page stores block type, referenced content id, position, optional title, internal notes, and minimal page configuration.
- **D-14:** The same HTML template may be used multiple times in a design. The same static PDF may not be duplicated in a single design.
- **D-15:** Removing a page should use local undo while the user remains on the designer screen.
- **D-16:** A design page stores a complete snapshot of the referenced content/metadata when it is added, so the design remains stable if the source template/PDF changes later.

### Validation
- **D-17:** Draft designs may be saved with no pages. Active designs must have at least one page.
- **D-18:** Activating a design requires name, document type, and at least one page.
- **D-19:** If a template snapshot or current template token set becomes incompatible with the design's document type schema, activation is blocked and the invalid tokens are shown clearly.
- **D-20:** The empty designer state should show two primary actions: `Add Template` and `Add PDF`.

### Visual Experience
- **D-21:** Phase 4 should provide mini-previews: textual/HTML preview for templates and metadata preview for PDFs. It should not attempt final PDF rendering.
- **D-22:** The designer layout should use content selection modal(s), a central page stack, and an inspector side panel for the selected page.
- **D-23:** The inspector side panel is where the user edits page title, notes, and page-level configuration for the selected page.
- **D-24:** Page cards and inspector should show type-specific indicators: icon plus metadata, including tokens for templates and page count/range for PDFs.

### the agent's Discretion
- Exact drag-and-drop library and implementation details.
- Exact database schema shape for design/page snapshots.
- Exact visual treatment of compact cards, inspector spacing, and mini-preview truncation, provided it stays consistent with the existing admin UI.
- Whether activation is a dedicated endpoint or an update action, as long as the lifecycle and validation rules above are enforced.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project and Requirements
- `.planning/PROJECT.md` - Product vision, core value, and key decisions about visual drag-and-drop being in MVP1.
- `.planning/REQUIREMENTS.md` - `DESIGN-01` and `DESIGN-02` requirement definitions.
- `.planning/ROADMAP.md` - Phase 4 goal, dependencies, and success criteria.

### Prior Phase Context
- `.planning/phases/02-document-types/02-CONTEXT.md` - Document type schema model, dotted token rules, and admin UI conventions.
- `.planning/phases/03-content-building-blocks/03-CONTEXT.md` - Template/PDF content primitive boundaries and decisions.
- `.planning/phases/03-content-building-blocks/03-01-SUMMARY.md` - HTML template API and validation behavior.
- `.planning/phases/03-content-building-blocks/03-02-SUMMARY.md` - Static PDF asset API and storage behavior.
- `.planning/phases/03-content-building-blocks/03-03-SUMMARY.md` - Content library frontend patterns and content API client.

### Existing Code
- `backend/app/api/document_types.py` - Existing authenticated list/detail API pattern.
- `backend/app/api/content_templates.py` - Template API and document-type scoped validation pattern.
- `backend/app/api/static_pdfs.py` - Static PDF upload/list/detail/download API.
- `frontend/src/pages/AuthenticatedShell.tsx` - Existing authenticated navigation shell.
- `frontend/src/pages/content/ContentLibraryPage.tsx` - Existing operational content library table/list patterns.
- `frontend/src/lib/content.ts` - Typed frontend client for Phase 3 content resources.
- `frontend/src/lib/documentTypes.ts` - Typed frontend client for document type resources.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DocumentType` / `DocumentTypeField` SQLAlchemy models already provide the schema that designs are scoped to.
- `HtmlTemplate` records document-type scoped HTML and token names; design validation can reuse those token names and the live schema.
- `StaticPdfAsset` records file metadata and page count/range information; design pages can reference these by stable ids and snapshot metadata.
- Frontend content pages already use operational tables, nested routes, and typed API wrappers that Phase 4 should extend.

### Established Patterns
- Backend API routers live under `backend/app/api/` and are protected by `Depends(get_current_user)`.
- SQLAlchemy models live under `backend/app/models/`, schemas under `backend/app/schemas/`, and Alembic migrations under `backend/alembic/versions/`.
- Frontend pages live under `frontend/src/pages/`, typed fetch wrappers under `frontend/src/lib/`, and authenticated navigation is centralized in `AuthenticatedShell`.
- Admin UI style is dense and utilitarian: tables, compact cards, restrained borders, and explicit actions.

### Integration Points
- New design endpoints should sit alongside `/api/document-types`, `/api/content/templates`, and `/api/content/static-pdfs`.
- The designer UI should live under the authenticated shell, likely as a new `Document Designs` navigation entry.
- Content selection must call existing template/PDF list/detail endpoints, or planner may add filtered list capabilities if needed.

</code_context>

<specifics>
## Specific Ideas

- The visual designer should feel like an operational page stack, not a marketing canvas or final PDF renderer.
- The central workflow is: choose document type, add compatible template/PDF pages, drag to reorder, inspect selected page, and activate when valid.
- Template incompatibility must be explicit and actionable by showing invalid token names.

</specifics>

<deferred>
## Deferred Ideas

- Editing existing designs after creation is deferred to Phase 5 with version history.
- Final PDF rendering and preview are deferred to Phase 6.
- Full visual page rendering is deferred; Phase 4 uses mini-previews only.
- External data resolution remains deferred beyond MVP1.

</deferred>

---

*Phase: 04-visual-designer*
*Context gathered: 2026-07-07*
