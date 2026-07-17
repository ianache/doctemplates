# Issuance Data Export And Audit Table Design

## Goal

Improve the document issuance detail screen by removing the bulky inline `Input Data` block, adding an explicit `Download Data` workflow, and moving `Audit Timeline` into a full-width `PagedTable` below the generated document viewer and right-side detail panel.

## Current Context

- `DocumentIssuanceDetailPage` currently renders:
  - Generated document preview/workbook state in the main left column.
  - `IssuanceProperties`, optional `Document Metadata`, `Input Data`, and `Audit Timeline` in the right sidebar.
- `Input Data` is shown as a large JSON `<pre>`, which consumes sidebar space and competes with higher-value document context.
- `Audit Timeline` is currently an ordered vertical list. It is useful audit data but becomes harder to scan as events grow.
- `PagedTable` already exists as a shared frontend table component and is used by catalog/list pages.
- Tracelogs are already fetched through `getDocumentTracelogs(id)` and held in `tracelogs` state.

## Approved UX Direction

The detail page will keep the document viewer and right-side details in the main grid, then render `Audit Timeline` as a full-width table beneath that entire grid.

The visible `Input Data` panel will be removed. Its content will move behind a new `Download Data` action in the page header.

## Header Actions

The existing actions will become:

- `Download PDF` or `Download XLSX`, preserving current output-format-aware label behavior.
- `Download Data`, new.
- `Share`, preserving current behavior.

`Download Data` opens a modal instead of downloading immediately.

## Download Data Modal

The modal will let the user select which data sections to export:

- `input_data`, selected by default.
- `metadata_values`, unselected by default.
- `tracelogs`, unselected by default.

Rules:

- If no option is selected, the modal download button is disabled.
- If exactly one option is selected, the browser downloads one JSON file:
  - `input_data.json`
  - `metadata_values.json`
  - `tracelogs.json`
- If more than one option is selected, the browser downloads a ZIP file containing one JSON file per selected section.
- JSON files are pretty-printed with two-space indentation.
- The ZIP filename is `issuance-<id>-data.zip`.
- Single-section JSON filenames are exactly `input_data.json`, `metadata_values.json`, or `tracelogs.json`.

Implementation preference:

- Generate exports in the frontend from already-loaded `detail` and `tracelogs`.
- Add a small ZIP library only if the project does not already have one.
- Do not add a backend export endpoint in this iteration.

## Audit Timeline Table

`Audit Timeline` moves out of the right sidebar and into a full-width section below the main grid.

The section uses `PagedTable<DocumentTracelog>`.

Columns:

- `Event`: human label using existing `EVENT_LABELS`, falling back to `event_type`.
- `Date`: `created_at` formatted with the existing `formatDate`.
- `Actor`: `User` when `user_id` exists, otherwise `Anonymous`.
- `User ID`: shortened visually, full value available via `title`.
- `Metadata`: compact text summary of `log.metadata` using existing `metadataValue` behavior for nested values.

Pagination:

- Use local state in `DocumentIssuanceDetailPage`.
- Default page size: 5.
- `rows` passed to `PagedTable` are the current page slice.
- `total` is `tracelogs.length`.

Empty state:

- If no tracelogs exist, render an empty state inside the table block: `No tracelog events recorded.`

## Right Sidebar After Change

The right sidebar contains only compact, high-value detail panels:

- `IssuanceProperties`.
- `Document Metadata`, only when `metadata_values` exists and has keys.

The sidebar no longer renders the `Input Data` JSON block or the audit timeline.

## Error Handling

- Existing page-level `error` and `notice` behavior remains.
- `Download Data` handles Blob/download failures by setting a modal-local error.
- If ZIP generation fails, show a clear error and keep the modal open.
- If `tracelogs` failed to load, the `tracelogs` checkbox remains enabled and exports the currently loaded `tracelogs` state, which may be an empty list. This avoids adding a separate loading/error state in this iteration.

## Testing And Verification

Required verification:

- Frontend build passes.
- `DocumentIssuanceDetailPage` no longer renders the visible `Input Data` block.
- `Download Data` modal opens with only `input_data` selected.
- One selected section downloads one JSON file.
- Multiple selected sections download one ZIP with independent JSON files.
- `Audit Timeline` renders with `PagedTable` below the main grid and paginates when event count exceeds page size.
- Existing download/share behavior remains unchanged.

Manual smoke path:

1. Open an issuance detail page.
2. Confirm document preview/workbook state is unchanged.
3. Confirm right sidebar contains properties and metadata only.
4. Use `Download Data` with default selection and inspect `input_data.json`.
5. Select all three sections and inspect the ZIP entries.
6. Confirm audit logs appear in the full-width table below the viewer.

## Out Of Scope

- Backend export endpoint.
- Server-side ZIP generation.
- Changes to tracelog API shape.
- Adding filters/search to audit logs.
- Persisting the user's last data export selection.
