# DocManagement Platform

## What This Is

A general-purpose document management platform where operational users visually design document mockups — composing pages from dynamic HTML templates (token-based, e.g. `{{cliente.nombre}}`) and uploaded static PDF pages (e.g. legal terms) — and generate final PDF documents via an API by supplying the data to fill those tokens. Each document design belongs to a **document type**, an admin-configurable concept that defines its own allowed data schema (tokens/fields). The "Sales Channel + Service" scenario from the original PRD (with Básico/Flota token filtering) is just one example document type this platform PDF generator supports generally.

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
- ✓ Nested object paths (`cliente.direccion.calle`) in schemas, validation, and template rendering — Phase 7
- ✓ Wildcard list paths (`cliente.contactos[].nombre`) in schemas, validation, and template rendering — Phase 7
- ✓ Case-insensitive token and payload key matching across the platform — Phase 7
- ✓ Detection and rejection of case-insensitive key collisions (e.g. `Name` vs `name`) — Phase 7
- ✓ AST-based parsing of templates to statically extract referenced token paths — Phase 8
- ✓ Static verification of template token paths against document type schema before activation — Phase 8
- ✓ Library interface for searching, filtering, and viewing past generated documents (issuances) — Phase 9
- ✓ Audit logging of document activities (generation, download, share) in a chronological timeline view — Phase 9
- ✓ public share URLs backed by HMAC signature verification to bypass auth requirements safely — Phase 9
- ✓ Visual tree builder and collapsible tree sidebar editor for nested document type schemas — Phase 10
- ✓ Previsualization with custom, editable mock JSON payloads persisted in browser `localStorage` — Phase 10

### Active (Next Milestone Goals)

- [ ] Platform resolves token data from external systems by reference ID, instead of requiring the API caller to supply all data directly (DATA-01).
- [ ] Fine-grained roles/permissions per document type or design (AUTH-02).
- [ ] Document access protection and access restrictions on shared links (SEC-01).
- [ ] Support non-PDF output formats (OUTPUT-01).

### Out of Scope

- Platform-side resolution of real operational data (platform fetching data from external systems by reference ID) — deferred to a future milestone (DATA-01).
- Non-PDF output formats — PDF-only format is maintained.
- Custom-built auth (email/password) — authentication is strictly OIDC-based.

## Context

- Codebase is fully functional. Backend is built with Python, FastAPI, SQLAlchemy, Alembic, and Jinja2; frontend is React with Vite and Tailwind CSS.
- Codebase includes full test coverage for nested schemas, AST token parsing, case-insensitive proxy matching, and PDF generation.

## Constraints

- **Tech stack**: Python/FastAPI, Postgres, SQLAlchemy/Alembic, React/TypeScript/Vite.
- **Auth**: Integrates Keycloak OAuth2/OIDC.
- **Output format**: PDF only.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Generalize "Canal de Venta + Servicio" into a generic "document type" abstraction | Platform must support many scenarios beyond the vehicle-contract example | Implemented (Phase 2) |
| Visual drag-and-drop designer is in scope for MVP1 | User confirmed the visual UI is needed now | Implemented (Phase 4) |
| Document types are admin-configurable through the platform | User wants operational users to create new document types without engineering involvement | Implemented (Phase 2) |
| Static PDFs are uploaded through the UI | User confirmed upload is the intended flow | Implemented (Phase 3) |
| MVP1 data flow: caller supplies all data; platform does not resolve data | Keeps MVP1 scoped; data-source integration explicitly deferred | Design confirmed (Phase 6) |
| Auth integrates Keycloak OIDC | Multi-user access with an existing identity provider | Implemented (Phase 1) |
| Document designs are versioned with history | Users need to iterate on designs without mutating historical records | Implemented (Phase 5) |
| Postgres partial unique indexes for version constraints | Guarantees at most one active and one draft version per design group | Implemented (Phase 5) |
| Preserve exact payload casing in DB but match case-insensitively using proxy wrappers | Satisfies casing tolerance while preserving original client request payloads | Implemented (Phase 7) |
| Parse template tokens via AST and statically check them against schemas | Validates templates at activation time to prevent downstream generation failures | Implemented (Phase 8) |
| Keep Documents Library search filters as query parameters and omit blanks | Clean URL state routing and allows dynamic backend-driven AND queries | Implemented (Phase 9) |
| Use HMAC-signed URLs for public share URLs | Allows secure download access for shared links without requiring OIDC auth | Implemented (Phase 9) |
| Store designer preview mock JSON in `localStorage` | Keeps user edits persistent across page reloads and canvas redraws | Implemented (Phase 10) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

---
*Last updated: 2026-07-11 after Milestone v2.0*
