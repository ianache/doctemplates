---
status: complete
phase: 05-versioning
source:
  - .planning/phases/05-versioning/05-01-SUMMARY.md
  - .planning/phases/05-versioning/05-02-SUMMARY.md
  - .planning/phases/05-versioning/05-03-SUMMARY.md
started: 2026-07-08T10:09:00Z
updated: 2026-07-08T10:21:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: |
  Kill any running server/service. Clear ephemeral state (temp DBs, caches, lock files). Start the application from scratch. Server boots without errors, any seed/migration completes, and a primary query (health check, homepage load, or basic API call) returns live data.
result: pass

### 2. The live current version shows Edit Design and Version History actions
expected: |
  Open design, verify action buttons present (Edit Design and Version History)
rationale: Requires UI interaction to verify button existence and style matches spec
result: pass

### 3. Edit Design forks the current version and opens the new draft
expected: |
  Click Edit Design, check navigation and URL update to draft
rationale: Requires interactive browser session validation
result: pass

### 4. Past versions render read-only with no mutating controls
expected: |
  Open superseded design, verify no drag handles, save buttons, or add actions
rationale: Requires verifying complete removal of mutable controls in UI
result: pass

### 5. Version history lists rows newest-first and distinguishes Current, Superseded, and Draft
expected: |
  Open version history page, inspect row badges and order
rationale: Requires visual check of badges and ordering in table
result: pass

### 6. Discard Draft Version is only available on an un-activated draft
expected: |
  Check for Discard button presence on draft detail and absence on current detail
rationale: Requires checking button visibility per status
result: pass

### 7. List and detail screens use the same version-aware status language
expected: |
  Check design list table pills against details page status badges
rationale: Requires visual validation across multiple screens
result: pass

### 8. Manual browser verification of versioning behavior
expected: |
  browser manual walkthrough
rationale: Requires visual confirmation of editor read-only status and draft management in React client
result: pass

### 9. First activation sets version_group_id, version_number = 1, and status = active
expected: First activation sets version_group_id, version_number = 1, and status = active
result: pass
source: automated
coverage_id: D1

### 10. Forking clones pages into a new draft without mutating the current version
expected: Forking clones pages into a new draft without mutating the current version
result: pass
source: automated
coverage_id: D2

### 11. Activating a draft supersedes the previous current version
expected: Activating a draft supersedes the previous current version
result: pass
source: automated
coverage_id: D3

### 12. A second Edit Design call resumes the existing draft instead of duplicating it
expected: A second Edit Design call resumes the existing draft instead of duplicating it
result: pass
source: automated
coverage_id: D4

### 13. Version history returns newest-first rows for the group, including an in-flight draft
expected: Version history returns newest-first rows for the group, including an in-flight draft
result: pass
source: automated
coverage_id: D5

### 14. Discarding a draft leaves the current version intact
expected: Discarding a draft leaves the current version intact
result: pass
source: automated
coverage_id: D6

### 15. Existing active designs migrate to version 1 and never-activated drafts remain version-less
expected: Existing active designs migrate to version 1 and never-activated drafts remain version-less
result: pass
source: automated
coverage_id: D7

## Summary

total: 15
passed: 15
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
