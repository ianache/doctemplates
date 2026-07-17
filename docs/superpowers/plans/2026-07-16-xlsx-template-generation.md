# XLSX Template Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add XLSX as a first-class DocManagement emission format using uploaded workbook templates, schema validation, image insertion, async generation, download/share support, and approximate preview.

**Architecture:** Keep PDF generation intact and add a format-aware layer around document types, designs, issuances, and workers. Store XLSX templates as their own content model, render with `openpyxl` plus sandboxed Jinja, and expose preview as read-only JSON for frontend grid rendering.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Celery, Pydantic, Jinja2 sandbox, `openpyxl`, Pillow, React, TypeScript, Vite, existing storage provider abstraction.

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

---

## File Structure

Create backend files:

- `backend/app/models/xlsx_template.py`: SQLAlchemy model for uploaded XLSX templates.
- `backend/app/schemas/xlsx_template.py`: Pydantic request/response/preview schemas.
- `backend/app/api/xlsx_templates.py`: upload, list, detail, validate, preview routes.
- `backend/app/services/xlsx_analysis.py`: workbook inspection, token extraction, metadata extraction.
- `backend/app/services/xlsx_images.py`: image payload normalization and validation.
- `backend/app/services/xlsx_renderer.py`: workbook render, repeated rows, image insertion, preview model.
- `backend/app/services/document_generation.py`: format dispatcher used by worker and sync paths.
- `backend/tests/test_xlsx_analysis.py`
- `backend/tests/test_xlsx_renderer.py`
- `backend/tests/test_xlsx_templates_api.py`
- `backend/tests/test_xlsx_issuance_generation.py`
- `backend/alembic/versions/0015_xlsx_generation.py`

Modify backend files:

- `backend/pyproject.toml`: add `openpyxl` and ensure `pillow` is available if not already transitive.
- `backend/app/main.py`: include XLSX template router.
- `backend/app/models/__init__.py`: import `XlsxTemplate`.
- `backend/app/models/document_type.py`: add `allowed_output_formats`.
- `backend/app/models/document_design.py`: add `output_format`, XLSX template reference/config fields, expand constraints.
- `backend/app/models/document_issuance.py`: add output metadata fields.
- `backend/app/schemas/document_type.py`: expose `allowed_output_formats`.
- `backend/app/schemas/document_design.py`: expose `output_format` and XLSX template selection.
- `backend/app/schemas/document_issuance.py`: expose `output_format`, `mime_type`, `filename`, `preview_url` behavior.
- `backend/app/api/document_types.py`: persist allowed formats.
- `backend/app/api/document_designs.py`: validate output format and create XLSX designs.
- `backend/app/api/issuances.py`: remove hardcoded PDF filename/MIME assumptions.
- `backend/app/services/issuance_jobs.py`: enqueue generic generation task.
- `backend/app/workers/document_generation.py`: dispatch by design output format.
- `backend/app/services/design_validation.py`: support XLSX design activation validation.

Create frontend files:

- `frontend/src/lib/xlsxTemplates.ts`: XLSX template API client and types.
- `frontend/src/pages/content/XlsxTemplatesPage.tsx`: list XLSX templates.
- `frontend/src/pages/content/XlsxTemplateUploadPage.tsx`: upload/validate flow.
- `frontend/src/pages/content/XlsxTemplateDetailPage.tsx`: metadata and preview entry point.
- `frontend/src/pages/content/components/XlsxPreviewGrid.tsx`: approximate read-only grid.

Modify frontend files:

- `frontend/src/lib/documentTypes.ts`: allowed output formats.
- `frontend/src/lib/documentDesigns.ts`: output format and XLSX template fields.
- `frontend/src/lib/documentIssuances.ts`: format-aware labels and filenames.
- `frontend/src/pages/AuthenticatedShell.tsx`: routes/navigation for XLSX templates if content nav is centralized there.
- `frontend/src/pages/content/ContentLibraryPage.tsx`: entry point for XLSX templates.
- `frontend/src/pages/document-types/DocumentTypeCreatePage.tsx`
- `frontend/src/pages/document-types/DocumentTypeDetailPage.tsx`
- `frontend/src/pages/document-designs/DocumentDesignCreatePage.tsx`
- `frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx`
- `frontend/src/pages/document-issuances/DocumentLibraryPage.tsx`
- `frontend/src/pages/document-issuances/DocumentIssuanceDetailPage.tsx`

---

### Task 1: Format-Aware Database Contract

**Files:**

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

**Interfaces:**

- Produces: `DocumentType.allowed_output_formats: list[str]`, default `["pdf"]`.
- Produces: `XlsxTemplate` SQLAlchemy model and `xlsx_templates` table.
- Produces: `DocumentDesign.output_format: str`, default `"pdf"`.
- Produces: `DocumentDesign.xlsx_template_id: UUID | None`.
- Produces: `DocumentIssuance.output_format: str`, `mime_type: str | None`, `filename: str | None`, `preview_storage_key: str | None`.
- Later tasks consume these fields in API, worker, and frontend clients.

- [ ] **Step 1: Write failing schema/model tests**

Create `backend/tests/test_xlsx_format_contract.py`:

```python
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
        document_type_id="00000000-0000-0000-0000-000000000001",
        name="Workbook design",
        description=None,
        output_format="xlsx",
        xlsx_template_id="00000000-0000-0000-0000-000000000002",
        mock_data=None,
    )

    assert payload.output_format == "xlsx"
    assert payload.xlsx_template_id is not None
    assert DESIGN_OUTPUT_FORMATS == ("pdf", "xlsx")
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
rtk pytest backend/tests/test_xlsx_format_contract.py -q
```

