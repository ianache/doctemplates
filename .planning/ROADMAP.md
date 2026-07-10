# Roadmap: DocManagement Platform

## Overview

The platform is built bottom-up along its natural dependency chain. Milestone v1.0 established authentication, document type configurations, content building blocks, the visual drag-and-drop designer, version history, and basic PDF generation.

For Milestone v2.0, the platform extends its core capabilities to support complex nested objects and list fields in schemas and templates, robust case-insensitive payload and template token matching, and static template validation using Abstract Syntax Tree (AST) parsing. Additionally, a document library is introduced to search, filter, preview, download, and share generated document issuances with a technical audit log, alongside UI enhancements for managing complex schemas and previsualizing nested data in the designer.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation & Authentication** - Platform scaffolding with access gated behind OAuth2/OIDC login
- [x] **Phase 2: Document Types** - Admins define document types with their own allowed token/field schemas
- [x] **Phase 3: Content Building Blocks** - Token-scoped HTML templates and uploaded static PDFs, with schema enforcement
- [x] **Phase 4: Visual Designer** - Drag-and-drop composition of ordered pages into a document design
- [x] **Phase 5: Versioning** - Editing a design creates a new version; history is preserved and viewable (completed 2026-07-08)
- [x] **Phase 6: Generation & Preview API** - API generates final and preview PDFs from a design plus caller-supplied data (completed 2026-07-08)
- [x] **Phase 7: Backend Core (Nested Data & Case-Insensitive Matching)** - Support nested objects, object lists, and case-insensitive matching in schema validation and template rendering (completed 2026-07-09)
- [x] **Phase 8: Template AST & Static Validation** - Extract referenced tokens via Jinja2 AST parsing and statically validate them against schemas before activation (completed 2026-07-10)
- [ ] **Phase 9: Search Documents Library & Audit Trace** - Retrieve, filter, view, download, and share generated documents with a detailed timeline audit log
- [ ] **Phase 10: Complex Schema UI & Nested Data Previsualization** - UI management of nested schemas and interactive previsualization of nested data in the visual editor

## Phase Details

### Phase 1: Foundation & Authentication

**Goal**: The platform has a working application foundation and gates all access behind an external OAuth2/OIDC identity provider — no custom-built credentials.
**Depends on**: Nothing (first phase)
**Requirements**: AUTH-01
**Success Criteria** (what must be TRUE):

  1. User can log in via the configured OAuth2/OIDC identity provider and reach the platform.
  2. Unauthenticated requests to the platform (UI and API) are rejected rather than allowed through.
  3. Multiple distinct users can each authenticate under their own identity and use the platform.

**Plans**: 8 plans
**UI hint**: yes

Plans:

- [x] 01-01-PLAN.md — Backend sub-project scaffold, Settings, SQLAlchemy models/Alembic, pytest infra
- [x] 01-02-PLAN.md — Docker Compose (Keycloak + Postgres) + Keycloak realm bootstrap
- [x] 01-03-PLAN.md — Frontend Vite/React scaffold + Precision Archival Tailwind design tokens
- [x] 01-04-PLAN.md — Bearer-token JWKS validation + cookie-session dependency
- [x] 01-05-PLAN.md — User upsert-on-login service + session create/delete service
- [x] 01-06-PLAN.md — Authlib OIDC login/callback/logout routes + CORS + protected /api/health
- [x] 01-07-PLAN.md — Frontend Login page + Authenticated Shell wired to backend contract
- [x] 01-08-PLAN.md — Manual end-to-end AUTH-01 verification checkpoint

### Phase 2: Document Types

**Goal**: Admin/operational users can define document types, each with its own allowed data schema, and browse existing ones.
**Depends on**: Phase 1
**Requirements**: DOCTYPE-01, DOCTYPE-02
**Success Criteria** (what must be TRUE):

  1. User can create a new document type and define its allowed schema (named tokens/fields).
  2. User can view a list of existing document types.
  3. User can view the allowed schema (tokens/fields) of a specific document type.

**Plans**: 3 plans
**UI hint**: yes

Plans:

