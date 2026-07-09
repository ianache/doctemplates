---
phase: 8
slug: template-ast-static-validation
status: drafted
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-09
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | backend/pyproject.toml |
| **Quick run command** | `cd backend && uv run pytest tests/test_document_types.py` |
| **Full suite command** | `cd backend && uv run pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/test_document_types.py`
- **After every plan wave:** Run `cd backend && uv run pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01   | 1    | AST-01      | T-08-02    | Jinja2 AST NodeVisitor scope-aware extractor | unit | `cd backend && uv run python -c "import app.services.content_validation"` | ✅ | ⬜ pending |
| 08-01-02 | 01   | 1    | AST-02      | T-08-03    | Route integration for design validation & status-based gates | integration | `cd backend && uv run python -c "import app.api.document_designs, app.schemas.document_design, app.services.design_validation"` | ✅ | ⬜ pending |
| 08-01-03 | 01   | 1    | AST-01, AST-02 | T-08-02, T-08-03 | Comprehensive test suite for AST scope-aware mapping, globals, and API responses | integration | `cd backend && uv run pytest tests/test_template_ast_validation.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_template_ast_validation.py` — unit & integration test suite stub (Plan 01 Task 03)

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
