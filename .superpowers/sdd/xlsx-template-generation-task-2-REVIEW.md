---
phase: xlsx-template-generation-task-2
reviewed: 2026-07-16T05:34:21Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - backend/app/schemas/xlsx_template.py
  - backend/app/services/xlsx_analysis.py
  - backend/app/api/xlsx_templates.py
  - backend/app/config.py
  - backend/app/dependencies.py
  - backend/app/main.py
  - backend/pyproject.toml
  - backend/uv.lock
  - backend/tests/test_xlsx_analysis.py
  - backend/tests/test_xlsx_templates_api.py
findings:
  critical: 2
  warning: 1
  info: 0
  total: 3
status: issues_found
---

# Phase xlsx-template-generation-task-2: Code Review Report

**Reviewed:** 2026-07-16T05:34:21Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Task 2 is not ready to ship. The API route is included, schema-token warnings are implemented, and storage category wiring exists for local and S3 providers. However, the upload path only checks the submitted filename, so macro-enabled workbooks can be accepted and stored if renamed to `.xlsx`. The dependency state is also incoherent: `pyproject.toml` imports and declares `openpyxl`, but `uv.lock` does not lock it or list it in the project package stanza.

Spec verdict: FAIL.

Quality verdict: Findings.

## Critical Issues

### CR-01: Macro-enabled workbooks can be accepted when renamed `.xlsx`

**File:** `backend/app/api/xlsx_templates.py:60`

**Issue:** The upload endpoint rejects files solely by `file.filename.lower().endswith(".xlsx")`. It then analyzes and stores the original bytes. That satisfies simple `.xlsm` filename rejection, but it does not reject macro-enabled XLSM content renamed to `.xlsx`, even though the brief explicitly requires rejecting macros. A macro-enabled OOXML package can contain `xl/vbaProject.bin` and macro content types regardless of the submitted filename.

**Fix:**
```python
from zipfile import BadZipFile, ZipFile


def _reject_macro_enabled_workbook(workbook_bytes: bytes) -> None:
    try:
        with ZipFile(BytesIO(workbook_bytes)) as archive:
            names = set(archive.namelist())
            content_types = archive.read("[Content_Types].xml").decode("utf-8", errors="ignore")
    except (BadZipFile, KeyError) as exc:
        raise HTTPException(status_code=400, detail="Invalid .xlsx file") from exc

    if "xl/vbaProject.bin" in names or "vnd.ms-office.vbaProject" in content_types:
        raise HTTPException(status_code=400, detail="Only .xlsx files are supported")
```

Call this after reading `workbook_bytes` and before `analyze_xlsx_template()` or `storage_provider.save()`.

### CR-02: `uv.lock` does not lock the new `openpyxl` runtime dependency

**File:** `backend/uv.lock:547`

**Issue:** `backend/pyproject.toml:25` adds `openpyxl>=3.1.5`, and `backend/app/services/xlsx_analysis.py:5` imports it at runtime, but `backend/uv.lock` has no `openpyxl` package entry and the `docmanagement-backend` dependency list in `uv.lock` omits it. Reproducible/frozen uv installs will not include the dependency required by the new service.

**Fix:** Regenerate and commit `backend/uv.lock` from the updated `pyproject.toml` in an environment with uv cache access, then verify the lock includes both the package stanza and the project dependency entry for `openpyxl`.

## Warnings

### WR-01: Stored workbook is not cleaned up when database commit fails

**File:** `backend/app/api/xlsx_templates.py:79`

**Issue:** The endpoint saves workbook bytes to storage before inserting and committing the `XlsxTemplate` row. If `db.commit()` fails at line 93, the API returns an error but leaves an unreferenced workbook in `xlsx_templates` storage. This is a robustness defect in the upload flow.

**Fix:** Wrap the storage save and DB commit in error handling and delete the stored key on failure.

```python
storage_provider.save(storage_key, workbook_bytes, category="xlsx_templates")
try:
    db.add(template)
    db.commit()
except Exception:
    storage_provider.delete(storage_key, category="xlsx_templates")
    db.rollback()
    raise
```

---

_Reviewed: 2026-07-16T05:34:21Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
