# Phase 15: implementar-scopes-prd5-md - Context

**Gathered:** 2026-07-13
**Status:** Ready for planning
**Source:** `.scopes/PRD5.md`

<domain>
## Phase Boundary

This phase adds a reusable page-size selector to the existing frontend `PagedTable` flow. It does not change backend APIs, server-side pagination, persistence, routing, or data fetching contracts.

The phase is complete when:
1. `PagedTable` can optionally expose a page-size selector.
2. `Pagination` renders the selector using the existing reusable `Select` atom.
3. Existing consumers continue to work when no selector props are passed.
4. Static PDFs, Templates, and Document Types use configurable page-size state instead of fixed `PAGE_SIZE` constants.
5. Changing page size resets the current page to `1`.
6. The frontend build passes.
</domain>

<decisions>
## Implementation Decisions

### Component Contract
- Extend `PagedTableProps<T>` with:
  - `pageSizeOptions?: number[]`
  - `onChangePageSize?: (pageSize: number) => void`
- Extend `PaginationProps` with the same optional props.
- Render the selector only when both `pageSizeOptions` and `onChangePageSize` are present.
- Use `frontend/src/components/atoms/Select.tsx`; do not create a new `ComboBox`.
- Keep `pageSize` as the current selected value and `pageSizeOptions` as the selectable list.

### UI Behavior
- Standard options are `[5, 10, 20, 50]`.
- Selector label text should be `Rows per page` to match the existing English `Showing X-Y of Z` pagination copy.
- On selector change, parse the selected value as a number and call `onChangePageSize(nextSize)`.
- The parent page owns `pageSize` state and resets `page` to `1`.

### Consumers
- Update all current `PagedTable` consumers:
  - `frontend/src/pages/content/StaticPdfsPage.tsx`
  - `frontend/src/pages/content/TemplatesPage.tsx`
  - `frontend/src/pages/document-types/DocumentTypeListPage.tsx`
- Replace fixed `PAGE_SIZE` constants with state.
- Keep local `slice` pagination; do not introduce server-side pagination.

### the agent's Discretion
- Exact placement of the selector within the pagination footer, as long as it remains readable on desktop and does not break existing navigation controls.
- Whether to extract `[5, 10, 20, 50]` to a shared constant, provided all three pages use the same options.
</decisions>

<requirements>
## Requirement IDs

- **PAGE-01:** `PagedTable` accepts optional `pageSizeOptions` and `onChangePageSize` without breaking existing callers.
- **PAGE-02:** `Pagination` renders a reusable `Select` page-size control when selector props are provided.
- **PAGE-03:** Static PDFs uses configurable `pageSize` state with options `[5, 10, 20, 50]`.
- **PAGE-04:** Templates uses configurable `pageSize` state with options `[5, 10, 20, 50]`.
- **PAGE-05:** Document Types uses configurable `pageSize` state with options `[5, 10, 20, 50]`.
- **PAGE-06:** Changing page size resets current page to `1` and recalculates the visible range and page buttons.
- **PAGE-07:** Frontend build passes after the component and page updates.
</requirements>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Scope
- `.scopes/PRD5.md` — Full proposal and acceptance criteria.

### Frontend Components
- `frontend/src/components/organisms/PagedTable.tsx` — Reusable table wrapper.
- `frontend/src/components/molecules/Pagination.tsx` — Pagination footer and page controls.
- `frontend/src/components/atoms/Select.tsx` — Existing reusable select atom.

### Current Consumers
- `frontend/src/pages/content/StaticPdfsPage.tsx` — Current `PAGE_SIZE = 8`.
- `frontend/src/pages/content/TemplatesPage.tsx` — Current `PAGE_SIZE = 8`.
- `frontend/src/pages/document-types/DocumentTypeListPage.tsx` — Current `PAGE_SIZE = 10`.
</canonical_refs>

<specifics>
## Specific Ideas

- Prefer a small, backwards-compatible prop extension over a larger table abstraction refactor.
- Keep page-size state at the consuming page level because each page already performs local filtering and slicing.
- Use `setPage(1)` in each `onChangePageSize` handler.
</specifics>

<deferred>
## Deferred Ideas

- Persist selected page size in `localStorage`.
- User-specific page-size defaults.
- Server-side pagination.
- New `ComboBox` component.
- Changing backend API contracts.
</deferred>

---

*Phase: 15-implementar-scopes-prd5-md*
*Context gathered: 2026-07-13 via PRD5 planning*
