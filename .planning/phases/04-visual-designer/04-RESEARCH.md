---
phase: 04-visual-designer
status: complete
researched: 2026-07-07
---

# Phase 4: Visual Designer - Research

## Scope

Phase 4 builds the first usable document design workflow. It creates persisted designs scoped to a document type, stores ordered pages that reference Phase 3 content primitives, and exposes a React designer where users compose and reorder pages. It does not render final PDFs, create previews, or implement version history.

## Existing System Fit

### Backend

- Use the established FastAPI router pattern under `backend/app/api/`.
- Protect every design endpoint with `Depends(get_current_user)`.
- Use SQLAlchemy models under `backend/app/models/`, Pydantic schemas under `backend/app/schemas/`, and Alembic migrations under `backend/alembic/versions/`.
- Reuse `DocumentType` / `DocumentTypeField` for design scoping and activation validation.
- Reuse `HtmlTemplate` token metadata and raw HTML for template page snapshots.
- Reuse `StaticPdfAsset` metadata for PDF page snapshots.

### Frontend

- Extend the authenticated shell with a `Document Designs` navigation entry.
- Add typed design API wrappers under `frontend/src/lib/`.
- Add React Router pages under `frontend/src/pages/document-designs/`.
- Preserve the existing admin-oriented UI: compact tables, compact cards, restrained borders, explicit actions.

## Drag-and-Drop Approach

Use `@dnd-kit/core`, `@dnd-kit/sortable`, and `@dnd-kit/utilities` for the page stack. The dnd-kit sortable docs describe `SortableContext`, `useSortable`, `arrayMove`, `verticalListSortingStrategy`, and keyboard/pointer sensors as the standard building blocks for sortable lists: https://dndkit.com/legacy/presets/sortable/overview/

Fit for this phase:

- The user selected a vertical ordered page stack, not a freeform canvas.
- `verticalListSortingStrategy` matches the required page-stack behavior.
- `SortableContext` requires the `items` prop to match render order; this aligns with autosaving order after drag end.
- Keyboard sensor support is available, but the context decision only requires drag-and-drop as the primary interaction. The implementation may still include keyboard sensor support if straightforward.

## Data Model Recommendation

Create two new tables:

- `document_designs`: id, document_type_id, name, description, status (`draft` or `active`), created_by_id, created_at.
- `document_design_pages`: id, design_id, position, block_type (`html_template` or `static_pdf`), content_id, title, notes, config JSON, snapshot JSON, created_at.

Update `static_pdf_assets`:

- Add nullable `document_type_id` so PDFs may be global or associated with a document type.
- Existing PDFs with null document type remain global.

Snapshots should include enough data for downstream generation stability:

- Template snapshot: template id/name/html/token_names/document_type_id.
- PDF snapshot: asset id/filename/page_count/page_start/page_end/file_size/stored_filename.

## API Recommendation

Add `/api/document-designs`:

- `POST /api/document-designs` creates a draft design.
- `GET /api/document-designs` lists designs.
- `GET /api/document-designs/{id}` returns design metadata and ordered pages.
- `POST /api/document-designs/{id}/pages/template` adds a template page.
- `POST /api/document-designs/{id}/pages/static-pdf` adds a PDF page.
- `PATCH /api/document-designs/{id}/pages/reorder` persists page order.
- `PATCH /api/document-designs/{id}/pages/{page_id}` updates title/notes/config.
- `DELETE /api/document-designs/{id}/pages/{page_id}` removes a page.
- `POST /api/document-designs/{id}/activate` validates and marks active.

Validation rules:

- Draft designs may have zero pages.
- Active designs must have at least one page.
- Template pages must belong to the design's document type.
- Activation must compare template token names against the live document type fields and report invalid tokens.
- A static PDF can be added when it is global or associated with the design's document type.
- A static PDF cannot be duplicated within the same design.
- Template pages may be duplicated.

## Planning Split

1. Backend model/API and tests.
2. Frontend routes, API client, list/create/detail shell.
3. Frontend designer stack: selectors, dnd reorder, inspector, activation, manual verification.

## Risks

- Existing `StaticPdfAsset` does not yet carry document-type association; adding it must preserve current global PDF behavior.
- Snapshots can drift from live source content by design. Activation still needs to validate template compatibility against the current document type schema.
- Autosave reorder needs optimistic UI plus error handling so order does not silently diverge from persisted state.

