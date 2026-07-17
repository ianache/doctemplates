# Task 2 Fix Brief

Fix Task 2 review findings only.

## Inputs

- Original brief: `.superpowers/sdd/xlsx-template-generation-task-2-brief.md`
- Review package: `.superpowers/sdd/xlsx-template-generation-task-2-review-package.md`
- Review artifact: `.superpowers/sdd/xlsx-template-generation-task-2-REVIEW.md`

## Findings To Fix

1. Block macro-enabled workbooks even when renamed `.xlsx`.
   - Add OOXML zip inspection before analysis/storage.
   - Reject if the archive contains `xl/vbaProject.bin`.
   - Reject if `[Content_Types].xml` includes a VBA or macro-enabled content type.
   - Return HTTP 400 with detail `"Macro-enabled workbooks are not supported"`.
   - Add a unit test or API test for renamed macro-enabled workbook bytes.

2. Make dependency state coherent.
   - `backend/pyproject.toml` includes `openpyxl`.
   - Update `backend/uv.lock` if possible.
   - If `uv lock` remains blocked by cache permissions, inspect existing lock format and make the minimal deterministic lockfile update needed for `docmanagement-backend` to include `openpyxl`, only if the package stanza already exists in the lock. Do not invent package versions if the package is absent.
   - If the package stanza is absent and lock update is blocked, report this as still blocked.

3. Prevent orphan stored XLSX files if DB commit fails.
   - In `backend/app/api/xlsx_templates.py`, after saving to storage and before returning, wrap `db.commit()` in `try/except`.
   - On exception: `db.rollback()`, attempt `storage_provider.delete(storage_key, category="xlsx_templates")`, then re-raise.
   - Do not swallow the original DB error.

## Constraints

- Do not implement rendering, repeated rows, image insertion, or preview.
- Preserve PDF behavior.
- Do not revert unrelated dirty files.
- Commands must be prefixed with `rtk`.
- Git commit may fail due `.git/index.lock`; report exact failure.

## Verification

Run:

```powershell
rtk pytest backend/tests/test_xlsx_analysis.py backend/tests/test_xlsx_templates_api.py -q
```

If pytest is blocked by environment, run:

```powershell
rtk proxy python -m compileall -q backend\app\schemas\xlsx_template.py backend\app\services\xlsx_analysis.py backend\app\api\xlsx_templates.py backend\app\config.py backend\app\dependencies.py backend\app\main.py backend\tests\test_xlsx_analysis.py backend\tests\test_xlsx_templates_api.py
```

Also run a direct smoke check for macro detection if pytest is blocked.

## Report

Append fix report to `.superpowers/sdd/xlsx-template-generation-task-2-report.md`.
