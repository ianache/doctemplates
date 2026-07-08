---
phase: 5
slug: versioning
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-07
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) — version pinned via `backend/.venv`; config at `backend/pyproject.toml` `[tool.pytest.ini_options]` |
| **Config file** | `backend/pyproject.toml` (`testpaths = ["tests"]`, `pythonpath = ["."]`) |
| **Quick run command** | `cd backend && pytest tests/test_document_designs.py -x` |
| **Full suite command** | `cd backend && pytest` |
| **Estimated runtime** | ~10 seconds |

**Frontend:** No test framework configured yet (no `vitest`/`jest` in `frontend/package.json`, no `*.test.tsx` files found). Frontend verification for this phase remains manual/visual, consistent with Phases 1–4.

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/test_document_designs.py -x`
- **After every plan wave:** Run `cd backend && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-TBD | TBD | 0 | VERSION-01 | unit/integration | `pytest tests/test_document_designs.py::test_first_activation_becomes_version_1 -x` | ❌ W0 | ⬜ pending |
| 05-TBD | TBD | 0 | VERSION-01 | integration | `pytest tests/test_document_designs.py::test_fork_clones_pages_without_mutating_current -x` | ❌ W0 | ⬜ pending |
| 05-TBD | TBD | 0 | VERSION-01 | integration | `pytest tests/test_document_designs.py::test_activate_draft_supersedes_old_current -x` | ❌ W0 | ⬜ pending |
| 05-TBD | TBD | 0 | VERSION-01 | integration | `pytest tests/test_document_designs.py::test_fork_resumes_existing_draft -x` | ❌ W0 | ⬜ pending |
| 05-TBD | TBD | 0 | VERSION-01 | migration/integration | `pytest tests/test_document_designs.py::test_migration_backfill_d05 -x` | ❌ W0 | ⬜ pending |
| 05-TBD | TBD | 0 | VERSION-02 | integration | `pytest tests/test_document_designs.py::test_version_history_newest_first_includes_draft -x` | ❌ W0 | ⬜ pending |
| 05-TBD | TBD | 0 | VERSION-02 | integration | `pytest tests/test_document_designs.py::test_discard_draft_leaves_current_intact -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Task IDs, plan numbers, and wave assignments to be finalized by gsd-planner; this table maps requirements to tests to seed Wave 0.*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_document_designs.py` — extend with the 7 test cases above (file exists, needs new tests appended; existing `_auth_client`/`_create_document_type`/`_create_template`/`_create_pdf`/`_create_design` helpers in this file are directly reusable)
- [ ] Alembic migration `backend/alembic/versions/0006_document_design_versioning.py` — new file, following the exact `inspect(op.get_bind())` idempotency-guard style of `0004`/`0005`
- [ ] No new fixtures needed in `backend/tests/conftest.py` — existing `db_session`/`client`/`_auth_client` fixtures cover this phase's needs

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Version History table UI (Current/Superseded/Draft badges, correct ordering) | VERSION-02 | No frontend test framework configured yet | Open a design with 2+ versions in the browser, confirm badges and newest-first ordering match `05-UI-SPEC.md` |
| "Edit Design" resumes existing draft instead of duplicating | VERSION-01 | No frontend test framework configured yet | Click "Edit Design" twice on the same active design, confirm only one draft row appears in the UI |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
