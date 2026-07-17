# Task 1 Fix Brief

Fix the Task 1 review findings. Keep scope limited to the Task 1 files and existing API wiring needed for the format-aware contract.

## Inputs

- Original brief: `.superpowers/sdd/xlsx-template-generation-task-1-brief.md`
- Review package: `.superpowers/sdd/xlsx-template-generation-task-1-review-package.md`
- Review findings:
  - Persist and copy `output_format` and `xlsx_template_id` in `backend/app/api/document_designs.py` create/update/draft version creation paths.
  - Persist and return `allowed_output_formats` in `backend/app/api/document_types.py` create/update/detail/list DTO builders.
  - Validate known output format values. Arbitrary values such as `"docx"` must be rejected by schemas and/or DB check constraints.

## Required Changes

1. In `backend/app/schemas/document_type.py`:
   - Add an `OutputFormat = Literal["pdf", "xlsx"]` type or equivalent.
   - Change `allowed_output_formats` in `DocumentTypeCreate`, `DocumentTypeListItem`, and `DocumentTypeDetail` to use list of the allowed output format type.
   - Add a validator that rejects an empty `allowed_output_formats` list and duplicate values.

2. In `backend/app/schemas/document_design.py`:
   - Use the same allowed output format type for `output_format` in create/update/list/detail schemas.

3. In `backend/app/models/document_design.py`:
   - Add a `CheckConstraint` for `output_format IN ("pdf", "xlsx")` while preserving existing constraints/indexes.

4. In `backend/alembic/versions/0015_xlsx_generation.py`:
   - Add check constraints for `document_designs.output_format` and `document_issuances.output_format`.
   - Add a check or equivalent validation for `document_types.allowed_output_formats` if practical for both SQLite/Postgres; if not practical, schema validation is acceptable. Do not add DB-specific JSON validation that would break SQLite tests.

5. In `backend/app/api/document_types.py`:
   - Create: assign `allowed_output_formats=payload.allowed_output_formats`.
   - Update: assign `document_type.allowed_output_formats = payload.allowed_output_formats`.
   - `_to_detail`: return actual `allowed_output_formats`.
   - `list_document_types`: return actual `allowed_output_formats`.

6. In `backend/app/api/document_designs.py`:
   - Create: persist `payload.output_format` and `payload.xlsx_template_id`.
   - Update: persist `payload.output_format` and `payload.xlsx_template_id`.
   - Detail/list DTOs should already expose fields from schemas; ensure `_detail` and list builder pass actual values.
   - Any draft/version copy path must copy `output_format` and `xlsx_template_id` from the source design.
   - Do not implement Task 4’s document-type/template compatibility validation yet, except simple schema-level allowed value validation. Task 4 will validate design selection against `DocumentType.allowed_output_formats` and `XlsxTemplate.document_type_id`.

7. Tests:
   - Extend `backend/tests/test_xlsx_format_contract.py` or add focused tests proving:
     - `DocumentTypeCreate(allowed_output_formats=[])` fails.
     - `DocumentTypeCreate(allowed_output_formats=["pdf", "pdf"])` fails.
     - invalid design output format fails schema validation.
   - Run compileall for changed files.
   - Try the targeted pytest; if blocked by environment, report exact failure.

## Constraints

- Do not add upload/render APIs.
- Do not revert unrelated dirty files.
- Commands must be prefixed with `rtk`.
- Git commit may fail due `.git/index.lock`; report exact failure.

## Report

Append your fix report to `.superpowers/sdd/xlsx-template-generation-task-1-report.md` and return a concise status.
