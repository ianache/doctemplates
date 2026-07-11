# Phase 10: Complex Schema UI & Nested Data Previsualization - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-10
**Phase:** 10-complex-schema-ui-nested-data-previsualization
**Areas discussed:** Document Type Schema Fields UI (COMPUI-01), Designer Mock Data Editor UI (COMPUI-02), Mock Data Persistence

---

## Document Type Schema Fields UI (COMPUI-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Visual Tree Builder | Visually add objects/lists as hierarchy folders and sub-fields, auto-compiling down to backend flat path strings (e.g. `cliente.direccion.calle`) | ✓ |
| Flat Path Editor with Live Syntax Helper | Direct path text inputs (e.g. typing `cliente.contactos[].nombre`) with an interactive sidebar preview of the parsed tree structure | |
| You decide | Balance the visual editor design and implementation complexity | |

**User's choice:** Visual Tree Builder
**Notes:** The user also selected a Collapsible Tree Layout for displaying fields on the Document Type Detail view to match the builder's visual hierarchy.

---

## Designer Mock Data Editor UI (COMPUI-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Raw JSON Code Editor Panel | A syntax-checking textarea pre-filled with correct mock schema structure, allowing quick edits and copy-pasting raw JSON payloads | ✓ |
| Dynamic Form Builder | A dynamically generated form with input fields for nested keys and list add/remove rows buttons | |
| You decide | Choose the best layout for previewing dynamic data | |

**User's choice:** Raw JSON Code Editor Panel
**Notes:** The user also selected the Interactive Preview Toggle Mode to switch the page canvas sheet into a full-height PDF viewer.

---

## Mock Data Persistence

| Option | Description | Selected |
|--------|-------------|----------|
| Local Browser Storage (localStorage) | Persist the mock JSON locally in the user's browser keyed by design ID. Simple, requires no database migrations or new API endpoints | ✓ |
| Session-only State (No Persistence) | Keep mock JSON in component state only, resetting to default schema structure on page refresh | |
| Backend Draft Persistence | Store the mock JSON payload in the backend database (e.g. as a column on the DocumentDesign draft version) to persist it across different devices | |
| You decide | Implement the most pragmatic persistence strategy | |

**User's choice:** Local Browser Storage (localStorage)
**Notes:** None.

---

## the agent's Discretion

- Tree builder add/remove buttons visual layout.
- Collapsible folders state animation style.
- JSON syntax validation highlight/formatting error presentation.

## Deferred Ideas

None.
