# Phase 5: Versioning - Research

**Researched:** 2026-07-07
**Domain:** SQLAlchemy 2.0 / PostgreSQL versioning (row-per-version, self-grouping) + FastAPI fork/activate endpoints + React version-history UI
**Confidence:** HIGH (schema/migration approach verified against existing codebase patterns + official SQLAlchemy docs; MEDIUM on exact concurrency edge cases, flagged below)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Versioning only begins after a design's *first activation*. Before that, a design behaves exactly as Phase 4 built it — a single `draft`/`active` record edited directly, no forking, no version history.
- **D-02:** The moment a design is activated for the first time, that activated state becomes "Version 1 / Current." From then on, clicking "Edit Design" forks a new draft version instead of editing the current version directly.
- **D-03:** An in-progress, un-activated draft version (created via "Edit Design") appears as a row in the Version History table, using the existing status-pill styling as its "Draft" badge — sorted newest-first alongside "Current" and "Superseded" rows.
- **D-04:** Only one in-flight draft is allowed per design. If a draft edit is already in progress and the user clicks "Edit Design" again, they are taken to the *existing* draft rather than a new one being forked. No blocking error, no duplicate drafts.
- **D-05:** Existing `active` designs become "Version 1 / Current." Existing `draft` (never activated) designs stay version-less — no migration needed for those; they continue to be edited directly until first activation, at which point D-02 applies.

### Claude's Discretion
- Exact database schema shape for storing versions (new table vs. reusing `document_designs` rows with a parent/version-group id) — must satisfy: previous versions remain intact and retrievable (VERSION-01), current version is unambiguous, and migration behavior in D-05 is achievable without a destructive backfill.
- Whether "Activate" (forking a draft into the new current version) is a dedicated endpoint or an update action, as long as: the old current version becomes "Superseded," the draft becomes "Current," and both remain queryable.
- Concurrency/locking details for the "resume existing draft" behavior (D-04) — no specific mechanism was requested, only the outcome (no duplicate drafts).
- Exact query/index strategy for listing version history newest-first.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. Final PDF generation/preview referencing "the current version" remains Phase 6's concern (not addressed here beyond noting current-version resolution must be unambiguous for Phase 6 to build on).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VERSION-01 | User can edit an existing document design, creating a new version rather than overwriting | Schema design (`version_group_id`/`version_number`/status enum), fork-on-edit endpoint pattern, page-clone mechanics (see Architecture Patterns, Code Examples) |
| VERSION-02 | User can view the version history of a document design | Query/index strategy for group listing newest-first, `GET /{design_id}/versions` endpoint pattern, frontend Version History page pattern (see Architecture Patterns, Code Examples) |
</phase_requirements>

## Summary

Phase 5 should extend the existing `document_designs` table rather than introduce a new versions table. Add two nullable columns — `version_group_id` (UUID) and `version_number` (int) — and extend `DESIGN_STATUSES` from `("draft", "active")` to `("draft", "active", "superseded")`. Each version of a design is its own row in `document_designs`, all sharing the same `version_group_id`. The `status` column doubles as the version-state badge source: `active` = "Current", `superseded` = "Superseded", `draft` = "Draft" (or the pre-Phase-5 unversioned draft, when `version_group_id IS NULL`). This reuses 100% of the existing `DocumentDesign`/`DocumentDesignPage` model shape, the existing cascade/`order_by` relationship pattern, and the existing detail/list API and UI verbatim for each version row — exactly what the UI-SPEC requires ("the exact same `DocumentDesignDetailPage` UI Phase 4 already built").

Two PostgreSQL **partial unique indexes** enforce the two invariants that matter most: at most one `active` row per `version_group_id` (current version is unambiguous — this is *also* what Phase 6 will rely on to resolve "the current version" for generation) and at most one `draft` row per `version_group_id` (D-04, no duplicate in-flight drafts). Both are enforced at the database level, not just in application code, which closes races between concurrent "Edit Design" clicks or double-submits. D-05's migration becomes a single backfill `UPDATE ... SET version_group_id = id, version_number = 1 WHERE status = 'active'` — non-destructive, and `draft` rows are simply left with `NULL` versioning columns, which is exactly the "version-less" semantics D-05 describes.

