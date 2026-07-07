# Phase 2: Document Types - Context

**Gathered:** 2026-07-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Admin/operational users can define a new document type with its own allowed data schema (named tokens/fields, each typed), and can list/view existing document types and their schemas. This phase covers DOCTYPE-01 and DOCTYPE-02 only. Templates, static PDFs, the visual designer, versioning, and generation are out of scope — those are Phases 3-6. Document types are a standalone data-modeling concept in this phase; nothing yet references or validates against them (that starts in Phase 3's VALID-01).

</domain>

<decisions>
## Implementation Decisions

### Schema Field Model
- **D-01:** Each field/token consists of: name, type (string/number/date/boolean), and an optional description. Untyped "name-only" fields were rejected — typed fields are needed for real validation in Phase 3 (VALID-01) and clearer schema browsing (DOCTYPE-02).
- **D-02:** Dotted/namespaced token names (e.g. `cliente.nombre`, `servicio.tipo`) are an available convention, not an enforced structure. The platform treats the full token name as one opaque string — no nested-namespace parsing or grouping logic. Admins are free to use dots for readability, matching the PRD's existing `{{cliente.nombre}}`-style examples.

### Document Type Lifecycle
- **D-03:** Document types are freely editable after creation — an admin can add, remove, or rename fields at any time. No versioning of document types themselves (only document DESIGNS get versioned, per VERSION-01/02 in Phase 5). The risk of a schema edit breaking a design/template that referenced a removed field is explicitly accepted for MVP1 and not handled in this phase.
- **D-04:** What happens to templates/designs referencing a removed field is explicitly deferred to Phase 3 (Content Building Blocks) — that's where token-vs-schema validation is actually implemented. Phase 2 defines schemas in isolation; nothing consumes them yet.

### Creation UX
- **D-05:** Admin builds the schema via a form with add/remove field rows (name, type, description per row) — no JSON authoring required. Matches the "no engineering involvement" core value.
- **D-06:** A document type has name + description only as top-level metadata, beyond its field list. No category/tag system — no evidence yet that MVP1 needs one.

### List/Detail View
- **D-07:** The document type list shows: name, description, field count, AND created-by/created-at audit info per row (the local user record from Phase 1's D-07 already supports attribution).
- **D-08:** List layout is a table (not cards) — dense, scannable, fits an admin/operational tool and scales as the number of document types grows.

### Claude's Discretion
- Exact DB schema for storing typed fields (e.g. JSONB column vs. a separate `document_type_fields` table) — implementation detail for research/planning to resolve.
- Detail/schema view layout specifics (beyond "shows the full field list with types/descriptions").
- Whether type values are a fixed enum (string/number/date/boolean) or extensible — start with the fixed 4 types named in D-01 unless research surfaces a reason to expand.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & Requirements
- `.planning/PROJECT.md` — Vision, "document type" abstraction rationale, Key Decisions log
- `.planning/REQUIREMENTS.md` — DOCTYPE-01, DOCTYPE-02 requirement definitions and traceability to Phase 2
- `.planning/ROADMAP.md` §Phase 2 — Phase 2 goal and success criteria

### Prior Phase Context
- `.planning/phases/01-foundation-authentication/01-CONTEXT.md` — D-07 (local user record for attribution), D-10/D-11 (Postgres + Alembic as the persistence foundation this phase builds on)
- `.planning/phases/01-foundation-authentication/01-08-SUMMARY.md` — Confirms Phase 1's auth foundation (session cookies, bearer tokens) is verified end-to-end and ready to build on

### Existing Codebase Analysis
- `.planning/codebase/STACK.md`, `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md` — Pre-Phase-1 codebase state (superseded in practice by the backend/frontend structure Phase 1 actually built: `backend/app/{models,api,auth}`, `frontend/src/{pages,lib}`)

No external specs beyond the above — this phase has no ADRs or schema-design docs to follow beyond the PRD's illustrative token examples.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/models/user.py`, `backend/app/models/session.py` — SQLAlchemy model patterns to follow for the new `document_type` (and field) model(s).
- `backend/app/api/health.py` — Existing FastAPI router pattern to follow for new document-type endpoints.
- Alembic migration setup (from 01-01-PLAN) — reuse for the new document-type schema migration.

### Established Patterns
- SQLAlchemy models live under `backend/app/models/`; API routers live under `backend/app/api/`.
- Local user record (from Phase 1 D-07) exists and can be used directly for `created_by` attribution (D-07 in this phase).

### Integration Points
- New document-type endpoints will sit alongside the existing `/api/health` router, behind the same auth gate (session cookie / bearer token) established in Phase 1.
- Frontend: new pages will live under `frontend/src/pages/`, following the pattern from the Phase 1 login/authenticated-shell pages.

</code_context>

<specifics>
## Specific Ideas

The PRD's `{{cliente.nombre}}` token style is the reference example for how dotted token names look in practice (informs D-02) — no other specific visual/UX references were given for this phase.

</specifics>

<deferred>
## Deferred Ideas

- Category/tag system for organizing document types — no evidence yet that MVP1 needs it at expected scale; revisit if the list grows large.
- Enforced nested-namespace schema structure (parsing `cliente.*` into real groups) — deferred; dots remain a naming convention only for now.
- Locking/versioning document types themselves once designs reference them — deferred; only document DESIGNS are versioned (Phase 5), not document types.
- Field-removal impact handling (what breaks when a referenced field is deleted) — explicitly deferred to Phase 3, where schema validation is actually implemented.

</deferred>

---

*Phase: 02-document-types*
*Context gathered: 2026-07-06*