- [x] 02-01-PLAN.md — Backend: DocumentType/DocumentTypeField models, migration, schemas, create/list/detail API (TDD)
- [x] 02-02-PLAN.md — Frontend: nested routing + left nav rail, document type list + detail pages
- [x] 02-03-PLAN.md — Frontend: document type create form (react-hook-form + useFieldArray) + manual E2E verification checkpoint

### Phase 3: Content Building Blocks

**Goal**: Users can create the two kinds of page content that document designs are composed from — token-scoped HTML templates and uploaded static PDFs — with schema violations rejected.
**Depends on**: Phase 2
**Requirements**: CONTENT-01, CONTENT-02, CONTENT-03, VALID-01
**Success Criteria** (what must be TRUE):

  1. User can create an HTML template with tokens, scoped to a chosen document type.
  2. Saving a template that uses a token outside the document type's allowed schema is rejected with a clear error (e.g. 400) instead of silently accepted.
  3. User can upload a static PDF, or a specific page range extracted from one, as page content.
  4. Uploaded static PDFs are stored by the platform and remain referenceable for later use in document designs.

**Plans**: 3 plans
**UI hint**: yes

Plans:

- [x] 03-01-PLAN.md — Backend: schema-scoped HTML templates + live token validation
- [x] 03-02-PLAN.md — Backend: static PDF uploads, local storage, and page-range extraction
- [x] 03-03-PLAN.md — Frontend: content library, template authoring, PDF upload, and manual verification checkpoint

### Phase 4: Visual Designer

**Goal**: Users can visually compose a document design from an ordered sequence of the content pieces built in Phase 3.
**Depends on**: Phase 3
**Requirements**: DESIGN-01, DESIGN-02
**Success Criteria** (what must be TRUE):

  1. User can create a new document design scoped to a chosen document type using a drag-and-drop canvas.
  2. User can add both HTML-template pages and static-PDF pages to the design as an ordered sequence.
  3. User can reorder pages in the canvas, and the resulting order is what persists and is used downstream.

**Plans**: 3 plans
**UI hint**: yes

Plans:

- [x] 04-01-PLAN.md - Backend: document design models, page snapshots, compatibility rules, activation validation (TDD)
- [x] 04-02-PLAN.md - Frontend: document design routes, API client, list/create/detail shell
- [x] 04-03-PLAN.md - Frontend: interactive designer stack, content modals, inspector, activation checkpoint

### Phase 5: Versioning

**Goal**: Users can revise an existing document design without losing prior versions.
**Depends on**: Phase 4
**Requirements**: VERSION-01, VERSION-02
**Success Criteria** (what must be TRUE):

  1. Editing an existing document design creates a new version; the previous version remains intact and retrievable.
  2. User can view the version history of a document design, distinguishing past versions from the current one.

**Plans**: 3 plans
**UI hint**: yes

Plans:

- [x] 05-01-PLAN.md — Backend: versioned document_designs schema, fork/activate/discard APIs, and migration
- [x] 05-02-PLAN.md — Frontend: edit flow, version history page, read-only mode, and API client
- [x] 05-03-PLAN.md — Manual browser verification checkpoint

### Phase 6: Generation & Preview API

**Goal**: External callers can generate a final merged PDF from a document design plus supplied data, and preview a design with mock data without persisting an issuance.
**Depends on**: Phase 5
**Requirements**: GEN-01, GEN-02
**Success Criteria** (what must be TRUE):

  1. Calling the generation API with a document design and caller-supplied data returns a merged final PDF: template tokens filled in, static pages merged in the design's configured order.
  2. Calling the preview API with mock/sample data returns a PDF without creating a persisted issuance record.
  3. The output PDF's page order and content exactly reflects what was configured in the design (dynamic and static pages combined correctly).

**Plans**: 2 plans
**UI hint**: no

Plans:

- [x] 06-01-PLAN.md — Configure backend libraries, document issuance tracking DB schema/migration, and core PDF generator orchestrator
- [x] 06-02-PLAN.md — Integrate FastAPI routes, register routers, and implement integration test coverage

### Phase 7: Backend Core (Nested Data & Case-Insensitive Matching)