**Primary recommendation:** Add `version_group_id`/`version_number` columns + `superseded` status to the existing `document_designs` table (no new table), enforce "one active" and "one draft" per group with partial unique indexes (`WHERE status = 'active'` / `WHERE status = 'draft'`), and implement "fork" as a new endpoint that clones the current version's `DocumentDesignPage` rows into a brand-new draft row — reusing the existing model/cascade/snapshot pattern unchanged.

## Standard Stack

### Core (already in use — no new dependencies)
| Library | Version (verified) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | >=2.0.51 (pyproject.toml) | ORM, `Index(..., postgresql_where=...)` for partial indexes | Already the project's ORM; partial-index support via `postgresql_where` is long-stable in the `sqlalchemy.dialects.postgresql` extension |
| Alembic | >=1.18.5 (pyproject.toml) | Schema migrations | Existing hand-written migration pattern (`inspect(op.get_bind())` idempotency guards) in `backend/alembic/versions/0001`–`0005` |
| psycopg (v3, binary) | >=3.3.4 (pyproject.toml) | Postgres driver | Confirmed via `docker-compose.yml`: `DATABASE_URL=postgresql+psycopg://...` — this is a real Postgres 16 instance (`postgres:16` image), not SQLite, so partial indexes and immediate (non-deferred) constraint checking are both fully available |
| FastAPI | >=0.139.0 (pyproject.toml) | API routing | Existing router pattern in `backend/app/api/document_designs.py` |

**No new packages need to be installed for this phase.** Everything required (partial indexes, self-referential grouping, JSON snapshot cloning) is achievable with the stack already in `pyproject.toml`.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Row-per-version in `document_designs` (recommended) | Separate `document_design_versions` table, with `document_designs` becoming a lightweight "group" header row | Cleaner conceptual separation, but duplicates 90% of the existing columns (name, description, document_type_id, pages relationship) into a new table, requires a second FK target for `DocumentDesignPage.design_id`, and adds a migration to move Phase-4 data into the new table structure — strictly more work for no capability the row-per-version approach lacks. Rejected: violates D-05's "no destructive backfill" preference by requiring data to move tables rather than just gaining columns. |
| Partial unique index for "one active/draft per group" | Application-level check-then-insert with explicit row locking (`SELECT ... FOR UPDATE`) | Works, but is strictly weaker than a DB constraint — a bug or a second app instance can still create duplicates. The partial unique index is free correctness; use FOR UPDATE only as a *pre-check* to avoid throwing on the common path (see Concurrency pattern below), not as the sole guard. |
| `version_number` assigned at fork time (recommended) | `version_number` assigned only at activation time | Assigning at activation time leaves in-flight drafts without a version number, but D-03 requires the draft to show a row in the Version History table, and the UI-SPEC's "Version" column and "New draft created from version {n}" copy both need a concrete number to display *before* activation. Fork-time assignment is required to satisfy the UI contract. |

**Installation:** None — no new dependencies.

**Version verification:** All versions above were read directly from `backend/pyproject.toml` (installed versions, not training-data guesses). Postgres engine confirmed via `docker-compose.yml` (`postgres:16`) and `.env.example` (`postgresql+psycopg://...`) — this is authoritative for the current project, not an assumption.

## Architecture Patterns

### Recommended Schema Change
Extend `backend/app/models/document_design.py`:

```python
DESIGN_STATUSES = ("draft", "active", "superseded")
```

Add to `DocumentDesign`:
- `version_group_id: Mapped[uuid.UUID | None]` — `mapped_column(nullable=True, index=True)`. `NULL` = pre-first-activation, unversioned (Phase 4 legacy behavior, per D-05). Once a design is first activated, this is set to the *originating row's own id* — i.e. the first version becomes the permanent "anchor" that every later fork copies forward. This needs no self-referential `ForeignKey` (Postgres doesn't require the referenced row to declare itself specially) — it's just a plain UUID column that happens to equal an `id` that exists in the same table.
- `version_number: Mapped[int | None]` — `mapped_column(nullable=True)`. `NULL` for the same unversioned case; `1, 2, 3, …` once versioning begins. Assigned once, at fork time (or at first-activation for version 1), and never changed again for that row.

