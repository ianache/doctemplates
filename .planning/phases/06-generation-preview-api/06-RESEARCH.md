# Phase 6: Generation & Preview API - Research

This research document answers "What do I need to know to PLAN this phase well?" for Phase 6.

## User Constraints (from CONTEXT.md)

As decided in [06-CONTEXT.md](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/phases/06-generation-preview-api/06-CONTEXT.md):

### PDF Rendering & Templating Engines
*   **D-01:** Use `xhtml2pdf` [ASSUMED] (pure Python ReportLab-based engine). Zero system-level binary dependencies. Installs cleanly on Windows.
*   **D-02:** Use `Jinja2` [ASSUMED] to interpolate Mustache/Handlebars-style tokens (e.g. `{{ cliente.nombre }}`) which handles nested dictionary resolution natively.
*   **D-03:** Style margins, headers, footers, and page numbers using standard CSS `@page` rules in a default base stylesheet (e.g., standard Letter/A4 layout).
*   **D-04:** Use standard built-in system/PDF fonts (Helvetica, Times, Courier) to ensure fast rendering and simple, zero-setup setup.

### Data Validation & Type Constraints
*   **D-05:** Reject request with `400 Bad Request` if any fields defined in the document type schema are missing from the API payload (guarantees legal documents are never generated blank/incomplete).
*   **D-06:** Ignore extra fields in the API payload that are not defined in the document type schema, rather than rejecting them.
*   **D-07:** Attempt to coerce payload types to the schema types (e.g., parsing numeric or boolean strings), raising `400 Bad Request` only if conversion fails.
*   **D-08:** Validate date fields against ISO 8601 `YYYY-MM-DD` format. Expose a custom formatting Jinja2 filter (e.g., `{{ date_val | date_format }}`) to allow document designs to render human-readable dates.

### Issuance Persistence & PDF Storage
*   **D-09:** Save generated production PDFs to disk (e.g. `storage/issuances/`) so they are immutable and re-downloadable.
*   **D-10:** Track each issuance in a new `DocumentIssuance` table recording the issuance ID, design version ID, file path, and user ID.
*   **D-11:** Use secure, collision-free UUID naming convention on disk (`{issuance_id}.pdf`).
*   **D-12:** Persist the raw JSON payload in a JSONB column (`input_data`) on the issuance record for debugging and historical validation.

### Preview API & Mock Data Sourcing
*   **D-13:** Accept optional caller-supplied preview data, falling back to auto-generated mock values based on field types (e.g. "Mock String", 123.45, current date, true) for any omitted fields.
*   **D-14:** Support preview generation for both `draft` and `active` versions of a document design (allows visual designer preview before activation).
*   **D-15:** Return the preview PDF as a raw binary stream with `Content-Type: application/pdf`.
*   **D-16:** Do not write preview files to disk or record any entries in the database; preview operations must remain in-memory and stateless.

---

## Technical Domain Investigation

### 1. HTML-to-PDF Generation via `xhtml2pdf` [ASSUMED]
*   **Engine & Mechanics**: `xhtml2pdf` [ASSUMED] converts HTML and CSS code to PDF format using the ReportLab toolkit. It runs entirely in Python, making it extremely easy to distribute and deploy compared to headless-browser-based solutions (like Playwright or WeasyPrint), which require compiling and installing system binaries [CITED: 06-DISCUSSION-LOG.md].
*   **CSS Constraints**: It supports standard HTML5 and CSS 2.1 properties [CITED: WebSearch]. It does **not** support modern CSS layouts like Flexbox or Grid. All layouts must be built using classic block/inline elements, absolute positioning, or table structures.
*   **Paged Media Layout**: Standard Letter/A4 layouts, page margins, headers, and footers must be defined using CSS `@page` and `@frame` rules:
    ```css
    @page {
        size: letter portrait;
        margin: 1in;
        @frame header_frame {
            -pdf-frame-content: header_content;
            left: 1in; top: 0.5in; width: 6.5in; height: 0.5in;
        }
        @frame content_frame {
            left: 1in; top: 1.2in; width: 6.5in; height: 8.6in;
        }
        @frame footer_frame {
            -pdf-frame-content: footer_content;
            left: 1in; bottom: 0.5in; width: 6.5in; height: 0.5in;
        }
    }
    ```
