# Roadmap: DocManagement Platform

## Overview

The platform is built bottom-up along its natural dependency chain: first gate access behind an external identity provider, then let admins define document types and their schemas, then build the two content primitives (token-scoped HTML templates and uploaded static PDFs) that designs are made of, then deliver the visual drag-and-drop designer that composes those primitives into ordered pages, then add version history so designs can be safely revised, and finally expose the generation and preview API that turns a design plus caller-supplied data into a merged final PDF. Each phase is independently verifiable and unblocks the next.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation & Authentication** - Platform scaffolding with access gated behind OAuth2/OIDC login
- [x] **Phase 2: Document Types** - Admins define document types with their own allowed token/field schemas
- [ ] **Phase 3: Content Building Blocks** - Token-scoped HTML templates and uploaded static PDFs, with schema enforcement
- [ ] **Phase 4: Visual Designer** - Drag-and-drop composition of ordered pages into a document design
- [ ] **Phase 5: Versioning** - Editing a design creates a new version; history is preserved and viewable
- [ ] **Phase 6: Generation & Preview API** - API generates final and preview PDFs from a design plus caller-supplied data

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

Plans:
- [x] 01-01-PLAN.md — Backend sub-project scaffold, Settings, SQLAlchemy models/Alembic, pytest infra
- [x] 01-02-PLAN.md — Docker Compose (Keycloak + Postgres) + Keycloak realm bootstrap
- [x] 01-03-PLAN.md — Frontend Vite/React scaffold + Precision Archival Tailwind design tokens
- [x] 01-04-PLAN.md — Bearer-token JWKS validation + cookie-session dependency
- [x] 01-05-PLAN.md — User upsert-on-login service + session create/delete service
- [x] 01-06-PLAN.md — Authlib OIDC login/callback/logout routes + CORS + protected /api/health
- [x] 01-07-PLAN.md — Frontend Login page + Authenticated Shell wired to backend contract
- [x] 01-08-PLAN.md — Manual end-to-end AUTH-01 verification checkpoint
**UI hint**: yes

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
- [ ] 04-03-PLAN.md - Frontend: interactive designer stack, content modals, inspector, activation checkpoint

### Phase 5: Versioning
**Goal**: Users can revise an existing document design without losing prior versions.
**Depends on**: Phase 4
**Requirements**: VERSION-01, VERSION-02
**Success Criteria** (what must be TRUE):
  1. Editing an existing document design creates a new version; the previous version remains intact and retrievable.
  2. User can view the version history of a document design, distinguishing past versions from the current one.
**Plans**: TBD
**UI hint**: yes

### Phase 6: Generation & Preview API
**Goal**: External callers can generate a final merged PDF from a document design plus supplied data, and preview a design with mock data without persisting an issuance.
**Depends on**: Phase 5
**Requirements**: GEN-01, GEN-02
**Success Criteria** (what must be TRUE):
  1. Calling the generation API with a document design and caller-supplied data returns a merged final PDF: template tokens filled in, static pages merged in the design's configured order.
  2. Calling the preview API with mock/sample data returns a PDF without creating a persisted issuance record.
  3. The output PDF's page order and content exactly reflects what was configured in the design (dynamic and static pages combined correctly).
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Authentication | 8/8 | Complete | 2026-07-07 |
| 2. Document Types | 3/3 | Complete | 2026-07-07 |
| 3. Content Building Blocks | 3/3 | Ready to execute | - |
| 4. Visual Designer | 2/3 | In Progress | - |
| 5. Versioning | 0/TBD | Not started | - |
| 6. Generation & Preview API | 0/TBD | Not started | - |
