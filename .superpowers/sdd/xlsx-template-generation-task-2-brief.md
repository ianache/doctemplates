# Task 2 Brief: XLSX Template Model, Analysis, And Upload API

Plan: `docs/superpowers/plans/2026-07-16-xlsx-template-generation.md`

## Global Constraints

- XLSX is a first-class emission format; document types declare allowed formats and each design selects one.
- Initial XLSX template creation is upload-based, not a spreadsheet editor.
- Same `DocumentTypeField` schema is used for PDF/HTML and XLSX.
- Support `.xlsx` only; reject `.xls`, `.xlsm`, macros, and Office automation.
- No XLSX-to-PDF generation in this version.
- Preview is approximate and read-only; downloaded workbook authoritative.
- Preserve existing PDF behavior and compatibility.
- Shell commands must be prefixed with `rtk`.

## Context

Task 1 added the DB/schema contract and `XlsxTemplate` model/table. This task adds:

- `openpyxl`/Pillow dependencies if absent.
- XLSX workbook analysis service.
- XLSX template schemas.
- Upload/list/detail/validate API under `/api/xlsx-templates`.
- Storage category wiring for `xlsx_templates`.

Do not implement rendering, repeated rows, image insertion, or preview API in this task.

The repo has many pre-existing dirty files. Do not revert unrelated changes. Git commits may fail because `.git` is read-only; report exact failure.

## Files

- Create: `backend/app/schemas/xlsx_template.py`
- Create: `backend/app/services/xlsx_analysis.py`
- Create: `backend/app/api/xlsx_templates.py`
- Modify: `backend/pyproject.toml`
- Modify: `backend/uv.lock` if lock update works.
- Modify: `backend/app/config.py`
- Modify: `backend/app/dependencies.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_xlsx_analysis.py`
- Test: `backend/tests/test_xlsx_templates_api.py`

## Interfaces

- `analyze_xlsx_template(workbook_bytes: bytes, schema_tokens: set[str]) -> XlsxTemplateAnalysis`
- `XlsxTemplateAnalysis.detected_sheets: list[dict]`
- `XlsxTemplateAnalysis.detected_tokens: list[str]`
- `XlsxTemplateAnalysis.image_slots: list[dict]`
- `XlsxTemplateAnalysis.validation_warnings: list[dict]`

## Analysis Requirements

Create `backend/app/services/xlsx_analysis.py`:

- Use `openpyxl.load_workbook(BytesIO(workbook_bytes))`.
- Extract tokens from string cells matching simple Jinja token syntax like `{{cliente.nombre}}`.
- Preserve first-seen order of tokens.
- For each worksheet, include:
  - `name`
  - `max_row`
  - `max_column`
  - `print_area`
  - `merged_ranges`
- If a detected token is not in `schema_tokens`, add a warning:
  - `type`: `"unknown_schema_token"`
  - `sheet`
  - `cell`
  - `message`
  - `suggestion`
- Return `image_slots=[]` in this task.

## Storage Requirements

Storage currently supports only `static_pdfs` and `issuances`.

Add:

- `Settings.xlsx_template_storage_root: str = "../.content-storage/xlsx-templates"`
- `Settings.storage_s3_bucket_xlsx_templates: str = "docmanagement-xlsx-templates"`
- In `get_storage_provider()`, add `xlsx_templates` to local root paths and S3 buckets.

Do not change PDF storage behavior.

## API Requirements

Create router `backend/app/api/xlsx_templates.py`:

- Prefix: `/api/xlsx-templates`
- Tags: `["xlsx-templates"]`
- Include router in `backend/app/main.py`.

Endpoints:

1. `POST /api/xlsx-templates`
   - Multipart form fields:
     - `document_type_id: UUID`
     - `name: str`
     - `description: str | None`
     - `file: UploadFile`
   - Reject filenames not ending `.xlsx` with `400` detail `"Only .xlsx files are supported"`.
   - Load document type with fields.
   - Read bytes.
   - Analyze workbook against document type field names.
   - Store bytes with category `xlsx_templates`, using a stable unique key like `{uuid}.xlsx`.
   - Create `XlsxTemplate`.
   - Return detail response.

2. `GET /api/xlsx-templates`
   - Optional query `document_type_id`.
   - Return list ordered newest first.

3. `GET /api/xlsx-templates/{template_id}`
   - Return detail or 404.

4. `POST /api/xlsx-templates/{template_id}/validate`
   - Re-read stored workbook, re-analyze against current document type fields, update detected metadata/warnings, return detail.

## Schemas

Create `backend/app/schemas/xlsx_template.py` with:

- `XlsxTemplateListItem`
- `XlsxTemplateDetail`

Fields:

- `id`
- `document_type_id`
- `document_type_name`
- `name`
- `description`
- `original_filename`
- `detected_sheets`
- `detected_tokens`
- `image_slots`
- `validation_warnings`
- `mock_data`
- `created_by_email`
- `created_at`

## Tests

Create `backend/tests/test_xlsx_analysis.py` with unit tests:

- valid workbook extracts `Summary`, `{{cliente.nombre}}`, and print area.
- unknown schema token produces `unknown_schema_token` warning with `cell`.

Create `backend/tests/test_xlsx_templates_api.py` with API tests where practical:

- upload valid workbook returns `201` and detected token.
- upload `.xlsm` or `.txt` returns `400`.
- list/detail returns uploaded metadata.

Use existing test fixture patterns. If environment blocks pytest collection due missing settings/dependencies, record exact failure.

## Commands

Run:

```powershell
rtk pytest backend/tests/test_xlsx_analysis.py -q
rtk pytest backend/tests/test_xlsx_templates_api.py -q
```

If blocked, run:

```powershell
rtk proxy python -m compileall -q backend\app\schemas\xlsx_template.py backend\app\services\xlsx_analysis.py backend\app\api\xlsx_templates.py backend\app\config.py backend\app\dependencies.py backend\app\main.py backend\tests\test_xlsx_analysis.py backend\tests\test_xlsx_templates_api.py
```

## Report

Write report to `.superpowers/sdd/xlsx-template-generation-task-2-report.md`.

Report:

- Status
- Files changed
- Tests run with exact command/result
- Commit result or exact git failure
- Concerns/deviations
