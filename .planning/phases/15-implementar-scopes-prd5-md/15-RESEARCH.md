# Phase 15: implementar-scopes-prd5-md - Research

**Researched:** 2026-07-14  
**Domain:** React/TypeScript frontend pagination component extension  
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

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

### Deferred Ideas (OUT OF SCOPE)

## Deferred Ideas

- Persist selected page size in `localStorage`.
- User-specific page-size defaults.
- Server-side pagination.
- New `ComboBox` component.
- Changing backend API contracts.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PAGE-01 | `PagedTable` accepts optional `pageSizeOptions` and `onChangePageSize` without breaking existing callers. | Existing `PagedTableProps<T>` has a narrow pagination pass-through contract and can be extended with optional props. [VERIFIED: codebase grep] |
| PAGE-02 | `Pagination` renders a reusable `Select` page-size control when selector props are provided. | Existing `Select` atom wraps native `<select>` and accepts standard select attributes, so it can be used for numeric option values serialized as strings. [VERIFIED: codebase grep] |
| PAGE-03 | Static PDFs uses configurable `pageSize` state with options `[5, 10, 20, 50]`. | Static PDFs currently uses fixed `PAGE_SIZE = 8` for local `slice`, so state must replace the constant in the slice and `PagedTable` props. [VERIFIED: codebase grep] |
| PAGE-04 | Templates uses configurable `pageSize` state with options `[5, 10, 20, 50]`. | Templates currently uses fixed `PAGE_SIZE = 8` for local `slice`, so state must replace the constant in the slice and `PagedTable` props. [VERIFIED: codebase grep] |
| PAGE-05 | Document Types uses configurable `pageSize` state with options `[5, 10, 20, 50]`. | Document Types currently uses fixed `PAGE_SIZE = 10` for local `slice`, so state must replace the constant in the slice and `PagedTable` props. [VERIFIED: codebase grep] |
| PAGE-06 | Changing page size resets current page to `1` and recalculates the visible range and page buttons. | `Pagination` derives `totalPages`, `startIdx`, `endIdx`, and page buttons from `page`, `pageSize`, and `total`; parent page reset is sufficient when page size changes. [VERIFIED: codebase grep] |
| PAGE-07 | Frontend build passes after the component and page updates. | `frontend/package.json` defines `npm run build` as `tsc -b && vite build`. [VERIFIED: codebase grep] |
</phase_requirements>

## Summary

Phase 15 should be implemented as a small backwards-compatible frontend component extension. `PagedTable` already delegates all footer behavior to `Pagination`; therefore `PagedTable` should only accept two new optional props and pass them through. `Pagination` should own only the rendering and event adaptation for the page-size selector, while each page continues to own pagination state and local data slicing. [VERIFIED: codebase grep]

The current data flow is entirely local: pages fetch full arrays, apply filters in `useMemo`, slice the filtered array using the current page and fixed page size, then pass sliced rows plus `total={filtered.length}` to `PagedTable`. The implementation must preserve that flow and only make page size configurable. [VERIFIED: codebase grep]

**Primary recommendation:** add optional page-size props to `PagedTable` and `Pagination`, render the existing `Select` atom inside `Pagination` only when both selector props exist, then update the three known consumers to use `pageSize` state and reset `page` to `1` on page-size changes. [CITED: .planning/phases/15-implementar-scopes-prd5-md/15-CONTEXT.md]

## Project Constraints (from AGENTS.md)

- No `AGENTS.md` file exists at repository root during this research run. [VERIFIED: shell Test-Path/read attempt]
- The prompt supplied AGENTS instructions requiring shell commands to be prefixed with `rtk`; planning and verification commands should preserve that convention. [CITED: user-provided AGENTS.md instructions]
- Application code must not be modified during research. [CITED: user prompt]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Page-size selector rendering | Browser / Client | - | The selector is a React UI control inside the existing pagination footer. [VERIFIED: codebase grep] |
| Page-size state | Browser / Client | - | Existing pagination state lives in page components via `useState`; no server or router state is involved. [VERIFIED: codebase grep] |
| Filtered result slicing | Browser / Client | - | Current consumers slice in `useMemo` after local filtering. [VERIFIED: codebase grep] |
| Backend pagination | - | - | Backend pagination is explicitly out of scope for this phase. [CITED: .scopes/PRD5.md] |