Expected: fail because fields/constants are not defined yet.

- [ ] **Step 3: Add model fields and constants**

Implement these exact concepts:

```python
# backend/app/models/xlsx_template.py
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class XlsxTemplate(Base):
    __tablename__ = "xlsx_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_types.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(index=True)
    description: Mapped[str | None] = mapped_column(nullable=True)
    storage_key: Mapped[str]
    original_filename: Mapped[str]
    detected_sheets: Mapped[list[dict]] = mapped_column(JSON, default=list)
    detected_tokens: Mapped[list[str]] = mapped_column(JSON, default=list)
    image_slots: Mapped[list[dict]] = mapped_column(JSON, default=list)
    validation_warnings: Mapped[list[dict]] = mapped_column(JSON, default=list)
    mock_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    document_type: Mapped["DocumentType"] = relationship()
    created_by: Mapped["User"] = relationship()
```

```python
# backend/app/models/document_type.py
DEFAULT_OUTPUT_FORMATS = ["pdf"]

allowed_output_formats: Mapped[list[str]] = mapped_column(JSON, default=list)
```

```python
# backend/app/models/document_design.py
DESIGN_OUTPUT_FORMATS = ("pdf", "xlsx")

output_format: Mapped[str] = mapped_column(default="pdf")
xlsx_template_id: Mapped[uuid.UUID | None] = mapped_column(
    ForeignKey("xlsx_templates.id", ondelete="RESTRICT"),
    nullable=True,
)
xlsx_template: Mapped["XlsxTemplate | None"] = relationship()
```

```python
# backend/app/models/document_issuance.py
output_format: Mapped[str] = mapped_column(default="pdf")
mime_type: Mapped[str | None] = mapped_column(nullable=True, default=None)
filename: Mapped[str | None] = mapped_column(nullable=True, default=None)
preview_storage_key: Mapped[str | None] = mapped_column(nullable=True, default=None)
```

- [ ] **Step 4: Add Alembic migration**

Create `backend/alembic/versions/0015_xlsx_generation.py` with upgrade operations:

```python
from alembic import op
import sqlalchemy as sa

revision = "0015_xlsx_generation"
down_revision = "0014_template_ai_proposals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document_types", sa.Column("allowed_output_formats", sa.JSON(), nullable=True))
    op.execute("UPDATE document_types SET allowed_output_formats = '[\"pdf\"]' WHERE allowed_output_formats IS NULL")
    op.alter_column("document_types", "allowed_output_formats", nullable=False)

    op.create_table(
        "xlsx_templates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("document_type_id", sa.Uuid(), sa.ForeignKey("document_types.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("storage_key", sa.String(), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("detected_sheets", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("detected_tokens", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("image_slots", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("validation_warnings", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("mock_data", sa.JSON(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ix_xlsx_templates_name"), "xlsx_templates", ["name"], unique=False)

    op.add_column("document_designs", sa.Column("output_format", sa.String(), nullable=True))
    op.execute("UPDATE document_designs SET output_format = 'pdf' WHERE output_format IS NULL")
    op.alter_column("document_designs", "output_format", nullable=False)
    op.add_column("document_designs", sa.Column("xlsx_template_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_document_designs_xlsx_template_id",
        "document_designs",
        "xlsx_templates",
        ["xlsx_template_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.add_column("document_issuances", sa.Column("output_format", sa.String(), nullable=True))
    op.execute("UPDATE document_issuances SET output_format = 'pdf' WHERE output_format IS NULL")
    op.alter_column("document_issuances", "output_format", nullable=False)
    op.add_column("document_issuances", sa.Column("mime_type", sa.String(), nullable=True))
    op.add_column("document_issuances", sa.Column("filename", sa.String(), nullable=True))
    op.add_column("document_issuances", sa.Column("preview_storage_key", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("document_issuances", "preview_storage_key")
    op.drop_column("document_issuances", "filename")
    op.drop_column("document_issuances", "mime_type")
    op.drop_column("document_issuances", "output_format")
    op.drop_constraint("fk_document_designs_xlsx_template_id", "document_designs", type_="foreignkey")
    op.drop_column("document_designs", "xlsx_template_id")
    op.drop_column("document_designs", "output_format")
    op.drop_index(op.f("ix_xlsx_templates_name"), table_name="xlsx_templates")
    op.drop_table("xlsx_templates")
    op.drop_column("document_types", "allowed_output_formats")
```

- [ ] **Step 5: Update schemas**

Add fields with defaults:

```python
allowed_output_formats: list[str] = ["pdf"]
output_format: str = "pdf"
xlsx_template_id: UUID | None = None
mime_type: str | None = None
filename: str | None = None
preview_storage_key: str | None = None
```

- [ ] **Step 6: Run tests**

Run:

```powershell
rtk pytest backend/tests/test_xlsx_format_contract.py -q
rtk pytest backend/tests/test_document_types.py backend/tests/test_document_designs.py backend/tests/test_document_issuances.py -q
```

Expected: new test passes; existing tests pass or fail only where assertions need format fields added to expected payloads.

- [ ] **Step 7: Commit**

```powershell
rtk git add backend/alembic/versions/0015_xlsx_generation.py backend/app/models backend/app/schemas backend/tests/test_xlsx_format_contract.py
rtk git commit -m "feat: add format-aware document contract"
```

---

### Task 2: XLSX Template Model, Analysis, And Upload API

**Files:**

- Create: `backend/app/schemas/xlsx_template.py`
- Create: `backend/app/services/xlsx_analysis.py`
- Create: `backend/app/api/xlsx_templates.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/pyproject.toml`
- Modify: `backend/alembic/versions/0015_xlsx_generation.py`
- Test: `backend/tests/test_xlsx_analysis.py`
- Test: `backend/tests/test_xlsx_templates_api.py`