Two partial unique indexes (added via `__table_args__` and mirrored in the Alembic migration):

```python
from sqlalchemy import Index

__table_args__ = (
    CheckConstraint(f"status IN {DESIGN_STATUSES!r}", name="ck_document_design_status"),
    Index(
        "uq_document_design_one_active_per_group",
        "version_group_id",
        unique=True,
        postgresql_where=text("status = 'active' AND version_group_id IS NOT NULL"),
    ),
    Index(
        "uq_document_design_one_draft_per_group",
        "version_group_id",
        unique=True,
        postgresql_where=text("status = 'draft' AND version_group_id IS NOT NULL"),
    ),
)
```

**Source:** SQLAlchemy official docs (PostgreSQL dialect, "Partial Indexes" section) confirm `postgresql_where` on `Index(...)` combined with `unique=True` generates `CREATE UNIQUE INDEX ... WHERE <predicate>` — https://docs.sqlalchemy.org/en/20/dialects/postgresql.html (verified via WebFetch during this research session; the WebSearch tool was unavailable due to a gateway error, so this is the sole external verification — cross-check the generated DDL locally with `alembic upgrade` + `\d document_designs` before relying on it further).

**Why NULL is safe for uniqueness:** Postgres never treats two `NULL`s as equal for uniqueness purposes (standard SQL semantics), so multiple pre-Phase-5 `draft` rows with `version_group_id IS NULL` can coexist even without the explicit `AND version_group_id IS NOT NULL` clause — the clause is included purely for documentation/readability, not because it changes behavior.

**Why `status` alone can carry the version badge:** `active` → "Current", `superseded` → "Superseded", `draft` (with `version_group_id` set) → "Draft" badge (reusing the exact `text-primary` status-pill class already in `DocumentDesignDetailPage.tsx`, per the UI-SPEC). No separate `is_current` boolean or `version_state` enum is needed — the existing `status` field already carries this exactly, extended with one new value.

### Pattern: Fork (Edit Design → new draft)
**What:** Clone the current version's `DocumentDesignPage` rows into a brand-new `DocumentDesign` draft row within the same `version_group_id`.
**When to use:** `POST /api/document-designs/{design_id}/versions` (new endpoint) — called when the user clicks "Edit Design" on a *current* (`active`) version.
**Example:**
```python
# Source: pattern derived from existing backend/app/api/document_designs.py
# (create_document_design + add_template_page use the same DocumentDesign/
# DocumentDesignPage construction style)
from sqlalchemy.exc import IntegrityError

@router.post("/{design_id}/versions", response_model=DocumentDesignDetail, status_code=201)
def fork_document_design_version(
    design_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignDetail:
    current = _require_design(db, design_id)
    if current.status != "active":
        raise HTTPException(status_code=400, detail="Only the current version can be edited")

    group_id = current.version_group_id or current.id  # first fork off a pre-Phase-5 active row

    # D-04: resume existing draft if one is already in flight (cheap indexed lookup)
    existing_draft = (
        db.query(DocumentDesign)
        .filter(DocumentDesign.version_group_id == group_id, DocumentDesign.status == "draft")
        .first()
    )
    if existing_draft is not None:
        return _detail(existing_draft)

    next_version = (
        db.query(func.max(DocumentDesign.version_number))
        .filter(DocumentDesign.version_group_id == group_id)
        .scalar() or 0
    ) + 1

    draft = DocumentDesign(
        document_type_id=current.document_type_id,
        name=current.name,
        description=current.description,
        status="draft",
        version_group_id=group_id,
        version_number=next_version,
        created_by=user,
    )
    # Deep-copy pages — never reassign existing page rows, that would rewrite history.
    for page in sorted(current.pages, key=lambda p: p.position):
        draft.pages.append(
            DocumentDesignPage(
                block_type=page.block_type,
                content_id=page.content_id,
                position=page.position,
                title=page.title,
                notes=page.notes,
                config=dict(page.config or {}),
                snapshot=dict(page.snapshot or {}),
            )
        )
    db.add(draft)
    try:
        db.commit()
    except IntegrityError:
        # Race: another request forked first — fall back to their draft.
        db.rollback()
        existing_draft = (
            db.query(DocumentDesign)
            .filter(DocumentDesign.version_group_id == group_id, DocumentDesign.status == "draft")
            .first()
        )
        if existing_draft is not None:
            return _detail(existing_draft)
        raise
    db.refresh(draft)
    return _detail(draft)
```

