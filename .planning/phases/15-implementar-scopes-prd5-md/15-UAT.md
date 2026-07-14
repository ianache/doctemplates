---
status: complete
phase: 15-implementar-scopes-prd5-md
source: [15-VERIFICATION.md]
started: 2026-07-14T03:45:00Z
updated: 2026-07-14T03:45:00Z
---

# Phase 15 UAT: PagedTable Page Size Selector

## Current Test

[testing complete]

## Tests

### 1. Static PDFs rows-per-page browser flow

expected: |
  Open Static PDFs. Confirm the Rows per page selector is visible. Change the
  selector between 5, 10, 20, and 50. Confirm visible row count changes when
  enough rows exist, the range text updates, page buttons recalculate, and
  previous/next navigation still works.
result: issue
reported: "Pages selector la  'Rows per page' must be in a single line before dropdown (select)"
severity: cosmetic

### 2. Templates rows-per-page browser flow with filters

expected: |
  Open Templates. Apply at least one filter. Confirm the Rows per page selector
  is visible. Change the selector between 5, 10, 20, and 50. Confirm visible
  row count changes when enough rows exist, the range text updates, page
  buttons recalculate, and previous/next navigation still works.
result: pass

### 3. Document Types page reset browser flow

expected: |
  Open Document Types. Navigate to page 2 or later when enough rows exist.
  Change the Rows per page value. Confirm the current page resets to 1, the
  visible rows update, the Showing X-Y of Z range updates, and previous/next
  navigation still works.
result: issue
reported: "In PagedTable footer label 'Rows per page' must be drawn on only a line"
severity: cosmetic

## Summary

total: 3
passed: 1
issues: 2
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "Static PDFs rows-per-page browser flow displays the Rows per page selector clearly before the dropdown."
  status: failed
  reason: "User reported: Pages selector la  'Rows per page' must be in a single line before dropdown (select)"
  severity: cosmetic
  test: 1
  root_cause: "Pagination renders the Rows per page text in a plain span inside a flexible footer without a no-wrap constraint, so the label can wrap instead of staying on one line before the select."
  artifacts:
    - path: "frontend/src/components/molecules/Pagination.tsx"
      issue: "Rows per page span lacks a whitespace-nowrap/no-wrap class."
  missing:
    - "Add no-wrap styling to the Rows per page label text and keep it inline before the Select control."

- truth: "Document Types rows-per-page footer label displays 'Rows per page' on a single line before the select."
  status: failed
  reason: "User reported: In PagedTable footer label 'Rows per page' must be drawn on only a line"
  severity: cosmetic
  test: 3
  root_cause: "Same Pagination footer label is reused across PagedTable consumers; without no-wrap styling the label can render across multiple lines."
  artifacts:
    - path: "frontend/src/components/molecules/Pagination.tsx"
      issue: "Shared Rows per page label can wrap across all PagedTable consumers."
  missing:
    - "Ensure the shared Pagination label remains on one line before the dropdown for every PagedTable consumer."