**Interfaces:**

- Consumes: `DocumentType.allowed_output_formats` from Task 1.
- Produces: `analyze_xlsx_template(workbook_bytes: bytes, schema_tokens: set[str]) -> XlsxTemplateAnalysis`.
- Produces API routes under `/api/xlsx-templates`.
- Consumes `XlsxTemplate` model from Task 1 and produces upload/list/detail API consumed by design creation and renderer.

- [ ] **Step 1: Write failing analysis tests**

Create `backend/tests/test_xlsx_analysis.py`:

```python
from io import BytesIO

from openpyxl import Workbook

from app.services.xlsx_analysis import analyze_xlsx_template


def workbook_bytes() -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Summary"
    worksheet["A1"] = "Customer"
    worksheet["B1"] = "{{cliente.nombre}}"
    worksheet.print_area = "A1:B10"
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_analyze_extracts_sheets_tokens_and_print_area():
    analysis = analyze_xlsx_template(workbook_bytes(), {"cliente.nombre"})

    assert analysis.detected_tokens == ["cliente.nombre"]
    assert analysis.detected_sheets[0]["name"] == "Summary"
    assert analysis.detected_sheets[0]["print_area"] == ["'Summary'!$A$1:$B$10"]
    assert analysis.validation_warnings == []


def test_analyze_warns_on_unknown_schema_token():
    analysis = analyze_xlsx_template(workbook_bytes(), set())

    assert analysis.validation_warnings[0]["type"] == "unknown_schema_token"
    assert analysis.validation_warnings[0]["cell"] == "B1"
```

- [ ] **Step 2: Run failing analysis tests**

```powershell
rtk pytest backend/tests/test_xlsx_analysis.py -q
```

Expected: fail because `openpyxl` dependency and analysis module are missing.

- [ ] **Step 3: Add dependency**

Add to `backend/pyproject.toml` dependencies:

```toml
"openpyxl>=3.1.5",
"pillow>=11.0.0",
```

Then run:

```powershell
rtk uv lock
```

Expected: lockfile updates successfully.

- [ ] **Step 4: Implement analysis service**

Create `backend/app/services/xlsx_analysis.py`:

```python
import re
from dataclasses import dataclass
from io import BytesIO

from openpyxl import load_workbook

TOKEN_RE = re.compile(r"{{\s*([a-zA-Z_][\w.\[\]]*)\s*}}")


@dataclass
class XlsxTemplateAnalysis:
    detected_sheets: list[dict]
    detected_tokens: list[str]
    image_slots: list[dict]
    validation_warnings: list[dict]


def analyze_xlsx_template(workbook_bytes: bytes, schema_tokens: set[str]) -> XlsxTemplateAnalysis:
    workbook = load_workbook(BytesIO(workbook_bytes))
    tokens: list[str] = []
    warnings: list[dict] = []
    sheets: list[dict] = []

    for worksheet in workbook.worksheets:
        sheets.append(
            {
                "name": worksheet.title,
                "max_row": worksheet.max_row,
                "max_column": worksheet.max_column,
                "print_area": list(worksheet.print_area or []),
                "merged_ranges": [str(rng) for rng in worksheet.merged_cells.ranges],
            }
        )
        for row in worksheet.iter_rows():
            for cell in row:
                if not isinstance(cell.value, str):
                    continue
                for match in TOKEN_RE.finditer(cell.value):
                    token = match.group(1)
                    if token not in tokens:
                        tokens.append(token)
                    if token not in schema_tokens:
                        warnings.append(
                            {
                                "type": "unknown_schema_token",
                                "sheet": worksheet.title,
                                "cell": cell.coordinate,
                                "message": f"Token '{token}' is not declared by the document type schema.",
                                "suggestion": "Add the token to the document type schema or correct the cell token.",
                            }
                        )

    return XlsxTemplateAnalysis(
        detected_sheets=sheets,
        detected_tokens=tokens,
        image_slots=[],
        validation_warnings=warnings,
    )
```

- [ ] **Step 5: Run analysis tests**

```powershell
rtk pytest backend/tests/test_xlsx_analysis.py -q
```

Expected: pass.

- [ ] **Step 6: Verify migration table**

Verify `backend/alembic/versions/0015_xlsx_generation.py` already creates `xlsx_templates` before adding `document_designs.xlsx_template_id` FK, as specified in Task 1.

- [ ] **Step 7: Add schemas and upload route**

Create schemas:

```python
class XlsxTemplateDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    document_type_id: UUID
    document_type_name: str
    name: str
    description: str | None
    original_filename: str
    detected_sheets: list[dict]
    detected_tokens: list[str]
    image_slots: list[dict]
    validation_warnings: list[dict]
    mock_data: dict | None
    created_by_email: str
    created_at: datetime
```

Create router behavior:

```python
@router.post("", response_model=XlsxTemplateDetail, status_code=201)
def upload_xlsx_template(
    document_type_id: UUID = Form(...),
    name: str = Form(...),
    description: str | None = Form(None),
    file: UploadFile = File(...),
    ...
) -> XlsxTemplateDetail:
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are supported")
```

Use `storage_provider.save(..., category="xlsx_templates")` if the interface supports arbitrary categories; otherwise add the category to local/S3 providers in this task.

- [ ] **Step 8: Write and run API tests**

Create API tests that upload a valid workbook and assert response fields:

```python
def test_upload_xlsx_template_extracts_tokens(client, auth_headers, document_type):
    file_bytes = workbook_bytes_with_token("{{cliente.nombre}}")
    response = client.post(
        "/api/xlsx-templates",
        data={"document_type_id": str(document_type.id), "name": "Template"},
        files={"file": ("template.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert response.json()["detected_tokens"] == ["cliente.nombre"]
```