**Critical pitfall called out explicitly:** Never do `page.design = draft` on an *existing* `DocumentDesignPage` object to "move" it into the new draft — that mutates the current version's own pages in place (since `design_id` is a real FK column) and would corrupt the version you're supposed to be preserving. Always construct **new** `DocumentDesignPage` objects with copied scalar/JSON field values.

### Pattern: Activate a draft version (draft → current, old current → superseded)
```python
@router.post("/{design_id}/activate", response_model=DocumentDesignDetail)
def activate_document_design(
    design_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignDetail:
    design = _require_design(db, design_id)
    validate_design_activation(design, db)

    if design.version_group_id is None:
        # First-ever activation (Phase 4 legacy path, D-02): becomes Version 1.
        design.version_group_id = design.id
        design.version_number = 1
        design.status = "active"
    else:
        # Forked draft becoming current: order matters for the partial unique index —
        # supersede the old current BEFORE activating the draft, in the same transaction,
        # so there is never a moment with two 'active' rows in the same group.
        old_current = (
            db.query(DocumentDesign)
            .filter(DocumentDesign.version_group_id == design.version_group_id, DocumentDesign.status == "active")
            .first()
        )
        if old_current is not None:
            old_current.status = "superseded"
            db.flush()  # apply the supersede UPDATE before the activate UPDATE
        design.status = "active"

    db.commit()
    return _detail(_require_design(db, design_id))
```

**Why `db.flush()` between the two status changes matters:** PostgreSQL checks a (non-deferred, default) unique index immediately after each row-level UPDATE, not only at COMMIT. If both UPDATEs are sent in a way that lets Postgres see "old=active, new=active" simultaneously even briefly within the same statement batch, the partial unique index will reject it. Flushing the supersede first guarantees the intermediate state (0 active rows) is valid before the second UPDATE runs. This is a genuine pitfall specific to this schema design — call it out in the plan's verification steps.

### Pattern: Version History query (VERSION-02)
```python
@router.get("/{design_id}/versions", response_model=list[DocumentDesignListItem])
def list_document_design_versions(
    design_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> list[DocumentDesignListItem]:
    anchor = _require_design(db, design_id)
    group_id = anchor.version_group_id or anchor.id
    designs = (
        db.query(DocumentDesign)
        .options(joinedload(DocumentDesign.document_type), joinedload(DocumentDesign.created_by), selectinload(DocumentDesign.pages))
        .filter(DocumentDesign.version_group_id == group_id)
        .order_by(DocumentDesign.version_number.desc())
        .all()
    )
    return [... same DocumentDesignListItem construction as list_document_designs ...]
```
Sort by `version_number DESC`, not `created_at DESC` — `version_number` is monotonic and assigned exactly once per row, so it has no tie-breaking ambiguity that timestamp collisions could introduce. The existing `ix_document_designs_version_group_id` index (plain, non-unique) makes the `WHERE version_group_id = :group_id` filter indexed; `version_number` does not need its own index since result sets per group are small (bounded by edit count, not overall table size).