## Current Pagination/Data-Slicing Flow

| File | Current page-size source | Filter source | Slicing flow | `PagedTable` input |
|------|--------------------------|---------------|--------------|--------------------|
| `frontend/src/pages/content/StaticPdfsPage.tsx` | Local constant `PAGE_SIZE = 8` inside component. [VERIFIED: codebase grep] | `filteredPdfs` memo filters loaded PDF assets by filename, document type, and upload date. [VERIFIED: codebase grep] | `start = (page - 1) * PAGE_SIZE`, then `filteredPdfs.slice(start, start + PAGE_SIZE)`. [VERIFIED: codebase grep] | `rows={paginatedPdfs}`, `pageSize={PAGE_SIZE}`, `total={filteredPdfs.length}`. [VERIFIED: codebase grep] |
| `frontend/src/pages/content/TemplatesPage.tsx` | Local constant `PAGE_SIZE = 8` inside component. [VERIFIED: codebase grep] | `filteredTemplates` memo filters loaded templates by keyword, document type, and creator. [VERIFIED: codebase grep] | `start = (page - 1) * PAGE_SIZE`, then `filteredTemplates.slice(start, start + PAGE_SIZE)`. [VERIFIED: codebase grep] | `rows={paginatedTemplates}`, `pageSize={PAGE_SIZE}`, `total={filteredTemplates.length}`. [VERIFIED: codebase grep] |
| `frontend/src/pages/document-types/DocumentTypeListPage.tsx` | Module constant `PAGE_SIZE = 10`. [VERIFIED: codebase grep] | `filtered` memo filters loaded document types by query. [VERIFIED: codebase grep] | `filtered?.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)`. [VERIFIED: codebase grep] | `rows={paged ?? []}`, `pageSize={PAGE_SIZE}`, `total={total}`. [VERIFIED: codebase grep] |

`PagedTable` currently renders a table, optional empty state, and a `Pagination` footer. It passes `page`, `pageSize`, `total`, `itemName`, and `onChangePage` directly to `Pagination`; it does not compute pages or slice rows. [VERIFIED: codebase grep]

`Pagination` currently computes `totalPages = Math.max(1, Math.ceil(total / pageSize))`, `startIdx`, `endIdx`, and `pages = buildPageList(page, totalPages)` from props. This means the selector only needs to update parent `pageSize`; the existing footer computations will recalculate automatically. [VERIFIED: codebase grep]

## Existing Reusable Component Patterns and Styling Constraints

