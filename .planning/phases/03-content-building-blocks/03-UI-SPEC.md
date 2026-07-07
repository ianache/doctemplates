---
phase: 3
slug: content-building-blocks
status: approved
preset: none
created: 2026-07-07
reviewed_at: 2026-07-07
---

# Phase 3 — UI Design Contract

**Phase scope reminder:** This phase delivers the content library only — schema-scoped HTML templates and uploaded static PDF assets. The UI must stay operational and admin-focused: list, create, inspect, and download. Do **not** build the visual designer, version history, generation, or preview UI here.

---

## Design System

**Carry-forward rule:** Reuse the established Phase 1/2 app shell and visual language. Do not introduce a new component library, new chrome, or a designer-style layout. This phase is a content administration surface, not a creative workspace.

**shadcn decision:** still not initialized for this phase. The screens here are straightforward forms, tables, and detail views; nothing in Phase 3 needs a new primitive library.

---

## Spacing Scale

Use the existing platform spacing rhythm from Phases 1 and 2. Keep content dense enough for scanning, but avoid cramming form rows together. The upload form may need a little extra vertical spacing around the file input and page-range controls so the error states remain readable.

---

## Typography

**Usage mapping for this phase's screens:**
- Page titles ("Content Library", "New Template", "Upload PDF") -> Heading
- Section labels, table headers, metadata labels, and token warnings -> Label
- Body copy, empty states, file metadata, and helper text -> Body
- Raw HTML, token strings, file paths, and download URLs -> Code

Keep the template body editor monospaced if the implementation uses a plain textarea preview of HTML. Do not make it look like a visual editor.

---

## Color

Continue the Phase 2 palette:
- Backgrounds and shells stay light and neutral.
- Primary actions use the established accent color.
- Error banners and field validation use the existing destructive tone.

Do not add extra accent colors for templates vs PDFs. The distinction should come from labels, icons, and page structure, not from a new color system.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Library page title | "Content Library" |
| Library page helper text | "Create reusable HTML templates and upload static PDF assets for later document designs." |
| Empty state — templates | "No templates yet" |
| Empty state — PDFs | "No PDF assets yet" |
| Template create CTA | "Create Template" |
| PDF upload CTA | "Upload PDF" |
| Template validation error | "This template uses tokens that are not allowed for the selected document type." |
| PDF upload failure | "We couldn't upload this PDF. Check the file and try again." |
| PDF page-range validation | "Enter a valid page range." |
| Detail-page 404 | "Content item not found." |

If the backend returns a specific invalid-token list, show it inline and keep the message concrete. Do not collapse token failures into a generic form error.

---

## Registry Safety

| shadcn official | none | not applicable |
| third-party | none | not applicable |

---

## Layout Notes (Phase 3 specific)

- **Content library entry page:** One authenticated page that introduces two clear routes or tabs: Templates and Static PDFs. Keep the surface simple and repetitive; it is a management console, not a marketing page.
- **Template list/detail:** Show document type, token count, creator, and timestamps in a table or compact detail card. The raw HTML should be visible on the detail page in a scrollable code-style block.
- **Template create page:** Show a document-type selector first, then a raw HTML textarea, then a submit button. Surface validation errors next to the HTML field and at the top of the form if the save fails.
- **PDF list/detail:** Show filename, page count, storage state, creator, and timestamps. The detail page should include a download action and enough metadata to prove the uploaded file was stored correctly.
- **PDF upload page:** Keep the upload affordance obvious. If page-range extraction is supported, show start/end page inputs directly adjacent to the file control so the user understands they operate together.
- **Icons:** Use neutral file/content/upload icons only. Avoid decorative artwork and avoid implying the future designer UI.

---

## Checker Sign-Off

[ ] Phase 3 UI contract matches the content-library scope
[ ] No designer/versioning/generation chrome included
[ ] Empty states and failure states are specified