### Recommended Project Structure (no new top-level folders)
```
backend/app/
├── models/document_design.py       # extend: DESIGN_STATUSES, version_group_id, version_number, 2 partial unique indexes
├── schemas/document_design.py      # extend: DocumentDesignListItem/Detail gain version_number, version_group_id (or omit group id from API surface — see Open Questions)
├── api/document_designs.py         # extend: POST /{id}/versions (fork), GET /{id}/versions (history), DELETE /{id} or POST /{id}/discard (discard draft), extend POST /{id}/activate
└── services/design_validation.py   # unchanged — validate_design_activation already applies per-row, works unchanged for draft rows

frontend/src/
├── lib/documentDesigns.ts          # extend: forkDesignVersion(), listDesignVersions(), discardDraftVersion(), DocumentDesignListItem gains version_number/version state
└── pages/document-designs/
    ├── DocumentDesignDetailPage.tsx   # extend: Edit Design / Version History buttons, read-only past-version mode, Discard Draft Version modal
    └── VersionHistoryPage.tsx         # NEW — mirrors DocumentDesignListPage.tsx's fetch/table pattern
```

### Anti-Patterns to Avoid
- **New `document_design_versions` table:** Rejected above — duplicates the pages relationship and existing snapshot logic for no benefit; the row-per-version approach with a group id is the standard "type-2 slowly changing dimension" pattern and fits this codebase's existing model shape exactly.
- **`is_current` boolean instead of extending `status`:** Would require keeping two fields in sync (`status` and `is_current`) and risks them disagreeing. The 3-value `status` enum is a single source of truth and reuses the UI's existing status-pill rendering unchanged.
- **Assigning `version_number` at activation time:** Breaks D-03 (draft must show a version number in the history table before it's activated).
- **Reassigning existing `DocumentDesignPage` rows to a new design instead of cloning:** Silently mutates/deletes history from the version being forked from.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| "Only one active/draft row per group" invariant | Application-level locking, cron cleanup job, or a `SELECT COUNT(*)` check-then-insert without a DB constraint | PostgreSQL partial unique index (`Index(..., unique=True, postgresql_where=...)`) | Race-proof at the database layer; the app-level check-then-insert is still useful as an optimization to avoid throwing on the common path, but must not be the only guard |
| Version ordering | A separate "is this the latest" recomputation pass | Monotonic `version_number` assigned once, sorted `DESC` | No ties, no recomputation, trivial to reason about |
| Draft page content | Manually diffing/patching the current version's pages in-place with an "edit mode" flag | Full clone of `DocumentDesignPage` rows into a new draft `DocumentDesign` row | Matches D-02 exactly ("clicking Edit Design forks a new draft version") and is simpler than tracking dirty/undo state across a shared row |

**Key insight:** The core hand-rolled risk in this phase is concurrency (two browser tabs both hitting "Edit Design" for the same design). The fix is not more application logic — it's a two-line database constraint plus a documented fallback path for the resulting `IntegrityError`.

## Common Pitfalls

### Pitfall 1: Partial unique index violated transiently during activation
**What goes wrong:** If the "old current → superseded" and "new draft → active" updates are not flushed in the correct order within the same transaction, Postgres can reject the second UPDATE because it briefly sees two `active` rows for the same group.
**Why it happens:** Postgres checks non-deferred unique indexes per-statement, not per-transaction — but ORM code that builds both changes in-memory and lets SQLAlchemy's autoflush batch them in an unexpected order can still trigger this.
**How to avoid:** Explicitly `db.flush()` after setting the old row to `superseded`, before setting the new row to `active` (see Code Examples above).
**Warning signs:** `IntegrityError: duplicate key value violates unique constraint "uq_document_design_one_active_per_group"` on the activate endpoint specifically (not on fork).

### Pitfall 2: Shallow-copying JSON columns during fork
**What goes wrong:** `config` and `snapshot` are `JSON` columns backed by Python `dict`s. If a forked page is constructed by reference (e.g. `config=page.config` without `dict(...)`) rather than by value, mutating the draft's page config later can, depending on SQLAlchemy's JSON change-tracking, also mark the *original* page's row as dirty, since both point at the same dict object in memory.
**Why it happens:** SQLAlchemy's `JSON` type does not do deep-copy-on-read by default.
**How to avoid:** Always `dict(page.config or {})` / `dict(page.snapshot or {})` when cloning (shown in the fork code example).
**Warning signs:** Editing a draft's page inspector fields appears to also change the "Superseded" version's read-only view of the same field.

### Pitfall 3: Forgetting the pre-Phase-5 legacy `draft`/`active` rows have `version_group_id IS NULL`
**What goes wrong:** Any new endpoint (fork, version-history list, activate) that assumes `version_group_id` is always populated will 500 or silently return nothing for designs created before this migration ships (or for any design still in its pre-first-activation Phase 4 state).
**Why it happens:** D-05 intentionally leaves those rows version-less — this is correct behavior, not a data-quality bug, but code must handle it explicitly (`group_id = design.version_group_id or design.id`).
**How to avoid:** Every new query/endpoint that resolves "the group" must fall back to the row's own `id` when `version_group_id is None`, exactly as shown in the fork/history code examples.
**Warning signs:** Version History or Edit Design working for newly-created designs in tests but breaking against seed/production data created before the phase shipped.

### Pitfall 4: "Discard Draft Version" needs its own endpoint, not the generic page-delete flow
**What goes wrong:** The UI-SPEC's "Discard Draft Version" action removes an entire in-flight draft `DocumentDesign` row (with its pages, via existing `cascade="all, delete-orphan"`), which is a different operation from `DELETE /{design_id}/pages/{page_id}` (removes one page from a design). Conflating them risks accidentally exposing draft-deletion through the wrong endpoint or forgetting to validate `status == "draft"` before allowing deletion (a "Current"/"Superseded" row must never be deletable).
**How to avoid:** Add a dedicated `DELETE /api/document-designs/{design_id}` (or `POST /{design_id}/discard`) that raises 400 unless `design.status == "draft"`.
**Warning signs:** A "Current" version becomes deletable through the API even though the UI never exposes a button for it — always enforce this in the backend, not just by hiding the button.

## Code Examples

See Architecture Patterns above for the full fork / activate / version-history endpoint bodies — all derived directly from the existing style in `backend/app/api/document_designs.py` (same `_require_design`, `_detail`, `joinedload`/`selectinload` query pattern).

### Frontend: `documentDesigns.ts` additions (follows existing `jsonOrError`/`apiFetch` convention exactly)
```typescript
// Source: pattern matches existing functions in frontend/src/lib/documentDesigns.ts
export async function forkDesignVersion(designId: string): Promise<DocumentDesignDetail> {
  return jsonOrError(
    await apiFetch(`/api/document-designs/${designId}/versions`, { method: "POST" }),
  );
}

export async function listDesignVersions(designId: string): Promise<DocumentDesignListItem[]> {
  return jsonOrError(await apiFetch(`/api/document-designs/${designId}/versions`));
}

export async function discardDraftVersion(designId: string): Promise<void> {
  const res = await apiFetch(`/api/document-designs/${designId}`, { method: "DELETE" });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(readErrorMessage(body, res.status));
  }
}
```

### Frontend: Version History page fetch pattern (mirrors `DocumentDesignListPage.tsx` exactly)
```tsx
// Source: pattern copied from frontend/src/pages/document-designs/DocumentDesignListPage.tsx
const [versions, setVersions] = useState<DocumentDesignListItem[] | null>(null);
useEffect(() => {
  let cancelled = false;
  listDesignVersions(id).then((data) => { if (!cancelled) setVersions(data); })
    .catch(() => { if (!cancelled) setError(true); });
  return () => { cancelled = true; };
}, [id]);
```
Route registration follows `frontend/src/App.tsx`'s existing flat `<Route path="document-designs/:id">` style — add `<Route path="document-designs/:id/versions" element={<VersionHistoryPage />} />`.

## Runtime State Inventory

Not applicable — Phase 5 is additive (new columns, new indexes, new endpoints, new routes). It is not a rename/refactor/migration-of-identifiers phase. The one genuine "existing data" concern (D-05's backfill of `active` rows into "Version 1") is a straightforward, non-destructive `UPDATE` covered in the Architecture Patterns / migration section above, not a runtime-state audit.

## Common Pitfalls
(see above — merged into the single Common Pitfalls section)

## State of the Art

| Old Approach (Phase 4) | Current Approach (Phase 5) | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `document_designs.status IN ('draft', 'active')`, one row = one design, editing not supported | `status IN ('draft', 'active', 'superseded')`, one row = one *version*, grouped by `version_group_id` | This phase | Existing `GET /{id}` and `activate` endpoints keep working unchanged for any design that has never been forked; the group/version concept is purely additive |
| `POST /{id}/activate` unconditionally sets `status = 'active'` | Same endpoint, now branches on whether `version_group_id` is already set (first activation vs. draft-becomes-current) | This phase | Must extend, not replace, `activate_document_design` — the existing 04-era tests for the simple draft→active path should keep passing untouched |

**Deprecated/outdated:** None — this is additive to Phase 4's schema, not a replacement.

## Open Questions

1. **Should `version_group_id` be exposed on the API/frontend types, or kept purely internal?**
   - What we know: The UI never needs to display a group id (only version numbers and Current/Superseded/Draft badges).
   - What's unclear: Whether the frontend needs the group id at all (e.g. to build the "Version History" link URL) — currently the recommended endpoint shape (`/{design_id}/versions`, using *any* version's id in the group) sidesteps needing the group id client-side entirely.
   - Recommendation: Do not add `version_group_id` to `DocumentDesignListItem`/`DocumentDesignDetail` response schemas unless a concrete frontend need appears during planning; keep `version_number` and `status` (Current/Superseded/Draft badge source) as the only new API-visible fields.

2. **Does "View" on a Superseded row need a distinct read-only route, or does the existing detail route just render differently based on `status`?**
   - What we know: UI-SPEC says "View" opens that version read-only, or the live designer if it's current — same `DocumentDesignDetailPage` component, different props/mode based on `design.status`.
   - What's unclear: Exact prop-driven vs. route-driven toggle mechanism (not specified in CONTEXT.md, left to planner/executor).
   - Recommendation: Reuse the same `/document-designs/:id` route for all statuses; `DocumentDesignDetailPage` derives read-only mode from `design.status !== "active"` fetched from the API — no new route needed beyond `/document-designs/:id/versions`.

3. **Does `validate_design_activation` need any change for draft-version activation?**
   - What we know: It already validates name/document_type/pages/token-compatibility per-row, which is identical for a forked draft row.
   - What's unclear: Whether token-compatibility should also be re-checked against the *current* schema (in case the document type's schema changed since the version was forked) — this is implicitly already true since `validate_design_activation` re-reads `design.document_type.fields` live.
   - Recommendation: No change needed to `design_validation.py`; it already re-validates against live schema state on every activation call, which is the desired behavior for new versions too.

