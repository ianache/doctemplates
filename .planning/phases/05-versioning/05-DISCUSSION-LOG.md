# Phase 5: Versioning - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-07
**Phase:** 05-versioning
**Areas discussed:** Versioning start point, In-progress draft visibility, One draft at a time, Migrating existing Phase 4 designs

---

## Area Selection

Presented gray areas (informed by the pre-existing `05-UI-SPEC.md`, which already locked most visual/interaction decisions):

| Option | Description | Selected |
|--------|-------------|----------|
| Versioning start point | When does a design first count as "version 1"? | ✓ |
| In-progress draft visibility | Does an unactivated draft show up in Version History? | ✓ |
| One draft at a time | What happens if "Edit Design" is clicked while a draft exists? | ✓ |
| Migrating existing Phase 4 designs | How do pre-existing draft/active designs map onto versioning? | ✓ |

All four selected.

---

## Versioning Start Point

| Option | Description | Selected |
|--------|-------------|----------|
| Only after first activation | Design stays version-less pre-activation (Phase 4 behavior); becomes "Version 1/Current" on first activation. | ✓ |
| Every design is "version 1" from creation | Even never-activated designs are treated as an existing Version 1 in Draft state. | |

**User's choice:** Only after first activation
**Notes:** Matches Phase 4's D-02 ("editing deferred to Phase 5") and D-04 ("draft/active lifecycle without version history in Phase 4").

---

## In-Progress Draft Visibility

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, show it with "Draft" badge | Draft appears in Version History table alongside Current/Superseded, newest-first. | ✓ |
| No, hide until activated | Version History only lists Current + Superseded rows. | |

**User's choice:** Yes, show it with "Draft" badge
**Notes:** Extends the UI-SPEC's Version History table description, which only explicitly covered Current/Superseded rows.

---

## One Draft at a Time (Concurrent Edits)

| Option | Description | Selected |
|--------|-------------|----------|
| Resume the existing draft | Clicking "Edit Design" while a draft exists navigates into that same draft, no duplicate created. | ✓ |
| Block with a message | Shows an error/notice with a link to the existing draft instead of auto-navigating. | |

**User's choice:** Resume the existing draft
**Notes:** Only one in-flight draft per design is ever allowed.

---

## Migrating Existing Phase 4 Designs

| Option | Description | Selected |
|--------|-------------|----------|
| Active → Version 1/Current; draft stays version-less | Existing `active` designs become Version 1/Current; existing `draft` designs stay version-less until first activation. | ✓ |
| All existing designs become Version 1, regardless of status | Both draft and active designs get retroactively wrapped as Version 1. | |

**User's choice:** Active → Version 1/Current; draft stays version-less
**Notes:** Consistent with the "only after first activation" start-point decision — no extra migration complexity for untouched drafts.

---

## Claude's Discretion

- Exact database schema shape for storing versions (new table vs. reusing `document_designs` rows with a parent/version-group id).
- Whether "Activate" (forking a draft into current) is a dedicated endpoint or an update action.
- Concurrency/locking mechanism underlying the "resume existing draft" behavior.
- Query/index strategy for listing version history newest-first.

## Deferred Ideas

None — discussion stayed within phase scope.