- `Select` is a global atom at `frontend/src/components/atoms/Select.tsx`; it extends `SelectHTMLAttributes<HTMLSelectElement>`, accepts `children`, forwards rest props, and merges `className` with `cn`. [VERIFIED: codebase grep]
- `Select` defaults to `w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none`. Pagination should override width with a constrained class such as `w-auto` or `min-w-[...]` so the footer selector does not occupy the whole footer. [VERIFIED: codebase grep]
- `Pagination` uses Tailwind utility constants for button dimensions and existing design tokens such as `border-outline-variant`, `bg-surface-container-low`, `text-secondary`, `text-on-surface`, and `text-on-primary`. New selector markup should reuse those tokens and avoid introducing a one-off visual system. [VERIFIED: codebase grep]
- `Pagination` footer is currently `flex items-center justify-between`; adding a selector increases horizontal content. Use a responsive structure such as `flex flex-col gap-sm sm:flex-row sm:items-center sm:justify-between` or a compact left-side range/selector group to avoid overlap on narrow widths. [VERIFIED: codebase grep]
- Existing page filters use native `<select>` controls directly, but Phase 15 specifically requires the pagination selector to use the reusable `Select` atom. [VERIFIED: codebase grep] [CITED: .scopes/PRD5.md]

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | `^19.2.7` | Component state and rendering. [VERIFIED: frontend/package.json] | Existing frontend stack already uses React pages and reusable components. [VERIFIED: codebase grep] |
| TypeScript | `~6.0.2` | Typed component props and build-time contract checks. [VERIFIED: frontend/package.json] | Existing build runs `tsc -b` before Vite. [VERIFIED: frontend/package.json] |
| Vite | `^8.1.1` | Frontend bundling. [VERIFIED: frontend/package.json] | Existing `npm run build` uses Vite after TypeScript. [VERIFIED: frontend/package.json] |
| Tailwind CSS | `^3.4.19` | Utility styling for atoms, molecules, organisms, and pages. [VERIFIED: frontend/package.json] | Existing components are styled with Tailwind utility classes and project design tokens. [VERIFIED: codebase grep] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Existing `Select` atom | Local component | Page-size select control. [VERIFIED: codebase grep] | Use inside `Pagination`; do not add package or new `ComboBox`. [CITED: .scopes/PRD5.md] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Existing `Select` atom | New `ComboBox` | Explicitly out of scope and unnecessary for fixed numeric options. [CITED: .scopes/PRD5.md] |
| Local slicing | Server-side pagination | Explicitly out of scope and would change backend/data-fetching contracts. [CITED: .planning/phases/15-implementar-scopes-prd5-md/15-CONTEXT.md] |
| Parent-owned state | Internal `PagedTable` state | Would conflict with existing page-owned `page` state and make filtering/page reset harder to reason about. [VERIFIED: codebase grep] |

**Installation:** no external package installation is required. [VERIFIED: frontend/package.json]

## Package Legitimacy Audit

No new external packages are recommended for Phase 15, so package legitimacy checks are not applicable. [VERIFIED: local research scope]

## Architecture Patterns

### System Architecture Diagram

```text
Fetched full list
      |
      v
Page component state
  - filters
  - page
  - pageSize
      |
      v
filteredRows = useMemo(full list + applied filters)
      |
      v
visibleRows = filteredRows.slice((page - 1) * pageSize, page * pageSize)
      |
      v
PagedTable
  - renders rows
  - delegates footer props
      |
      v
Pagination
  - computes visible range
  - computes page buttons
  - renders Select when pageSizeOptions + onChangePageSize exist
      |
      v
onChangePageSize(nextSize)
      |
      v
Parent page sets pageSize and resets page to 1
```

### Recommended Project Structure

```text
frontend/src/components/atoms/
└── Select.tsx                 # existing reusable select atom
frontend/src/components/molecules/
└── Pagination.tsx             # render selector and pagination controls
frontend/src/components/organisms/
└── PagedTable.tsx             # pass optional selector props through
frontend/src/pages/content/
├── StaticPdfsPage.tsx         # page-owned pageSize state
└── TemplatesPage.tsx          # page-owned pageSize state
frontend/src/pages/document-types/
└── DocumentTypeListPage.tsx   # page-owned pageSize state
```

### Pattern 1: Optional Prop Pass-Through

**What:** Add optional props to `PagedTableProps<T>` and pass them directly to `Pagination`. [VERIFIED: codebase grep]  
**When to use:** Use for component capabilities that are purely footer concerns and must not change existing callers. [CITED: .planning/phases/15-implementar-scopes-prd5-md/15-CONTEXT.md]

```tsx
// Source: existing PagedTable delegation pattern + Phase 15 context
<Pagination
  page={page}
  pageSize={pageSize}
  total={total}
  itemName={itemName}
  onChangePage={onChangePage}
  pageSizeOptions={pageSizeOptions}
  onChangePageSize={onChangePageSize}
/>
```

### Pattern 2: Parent-Owned Page Size

**What:** Each consumer owns `pageSize` with `useState`, uses it for local slicing, and resets `page` when it changes. [CITED: .scopes/PRD5.md]