Run:

```powershell
rtk pytest backend/tests/test_xlsx_analysis.py backend/tests/test_xlsx_templates_api.py -q
```

Expected: pass.

- [ ] **Step 9: Commit**

```powershell
rtk git add backend/pyproject.toml backend/uv.lock backend/alembic/versions/0015_xlsx_generation.py backend/app/schemas/xlsx_template.py backend/app/services/xlsx_analysis.py backend/app/api/xlsx_templates.py backend/app/main.py backend/tests/test_xlsx_analysis.py backend/tests/test_xlsx_templates_api.py
rtk git commit -m "feat: add xlsx template upload and analysis"
```

---

### Task 3: XLSX Renderer, Repeated Rows, And Image Normalization

**Files:**

- Create: `backend/app/services/xlsx_images.py`
- Create: `backend/app/services/xlsx_renderer.py`
- Test: `backend/tests/test_xlsx_renderer.py`

**Interfaces:**

- Consumes: `XlsxTemplateAnalysis` and stored workbook bytes from Task 2.
- Produces: `render_xlsx_template(workbook_bytes: bytes, payload: dict, image_values: dict | None = None) -> bytes`.
- Produces: `preview_xlsx_template(workbook_bytes: bytes, payload: dict) -> XlsxPreview`.
- Produces: `normalize_image_value(value: object) -> NormalizedImage`.

- [ ] **Step 1: Write failing renderer tests**

Create `backend/tests/test_xlsx_renderer.py`:

```python
from io import BytesIO

from openpyxl import Workbook, load_workbook

from app.services.xlsx_renderer import render_xlsx_template


def workbook_bytes() -> bytes:
    workbook = Workbook()
    ws = workbook.active
    ws.title = "Summary"
    ws["A1"] = "Customer"
    ws["B1"] = "{{cliente.nombre}}"
    ws.column_dimensions["B"].width = 30
    ws.print_area = "A1:B10"
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_render_replaces_cell_token_and_preserves_print_area():
    output = render_xlsx_template(workbook_bytes(), {"cliente": {"nombre": "ACME"}})
    workbook = load_workbook(BytesIO(output))
    ws = workbook["Summary"]

    assert ws["B1"].value == "ACME"
    assert list(ws.print_area) == ["'Summary'!$A$1:$B$10"]
    assert ws.column_dimensions["B"].width == 30
```

- [ ] **Step 2: Run failing renderer test**

```powershell
rtk pytest backend/tests/test_xlsx_renderer.py::test_render_replaces_cell_token_and_preserves_print_area -q
```

Expected: fail because renderer does not exist.

- [ ] **Step 3: Implement simple sandboxed render**

Create `backend/app/services/xlsx_renderer.py`:

```python
from io import BytesIO

from jinja2.sandbox import SandboxedEnvironment
from openpyxl import load_workbook

env = SandboxedEnvironment(autoescape=False)


def render_xlsx_template(workbook_bytes: bytes, payload: dict, image_values: dict | None = None) -> bytes:
    workbook = load_workbook(BytesIO(workbook_bytes))
    for worksheet in workbook.worksheets:
        for row in worksheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and "{{" in cell.value:
                    cell.value = env.from_string(cell.value).render(payload)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
```

- [ ] **Step 4: Run simple render test**

```powershell
rtk pytest backend/tests/test_xlsx_renderer.py::test_render_replaces_cell_token_and_preserves_print_area -q
```

Expected: pass.

- [ ] **Step 5: Add repeated-row convention tests**

Use workbook row metadata convention in hidden comments or cell markers. Implement the first version as explicit JSON in a hidden defined name `_docman_repeats` containing:

```json
[{"sheet":"Items","row":2,"list":"items"}]
```

Test:

```python
def test_render_repeats_explicit_row_for_list_items():
    workbook = Workbook()
    ws = workbook.active
    ws.title = "Items"
    ws["A1"] = "Name"
    ws["B1"] = "Qty"
    ws["A2"] = "{{item.name}}"
    ws["B2"] = "{{item.qty}}"
    workbook.create_named_range("_docman_repeats", ws, "$Z$1")
    ws["Z1"] = '[{"sheet":"Items","row":2,"list":"items"}]'
    ws.column_dimensions["Z"].hidden = True
    buffer = BytesIO()
    workbook.save(buffer)

    output = render_xlsx_template(buffer.getvalue(), {"items": [{"name": "A", "qty": 1}, {"name": "B", "qty": 2}]})
    rendered = load_workbook(BytesIO(output))["Items"]

    assert rendered["A2"].value == "A"
    assert rendered["B2"].value == "1"
    assert rendered["A3"].value == "B"
    assert rendered["B3"].value == "2"
```

- [ ] **Step 6: Implement repeated-row rendering**

Add helpers:

```python
def _load_repeat_specs(workbook) -> list[dict]:
    # Read `_docman_repeats` defined name target cells and parse JSON.
    return specs


def _render_repeat_row(worksheet, row_index: int, items: list[dict]) -> None:
    # Insert rows for additional items, copy cell values/styles from template row,
    # then render each row with `item` in context.
```

Reject merged cells intersecting the repeated row with `ValueError("unsupported_merge_in_repeat_range")`.

- [ ] **Step 7: Add image normalization tests**

Create tests in same file or `backend/tests/test_xlsx_images.py`:

```python
from app.services.xlsx_images import normalize_image_value


def test_normalize_png_data_url():
    data_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="

    image = normalize_image_value(data_url)

    assert image.mime_type == "image/png"
    assert image.width >= 1
    assert image.height >= 1
```

