# Phase 6: Generation & Preview API - Context

**Gathered:** 2026-07-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 6 delivers the production and preview PDF generation endpoints:
1. Production endpoint: Generates a final merged PDF from a document design + caller-supplied data (interpolates templates, extracts static pages, and merges them in the configured order), saving the resulting file to disk and logging the issuance.
2. Preview endpoint: Generates an ephemeral in-memory preview PDF from caller-supplied or schema-derived mock data without creating disk files or database records.

Out of scope:
- Platform-side resolution of external operational data (BFF is the entry point, all data must be supplied in payload).
- Fine-grained RBAC roles on who can generate PDFs (handled generically under auth).
- Supporting non-PDF output formats.

</domain>

<decisions>
## Implementation Decisions

### PDF Rendering & Templating Engines
- **D-01 (HTML-to-PDF Renderer):** Use `xhtml2pdf` (pure Python ReportLab-based engine). It has zero system-level binary dependencies and installs cleanly on Windows via `pip`/`uv`.
- **D-02 (Templating Engine):** Use `Jinja2` to interpolate Mustache/Handlebars-style tokens (e.g. `{{ cliente.nombre }}`), which handles nested dictionary resolution natively.
- **D-03 (Page Layout):** Style margins, headers, footers, and page numbers using standard CSS `@page` rules in a default base stylesheet (e.g., standard Letter/A4 layout).
- **D-04 (Typography):** Use standard built-in system/PDF fonts (Helvetica, Times, Courier) to ensure fast rendering and simple, zero-setup setup.

### Data Validation & Type Constraints
- **D-05 (Missing Schema Fields):** Reject request with `400 Bad Request` if any fields defined in the document type schema are missing from the API payload (guarantees legal documents are never generated blank/incomplete).
- **D-06 (Extra Fields):** Ignore extra fields in the API payload that are not defined in the document type schema, rather than rejecting them.
- **D-07 (Type Validation & Coercion):** Attempt to coerce payload types to the schema types (e.g., parsing numeric or boolean strings), raising `400 Bad Request` only if conversion fails.
- **D-08 (Date Handling):** Validate date fields against ISO 8601 `YYYY-MM-DD` format. Expose a custom formatting Jinja2 filter (e.g., `{{ date_val | date_format }}`) to allow document designs to render human-readable dates.

### Issuance Persistence & PDF Storage
- **D-09 (Storage):** Save generated production PDFs to disk (e.g. `storage/issuances/`) so they are immutable and re-downloadable.
- **D-10 (Database Tracking):** Track each issuance in a new `DocumentIssuance` table recording the issuance ID, design version ID, file path, and user ID.
- **D-11 (Filenames):** Use secure, collision-free UUID naming convention on disk (`{issuance_id}.pdf`).
- **D-12 (Input Payload Logging):** Persist the raw JSON payload in a JSONB column (`input_data`) on the issuance record for debugging and historical validation.

### Preview API & Mock Data Sourcing
- **D-13 (Mock Data fallback):** Accept optional caller-supplied preview data, falling back to auto-generated mock values based on field types (e.g. "Mock String", 123.45, current date, true) for any omitted fields.
- **D-14 (Supported Statuses):** Support preview generation for both `draft` and `active` versions of a document design (allows visual designer preview before activation).
- **D-15 (Response Format):** Return the preview PDF as a raw binary stream with `Content-Type: application/pdf`.
- **D-16 (Ephemeral Execution):** Do not write preview files to disk or record any entries in the database; preview operations must remain in-memory and stateless.

### the agent's Discretion
- The exact layout of the base CSS stylesheet for `@page` layout setups (margins, footers).
- The exact Python functions/methods for generating default mock data based on field type.
- The structure/endpoints naming convention for the generation API (e.g., standard endpoints `/api/document-designs/{id}/generate` and `/api/document-designs/{id}/preview`).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project and Requirements
- [PROJECT.md](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/PROJECT.md) — Product vision, core value, and key decisions regarding caller-supplied data and PDF output constraints.
- [REQUIREMENTS.md](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/REQUIREMENTS.md) — `GEN-01` and `GEN-02` requirements.
- [ROADMAP.md](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/ROADMAP.md) — Phase 6 goals and dependencies.

### Prior Phase Context
- [02-CONTEXT.md](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/phases/02-document-types/02-CONTEXT.md) — Schema constraints and field rules.
- [03-CONTEXT.md](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/phases/03-content-building-blocks/03-CONTEXT.md) — Dynamic HTML template and static PDF asset boundaries.
- [03-01-SUMMARY.md](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/phases/03-content-building-blocks/03-01-SUMMARY.md) — Template token validation logic.
- [03-02-SUMMARY.md](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/phases/03-content-building-blocks/03-02-SUMMARY.md) — Static PDF file-handling/parsing (`pypdf` usage).
- [04-CONTEXT.md](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/phases/04-visual-designer/04-CONTEXT.md) — Design page serialization and snapshots.
- [05-CONTEXT.md](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/phases/05-versioning/05-CONTEXT.md) — Design statuses (`draft`, `active`, `superseded`) and active version rules.

### Existing Code
- [content_storage.py](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/backend/app/services/content_storage.py) — Reference helper using `pypdf` reader/writer to slice/merge PDFs.
- [content_validation.py](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/backend/app/services/content_validation.py) — Template token extraction.
- [design_validation.py](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/backend/app/services/design_validation.py) — Design activation token compatibility validation.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pypdf.PdfWriter` (imported in `backend/app/services/content_storage.py`): Reused to stitch together rendered HTML PDFs and static PDF page ranges in sequence.
- `app/services/design_validation.py`: `validate_design_activation` can be adapted to validate supplied data fields against the schema.

### Established Patterns
- APIs use FastAPI routers in `backend/app/api/` protected by OIDC auth (`Depends(get_current_user)`).
- SQL tables mapped via SQLAlchemy models in `backend/app/models/`.

### Integration Points
- Expose `/api/document-designs/{design_id}/generate` and `/api/document-designs/{design_id}/preview` endpoints.
- Create migration for the `DocumentIssuance` table.

</code_context>

<specifics>
## Specific Ideas
- Provide a Jinja filter like `date_format` (converting ISO 8601 strings to human-friendly local formats like `DD/MM/YYYY`) automatically in the rendering context.
- When generating preview mock data:
  - `string` -> `"{field_name}_val"`
  - `number` -> `123.45`
  - `boolean` -> `true`
  - `date` -> current date string (`YYYY-MM-DD`)

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-generation-preview-api*
*Context gathered: 2026-07-08*