**Goal**: Support nested objects, object lists, and case-insensitive payload mapping and Jinja2 rendering on the backend.
**Depends on**: Phase 6
**Requirements**: NEST-01, NEST-02, NEST-03, CASE-01, CASE-02, CASE-03
**Success Criteria** (what must be TRUE):

  1. The API successfully parses and validates Document Type schemas containing nested structures (e.g. `cliente.direccion.calle`) and object lists (e.g. `cliente.contactos[].nombre`).
  2. The PDF generator correctly renders templates containing nested or list tokens using case-insensitive resolving (e.g., `{{Cliente.Direccion.Calle}}` resolves to `cliente.direccion.calle`).
  3. API payload validation detects case-insensitive key collisions (e.g. `Name` and `name`) at any level and rejects requests with a clear `400 Bad Request`.
  4. The PDF generation API rejects payloads with unknown or mismatched field types according to the schema (e.g. passing a string to a nested object field).

**Plans**: 1/1 plans complete

- [x] 07-01-PLAN.md

**UI hint**: no

### Phase 8: Template AST & Static Validation

**Goal**: Analyze template tokens statically via Jinja2 AST parsing and validate them against the Document Type schema before design/template activation.
**Depends on**: Phase 7
**Requirements**: AST-01, AST-02
**Success Criteria** (what must be TRUE):

  1. The backend automatically parses Jinja2 templates using Python's AST (or Jinja2 Environment AST) to extract all referenced token paths (including nested objects and list fields).
  2. The system rejects saving/activation of a template or document design if it references any token paths not present in the Document Type's schema.
  3. Valid template designs containing nested or wildcard array expressions (e.g., `cliente.contactos[].nombre`) pass validation and can be activated successfully.

**Plans**: 1/1 plans complete

- [x] 08-01-PLAN.md

**UI hint**: no

### Phase 9: Search Documents Library & Audit Trace

**Goal**: Implement a search library interface, document detail view, direct download, public share, and detailed activity log (tracelog) timeline for generated issuances.
**Depends on**: Phase 8
**Requirements**: SRCH-01, SRCH-02, SRCH-03, SRCH-04, SRCH-05
**Success Criteria** (what must be TRUE):

  1. Operational users can retrieve and filter past generated issuances using a combination of design name, ID, status (Success/Failure), and date range (AND query).
  2. Selecting an issuance displays its metadata details along with an embedded, interactive preview of the generated PDF document.
  3. Users can download the PDF file directly from the detail view.
  4. Users can copy the public direct URL of the document to the clipboard via a "Share" button.
  5. The details page displays a chronological timeline (audit tracelog) recording creation, download, and share events for that document.

**Plans**: 3 plans
**UI hint**: yes

Plans:
**Wave 1**

- [ ] 09-01-PLAN.md - Backend: DocumentTracelog persistence and generation-event logging

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 09-02-PLAN.md - Backend: issuance search, detail, tracelog, download, share, and signed public download APIs

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 09-03-PLAN.md - Frontend: Documents Library navigation, search listing, detail preview, download, share, and timeline

### Phase 10: Complex Schema UI & Nested Data Previsualization

**Goal**: Enhance the frontend to support visual configuration of complex schemas and interactive previsualization of designs with nested/array mock data.
**Depends on**: Phase 9
**Requirements**: COMPUI-01, COMPUI-02
**Success Criteria** (what must be TRUE):

  1. Operational users can view, add, and manage nested object and list schema properties directly within the Document Types UI form.
  2. The document designer's preview panel supports rendering complex nested and array mock data, allowing users to previsualize layouts before activating the design.

**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Authentication | 8/8 | Complete | 2026-07-07 |
| 2. Document Types | 3/3 | Complete | 2026-07-07 |
| 3. Content Building Blocks | 3/3 | Complete | 2026-07-08 |
| 4. Visual Designer | 3/3 | Complete | 2026-07-07 |
| 5. Versioning | 3/3 | Complete | 2026-07-08 |
| 6. Generation & Preview API | 2/2 | Complete | 2026-07-08 |
| 7. Backend Core (Nested Data & Case-Insensitive Matching) | 1/1 | Complete   | 2026-07-09 |
| 8. Template AST & Static Validation | 1/1 | Complete    | 2026-07-10 |
| 9. Search Documents Library & Audit Trace | 0/3 | Proposed | |
| 10. Complex Schema UI & Nested Data Previsualization | 0/0 | Proposed | |