- [ ] **Step 8: Implement image normalization**

Create `backend/app/services/xlsx_images.py`:

```python
from dataclasses import dataclass
import base64
from io import BytesIO

from PIL import Image


@dataclass
class NormalizedImage:
    mime_type: str
    content: bytes
    width: int
    height: int


def normalize_image_value(value: object) -> NormalizedImage:
    if not isinstance(value, str) or not value.startswith("data:image/"):
        raise ValueError("invalid_image_payload")
    header, encoded = value.split(",", 1)
    mime_type = header.removeprefix("data:").split(";", 1)[0]
    content = base64.b64decode(encoded, validate=True)
    with Image.open(BytesIO(content)) as image:
        width, height = image.size
    return NormalizedImage(mime_type=mime_type, content=content, width=width, height=height)
```

- [ ] **Step 9: Run renderer tests**

```powershell
rtk pytest backend/tests/test_xlsx_renderer.py backend/tests/test_xlsx_images.py -q
```

Expected: pass.

- [ ] **Step 10: Commit**

```powershell
rtk git add backend/app/services/xlsx_renderer.py backend/app/services/xlsx_images.py backend/tests/test_xlsx_renderer.py backend/tests/test_xlsx_images.py
rtk git commit -m "feat: render xlsx templates"
```

---

### Task 4: XLSX Design Creation And Activation Validation

**Files:**

- Modify: `backend/app/api/document_designs.py`
- Modify: `backend/app/services/design_validation.py`
- Modify: `backend/app/schemas/document_design.py`
- Test: `backend/tests/test_xlsx_designs.py`

**Interfaces:**

- Consumes: `XlsxTemplate` from Task 2.
- Consumes: `DocumentDesign.output_format` and `xlsx_template_id` from Task 1.
- Produces: XLSX document designs that activate only when template and document type match.

- [ ] **Step 1: Write failing design API tests**

Create `backend/tests/test_xlsx_designs.py`:

```python
def test_create_xlsx_design_requires_allowed_document_type_format(client, auth_headers, document_type):
    response = client.post(
        "/api/document-designs",
        json={
            "document_type_id": str(document_type.id),
            "name": "Workbook",
            "description": None,
            "output_format": "xlsx",
            "xlsx_template_id": "00000000-0000-0000-0000-000000000001",
            "mock_data": None,
        },
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Document type does not allow xlsx output"
```

- [ ] **Step 2: Run failing test**

```powershell
rtk pytest backend/tests/test_xlsx_designs.py -q
```

Expected: fail because API does not validate `output_format`.

- [ ] **Step 3: Implement create/update validation**

In `create_document_design`, before creating model:

```python
if payload.output_format not in document_type.allowed_output_formats:
    raise HTTPException(status_code=400, detail=f"Document type does not allow {payload.output_format} output")
if payload.output_format == "xlsx" and payload.xlsx_template_id is None:
    raise HTTPException(status_code=400, detail="XLSX designs require xlsx_template_id")
if payload.output_format == "pdf" and payload.xlsx_template_id is not None:
    raise HTTPException(status_code=400, detail="PDF designs cannot reference an XLSX template")
```

Load `XlsxTemplate` and ensure `xlsx_template.document_type_id == document_type.id`.

- [ ] **Step 4: Add activation validation**

In `backend/app/services/design_validation.py`, make `validate_design_activation` branch:

```python
if design.output_format == "xlsx":
    if design.xlsx_template_id is None:
        raise ValueError("XLSX designs require a template before activation")
    if design.xlsx_template.validation_warnings:
        raise ValueError("XLSX template has validation warnings")
    return
```

Keep existing PDF page validation untouched.

- [ ] **Step 5: Run tests**

```powershell
rtk pytest backend/tests/test_xlsx_designs.py backend/tests/test_document_designs.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```powershell
rtk git add backend/app/api/document_designs.py backend/app/services/design_validation.py backend/app/schemas/document_design.py backend/tests/test_xlsx_designs.py
rtk git commit -m "feat: support xlsx document designs"
```

---

### Task 5: Format-Aware Worker And Issuance Download

**Files:**

- Create: `backend/app/services/document_generation.py`
- Modify: `backend/app/services/issuance_jobs.py`
- Modify: `backend/app/workers/document_generation.py`
- Modify: `backend/app/api/document_designs.py`
- Modify: `backend/app/api/issuances.py`
- Modify: `backend/app/schemas/document_issuance.py`
- Test: `backend/tests/test_xlsx_issuance_generation.py`
- Test: existing issuance tests.

**Interfaces:**

- Consumes: `render_xlsx_template(...) -> bytes` from Task 3.
- Produces: `generate_document_file(issuance: DocumentIssuance, db: Session, storage_provider: StorageProvider) -> GeneratedDocument`.
- Produces: downloads with XLSX MIME type and `.xlsx` filename.

- [ ] **Step 1: Write failing generation service test**

Create `backend/tests/test_xlsx_issuance_generation.py`:

```python
from app.services.document_generation import XLSX_MIME_TYPE


def test_xlsx_mime_type_constant():
    assert XLSX_MIME_TYPE == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
```

- [ ] **Step 2: Run failing test**

```powershell
rtk pytest backend/tests/test_xlsx_issuance_generation.py::test_xlsx_mime_type_constant -q
```

Expected: fail because service does not exist.

- [ ] **Step 3: Implement generation dispatcher**

Create `backend/app/services/document_generation.py`:

```python
from dataclasses import dataclass

from sqlalchemy.orm import Session as SQLAlchemySession

from app.models.document_issuance import DocumentIssuance
from app.services.pdf_generator import generate_composed_pdf
from app.services.storage.base import StorageProvider
from app.services.xlsx_renderer import render_xlsx_template