```tsx
// Source: PRD5 proposed behavior
const [page, setPage] = useState(1);
const [pageSize, setPageSize] = useState(8);

const handleChangePageSize = (nextSize: number) => {
  setPageSize(nextSize);
  setPage(1);
};
```

### Pattern 3: Controlled Select Value Conversion

**What:** Render numeric options as string-compatible `<option value={option}>` values, then parse `event.target.value` before calling the numeric callback. [CITED: .scopes/PRD5.md]

```tsx
// Source: PRD5 proposed behavior and existing Select atom contract
<Select
  value={String(pageSize)}
  onChange={(event) => onChangePageSize(Number(event.target.value))}
>
  {pageSizeOptions.map((option) => (
    <option key={option} value={option}>
      {option}
    </option>
  ))}
</Select>
```

### Anti-Patterns to Avoid

- **Adding internal pagination state to `PagedTable`:** current consumers already own the state and slice rows before rendering. [VERIFIED: codebase grep]
- **Showing selector when only one optional prop is present:** locked behavior says render only when both `pageSizeOptions` and `onChangePageSize` exist. [CITED: .planning/phases/15-implementar-scopes-prd5-md/15-CONTEXT.md]
- **Changing fetch/API contracts:** backend pagination is out of scope. [CITED: .scopes/PRD5.md]
- **Creating `ComboBox`:** explicitly out of scope. [CITED: .scopes/PRD5.md]
- **Leaving fixed `PAGE_SIZE` in dependency arrays:** once page size is state, memo dependencies must use `pageSize`; keeping a constant reference would produce TypeScript/lint or stale logic problems. [VERIFIED: codebase grep]

## Recommended Plan Boundaries/Waves

| Wave | Scope | Files | Acceptance Focus |
|------|-------|-------|------------------|
| Wave 1 | Extend reusable components only. | `PagedTable.tsx`, `Pagination.tsx` | Backwards-compatible optional props; selector hidden unless both props exist; `Select` atom used. [CITED: .planning/phases/15-implementar-scopes-prd5-md/15-CONTEXT.md] |
| Wave 2 | Update page consumers. | `StaticPdfsPage.tsx`, `TemplatesPage.tsx`, `DocumentTypeListPage.tsx` | Replace fixed constants with `pageSize` state; pass standard options; reset page to `1` on page-size change. [CITED: .scopes/PRD5.md] |
| Wave 3 | Verification and polish. | No intended app-code expansion beyond fixes found by verification. | Build passes; manual checks confirm visible rows, range text, buttons, and reset behavior on all three pages. [CITED: .scopes/PRD5.md] |

Keep the phase as one frontend plan or at most two small plans. Splitting each consumer into separate plans would add coordination overhead without reducing risk because all three pages share the same mechanical state/slice update. [ASSUMED]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Select input UI | New `ComboBox` or custom dropdown | Existing `Select` atom | The phase explicitly requires the existing atom and the option set is simple. [CITED: .scopes/PRD5.md] |
| Pagination math | New pagination algorithm | Existing `Pagination` `totalPages`, range, and `buildPageList` logic | Current logic already computes range and page buttons from `pageSize`. [VERIFIED: codebase grep] |
| Server pagination | New backend query params/endpoints | Existing local `slice` | Backend contract changes are out of scope. [CITED: .planning/phases/15-implementar-scopes-prd5-md/15-CONTEXT.md] |
| Preference persistence | `localStorage` or user settings | In-memory page state only | Persistence is deferred. [CITED: .scopes/PRD5.md] |

**Key insight:** this phase is a controlled-prop extension, not a table abstraction rewrite. [VERIFIED: codebase grep]

## Common Pitfalls

### Pitfall 1: Footer Layout Overlap

**What goes wrong:** Adding the selector to the existing `justify-between` footer can crowd the range text and page buttons on narrow content areas. [VERIFIED: codebase grep]  
**Why it happens:** The current footer assumes exactly two horizontal groups. [VERIFIED: codebase grep]  
**How to avoid:** Group range text and selector together, constrain `Select` width, and allow wrapping or a column layout at small breakpoints. [ASSUMED]  
**Warning signs:** Range text, selector, or navigation buttons overlap or compress unreadably during manual browser checks. [ASSUMED]

