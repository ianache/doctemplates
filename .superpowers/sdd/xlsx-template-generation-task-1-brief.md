# Task 1 Brief: Format-Aware Database Contract

Plan: `docs/superpowers/plans/2026-07-16-xlsx-template-generation.md`

## Global Constraints

- XLSX is a first-class emission format; document types declare allowed formats and each design selects one.
- Initial XLSX template creation is upload-based, not a spreadsheet editor.
- Same `DocumentTypeField` schema is used for PDF/HTML and XLSX.
- Support `.xlsx` only; reject `.xls`, `.xlsm`, macros, and Office automation.
- No XLSX-to-PDF generation in this version.
- Repeated tables require explicit template metadata; do not infer complex tables.
- Preview is approximate and read-only; the downloaded workbook is authoritative.
- Preserve existing PDF behavior and compatibility.
- Shell commands in this repo must be prefixed with `rtk`.

## Context

The current backend is FastAPI + SQLAlchemy + Alembic. Existing PDF document designs use `DocumentDesign`, `DocumentDesignPage`, and `DocumentIssuance`. This task adds only the format-aware database/schema contract and the `XlsxTemplate` model/table. Do not implement upload routes or rendering in this task.

The repo has many pre-existing dirty files. Do not revert unrelated changes. Git commits may fail because this sandbox cannot create `.git/index.lock`; if commit fails, report it and keep the working tree changes.

## Files

- Create: `backend/alembic/versions/0015_xlsx_generation.py`
- Create: `backend/app/models/xlsx_template.py`
- Modify: `backend/app/models/document_type.py`
- Modify: `backend/app/models/document_design.py`
- Modify: `backend/app/models/document_issuance.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/schemas/document_type.py`
- Modify: `backend/app/schemas/document_design.py`
- Modify: `backend/app/schemas/document_issuance.py`
- Test: `backend/tests/test_xlsx_format_contract.py`

## Required Interfaces

- `backend/app/models/document_type.py`
  - Add `DEFAULT_OUTPUT_FORMATS = ["pdf"]`.
  - Add `DocumentType.allowed_output_formats: Mapped[list[str]]`, JSON column, default PDF.

- `backend/app/models/xlsx_template.py`
  - Add `XlsxTemplate` SQLAlchemy model with table `xlsx_templates`.
  - Fields: `id`, `document_type_id`, `name`, `description`, `storage_key`, `original_filename`, `detected_sheets`, `detected_tokens`, `image_slots`, `validation_warnings`, `mock_data`, `created_by_id`, `created_at`.
  - Relationships: `document_type`, `created_by`.

- `backend/app/models/document_design.py`
  - Add `DESIGN_OUTPUT_FORMATS = ("pdf", "xlsx")`.
  - Add `output_format: Mapped[str]`, default `"pdf"`.
  - Add `xlsx_template_id: Mapped[uuid.UUID | None]` FK to `xlsx_templates.id`, nullable.
  - Add `xlsx_template` relationship.
  - Preserve existing PDF page behavior.

- `backend/app/models/document_issuance.py`
  - Add `output_format: Mapped[str]`, default `"pdf"`.
  - Add `mime_type: Mapped[str | None]`.
  - Add `filename: Mapped[str | None]`.
  - Add `preview_storage_key: Mapped[str | None]`.

- Schemas:
  - `DocumentTypeCreate`, `DocumentTypeDetail`, and list/detail outputs expose `allowed_output_formats: list[str] = ["pdf"]`.
  - `DocumentDesignCreate`, `DocumentDesignUpdate` if appropriate, `DocumentDesignDetail`, and `DocumentDesignListItem` expose `output_format: str = "pdf"` and `xlsx_template_id: UUID | None = None`.
  - `DocumentIssuanceOut` and `DocumentIssuanceLibraryItem` expose `output_format`, `mime_type`, `filename`, and `preview_storage_key`.

- Migration:
  - `revision = "0015_xlsx_generation"`.
  - `down_revision = "0014_template_ai_proposals"`.
  - Add `document_types.allowed_output_formats`, backfill `["pdf"]`, make non-null.
  - Create `xlsx_templates` before adding the design FK.
  - Add `document_designs.output_format`, backfill `"pdf"`, make non-null.
  - Add `document_designs.xlsx_template_id` FK to `xlsx_templates.id`.
  - Add issuance output metadata fields.
  - Downgrade drops in reverse order.

## Required Test

Create `backend/tests/test_xlsx_format_contract.py` with tests equivalent to:

```python
from uuid import UUID

from app.models.document_design import DESIGN_OUTPUT_FORMATS
from app.models.document_type import DEFAULT_OUTPUT_FORMATS
from app.schemas.document_design import DocumentDesignCreate
from app.schemas.document_type import DocumentTypeCreate


def test_document_type_defaults_to_pdf_format():
    payload = DocumentTypeCreate(
        name="Contract",
        description=None,
        fields=[],
        metadata_definitions=[],
    )

    assert payload.allowed_output_formats == ["pdf"]
    assert DEFAULT_OUTPUT_FORMATS == ["pdf"]


def test_document_design_accepts_xlsx_output_format():
    payload = DocumentDesignCreate(
        document_type_id=UUID("00000000-0000-0000-0000-000000000001"),
        name="Workbook design",
        description=None,
        output_format="xlsx",
        xlsx_template_id=UUID("00000000-0000-0000-0000-000000000002"),
        mock_data=None,
    )

    assert payload.output_format == "xlsx"
    assert payload.xlsx_template_id is not None
    assert DESIGN_OUTPUT_FORMATS == ("pdf", "xlsx")
```

Adjust only for the repository's actual Pydantic field types if needed.

## Commands

Run at least:

```powershell
rtk pytest backend/tests/test_xlsx_format_contract.py -q
```

Then run affected regressions if available:

```powershell
rtk pytest backend/tests/test_document_types.py backend/tests/test_document_designs.py backend/tests/test_document_issuances.py -q
```

## Report

Write your report to `.superpowers/sdd/xlsx-template-generation-task-1-report.md`.

Report format:

- Status: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`
- Files changed
- Tests run with exact commands and results
- Commit result, or exact git failure if commit is blocked
- Concerns or deviations from this brief