*   **Page Numbering**: Page numbers are injected dynamically by xhtml2pdf [ASSUMED] using custom XML tags `<pdf:pagenumber>` and `<pdf:pagecount>`.
*   **Standard Fonts**: Only Helvetica, Times-Roman, and Courier are available out of the box without loading custom external TrueType fonts [CITED: 06-CONTEXT.md].

### 2. PDF Slicing and Merging via `pypdf` [VERIFIED: backend/pyproject.toml]
*   The project already declares `pypdf>=6.1.0` in its backend dependencies [CITED: backend/pyproject.toml].
*   `pypdf.PdfWriter` allows joining multiple separate PDF streams/files together.
*   `pypdf.PdfReader` allows reading specific page subsets. Since uploaded static PDFs are already sliced to their selected page ranges upon upload (as implemented in [content_storage.py](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/backend/app/services/content_storage.py) [CITED: backend/app/services/content_storage.py]), we can directly merge the entire file found at `StaticPdfAsset.stored_path`.

### 3. Template Engine: Jinja2 [ASSUMED]
*   `Jinja2` [ASSUMED] is already present transitively in `uv.lock` via `headroom-ai`. We should add it explicitly to `backend/pyproject.toml` dependencies [CITED: backend/pyproject.toml].
*   We can register custom filters in the Jinja2 environment. For date formatting:
    ```python
    from datetime import datetime

    def date_format_filter(value: str, format_str: str = "%d/%m/%Y") -> str:
        if not value:
            return ""
        try:
            dt = datetime.strptime(value, "%Y-%m-%d")
            return dt.strftime(format_str)
        except Exception:
            return value
    ```
    This turns `"2026-07-08"` into `"08/07/2026"` by default in templates: `{{ date_val | date_format }}` [CITED: 06-CONTEXT.md].

---

## Core Architecture & Integration Points

### 1. Database Model for Issuances (`DocumentIssuance`)
We will create a new model inside `backend/app/models/document_issuance.py`:

```python
import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

class DocumentIssuance(Base):
    __tablename__ = "document_issuances"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    design_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_designs.id", ondelete="RESTRICT")
    )
    file_path: Mapped[str]
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    input_data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    design_version: Mapped["DocumentDesign"] = relationship()
    user: Mapped["User"] = relationship()
```
*   **ondelete="RESTRICT"** prevents deletion of a design version that has generated official issuances (audit safety).
*   A new Alembic migration `0007_document_issuances.py` will be created to generate the table.

### 2. Configuration Settings Update
Extend `Settings` in [config.py](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/backend/app/config.py) to configure the issuance output directory:
```python
    issuance_storage_root: str = "../.content-storage/issuances"
```

### 3. Generation Router Endpoint Implementations
We will add endpoints to `backend/app/api/document_designs.py` (or introduce a dedicated generator module):

#### A. Production Generation: `POST /api/document-designs/{design_id}/generate`
*   **Gated by Auth**: `user: User = Depends(get_current_user)`.
*   **Validation**: 
    1. Validate that the design is `active`. (Reject `draft` or `superseded` designs for production generation).
    2. Check if all fields defined in the document type schema are present in the payload (raise 400 if missing) [CITED: 06-CONTEXT.md].
    3. Coerce fields according to schema types (`string`, `number`, `boolean`, `date`). Raise 400 if coercion fails.
    4. Ignore extra fields.
*   **PDF Pipeline**:
    1. Render each page in sorted order.
        *   For `html_template` pages: Interpolate template string using Jinja2 with coerced inputs, render to PDF bytes via `xhtml2pdf` [ASSUMED].
        *   For `static_pdf` pages: Read the file at `stored_path` using `pypdf`.
    2. Merge all pages in order into a single `PdfWriter` stream.
    3. Save the final PDF to `{settings.issuance_storage_root}/{issuance_id}.pdf`.
    4. Write a record to `DocumentIssuance`.
*   **Response**: Return the raw PDF bytes with `Content-Type: application/pdf` and `Content-Disposition: attachment; filename="{issuance_id}.pdf"`. Add the header `X-Issuance-ID: {issuance_id}` for convenience.

