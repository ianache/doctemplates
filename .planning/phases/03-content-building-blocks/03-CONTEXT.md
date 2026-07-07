---
phase: 03-content-building-blocks
status: ready
gathered: 2026-07-07
---

# Phase 3: Content Building Blocks - Context

**Phase Boundary**

This phase delivers the content primitives that document designs will reuse later: HTML templates with token validation against a document type schema, and uploaded static PDF assets stored locally and referenceable by future designs. It covers `CONTENT-01`, `CONTENT-02`, `CONTENT-03`, and `VALID-01` only.

Out of scope for this phase:
- Drag-and-drop design composition
- Page ordering / canvas editing
- Versioning of document designs
- PDF generation / preview rendering
- Any platform-side resolution of external operational data

**Implementation Decisions**

- HTML templates are scoped to a single document type, and token validation must read the live document-type schema at save time.
- Dotted tokens remain opaque strings, matching Phase 2 decisions; no namespace parsing is introduced.
- Using a token outside the allowed document-type schema is rejected with a clear client error before save completes.
- Static PDFs are stored on the local filesystem, not in the database.
- Static PDF uploads may optionally extract a page range before storage.
- The phase should prefer simple administrative forms and tables, not a visual designer. The real canvas arrives in Phase 4.
- Phase 3 should not introduce versioning or lifecycle controls for templates/assets beyond create/list/detail and download where needed.

**Canonical References**

- `.planning/PROJECT.md` - Product vision and high-level decisions
- `.planning/REQUIREMENTS.md` - `CONTENT-01`, `CONTENT-02`, `CONTENT-03`, `VALID-01`
- `.planning/ROADMAP.md` - Phase 3 goal and success criteria
- `.planning/phases/02-document-types/02-CONTEXT.md` - document-type schema rules used for token validation
- `.planning/phases/02-document-types/02-RESEARCH.md` - normalized schema and `react-hook-form` precedent
- `.planning/phases/02-document-types/02-03-SUMMARY.md` - confirms the content-root Phase 2 UX and manual verification flow are stable

**Code Context**

- Backend follows FastAPI + SQLAlchemy + Alembic patterns established in Phases 1 and 2.
- Frontend follows React 19 + React Router nested-shell patterns established in Phase 2.
- Existing local filesystem conventions are available for new storage directories.
- `react-hook-form` is already installed in the frontend and can be reused for content-creation forms.

**Specifics**

- Token validation should be implemented server-side, not only in the UI.
- Template HTML is stored raw; rendering to PDF is deferred to Phase 6.
- The Phase 3 UI should expose content management as a simple operational library: a template authoring path and a PDF upload path.