PDF_MIME_TYPE = "application/pdf"
XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@dataclass
class GeneratedDocument:
    content: bytes
    mime_type: str
    filename: str
    extension: str


def generate_document_file(
    issuance: DocumentIssuance,
    db: SQLAlchemySession,
    storage_provider: StorageProvider,
) -> GeneratedDocument:
    design = issuance.design_version
    if design.output_format == "xlsx":
        workbook_bytes = storage_provider.get(design.xlsx_template.storage_key, category="xlsx_templates")
        content = render_xlsx_template(workbook_bytes, issuance.input_data)
        return GeneratedDocument(
            content=content,
            mime_type=XLSX_MIME_TYPE,
            filename=f"{issuance.id}.xlsx",
            extension="xlsx",
        )

    content = generate_composed_pdf(design, issuance.input_data, db, storage_provider, mock_fallback=False)
    return GeneratedDocument(
        content=content,
        mime_type=PDF_MIME_TYPE,
        filename=f"{issuance.id}.pdf",
        extension="pdf",
    )
```

- [ ] **Step 4: Update worker**

In `backend/app/workers/document_generation.py`, replace direct `generate_composed_pdf` call with `generate_document_file`. Save using generated extension:

```python
generated = generate_document_file(issuance, db, storage_provider)
storage_key = storage_provider.save(
    f"{issuance.id}.{generated.extension}",
    generated.content,
    category="issuances",
)
issuance.storage_key = storage_key
issuance.output_format = issuance.design_version.output_format
issuance.mime_type = generated.mime_type
issuance.filename = generated.filename
```

Keep status transitions and retry handling unchanged.

- [ ] **Step 5: Update enqueue naming**

In `backend/app/services/issuance_jobs.py`, keep public function name if too many callers depend on it, but route to generic task:

```python
def enqueue_document_generation(issuance_id: str) -> str:
    from app.workers.document_generation import generate_document
    task = generate_document.delay(issuance_id)
    return str(task.id)