### Pitfall 2: Backwards Compatibility Regression

**What goes wrong:** Existing or future callers without page-size props could see an empty selector area or TypeScript-required prop failures. [CITED: .planning/phases/15-implementar-scopes-prd5-md/15-CONTEXT.md]  
**Why it happens:** New props are accidentally made required or selector rendering checks only one prop. [ASSUMED]  
**How to avoid:** Mark props optional in both interfaces and render the selector only when `pageSizeOptions && onChangePageSize`. [CITED: .planning/phases/15-implementar-scopes-prd5-md/15-CONTEXT.md]  
**Warning signs:** `tsc -b` complains about missing props, or old table usage renders partial page-size UI. [ASSUMED]

### Pitfall 3: Page Not Reset After Size Change

**What goes wrong:** A user on a high page changes to a larger page size and remains on a now-invalid page, producing an empty or confusing visible slice. [CITED: .scopes/PRD5.md]  
**Why it happens:** The selected `page` state is independent from `pageSize` state in the parent page. [VERIFIED: codebase grep]  
**How to avoid:** Each consumer's `onChangePageSize` handler must call `setPageSize(nextSize)` and `setPage(1)`. [CITED: .scopes/PRD5.md]  
**Warning signs:** After changing page size from page 2 or later, the range does not start from item 1. [ASSUMED]

### Pitfall 4: Filtered Results and Page Size Drift

**What goes wrong:** Filtering changes the total rows while page size changes independently, causing range text or page buttons to represent stale assumptions. [VERIFIED: codebase grep]  
**Why it happens:** Filters and page size both affect the valid page range but are handled in separate state paths. [VERIFIED: codebase grep]  
**How to avoid:** Preserve existing filter handlers that reset `page` to `1`; add the same reset to page-size handlers. [VERIFIED: codebase grep]  
**Warning signs:** Applying a filter after changing page size leaves the table on page 2+ or shows `Showing` ranges outside the filtered total. [ASSUMED]

### Pitfall 5: TypeScript Select Value Mismatch

**What goes wrong:** `Select` receives a numeric `value` or emits a string that is passed directly into a numeric state setter/callback. [CITED: .scopes/PRD5.md]  
**Why it happens:** Native select values are strings, while `pageSize` and callback props are typed as `number`. [ASSUMED]  
**How to avoid:** Convert selected values with `Number(event.target.value)` and keep callback types numeric. [CITED: .scopes/PRD5.md]  
**Warning signs:** `tsc -b` type errors, page-size state becomes a string, or slice math behaves unexpectedly. [ASSUMED]

## Code Examples

### Pagination Selector Rendering

```tsx
// Source: Phase 15 context + existing Select atom
const showPageSizeSelector = pageSizeOptions && onChangePageSize;

{showPageSizeSelector ? (
  <label className="flex items-center gap-sm text-body-sm text-secondary">
    <span>Rows per page</span>
    <Select
      className="w-auto min-w-[4.5rem] bg-white"
      value={String(pageSize)}
      onChange={(event) => onChangePageSize(Number(event.target.value))}
    >
      {pageSizeOptions.map((option) => (
        <option key={option} value={option}>
          {option}
        </option>
      ))}
    </Select>
  </label>
) : null}
```

### Consumer Page Size State

```tsx
// Source: PRD5 proposed behavior adapted to current page-owned slicing
const PAGE_SIZE_OPTIONS = [5, 10, 20, 50];
const [page, setPage] = useState(1);
const [pageSize, setPageSize] = useState(8);

const paginatedRows = useMemo(() => {
  const start = (page - 1) * pageSize;
  return filteredRows.slice(start, start + pageSize);
}, [filteredRows, page, pageSize]);

<PagedTable
  page={page}
  pageSize={pageSize}
  pageSizeOptions={PAGE_SIZE_OPTIONS}
  onChangePageSize={(nextSize) => {
    setPageSize(nextSize);
    setPage(1);
  }}
/>
```