#### B. Ephemeral Preview: `POST /api/document-designs/{design_id}/preview`
*   **Gated by Auth**: `user: User = Depends(get_current_user)`.
*   **Validation & Fallbacks**:
    1. Allow previewing **both** `draft` and `active` versions of a design [CITED: 06-CONTEXT.md].
    2. If fields defined in the schema are missing from the input data, auto-generate fallback mock values [CITED: 06-CONTEXT.md]:
        *   `string` -> `"{field_name}_val"`
        *   `number` -> `123.45`
        *   `boolean` -> `True`
        *   `date` -> current date `YYYY-MM-DD`
    3. Validate and coerce input data for fields that were supplied.
*   **PDF Pipeline**: Same rendering and merging pipeline, except:
    *   No files written to disk.
    *   No database records written.
    *   Executed completely in-memory using `io.BytesIO`.
*   **Response**: Return raw PDF bytes with `Content-Type: application/pdf`.

#### C. Historical Retrieval: `GET /api/issuances/{issuance_id}/download` (Recommended addition)
*   Provides a way to retrieve and download a previously generated immutable PDF asset by its issuance ID.

---

## Implementation Pitfalls & Patterns

### 1. Token Dot-Notation Expansion Pitfall [HIGH]
*   **The Pitfall**: The system allows nested token names like `cliente.nombre` [CITED: CLAUDE.md]. If the payload is parsed as flat keys (`{"cliente.nombre": "Juan"}`), Jinja2's lookup `{{ cliente.nombre }}` will fail because Jinja2 expects a nested dictionary structure `{"cliente": {"nombre": "Juan"}}`.
*   **The Pattern**: Before rendering templates with Jinja2, the flat validated payload must be expanded recursively:
    ```python
    def expand_flat_dict(flat: dict[str, any]) -> dict[str, any]:
        nested = {}
        for key, val in flat.items():
            parts = key.split(".")
            d = nested
            for part in parts[:-1]:
                d = d.setdefault(part, {})
            d[parts[-1]] = val
        return nested
    ```

### 2. Strict Generation vs. Lenient Preview Validation [HIGH]
*   **The Pitfall**: Re-implementing validation logic separately for preview and generation leads to drift and bugs.
*   **The Pattern**: Implement a single validation/coercion function that accepts a `mock_fallback` flag:
    *   If `mock_fallback=False` (production): missing fields trigger `HTTPException(400)`.
    *   If `mock_fallback=True` (preview): missing fields get populated with default mock values.

### 3. Font Limitations in HTML Rendering [MEDIUM]
*   **The Pitfall**: Designing beautiful HTML templates using exotic fonts will cause them to look broken in the generated PDF, because `xhtml2pdf` [ASSUMED] only supports core standard fonts (Helvetica, Times, Courier) by default.
*   **The Pattern**: The default styling prepended to templates should explicitly set the font to Helvetica to avoid browser styling differences, and documentation should warn operational users to only use core PDF fonts.

---

## Assessment Table and Open Questions

### Confidence Assessment
| Feature Area | Confidence Level | Rationale |
| :--- | :--- | :--- |
| **PDF Merging (`pypdf`)** | **HIGH** | `pypdf` is already integrated and fully functional in prior phases. |
| **Jinja2 Rendering** | **HIGH** | Jinja2 is highly reliable and handles dot-notation keys easily via dictionary expansion. |
| **HTML PDF Generation (`xhtml2pdf`)** | **HIGH** | Fits standard ReportLab rendering needs, lightweight, and easy to run on Windows. |
| **Data Validation & Coercion** | **HIGH** | Simple schema validation loop with explicit parser rules. |
| **Database & Disk Persistence** | **HIGH** | Simple database tracking table and standard path storage. |

## Open Questions (RESOLVED)

1.  **Strict Mode for Extra Fields**: RESOLVED: Yes, log a warning when extra fields are received in the payload, but do not reject the request (ignore extra fields).
2.  **Superseded Version Generation**: RESOLVED: Yes, allow PDF generation for both `active` and `superseded` versions of a design to support historical reprints, but strictly block `draft` versions with `400 Bad Request`.