```

Keep a backwards-compatible task alias if tests import `generate_document_pdf`.

- [ ] **Step 6: Update issuance responses**

In `backend/app/api/issuances.py`, replace `_pdf_response` with:

```python
def _document_response(issuance: DocumentIssuance, storage_provider: StorageProvider, disposition: str = "attachment") -> Response:
    try:
        return storage_provider.get_download_response(
            issuance.storage_key,
            filename=issuance.filename or f"{issuance.id}.pdf",
            category="issuances",
            disposition=disposition,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Issued document file not found on storage")
```

Update ready error from `"Document PDF is not ready"` to `"Document file is not ready"`.

- [ ] **Step 7: Run tests**

```powershell
rtk pytest backend/tests/test_xlsx_issuance_generation.py backend/tests/test_document_issuances.py backend/tests/test_document_designs.py -q
```

Expected: pass.

- [ ] **Step 8: Commit**

```powershell
rtk git add backend/app/services/document_generation.py backend/app/services/issuance_jobs.py backend/app/workers/document_generation.py backend/app/api/document_designs.py backend/app/api/issuances.py backend/app/schemas/document_issuance.py backend/tests/test_xlsx_issuance_generation.py
rtk git commit -m "feat: generate xlsx document issuances"
```

---

### Task 6: XLSX Preview API

**Files:**

- Modify: `backend/app/services/xlsx_renderer.py`
- Modify: `backend/app/schemas/xlsx_template.py`
- Modify: `backend/app/api/xlsx_templates.py`
- Test: `backend/tests/test_xlsx_preview.py`

**Interfaces:**

- Consumes: `render_xlsx_template` from Task 3.
- Produces: `preview_xlsx_template(workbook_bytes: bytes, payload: dict) -> XlsxPreview`.
- Produces: `POST /api/xlsx-templates/{id}/preview`.

- [ ] **Step 1: Write failing preview test**

Create `backend/tests/test_xlsx_preview.py`:

```python
def test_preview_returns_sheet_cells(client, auth_headers, xlsx_template):
    response = client.post(
        f"/api/xlsx-templates/{xlsx_template.id}/preview",
        json={"mock_data": {"cliente": {"nombre": "ACME"}}},
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sheets"][0]["name"] == "Summary"
    assert body["sheets"][0]["cells"][0]["address"] == "B1"
    assert body["sheets"][0]["cells"][0]["value"] == "ACME"
```

- [ ] **Step 2: Run failing test**

```powershell
rtk pytest backend/tests/test_xlsx_preview.py -q
```

Expected: fail because preview endpoint/model is incomplete.

- [ ] **Step 3: Add preview schemas**

In `backend/app/schemas/xlsx_template.py`:

```python
class XlsxTemplatePreviewRequest(BaseModel):
    mock_data: dict | None = None


class XlsxPreviewCell(BaseModel):
    address: str
    value: str | int | float | bool | None
    style: dict = {}


class XlsxPreviewSheet(BaseModel):
    name: str
    max_row: int
    max_column: int
    merged_ranges: list[str]
    cells: list[XlsxPreviewCell]


class XlsxTemplatePreviewResponse(BaseModel):
    sheets: list[XlsxPreviewSheet]
    warnings: list[dict] = []
```

- [ ] **Step 4: Implement preview service**

In `backend/app/services/xlsx_renderer.py`:

```python
def preview_xlsx_template(workbook_bytes: bytes, payload: dict) -> dict:
    rendered = render_xlsx_template(workbook_bytes, payload)
    workbook = load_workbook(BytesIO(rendered), data_only=False)
    sheets = []
    for worksheet in workbook.worksheets:
        cells = []
        for row in worksheet.iter_rows():
            for cell in row:
                if cell.value is not None:
                    cells.append({"address": cell.coordinate, "value": cell.value, "style": {}})
        sheets.append(
            {
                "name": worksheet.title,
                "max_row": worksheet.max_row,
                "max_column": worksheet.max_column,
                "merged_ranges": [str(rng) for rng in worksheet.merged_cells.ranges],
                "cells": cells,
            }
        )
    return {"sheets": sheets, "warnings": []}
```

- [ ] **Step 5: Add route**

In `backend/app/api/xlsx_templates.py`:

```python
@router.post("/{template_id}/preview", response_model=XlsxTemplatePreviewResponse)
def preview_xlsx_template_route(...):
    template = _require_xlsx_template(db, template_id)
    workbook_bytes = storage_provider.get(template.storage_key, category="xlsx_templates")
    payload = request.mock_data or template.mock_data or {}
    return preview_xlsx_template(workbook_bytes, payload)
```

- [ ] **Step 6: Run preview tests**

```powershell
rtk pytest backend/tests/test_xlsx_preview.py backend/tests/test_xlsx_templates_api.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```powershell
rtk git add backend/app/services/xlsx_renderer.py backend/app/schemas/xlsx_template.py backend/app/api/xlsx_templates.py backend/tests/test_xlsx_preview.py
rtk git commit -m "feat: add xlsx template preview api"
```

---

### Task 7: Frontend XLSX Template Management And Preview

**Files:**

- Create: `frontend/src/lib/xlsxTemplates.ts`
- Create: `frontend/src/pages/content/XlsxTemplatesPage.tsx`
- Create: `frontend/src/pages/content/XlsxTemplateUploadPage.tsx`
- Create: `frontend/src/pages/content/XlsxTemplateDetailPage.tsx`
- Create: `frontend/src/pages/content/components/XlsxPreviewGrid.tsx`
- Modify: `frontend/src/pages/AuthenticatedShell.tsx`
- Modify: `frontend/src/pages/content/ContentLibraryPage.tsx`
- Modify: `frontend/src/lib/documentTypes.ts`
- Modify: `frontend/src/lib/documentDesigns.ts`
- Modify: `frontend/src/lib/documentIssuances.ts`
- Modify: `frontend/src/pages/document-types/DocumentTypeCreatePage.tsx`
- Modify: `frontend/src/pages/document-designs/DocumentDesignCreatePage.tsx`
- Modify: `frontend/src/pages/document-issuances/DocumentLibraryPage.tsx`

**Interfaces:**

- Consumes backend routes from Tasks 2 and 6.
- Produces upload/list/detail/preview UX for XLSX templates.
- Produces output format selection for document types and document designs.

- [ ] **Step 1: Add API client**

Create `frontend/src/lib/xlsxTemplates.ts`:

```ts
import { apiFetch, jsonOrError } from "./api";

export interface XlsxTemplateDetail {
  id: string;
  document_type_id: string;
  document_type_name: string;
  name: string;
  description?: string | null;
  original_filename: string;
  detected_sheets: Array<Record<string, unknown>>;
  detected_tokens: string[];
  image_slots: Array<Record<string, unknown>>;
  validation_warnings: Array<Record<string, unknown>>;
  mock_data?: Record<string, unknown> | null;
  created_by_email: string;
  created_at: string;
}

export interface XlsxPreviewResponse {
  sheets: Array<{
    name: string;
    max_row: number;
    max_column: number;
    merged_ranges: string[];
    cells: Array<{ address: string; value: string | number | boolean | null; style: Record<string, unknown> }>;
  }>;
  warnings: Array<Record<string, unknown>>;
}

export async function listXlsxTemplates(documentTypeId?: string): Promise<XlsxTemplateDetail[]> {
  const query = documentTypeId ? `?document_type_id=${encodeURIComponent(documentTypeId)}` : "";
  return jsonOrError(await apiFetch(`/api/xlsx-templates${query}`));
}

export async function uploadXlsxTemplate(payload: {
  documentTypeId: string;
  name: string;
  description?: string | null;
  file: File;
}): Promise<XlsxTemplateDetail> {
  const formData = new FormData();
  formData.append("document_type_id", payload.documentTypeId);
  formData.append("name", payload.name);
  if (payload.description) formData.append("description", payload.description);
  formData.append("file", payload.file);
  return jsonOrError(await apiFetch("/api/xlsx-templates", { method: "POST", body: formData }));
}

export async function previewXlsxTemplate(id: string, mockData?: Record<string, unknown>): Promise<XlsxPreviewResponse> {
  return jsonOrError(
    await apiFetch(`/api/xlsx-templates/${id}/preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mock_data: mockData ?? {} }),
    }),
  );
}
```

- [ ] **Step 2: Run TypeScript check**

```powershell
rtk npm --prefix frontend run typecheck
```

Expected: fail if no script exists or routes not imported; if no typecheck script exists, use:

```powershell
rtk npm --prefix frontend run build
```

- [ ] **Step 3: Build preview grid**

Create `XlsxPreviewGrid.tsx`:

```tsx
import type { XlsxPreviewResponse } from "../../../lib/xlsxTemplates";

