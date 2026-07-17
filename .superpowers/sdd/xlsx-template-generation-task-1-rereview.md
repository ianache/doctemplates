---
phase: xlsx-template-generation-task-1
reviewed: 2026-07-16T05:10:22Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - backend/alembic/versions/0015_xlsx_generation.py
  - backend/app/api/document_designs.py
  - backend/app/api/document_types.py
  - backend/app/models/__init__.py
  - backend/app/models/document_design.py
  - backend/app/models/document_issuance.py
  - backend/app/models/document_type.py
  - backend/app/models/xlsx_template.py
  - backend/app/schemas/document_design.py
  - backend/app/schemas/document_issuance.py
  - backend/app/schemas/document_type.py
  - backend/tests/test_xlsx_format_contract.py
findings:
  critical: 0
  warning: 1
  info: 0
  total: 1
status: issues_found
---

# Phase xlsx-template-generation-task-1: Code Review Report

**Reviewed:** 2026-07-16T05:10:22Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Re-reviewed Task 1 after fixes, limited to the format-aware DB/schema/API contract and the prior findings. The prior blocker findings are resolved: document design create/update/list/detail/version copy now persist and return `output_format` and `xlsx_template_id`; document type create/update/list/detail now persist and return `allowed_output_formats`; schema validation rejects invalid formats such as `docx`, plus empty and duplicate allowed format lists.

One remaining quality issue exists in model/migration consistency.

## Warnings

### WR-01: Issuance output format DB constraint is missing from SQLAlchemy model metadata

**File:** `backend/app/models/document_issuance.py:14`
**Issue:** The Alembic migration creates `ck_document_issuance_output_format` for `document_issuances.output_format`, but the SQLAlchemy model only declares the existing status check constraint. Fresh databases or tests created from `Base.metadata.create_all()` will not enforce the same known-format boundary for `DocumentIssuance.output_format`, allowing arbitrary values such as `docx` outside the migrated production path.
**Fix:** Add the same check constraint to `DocumentIssuance.__table_args__`:

```python
ISSUANCE_OUTPUT_FORMATS = ("pdf", "xlsx")

__table_args__ = (
    CheckConstraint(f"status IN {ISSUANCE_STATUSES!r}", name="ck_document_issuance_status"),
    CheckConstraint(
        f"output_format IN {ISSUANCE_OUTPUT_FORMATS!r}",
        name="ck_document_issuance_output_format",
    ),
)
```

---

_Reviewed: 2026-07-16T05:10:22Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