## Environment Availability

Skipped — this phase has no new external dependencies (no new packages, no new services). Postgres 16 and the existing Python/Node toolchain (already verified running in this repo via `docker-compose.yml` and `pyproject.toml`/`package.json`) are the only runtime requirements, and they are already in place for Phases 1–4.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend) — version pinned via `backend/.venv`; config at `backend/pyproject.toml` `[tool.pytest.ini_options]` |
| Config file | `backend/pyproject.toml` (`testpaths = ["tests"]`, `pythonpath = ["."]`) |
| Quick run command | `cd backend && pytest tests/test_document_designs.py -x` |
| Full suite command | `cd backend && pytest` |

**Frontend:** No test framework configured yet (no `vitest`/`jest` in `frontend/package.json`, no `*.test.tsx` files found). Frontend verification for this phase should remain manual/visual (per the UI-SPEC checker workflow), consistent with Phases 1–4.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VERSION-01 | Activating a design for the first time sets version_group_id/version_number=1/status=active | unit/integration | `pytest tests/test_document_designs.py::test_first_activation_becomes_version_1 -x` | ❌ Wave 0 |
| VERSION-01 | Forking (Edit Design) clones pages into a new draft row, current version untouched | integration | `pytest tests/test_document_designs.py::test_fork_clones_pages_without_mutating_current -x` | ❌ Wave 0 |
| VERSION-01 | Activating a draft supersedes the old current, both remain queryable | integration | `pytest tests/test_document_designs.py::test_activate_draft_supersedes_old_current -x` | ❌ Wave 0 |
| VERSION-01 | D-04: second "Edit Design" call resumes the existing draft, no duplicate created | integration | `pytest tests/test_document_designs.py::test_fork_resumes_existing_draft -x` | ❌ Wave 0 |
| VERSION-01 | D-05: migration backfills active rows to version 1, leaves never-activated drafts version-less | migration/integration | `pytest tests/test_document_designs.py::test_migration_backfill_d05 -x` (or a dedicated `tests/test_migrations.py`) | ❌ Wave 0 |
| VERSION-02 | Version history lists all versions of a group, newest-first, including the in-flight draft | integration | `pytest tests/test_document_designs.py::test_version_history_newest_first_includes_draft -x` | ❌ Wave 0 |
| VERSION-02 | Discard draft removes the draft row and its pages, current version untouched | integration | `pytest tests/test_document_designs.py::test_discard_draft_leaves_current_intact -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && pytest tests/test_document_designs.py -x`
- **Per wave merge:** `cd backend && pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_document_designs.py` — extend with the 7 test cases above (file exists, needs new tests appended; existing `_auth_client`/`_create_document_type`/`_create_template`/`_create_static_pdf_asset` fixtures in this file are directly reusable)
- [ ] Alembic migration `backend/alembic/versions/0006_document_design_versioning.py` — new file, following the exact `inspect(op.get_bind())` idempotency-guard style of `0004`/`0005`
- [ ] No new fixtures needed in `backend/tests/conftest.py` — existing `db_session`/`client`/`_auth_client` fixtures cover this phase's needs