## State of the Art

| Old Approach | Current Approach for Phase 15 | When Changed | Impact |
|--------------|-------------------------------|--------------|--------|
| Fixed `PAGE_SIZE` constants in each consumer. [VERIFIED: codebase grep] | Parent-owned `pageSize` state with shared option list. [CITED: .scopes/PRD5.md] | Phase 15 | User can control visible rows without duplicating selector UI per page. [CITED: .scopes/PRD5.md] |
| `Pagination` only changes page number. [VERIFIED: codebase grep] | `Pagination` also renders a controlled `Select` when optional props are supplied. [CITED: .planning/phases/15-implementar-scopes-prd5-md/15-CONTEXT.md] | Phase 15 | Existing callers continue to work; enhanced callers get page-size control. [CITED: .planning/phases/15-implementar-scopes-prd5-md/15-CONTEXT.md] |

**Deprecated/outdated:**
- Fixed page-size constants in the three current consumers should be replaced by state for this phase. [CITED: .scopes/PRD5.md]

## Runtime State Inventory

This is not a rename, rebrand, refactor, string replacement, or migration phase; runtime state inventory is not required. [CITED: .planning/phases/15-implementar-scopes-prd5-md/15-CONTEXT.md]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Node.js | Frontend build | Yes | `v22.23.1` | None needed. [VERIFIED: shell command] |
| npm | Frontend build | Yes | `11.9.0` | None needed. [VERIFIED: shell command] |
| Graphify context | Optional graph research | No | Disabled / no graph file | Use direct code inspection. [VERIFIED: shell command] |
| GSD phase init query | Optional phase metadata discovery | No | Current `gsd-sdk` lacks `query` command | Use provided phase path and context files. [VERIFIED: shell command] |

**Missing dependencies with no fallback:** none for implementation. [VERIFIED: shell command]

**Missing dependencies with fallback:** graphify and `gsd-sdk query init.phase-op` were unavailable; local code and phase context files were sufficient. [VERIFIED: shell command]

## Validation Architecture

`workflow.nyquist_validation` is explicitly `false` in `.planning/config.json`, so the formal validation architecture section is intentionally skipped. [VERIFIED: .planning/config.json]

## Concrete Verification Commands

Run these after implementation:

```powershell
rtk proxy powershell -NoProfile -Command "Set-Location frontend; npm run build"
```

Optional focused static checks:

```powershell
rtk rg "pageSizeOptions|onChangePageSize|PAGE_SIZE" frontend/src/components frontend/src/pages
```

```powershell
rtk proxy powershell -NoProfile -Command "Set-Location frontend; npm run lint"
```

Manual verification checklist:

- Static PDFs: switch page size among `5`, `10`, `20`, and `50`; visible row count, `Showing X-Y of Z`, and page buttons update. [CITED: .scopes/PRD5.md]
- Templates: repeat the same page-size checks after applying at least one filter. [CITED: .scopes/PRD5.md]
- Document Types: navigate to page 2 if enough rows exist, change page size, and confirm page resets to `1`. [CITED: .scopes/PRD5.md]
- Existing behavior: remove or omit selector props in a local review scenario and confirm `PagedTable` still renders without the selector. [CITED: .planning/phases/15-implementar-scopes-prd5-md/15-CONTEXT.md]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Keep the phase as one frontend plan or at most two small plans. | Recommended Plan Boundaries/Waves | Planner may split too coarsely or too finely, but implementation remains straightforward. |
| A2 | Responsive footer wrapping is the safest layout approach. | Common Pitfalls | A different exact layout may still be acceptable if manual UI checks pass. |
| A3 | TypeScript build will catch numeric/string mismatch for page-size callbacks. | Common Pitfalls | Runtime testing may be needed if a type escape hides the mismatch. |

## Open Questions