export function XlsxPreviewGrid({ preview }: { preview: XlsxPreviewResponse }) {
  const sheet = preview.sheets[0];
  if (!sheet) return <p className="text-sm text-on-surface-variant">No preview available.</p>;
  const byAddress = new Map(sheet.cells.map((cell) => [cell.address, cell]));
  const columns = Array.from({ length: Math.min(sheet.max_column, 12) }, (_, index) => index + 1);
  const rows = Array.from({ length: Math.min(sheet.max_row, 40) }, (_, index) => index + 1);

  function address(row: number, column: number): string {
    return `${String.fromCharCode(64 + column)}${row}`;
  }

  return (
    <div className="overflow-auto border border-outline">
      <table className="min-w-full border-collapse text-xs">
        <tbody>
          {rows.map((row) => (
            <tr key={row}>
              {columns.map((column) => {
                const cell = byAddress.get(address(row, column));
                return (
                  <td key={column} className="h-8 min-w-24 border border-outline-variant px-2 align-top">
                    {cell?.value == null ? "" : String(cell.value)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 4: Build upload/list/detail pages**

Follow existing content page patterns from `TemplatesPage.tsx` and `StaticPdfUploadPage.tsx`. Required behavior:

```tsx
await uploadXlsxTemplate({ documentTypeId, name, description, file });
```

Detail page loads template, calls `previewXlsxTemplate(template.id, template.mock_data ?? {})`, and renders `XlsxPreviewGrid`.

- [ ] **Step 5: Add routes and nav**

Add routes under content:

```tsx
<Route path="/content/xlsx-templates" element={<XlsxTemplatesPage />} />
<Route path="/content/xlsx-templates/upload" element={<XlsxTemplateUploadPage />} />
<Route path="/content/xlsx-templates/:id" element={<XlsxTemplateDetailPage />} />
```

Add a content library entry named `XLSX Templates`.

- [ ] **Step 6: Add format controls**

In document type create/edit UI, add checkboxes for `pdf` and `xlsx`, defaulting to `pdf`.

In document design create UI, add an output format selector filtered by selected document type allowed formats. When `xlsx` is selected, show XLSX template selector. When `pdf` is selected, preserve current behavior.

- [ ] **Step 7: Build frontend**

```powershell
rtk npm --prefix frontend run build
```

Expected: pass.

- [ ] **Step 8: Commit**

```powershell
rtk git add frontend/src/lib/xlsxTemplates.ts frontend/src/pages/content/XlsxTemplatesPage.tsx frontend/src/pages/content/XlsxTemplateUploadPage.tsx frontend/src/pages/content/XlsxTemplateDetailPage.tsx frontend/src/pages/content/components/XlsxPreviewGrid.tsx frontend/src/pages/AuthenticatedShell.tsx frontend/src/pages/content/ContentLibraryPage.tsx frontend/src/lib/documentTypes.ts frontend/src/lib/documentDesigns.ts frontend/src/lib/documentIssuances.ts frontend/src/pages/document-types/DocumentTypeCreatePage.tsx frontend/src/pages/document-designs/DocumentDesignCreatePage.tsx frontend/src/pages/document-issuances/DocumentLibraryPage.tsx
rtk git commit -m "feat: add xlsx template frontend"
```

---

### Task 8: End-To-End Verification And Polish

**Files:**

- Modify: `tests/DocManagement.postman_collection.json` if API collection is maintained.
- Modify: `docs/superpowers/specs/2026-07-16-xlsx-template-generation-design.md` only if implementation discovered a design correction.
- Modify: `docs/superpowers/plans/2026-07-16-xlsx-template-generation.md` to check off completed steps if executing inline.

**Interfaces:**

- Consumes all previous tasks.
- Produces verified feature with no known regressions in PDF generation.

- [ ] **Step 1: Run backend XLSX tests**

```powershell
rtk pytest backend/tests/test_xlsx_format_contract.py backend/tests/test_xlsx_analysis.py backend/tests/test_xlsx_templates_api.py backend/tests/test_xlsx_renderer.py backend/tests/test_xlsx_preview.py backend/tests/test_xlsx_designs.py backend/tests/test_xlsx_issuance_generation.py -q
```

Expected: pass.

- [ ] **Step 2: Run backend regression tests for affected areas**

```powershell
rtk pytest backend/tests/test_document_types.py backend/tests/test_document_designs.py backend/tests/test_document_issuances.py backend/tests/test_template_ai_proposals.py -q
```

Expected: pass.

- [ ] **Step 3: Run frontend build**

```powershell
rtk npm --prefix frontend run build
```

Expected: pass.

- [ ] **Step 4: Manual API smoke test**

Start services according to existing repo workflow, then verify:

```powershell
rtk docker compose up -d postgres redis backend frontend
```

Smoke path:

1. Create or use a document type with allowed formats `["pdf", "xlsx"]`.
2. Upload a workbook containing `{{cliente.nombre}}`.
3. Create an XLSX design linked to that template.
4. Activate the design.
5. Generate an issuance with `{"cliente":{"nombre":"ACME"}}`.
6. Download the issuance.
7. Open the workbook and confirm the rendered cell value is `ACME`.

- [ ] **Step 5: Check worktree**

```powershell
rtk git status --short
```

Expected: only intentional files changed. Existing unrelated dirty files from before this feature must not be reverted.

- [ ] **Step 6: Final commit if needed**

```powershell
rtk git add tests/DocManagement.postman_collection.json docs/superpowers/specs/2026-07-16-xlsx-template-generation-design.md docs/superpowers/plans/2026-07-16-xlsx-template-generation.md
rtk git commit -m "test: verify xlsx generation workflow"
```

Skip this commit if no files changed in this task.

---

## Self-Review Notes

- Spec coverage: document type allowed formats, design output format, XLSX upload, validation, render, image normalization, preview, worker generation, download/share, frontend management, and tests are covered.
- Scope: the plan is large but each task is independently testable. It should be executed task-by-task, with review after each task.
- Known dependency: commit steps may fail in this current sandbox if `.git/index.lock` cannot be created. If that happens, keep the file changes and report the exact git permission error instead of retrying destructive commands.