## Sources

### Primary (HIGH confidence)
- `backend/app/models/document_design.py`, `backend/app/api/document_designs.py`, `backend/app/schemas/document_design.py` — existing shipped code, read directly this session
- `backend/alembic/versions/0004_static_pdf_assets.py`, `0005_document_designs.py` — existing migration style precedent, read directly this session
- `backend/pyproject.toml`, `docker-compose.yml`, `.env.example` — confirmed exact dependency versions and Postgres 16 as the real engine (not SQLite), read directly this session
- SQLAlchemy official docs, PostgreSQL dialect "Partial Indexes" section (https://docs.sqlalchemy.org/en/20/dialects/postgresql.html) — verified via WebFetch this session; confirms `Index(..., postgresql_where=...)` syntax

### Secondary (MEDIUM confidence)
- PostgreSQL partial unique index semantics (NULL-not-equal-NULL, per-statement constraint checking rather than deferred) — this is standard, long-stable PostgreSQL behavior consistent with training knowledge, but could not be independently re-verified this session because the WebSearch tool returned repeated `502` gateway errors (see below). Recommend a quick local sanity check (`\d document_designs` after migration, plus the two-active-rows-race test in Wave 0) before relying on it in production.

### Tertiary (LOW confidence / tool unavailable)
- WebSearch tool was unavailable this session (`API Error: 502 ... Unable to safely convert buffered response to SSE`, repeated across 3 attempts). No community/ecosystem cross-verification of the partial-unique-index pattern was possible beyond the one official-docs WebFetch above. If the planner or executor wants additional confirmation, retry WebSearch for "postgresql partial unique index sqlalchemy" or consult the PostgreSQL manual directly (https://www.postgresql.org/docs/current/indexes-partial.html).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all versions read directly from `pyproject.toml`/`docker-compose.yml`
- Architecture (schema/fork/activate pattern): HIGH — directly extends existing, shipped model/API code; partial-unique-index syntax confirmed via official docs WebFetch
- Concurrency edge cases (flush ordering, NULL semantics): MEDIUM — standard well-established PostgreSQL behavior, but WebSearch cross-verification was unavailable this session; flagged explicitly for a Wave 0 test to confirm empirically against the real Postgres 16 instance
- Pitfalls: HIGH — derived from concrete code-reading of the JSON column / cascade relationship behavior already present in this codebase

**Research date:** 2026-07-07
**Valid until:** 30 days (stable stack, no fast-moving dependencies involved)
