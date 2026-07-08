---
phase: 05-versioning
plan: 01
subsystem: api
tags: [postgres, fastapi, sqlalchemy, alembic]

requires: []
provides:
  - Versioned document design database schema and constraints
  - Version fork, activate, list, and discard endpoints
affects: [05-versioning]

tech-stack:
  added: []
  patterns: [partial unique index constraints, row-level schema versioning, database superseding flow]

key-files:
  created: [backend/alembic/versions/0006_document_design_versioning.py]
  modified: [backend/app/models/document_design.py, backend/app/schemas/document_design.py, backend/app/api/document_designs.py, backend/tests/test_document_designs.py]

key-decisions:
  - "Row-per-version design schema extending document_designs with version_group_id and version_number."
  - "Postgres partial unique indexes to guarantee at most one active and one draft version per group."
  - "Exclusively allow modifying design pages (add, update, delete, reorder) on draft designs."
  - "Resume existing draft instead of duplicating when Edit Design is clicked concurrently."

patterns-established:
  - "Draft-only mutation: Raise 400 bad request for mutations on non-draft designs."
  - "Ordered supersede activation: db.flush() old superseded version before setting new version active."

requirements-completed: [VERSION-01, VERSION-02]

coverage:
  - id: D1
    description: "First activation sets version_group_id, version_number = 1, and status = active"
    requirement: "VERSION-01"
    verification:
      - kind: integration
        ref: "backend/tests/test_document_designs.py#test_first_activation_becomes_version_1"
        status: pass
    human_judgment: false
  - id: D2
    description: "Forking clones pages into a new draft without mutating the current version"
    requirement: "VERSION-01"
    verification:
      - kind: integration
        ref: "backend/tests/test_document_designs.py#test_fork_clones_pages_without_mutating_current"
        status: pass
    human_judgment: false
  - id: D3
    description: "Activating a draft supersedes the previous current version"
    requirement: "VERSION-01"
    verification:
      - kind: integration
        ref: "backend/tests/test_document_designs.py#test_activate_draft_supersedes_old_current"
        status: pass
    human_judgment: false
  - id: D4
    description: "A second Edit Design call resumes the existing draft instead of duplicating it"
    requirement: "VERSION-01"
    verification:
      - kind: integration
        ref: "backend/tests/test_document_designs.py#test_fork_resumes_existing_draft"
        status: pass
    human_judgment: false
  - id: D5
    description: "Version history returns newest-first rows for the group, including an in-flight draft"
    requirement: "VERSION-02"
    verification:
      - kind: integration
        ref: "backend/tests/test_document_designs.py#test_version_history_newest_first_includes_draft"
        status: pass
    human_judgment: false
  - id: D6
    description: "Discarding a draft leaves the current version intact"
    requirement: "VERSION-01"
    verification:
      - kind: integration
        ref: "backend/tests/test_document_designs.py#test_discard_draft_leaves_current_intact"
        status: pass
    human_judgment: false
  - id: D7
    description: "Existing active designs migrate to version 1 and never-activated drafts remain version-less"
    requirement: "VERSION-01"
    verification:
      - kind: integration
        ref: "backend/tests/test_document_designs.py#test_migration_backfill_d05"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-07-08
status: complete
---

# Phase 05 Plan 01: Versioned design schema, migration, and API behavior Summary

**Row-per-version design schema using Postgres partial unique indexes, with fork, activate, discard, and history endpoints**

## Performance

- **Duration:** 15 min
- **Started:** 2026-07-08T05:46:17Z
- **Completed:** 2026-07-08T06:01:33Z
- **Tasks:** 1
- **Files modified:** 5

## Accomplishments
- Extended `DocumentDesign` model with versioning columns and partial unique indexes to guarantee database integrity.
- Implemented backend version history and fork-on-edit endpoints.
- Added a non-destructive database migration for existing legacy active designs to become version 1.
- Restructured detail and listing endpoints to be version-aware and resolved grouping query errors in Postgres.

## Task Commits

Each task was committed atomically:

1. **Task 1: Versioned design schema, migration, and API behavior** - `15463a2` (feat)

## Files Created/Modified
- `backend/alembic/versions/0006_document_design_versioning.py` - Alembic migration script
- `backend/app/models/document_design.py` - Document design models with constraints
- `backend/app/schemas/document_design.py` - Pydantic output schemas
- `backend/app/api/document_designs.py` - API routing and endpoints
- `backend/tests/test_document_designs.py` - Integration and migration tests

## Decisions Made
- Used a row-per-version structure inside `document_designs` with a shared `version_group_id` for simplicity and reuse.
- Added `selectinload` optimization to avoid N+1 query issue and resolve PostgreSQL grouping errors.
- Discarding drafts is implemented as design deletion which cascades cleanly to pages.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Solved PostgreSQL GroupingError on listing document designs**
- **Found during:** Running baseline test suite
- **Issue:** `list_document_designs` joined tables using `joinedload` under `GROUP BY` without grouping by the joined primary keys.
- **Fix:** Switched `joinedload` to `selectinload` for related models.
- **Files modified:** `backend/app/api/document_designs.py`
- **Verification:** Full pytest suite passes cleanly
- **Committed in:** `15463a2`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Bug fix was necessary to run integration tests under PostgreSQL. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Versioning backend implementation is complete and verified with regression tests.
- Ready for Phase 05 Plan 02 to implement the frontend user interface for version history and draft actions.

## Self-Check: PASSED
