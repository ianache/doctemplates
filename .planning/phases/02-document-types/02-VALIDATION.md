---
phase: 02
slug: document-types
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-06
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (`pytest-asyncio` 1.4.0 also installed) |
| **Config file** | `backend/pyproject.toml` (`[tool.pytest.ini_options]`, `testpaths = ["tests"]`) |
| **Quick run command** | `cd backend && VIRTUAL_ENV= uv run pytest tests/test_document_types.py -q` |
| **Full suite command** | `cd backend && VIRTUAL_ENV= uv run pytest -q` |
| **Estimated runtime** | ~10 seconds |

> Note: Phase 1 SUMMARYs flag that a stray `VIRTUAL_ENV` env var breaks `uv run pytest` in this shell — unset it first (`VIRTUAL_ENV=`), or invoke `.venv/Scripts/python.exe -m pytest` directly.

---

## Sampling Rate

- **After every task commit:** Run `cd backend && VIRTUAL_ENV= uv run pytest tests/test_document_types.py -q`
- **After every plan wave:** Run `cd backend && VIRTUAL_ENV= uv run pytest -q` (full suite, including Phase 1's auth tests, to catch regressions from the new router/models)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-XX | 01 | 0/1 | DOCTYPE-01 | integration | `uv run pytest tests/test_document_types.py::test_create_document_type -x` | ❌ W0 | ⬜ pending |
| 02-01-XX | 01 | 1 | DOCTYPE-01 | integration | `uv run pytest tests/test_document_types.py::test_create_rejects_duplicate_field_names -x` | ❌ W0 | ⬜ pending |
| 02-01-XX | 01 | 1 | DOCTYPE-01 | integration | `uv run pytest tests/test_document_types.py::test_create_rejects_invalid_field_type -x` | ❌ W0 | ⬜ pending |
| 02-01-XX | 01 | 1 | DOCTYPE-01 | integration | `uv run pytest tests/test_document_types.py::test_create_requires_auth -x` | ❌ W0 | ⬜ pending |
| 02-01-XX | 01 | 1 | DOCTYPE-02 | integration | `uv run pytest tests/test_document_types.py::test_list_document_types -x` | ❌ W0 | ⬜ pending |
| 02-01-XX | 01 | 1 | DOCTYPE-02 | integration | `uv run pytest tests/test_document_types.py::test_get_document_type_detail -x` | ❌ W0 | ⬜ pending |
| 02-01-XX | 01 | 1 | DOCTYPE-02 | integration | `uv run pytest tests/test_document_types.py::test_get_document_type_not_found -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_document_types.py` — stubs for DOCTYPE-01, DOCTYPE-02 (new file; reuses existing `client`/`db_session` fixtures from `backend/tests/conftest.py`, no new fixtures needed)
- [ ] `backend/alembic/versions/0002_document_types.py` — new migration (autogenerate now viable against live Postgres; watch the `alembic/env.py` model-import registration gotcha)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Document type create/list/detail pages render and behave correctly in browser | DOCTYPE-01, DOCTYPE-02 | No frontend test framework detected in `frontend/package.json` (no vitest/jest/testing-library); Phase 1 also had no frontend automated tests | Start dev server, create a document type with several fields via the UI, confirm it appears in the list, open its detail view and confirm fields/types/descriptions display correctly |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
