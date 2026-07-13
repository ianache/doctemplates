# Roadmap: DocManagement Platform

## Milestones

- ✅ **v1.0 MVP** — Phases 1-6 (shipped 2026-07-08)
- ✅ **v2.0 Nested Objects & Case-Insensitive Templates** — Phases 7-10 (shipped 2026-07-11)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-6) — SHIPPED 2026-07-08</summary>

- [x] Phase 1: Foundation & Authentication (8/8 plans) — completed 2026-07-07
- [x] Phase 2: Document Types (3/3 plans) — completed 2026-07-07
- [x] Phase 3: Content Building Blocks (3/3 plans) — completed 2026-07-08
- [x] Phase 4: Visual Designer (3/3 plans) — completed 2026-07-07
- [x] Phase 5: Versioning (3/3 plans) — completed 2026-07-08
- [x] Phase 6: Generation & Preview API (2/2 plans) — completed 2026-07-08

</details>

<details>
<summary>✅ v2.0 Nested Objects & Case-Insensitive Templates (Phases 7-10) — SHIPPED 2026-07-11</summary>

- [x] Phase 7: Backend Core (Nested Data & Case-Insensitive Matching) (1/1 plan) — completed 2026-07-09
- [x] Phase 8: Template AST & Static Validation (1/1 plan) — completed 2026-07-10
- [x] Phase 9: Search Documents Library & Audit Trace (3/3 plans) — completed 2026-07-11
- [x] Phase 10: Complex Schema UI & Nested Data Previsualization (5/5 plans) — completed 2026-07-11

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation & Authentication | v1.0 | 8/8 | Complete | 2026-07-07 |
| 2. Document Types | v1.0 | 3/3 | Complete | 2026-07-07 |
| 3. Content Building Blocks | v1.0 | 3/3 | Complete | 2026-07-08 |
| 4. Visual Designer | v1.0 | 3/3 | Complete | 2026-07-07 |
| 5. Versioning | v1.0 | 3/3 | Complete | 2026-07-08 |
| 6. Generation & Preview API | v1.0 | 2/2 | Complete | 2026-07-08 |
| 7. Backend Core (Nested Data & Case-Insensitive Matching) | v2.0 | 1/1 | Complete | 2026-07-09 |
| 8. Template AST & Static Validation | v2.0 | 1/1 | Complete | 2026-07-10 |
| 9. Search Documents Library & Audit Trace | v2.0 | 3/3 | Complete | 2026-07-11 |
| 10. Complex Schema UI & Nested Data Previsualization | v2.0 | 5/5 | Complete | 2026-07-11 |

### Phase 11: Necesito introducir un componente bff entre frontend y backend aislando la logica del core en el backend

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 10
**Plans:** 1/1 plans complete

Plans:

- [x] 11-01-PLAN.md

- [x] TBD (run /gsd-plan-phase 11 to break down) (completed 2026-07-12)

### Phase 12: implementar la propuesta de atomic design

**Goal:** Implement formal hybrid Atomic Design pattern across frontend components, extracting form atoms and reorganizing modules into molecules and organisms.
**Requirements:** ATOMIC-01, ATOMIC-02, ATOMIC-03, ATOMIC-04
**Depends on:** Phase 11
**Plans:** 4/4 plans complete

Plans:

- [x] 12-01-PLAN.md — Reorganize global PageHeader and extract form atoms (InputText, Select, Checkbox)
- [x] 12-02-PLAN.md — Move DesignPageCard, TokenExplorer, and HtmlJinjaEditor to subfolders under document-designs/components/
- [x] 12-03-PLAN.md — Move AddContentModal, DesignPageInspector, MockDataPanel, and PreviewFrame to document-designs/components/organisms/
- [x] 12-04-PLAN.md — Move SchemaFieldEditor and SchemaMetadataEditor to document-types/components/organisms/

### Phase 13: implementar la propuesta de separacion de almacenamiento

**Goal:** Decouple file storage in the backend by introducing a StorageProvider abstraction supporting local filesystem and S3-compatible providers (MinIO, Oracle Object Storage).
**Requirements:** STORAGE-01, STORAGE-02, STORAGE-03, STORAGE-04
**Depends on:** Phase 12
**Plans:** 5/5 plans executed

Plans:

- [x] 13-01-PLAN.md — Rename stored_path/file_path to storage_key in DB and generate migration.
- [x] 13-02-PLAN.md — Define StorageProvider interface, LocalStorageProvider and update config.py.
- [x] 13-03-PLAN.md — Refactor content_storage.py, pdf_generator.py and API routers to consume StorageProvider.
- [x] 13-04-PLAN.md — Implement S3StorageProvider using boto3 and add environment variables.
- [x] 13-05-PLAN.md — Create test_storage_providers.py and verify all backend tests pass.

### Phase 14: implementar .scopes\PRD4.md

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 13
**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 14 to break down)
