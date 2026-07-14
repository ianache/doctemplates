---
status: testing
phase: 15-implementar-scopes-prd5-md
source: [15-VERIFICATION.md]
started: 2026-07-14T03:45:00Z
updated: 2026-07-14T03:45:00Z
---

# Phase 15 UAT: PagedTable Page Size Selector

## Current Test

number: 1
name: Static PDFs rows-per-page browser flow
expected: |
  Static PDFs shows the Rows per page selector. Switching between 5, 10, 20,
  and 50 updates visible row count when enough rows exist, updates the
  Showing X-Y of Z range, recalculates page buttons, and preserves
  previous/next navigation behavior.
awaiting: user response

## Tests

### 1. Static PDFs rows-per-page browser flow

expected: |
  Open Static PDFs. Confirm the Rows per page selector is visible. Change the
  selector between 5, 10, 20, and 50. Confirm visible row count changes when
  enough rows exist, the range text updates, page buttons recalculate, and
  previous/next navigation still works.
result: pending

### 2. Templates rows-per-page browser flow with filters

expected: |
  Open Templates. Apply at least one filter. Confirm the Rows per page selector
  is visible. Change the selector between 5, 10, 20, and 50. Confirm visible
  row count changes when enough rows exist, the range text updates, page
  buttons recalculate, and previous/next navigation still works.
result: pending

### 3. Document Types page reset browser flow

expected: |
  Open Document Types. Navigate to page 2 or later when enough rows exist.
  Change the Rows per page value. Confirm the current page resets to 1, the
  visible rows update, the Showing X-Y of Z range updates, and previous/next
  navigation still works.
result: pending

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
