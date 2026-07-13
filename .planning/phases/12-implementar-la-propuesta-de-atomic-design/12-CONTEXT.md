# Phase 12: implementar-la-propuesta-de-atomic-design - Context

**Gathered:** 2026-07-12
**Status:** Ready for planning
**Source:** Proposed Atomic Design in .design/atomic_design_proposal.md

<domain>
## Phase Boundary

Implement the Atomic Design refactoring proposal for the DocManagement frontend.
This involves:
- Reorganizing global shared components into `components/atoms`, `components/molecules`, and `components/organisms`.
- Reorganizing domain-specific components into modular components inside their respective page directories.
- Refactoring imports across the entire frontend to ensure it builds correctly.
</domain>

<decisions>
## Implementation Decisions

### Component Classification
- **Atoms (Atoms):**
  - Move/Verify: `Button.tsx`, `Icon.tsx`, `Badge.tsx`, `StatusDot.tsx` in `src/components/atoms`.
  - Extract/Create: `InputText.tsx`, `Select.tsx`, `Checkbox.tsx` (using Tailwind styles from forms).
- **Molecules (Molecules):**
  - Move/Verify: `TableHeader.tsx`, `Pagination.tsx`, `DateRange.tsx` in `src/components/molecules`.
  - Move: `PageHeader.tsx` from `src/components/PageHeader.tsx` to `src/components/molecules/PageHeader.tsx`.
- **Organisms (Organisms):**
  - Move/Verify: `PagedTable.tsx` in `src/components/organisms`.
- **Hybrid Modular Components (Domain-Specific):**
  - Under `src/pages/document-designs/components/`:
    - `DesignPageCard.tsx` (Molecule)
    - `HtmlJinjaEditor.tsx` (Organism)
    - `TokenExplorer.tsx` (Organism)
    - `AddContentModal.tsx` (Organism)
    - `DesignPageInspector.tsx` (Organism)
    - `MockDataPanel.tsx` (Organism)
    - `PreviewFrame.tsx` (Organism)
  - Under `src/pages/document-types/components/`:
    - `SchemaFieldEditor.tsx` (Organism)
    - `SchemaMetadataEditor.tsx` (Organism)

### Codebase Refactoring
- Update all component imports in `App.tsx` and all page files to point to the new paths.
- Ensure no compilation or build errors in the frontend.
</decisions>

<canonical_refs>
## Canonical References

- `.design/atomic_design_proposal.md` — The design proposal detailing the levels of composition and its impact.
</canonical_refs>
