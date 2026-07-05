# Requirements: DocManagement Platform

**Defined:** 2026-07-05
**Core Value:** Operational users can visually compose a document design (templates + fixed content, in order) and reliably generate a correct final PDF from it via API, without engineering involvement per document type.

## v1 Requirements

Requirements for initial release (MVP1). Each maps to roadmap phases.

### Document Types

- [ ] **DOCTYPE-01**: Admin/operational user can define a new document type with its own allowed data schema (tokens/fields)
- [ ] **DOCTYPE-02**: User can list/view existing document types and their schemas

### Designer

- [ ] **DESIGN-01**: User can visually design a document (drag-and-drop canvas) by composing an ordered sequence of pages, scoped to a chosen document type
- [ ] **DESIGN-02**: User can reorder pages in the designer; the resulting order is preserved through to generation

### Content

- [ ] **CONTENT-01**: A page can be a dynamic HTML template containing tokens restricted to the document type's allowed schema
- [ ] **CONTENT-02**: A page can be a static PDF (or a specific page extracted from one), uploaded through the UI
- [ ] **CONTENT-03**: Uploaded static PDFs are stored by the platform and referenceable by document designs

### Versioning

- [ ] **VERSION-01**: User can edit an existing document design, creating a new version rather than overwriting
- [ ] **VERSION-02**: User can view the version history of a document design

### Generation

- [ ] **GEN-01**: API generates a final merged PDF from a document design + caller-supplied data (fills template tokens, merges pages in order)
- [ ] **GEN-02**: API generates a preview PDF from mock/sample data without persisting an issuance record

### Validation

- [ ] **VALID-01**: Using a token outside a document type's allowed schema is rejected with a clear error (e.g. 400 Bad Request) rather than silently ignored or leaking data

### Auth

- [ ] **AUTH-01**: Multi-user access is gated behind an OAuth2/OIDC login flow (generic identity provider integration, not custom-built credentials)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Data Integration

- **DATA-01**: Platform resolves token data from external systems by reference ID, instead of requiring the API caller to supply all data directly

### Output

- **OUTPUT-01**: Support non-PDF output formats

### Access Control

- **AUTH-02**: Fine-grained roles/permissions per document type or design (beyond basic authenticated access)

## Out of Scope

Explicitly excluded from MVP1. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Platform-side resolution of real operational data | MVP1 requires the API caller to supply all data directly; external data integration is deferred (see DATA-01) |
| Non-PDF output formats | MVP1 is PDF-only (see OUTPUT-01) |
| Hardcoded Sales Channel / Service (B2C Básico vs B2B Flota) business rule | Becomes an example document type configured through the general DOCTYPE mechanism, not bespoke code |
| Custom-built auth (email/password, owned credentials) | MVP1 integrates an existing OAuth2/OIDC identity provider instead |

## Traceability

Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DOCTYPE-01 | TBD | Pending |
| DOCTYPE-02 | TBD | Pending |
| DESIGN-01 | TBD | Pending |
| DESIGN-02 | TBD | Pending |
| CONTENT-01 | TBD | Pending |
| CONTENT-02 | TBD | Pending |
| CONTENT-03 | TBD | Pending |
| VERSION-01 | TBD | Pending |
| VERSION-02 | TBD | Pending |
| GEN-01 | TBD | Pending |
| GEN-02 | TBD | Pending |
| VALID-01 | TBD | Pending |
| AUTH-01 | TBD | Pending |

**Coverage:**
- v1 requirements: 13 total
- Mapped to phases: 0
- Unmapped: 13 ⚠️ (roadmap not yet created)

---
*Requirements defined: 2026-07-05*
*Last updated: 2026-07-05 after initial definition*
