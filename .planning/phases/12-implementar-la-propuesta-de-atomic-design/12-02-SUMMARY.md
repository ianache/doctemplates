---
phase: 12-implementar-la-propuesta-de-atomic-design
plan: "02"
subsystem: frontend
tags: [atomic-design, refactor, molecules, organisms]

# Dependency graph
requires: []
provides:
  - design-components
  - TokenExplorer-organism
  - HtmlJinjaEditor-organism
affects: [frontend]

# Tech tracking
tech-stack:
  added: []
  patterns: [Atomic Design]

key-files:
  created:
    - frontend/src/pages/document-designs/components/molecules/DesignPageCard.tsx
    - frontend/src/pages/document-designs/components/organisms/TokenExplorer.tsx
    - frontend/src/pages/document-designs/components/organisms/HtmlJinjaEditor.tsx
  modified:
    - frontend/src/pages/content/TemplatesPage.tsx
    - frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx

key-decisions:
  - "Moved DesignPageCard to document-designs/components/molecules/ and adjusted its relative import path."
  - "Moved TokenExplorer and HtmlJinjaEditor to document-designs/components/organisms/ to enforce localized page folder scopes."
  - "Updated the import path of TokenExplorer in TemplatesPage.tsx and DesignPageCard in DocumentDesignDetailPage.tsx."

requirements-completed:
  - ATOMIC-03
  - ATOMIC-04

# Metrics
duration: 15min
completed: 2026-07-12
status: complete
---

# Phase 12 Plan 02: Relocate Design Page Components Summary

**Relocated design-specific page components (DesignPageCard, TokenExplorer, HtmlJinjaEditor) to molecules and organisms under document-designs/components.**

## Performance

- **Duration:** 15 min
- **Tasks:** 2 completed
- **Files modified/created:** 5

## Accomplishments
- Moved DesignPageCard to `frontend/src/pages/document-designs/components/molecules/DesignPageCard.tsx` and updated references in `DocumentDesignDetailPage.tsx`.
- Moved TokenExplorer to `frontend/src/pages/document-designs/components/organisms/TokenExplorer.tsx` and updated references in `TemplatesPage.tsx`.
- Moved HtmlJinjaEditor to `frontend/src/pages/document-designs/components/organisms/HtmlJinjaEditor.tsx`.
- Verified that all imports compile cleanly without errors.

## Task Commits

Each task was committed:
1. **Task 1: Move DesignPageCard and TokenExplorer and update imports** - `2d41831` (feat)
2. **Task 2: Move HtmlJinjaEditor to organisms** - `2d41831` (feat)

## Known Stubs
None.

## Threat Flags
None.

## Self-Check: PASSED
- [x] Components relocated to their respective directories.
- [x] Imports updated and verified via compile check.
- [x] Application successfully built.
