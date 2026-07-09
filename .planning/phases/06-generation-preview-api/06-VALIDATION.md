---
phase: 6
slug: generation-preview-api
status: drafted
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-08
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | backend/pyproject.toml |
| **Quick run command** | `uv run pytest tests/test_smoke.py` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_smoke.py`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01   | 1    | GEN-01      | T-03       | Audit log database setup | migration | `cd backend && uv run alembic upgrade head` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01   | 1    | GEN-01, GEN-02 | T-05, T-06 | Pure python rendering and sandboxing | unit | `cd backend && uv run python -c "import app.services.pdf_generator"` | ✅ | ⬜ pending |
| 06-02-01 | 02   | 2    | GEN-01, GEN-02 | T-01, T-02, T-04 | Auth-gated endpoints and traversal prevention | integration | `cd backend && uv run python -c "import app.api.document_designs, app.api.issuances"` | ✅ | ⬜ pending |
| 06-02-02 | 02   | 2    | GEN-01, GEN-02 | T-01, T-02, T-04 | End-to-end integration verification | integration | `cd backend && uv run pytest tests/test_generation_preview.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_generation_preview.py` — integration test suite stub (Plan 02 Task 02)
- [ ] `backend/app/models/document_issuance.py` — model stub for migration checks (Plan 01 Task 01)

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
