# Phase 5: Versioning - Context

**Gathered:** 2026-07-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 5 delivers versioning for document designs: editing an existing (already-activated) document design creates a new version rather than overwriting the current one, and users can view the version history of a design, distinguishing past versions from the current one. This phase covers `VERSION-01` and `VERSION-02`.

Phase 5 reuses the Phase 4 interactive designer (page stack, drag-and-drop, inspector, content modals) unchanged for the actual editing surface — this phase does not redesign the designer canvas, it adds forking/version-tracking around it.

Out of scope for this phase:
- Final PDF generation and preview, which belong to Phase 6.
- Platform-side resolution of external operational data.
- Fine-grained roles/permissions on who can edit or view versions (deferred to v2, see AUTH-02).

</domain>

<decisions>
## Implementation Decisions

### Versioning Start Point
- **D-01:** Versioning only begins after a design's *first activation*. Before that, a design behaves exactly as Phase 4 built it — a single `draft`/`active` record edited directly, no forking, no version history. This matches Phase 4's D-02 ("editing existing designs deferred to Phase 5") and D-04 ("designs have a simple draft/active lifecycle in Phase 4, without version history").
- **D-02:** The moment a design is activated for the first time, that activated state becomes "Version 1 / Current." From then on, clicking "Edit Design" (per the UI-SPEC) forks a new draft version instead of editing the current version directly.

### In-Progress Draft Visibility
- **D-03:** An in-progress, un-activated draft version (created via "Edit Design") appears as a row in the Version History table, using the existing status-pill styling as its "Draft" badge — sorted newest-first alongside "Current" and "Superseded" rows. This extends the UI-SPEC's Version History table (which only explicitly described Current/Superseded rows) to also include the in-flight draft.

### Concurrent Edits
- **D-04:** Only one in-flight draft is allowed per design. If a draft edit is already in progress and the user clicks "Edit Design" again (different tab, or navigating back after leaving), they are taken to the *existing* draft rather than a new one being forked. No blocking error, no duplicate drafts.

### Migrating Existing Phase 4 Data
- **D-05:** Existing designs created before this phase ships map onto the new versioning model as follows: any design currently `active` is treated as if it had just been activated for the first time and becomes "Version 1 / Current." Any design currently `draft` (never activated) stays version-less, consistent with D-01 — no migration needed for those; they continue to be edited directly until their first activation, at which point D-02 applies.

### Claude's Discretion
- Exact database schema shape for storing versions (e.g., new version-tracking table vs. reusing `document_designs` rows with a parent/version-group id) — must satisfy: previous versions remain intact and retrievable (VERSION-01), current version is unambiguous, and migration behavior in D-05 is achievable without a destructive backfill.
- Whether "Activate" (forking a draft into the new current version) is a dedicated endpoint or an update action, as long as: the old current version becomes "Superseded," the draft becomes "Current," and both remain queryable — mirrors the same discretion Phase 4 granted for its own Activate action.
- Concurrency/locking details for the "resume existing draft" behavior (D-04) — no specific mechanism was requested, only the outcome (no duplicate drafts).
- Exact query/index strategy for listing version history newest-first.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project and Requirements
- `.planning/PROJECT.md` — Product vision, core value, and the "document designs are editable with version history" key decision.
- `.planning/REQUIREMENTS.md` — `VERSION-01` and `VERSION-02` requirement definitions.
- `.planning/ROADMAP.md` — Phase 5 goal, dependencies, and success criteria.

### UI Design Contract
- `.planning/phases/05-versioning/05-UI-SPEC.md` — Full visual/interaction contract for this phase: Edit Design/Version History actions, version badges (Current/Superseded/Draft), Version History page layout, read-only past-version view, Discard Draft Version flow, and copywriting contract. Locks the UI this phase must implement; the decisions in this CONTEXT.md fill the gaps the UI-SPEC left open (start point, draft visibility in history table, concurrency, migration).

### Prior Phase Context
- `.planning/phases/04-visual-designer/04-CONTEXT.md` — D-02 ("editing deferred to Phase 5") and D-04 ("draft/active lifecycle without version history in Phase 4") are the direct basis for this phase's D-01/D-02.

### Existing Code
- `backend/app/models/document_design.py` — Current `DocumentDesign`/`DocumentDesignPage` models with `DESIGN_STATUSES = ("draft", "active")` and no version concept yet; this is the schema versioning must extend or wrap.
- `frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx` — Existing detail page with the "Activate" action this phase's "Edit Design"/"Version History" actions extend.
- `frontend/src/pages/document-designs/DocumentDesignListPage.tsx` — Existing table chrome the Version History page's table should reuse (per UI-SPEC).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DocumentDesign` / `DocumentDesignPage` SQLAlchemy models (`backend/app/models/document_design.py`) — current single-record-per-design shape with `status` in `("draft", "active")`; versioning extends this rather than replacing it.
- `DocumentDesignDetailPage.tsx` — the exact designer UI (page stack, drag-and-drop, inspector, Add Template/Add PDF, Activate) that both "Edit Design" drafts and read-only past-version views reuse verbatim per the UI-SPEC.
- `DocumentDesignListPage.tsx` — table chrome (`rounded border border-outline-variant bg-surface-container-lowest`, header row styling) reused for the new Version History table.

### Established Patterns
- Backend API routers live under `backend/app/api/`, protected by `Depends(get_current_user)`.
- SQLAlchemy models under `backend/app/models/`, schemas under `backend/app/schemas/`, Alembic migrations under `backend/alembic/versions/`.
- Frontend pages under `frontend/src/pages/document-designs/`, typed fetch wrappers under `frontend/src/lib/`.

### Integration Points
- New version-related endpoints should sit alongside the existing `document_designs` API surface (list/detail/activate).
- The Version History page is a new route (e.g. `/document-designs/{id}/versions`), reached from the detail page — not a tab, per the UI-SPEC's page-per-route precedent.

</code_context>

<specifics>
## Specific Ideas

- A design's life is in two phases: pre-first-activation (Phase 4 behavior, no versioning) and post-first-activation (Phase 5 behavior, every edit forks a new draft that must be activated to become current).
- "Resume the existing draft" — no duplicate in-flight drafts should ever be creatable for the same design.
- Version History must always show every version that has ever been current or superseded, plus the in-flight draft if one exists — nothing is hidden or deleted, matching VERSION-01's "previous version remains intact and retrievable."

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. Final PDF generation/preview referencing "the current version" remains Phase 6's concern (not addressed here beyond noting current-version resolution must be unambiguous for Phase 6 to build on).

</deferred>

---

*Phase: 05-versioning*
*Context gathered: 2026-07-07*