1. **Should the `[5, 10, 20, 50]` options live in a shared constant file?**
   - What we know: the context allows either local or shared extraction if all three pages use the same options. [CITED: .planning/phases/15-implementar-scopes-prd5-md/15-CONTEXT.md]
   - What's unclear: there is no existing shared pagination constants module. [VERIFIED: codebase grep]
   - Recommendation: use a small local constant in each page or export a component-level constant only if an existing constants pattern is found during implementation. [ASSUMED]

## Security Domain

Phase 15 does not alter authentication, authorization, backend access, secrets, storage, or user-supplied HTML/PDF processing. Primary security risk is low and limited to preserving existing client-side behavior. [VERIFIED: phase scope]

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | No | No auth contract changes. [CITED: .planning/phases/15-implementar-scopes-prd5-md/15-CONTEXT.md] |
| V3 Session Management | No | No session changes. [CITED: .planning/phases/15-implementar-scopes-prd5-md/15-CONTEXT.md] |
| V4 Access Control | No | No API or permission changes. [CITED: .planning/phases/15-implementar-scopes-prd5-md/15-CONTEXT.md] |
| V5 Input Validation | Minimal | Convert select value to number from fixed options. [CITED: .scopes/PRD5.md] |
| V6 Cryptography | No | No cryptography changes. [CITED: .planning/phases/15-implementar-scopes-prd5-md/15-CONTEXT.md] |

## Sources

### Primary (HIGH confidence)

- `.planning/PROJECT.md` - project scope, active stack, validated requirements. [VERIFIED: file read]
- `.planning/ROADMAP.md` - phase sequencing and Phase 15 addition. [VERIFIED: file read]
- `.planning/STATE.md` - current project state and prior component extraction decisions. [VERIFIED: file read]
- `.planning/phases/15-implementar-scopes-prd5-md/15-CONTEXT.md` - locked implementation decisions and requirement IDs. [VERIFIED: file read]
- `.scopes/PRD5.md` - product behavior, acceptance criteria, verification command, and out-of-scope boundaries. [VERIFIED: file read]
- `frontend/src/components/organisms/PagedTable.tsx` - current reusable table contract and pagination delegation. [VERIFIED: file read]
- `frontend/src/components/molecules/Pagination.tsx` - current footer, page range, and page button logic. [VERIFIED: file read]
- `frontend/src/components/atoms/Select.tsx` - reusable select atom contract and styling. [VERIFIED: file read]
- `frontend/src/pages/content/StaticPdfsPage.tsx` - current fixed page size and local slicing. [VERIFIED: file read]
- `frontend/src/pages/content/TemplatesPage.tsx` - current fixed page size and local slicing. [VERIFIED: file read]
- `frontend/src/pages/document-types/DocumentTypeListPage.tsx` - current fixed page size and local slicing. [VERIFIED: file read]
- `frontend/package.json` - build command and frontend package versions. [VERIFIED: file read]
- `.planning/config.json` - validation workflow setting. [VERIFIED: file read]

### Secondary (MEDIUM confidence)

- `rtk rg "<PagedTable|PAGE_SIZE|pageSizeOptions|onChangePageSize" frontend/src` - confirmed only the three named consumers currently use `PagedTable`/fixed `PAGE_SIZE` in scope. [VERIFIED: codebase grep]
- Shell probes for Node/npm availability. [VERIFIED: shell command]

### Tertiary (LOW confidence)

- No external web or package ecosystem sources were needed because this phase adds no dependencies and relies on local React components. [VERIFIED: local research scope]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - verified from `frontend/package.json`.
- Architecture: HIGH - verified from local component/page flow.
- Pitfalls: MEDIUM - primary risks are derived from verified local code plus expected UI/state behavior.
- Plan boundaries: HIGH - phase scope and target files are explicitly locked in `15-CONTEXT.md` and `.scopes/PRD5.md`.

**Research date:** 2026-07-14  
**Valid until:** 2026-08-13

## RESEARCH COMPLETE
