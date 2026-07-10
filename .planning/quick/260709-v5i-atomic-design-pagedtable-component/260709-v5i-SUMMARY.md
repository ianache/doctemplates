---
status: complete
quick_id: 260709-v5i
slug: atomic-design-pagedtable-component
description: Atomic Design PagedTable component
date: 2026-07-10
---

# Quick Task 260709-v5i: Atomic Design PagedTable component

## Result

Applied Atomic Design to `frontend/src/components/` and delivered a reusable, externally-controlled `PagedTable` organism matching the table in `.design/mvp2/search_repository.html`. Refactored `DocumentTypeListPage` to consume it.

## Commits

| Commit | Description |
|--------|-------------|
| 8fc67ee | feat(ui): add atomic design atoms (Icon, Button, Badge, StatusDot) |
| 205caf0 | feat(ui): add PagedTable organism with controlled pagination |
| 8c7e421 | refactor(doc-types): use PagedTable in DocumentTypeListPage |
| d1d9746 | refactor(ui): move cn helper to lib/cn for fast-refresh compliance |

## Files Created

- `frontend/src/components/atoms/Icon.tsx` — Material Symbols icon wrapper
- `frontend/src/components/atoms/Button.tsx` — variant-driven button (primary/secondary/ghost/danger)
- `frontend/src/components/atoms/Badge.tsx` — tag/chip label
- `frontend/src/components/atoms/StatusDot.tsx` — colored status dot + label (signed/draft/archived)
- `frontend/src/components/molecules/Pagination.tsx` — controlled pagination footer with numbered + prev/next buttons
- `frontend/src/components/molecules/TableHeader.tsx` — generic thead from column defs
- `frontend/src/components/organisms/PagedTable.tsx` — generic `<T>`-parametric table + pagination, fully controlled (no internal state)
- `frontend/src/lib/cn.ts` — class-name join helper (extracted to satisfy oxlint fast-refresh rule)

## Files Refactored

- `frontend/src/pages/document-types/DocumentTypeListPage.tsx` — replaced manual `<table>/<thead>/<tbody>/pagination` markup with `<PagedTable>`; added `page` state + client-side slice.

## Decisions Honored

- **D-01 Atomic Design scope:** atoms/molecules/organisms hierarchy created.
- **D-02 Controlled pagination:** `PagedTable` receives `page`, `pageSize`, `total`, `rows`, `onChangePage` — zero `useState`/`useEffect` inside the organism.
- **D-03 Refactor:** `DocumentTypeListPage` now renders via `PagedTable`.

## Notable Design Calls

- **Skipped `TableRow.tsx` molecule** — a generic TableRow adds indirection without value; `PagedTable` renders `<tbody>` rows directly via each column's `render(row)` function. Documented in PLAN.md.
- **`cn` helper moved to `lib/cn.ts`** (deviation from plan's "put cn in Icon.tsx") — oxlint's `react(only-export-components)` rule warned when Icon.tsx exported both a component and a function; moving `cn` to its own utility file resolves the warning cleanly.
- **`Column` type defined in `PagedTable.tsx`**, imported by `TableHeader` via `import type` (erased at compile, no runtime circular dependency).
- **`PagedTable` declared as `function PagedTable<T>`** (not arrow) so it can be generic with a default export.

## Verification

- `npx tsc -b` — passes for all quick-task files (one unrelated pre-existing error in `DocumentLibraryPage.tsx` from 09-02 work, not touched by this task).
- `npm run lint` — 0 warnings, 0 errors.
- Manual: table renders with same styling as before refactor; pagination footer shows "Showing X-Y of N document types"; page nav updates visible rows; search resets to page 1.
