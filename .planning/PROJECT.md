# DocManagement Platform

## What This Is

A general-purpose document management platform where operational users visually design document mockups — composing pages from dynamic HTML templates (token-based, e.g. `{{cliente.nombre}}`) and uploaded static PDF pages (e.g. legal terms) — and generate final PDF documents via an API by supplying the data to fill those tokens. Each document design belongs to a **document type**, an admin-configurable concept that defines its own allowed data schema (tokens/fields). The "Sales Channel + Service" scenario from the original PRD (with Básico/Flota token filtering) is just one example document type this platform must support generally — not a hardcoded rule.

## Core Value

Operational users can visually compose a document design (templates + fixed content, in order) and reliably generate a correct final PDF from it via API, without engineering involvement per document type.

## Requirements

### Validated

- ✓ Multi-user access with OAuth2/OIDC-based authentication — Phase 1
- ✓ Admin/operational users can define a new "document type" with its own allowed data schema (tokens/fields) — Phase 2
- ✓ A page can be a dynamic HTML template with tokens scoped to the document type's schema — Phase 3
- ✓ A page can be a static PDF (or specific page range from one), uploaded through the UI — Phase 3
- ✓ Static PDFs uploaded through the UI are stored and referenceable by document designs — Phase 3
- ✓ Attempting to use a token outside a document type's allowed schema is rejected (400-style error) — Phase 3
- ✓ Users can visually design a document (drag-and-drop canvas) by composing ordered pages — Phase 4
- ✓ Users can reorder pages in the designer; order is preserved through to generation — Phase 4
- ✓ Users can edit an existing document design, creating a new version (version history preserved) — Phase 5
- ✓ API endpoint generates a final merged PDF from a document design + caller-supplied data (fills template tokens, merges with static pages in order) — Phase 6
- ✓ Preview endpoint generates a PDF from mock/sample data without persisting an issuance — Phase 6

### Active

- [ ] Support nested objects (e.g. `cliente.direccion.calle`) in Document Type schemas, validation, and template rendering
- [ ] Support lists of objects (e.g. `cliente.contactos[].nombre`) in Document Type schemas, validation, and template rendering
- [ ] Implement case-insensitive token and payload key matching across the platform

### Out of Scope

- Platform-side resolution of real operational data (platform fetching data from external systems by reference ID) — deferred to a future milestone; MVP1 requires the API caller to supply all data directly
- Non-PDF output formats — MVP1 is PDF-only
- The specific Sales Channel / Service (B2C Básico vs B2B Flota) business rule as a hardcoded feature — it becomes an example document type configured through the general mechanism, not bespoke code
- Custom-built auth (email/password) — MVP1 integrates an existing OAuth2/OIDC identity provider rather than owning credentials

## Context

- Originates from a PRD (`PRD.md`, in Spanish) describing a narrower "maquetas de documentos" designer scoped to Canal de Venta + Servicio for vehicle-related contracts. That PRD is treated as one concrete example/reference, not the full scope — the platform must generalize the pattern (document type → allowed schema → template/fixed-content composition → generation) to arbitrary scenarios.
- Codebase is pre-alpha: `main.py` is a 5-line stub, no real dependencies chosen yet. See `.planning/codebase/` for the current-state map (STACK.md, ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, INTEGRATIONS.md, CONCERNS.md).
- `headroom-ai` in `pyproject.toml` is developer tooling (token-optimization CLI used during this project's own development), not a product dependency — no relation to the platform being built.
- PRD's rendering pipeline (token interpolation → HTML-to-PDF → static PDF page extraction → merge in page order) is a useful reference for the generation pipeline design, generalized beyond the vehicle-contract example.

## Constraints

- **Tech stack**: No hard constraints — free to choose a modern, sensible stack (backend language/framework, PDF/HTML-to-PDF library, template engine, frontend framework)
- **Timeline**: No hard deadline stated
- **Auth**: Must integrate an external OAuth2/OIDC identity provider (generic — not a named provider yet); platform does not own user credentials
- **Output format**: PDF only for MVP1

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Generalize "Canal de Venta + Servicio" into a generic "document type" abstraction | Platform must support many scenarios beyond the vehicle-contract example; hardcoding one business rule would block reuse | Implemented (Phase 2) |
| Visual drag-and-drop designer is in scope for MVP1 (not API/JSON-only) | User confirmed the visual UI is needed now, not deferred | Implemented (Phase 4) |
| Document types are admin-configurable through the platform, not developer-defined config | User wants operational users to create new document types without engineering involvement | Implemented (Phase 2) |
| Static PDFs are uploaded through the UI (not referenced from a pre-existing repository) | User confirmed upload is the intended flow | Implemented (Phase 3) |
| MVP1 data flow: caller supplies all data in the generation request; platform does not resolve data from external systems | Keeps MVP1 scoped; data-source integration explicitly deferred | Design confirmed (Phase 6) |
| Auth integrates an existing OAuth2/OIDC IdP rather than building custom auth | User confirmed multi-user with an existing identity provider, generic OIDC | Implemented (Phase 1) |
| Document designs are editable with version history | User wants to iterate on designs after creation without losing prior versions | Implemented (Phase 5) |
| Row-per-version design schema extending document_designs with version_group_id and version_number | Simplifies SQL querying of past designs and keeps schemas uniform across versions | Implemented (Phase 5) |
| Postgres partial unique indexes to guarantee at most one active and one draft version per group | Leverages database-level constraints for versioning safety | Implemented (Phase 5) |
| Exclusively allow modifying design pages (add, update, delete, reorder) on draft designs | Prevents mutation of activated/superseded historical designs | Implemented (Phase 5) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-07-09 after Milestone v1.0*
