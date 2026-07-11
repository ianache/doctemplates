---
phase: 10
slug: complex-schema-ui-nested-data-previsualization
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-10
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | TypeScript compiler (tsc) + Vite build + pytest (backend preview contract) |
| **Config file** | `frontend/tsconfig.json`, `frontend/vite.config.ts`, `backend/pyproject.toml` |
| **Quick run command** | `npm run build` (in `frontend` directory) |
| **Full suite command** | `npm run build` (in `frontend` directory) && `uv run pytest tests/test_generation_preview.py tests/test_nested_case_insensitive.py` (in `backend` directory) |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `npm run build` in `frontend` or `uv run pytest` in `backend` depending on tier.
- **After every plan wave:** Build the frontend and run backend tests.
- **Before `/gsd-verify-work`:** Frontend must build cleanly and backend tests must pass.
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | COMPUI-01 | — | TS path parsing, duplicate checking, and normalization helpers | compile/unit | `npm run build` | ✅ | ⬜ pending |
| 10-01-02 | 01 | 1 | COMPUI-01 | T-10-01 | Visual schema editor form supports nested/list rows | compile/unit | `npm run build` | ✅ | ⬜ pending |
| 10-01-03 | 01 | 1 | COMPUI-01 | T-10-02 | Inferred collapsible tree detail view rendering | compile/unit | `npm run build` | ✅ | ⬜ pending |
| 10-02-01 | 02 | 2 | COMPUI-02 | — | Nested mock JSON generator uses correct JSON data types | compile/unit | `npm run build` | ✅ | ⬜ pending |
| 10-02-02 | 02 | 2 | COMPUI-02 | T-10-03, T-10-04 | Reusable MockDataPanel JSON editing and PDF PreviewFrame | compile/unit | `npm run build` | ✅ | ⬜ pending |
| 10-03-01 | 03 | 3 | COMPUI-02 | — | Load schema fields and initialize mock data on designer load | compile/unit | `npm run build` | ✅ | ⬜ pending |
| 10-03-02 | 03 | 3 | COMPUI-02 | T-10-06, T-10-08 | Wire PDF preview toggles, API calls, and PreviewFrame UI | compile/unit | `npm run build` | ✅ | ⬜ pending |
| 10-05-01 | 05 | 4 | COMPUI-02 | T-10-11 | localStorage mock JSON load, save, and reset actions | compile/unit | `npm run build` | ✅ | ⬜ pending |
| 10-04-01 | 04 | 5 | COMPUI-01, COMPUI-02 | — | Clean frontend production build and backend preview tests | compile/unit | `npm run build` && backend tests | ✅ | ⬜ pending |
| 10-04-02 | 04 | 5 | COMPUI-01, COMPUI-02 | T-10-09, T-10-10 | Full end-to-end browser walk verification of features | manual | Manual browser walk | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure (TypeScript compiler + FastAPI preview integration tests) covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual tree builder editor and nested list schema configuration | COMPUI-01 | Requires visual browser interactions for adding/managing fields | Create a new document type in `/document-types/new`, add nested object properties (e.g. `cliente.direccion.calle`) and list arrays (e.g. `cliente.contactos[].nombre`), verify the visual tree groups folders correctly, and submit. Check backend creation is correct. |
| Collapsible tree visualization in Detail view | COMPUI-01 | Visual presentation layout | Navigate to a created Document Type detail page and verify the schema fields display under expandable/collapsible folders matching the configured hierarchy. |
| Custom mock JSON payload previsualization in designer | COMPUI-02 | Visual preview and PDF embedding | Open a document design draft in the designer, toggle the preview panel, verify that correct mock data is generated from the schema, edit values in the Raw JSON panel, and click preview. Check that the rendered PDF compiles dynamically. |
| No persistent issuance on preview | COMPUI-02 | Generation vs preview contract | Confirm that generating multiple previews in the designer does not insert records into `document_issuances` or the `document_tracelogs` database tables. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
