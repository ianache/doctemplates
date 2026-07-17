# XLSX Template Generation Design

Date: 2026-07-16
Status: Design approved for user review

## Goal

Add XLSX as a first-class document emission format in DocManagement. A document type declares which output formats it supports, and each document design selects one format. For XLSX designs, users initially create templates by uploading existing `.xlsx` workbooks, then DocManagement validates them, renders them with the document type schema, inserts images, stores generated `.xlsx` emissions, and provides an approximate web preview.

The feature must support workbooks with multiple sheets and print-oriented page setup inside sheets. It must preserve Excel layout fidelity as much as practical while keeping the current PDF flow intact.

## Non-Goals

- Building a full spreadsheet editor in DocManagement for the first version.
- Supporting `.xls`, `.xlsm`, macros, external workbook links, or arbitrary Office automation.
- Generating PDF from XLSX in the first version.
- Creating an independent XLSX schema separate from the document type schema.
- Inferring complex repeated tables without an explicit template convention.

## Recommended Approach

Use a dedicated XLSX template and generation path, integrated into the existing document type, design, issuance, storage, and worker concepts. This keeps Excel-specific concerns such as sheets, print areas, row cloning, formulas, images, and workbook metadata out of the current PDF page composition model.

This approach avoids forcing XLSX workbooks into `DocumentDesignPage`, which is naturally PDF-oriented. It also avoids a standalone utility that would bypass versioning, validation, preview, download, share, and audit behavior.

## Architecture

Add `output_format` to document designs with initial values `pdf` and `xlsx`. Add allowed output formats to document types, so a document type can permit PDF, XLSX, or both, while each design chooses one format.

The existing PDF design behavior remains unchanged for PDF designs. XLSX designs reference an uploaded XLSX template and its validated metadata instead of using an ordered list of PDF-like pages.

Introduce a generation dispatcher in the worker path. The current worker concept changes from "generate PDF" to "generate document emission" and dispatches by format:

- PDF designs use the existing PDF generation service.
- XLSX designs use a new XLSX generation service.

`DocumentIssuance` becomes format-aware by storing `output_format`, `mime_type`, `filename`, and optionally `preview_storage_key`. Download, preview, share, and tracelog endpoints use these fields instead of hardcoded PDF names and messages.

## Data Model

Add an `XlsxTemplate` content model linked to a document type and creator. It stores:

- `id`
- `document_type_id`
- `name`
- `description`
- `storage_key`
- `original_filename`
- `detected_sheets`
- `detected_tokens`
- `image_slots`
- `validation_warnings`
- `mock_data`
- `created_by_id`
- `created_at`

Detected sheet metadata includes sheet name, used range, print areas, page setup summary, merges, and dimensions required for preview.

Detected tokens are extracted from textual cells and explicit XLSX template metadata. Tokens must validate against the same `DocumentTypeField` schema used by HTML/PDF templates.

Image slots support two forms:

- Token-driven slots, where a cell value such as `{{logo}}` is replaced by an image anchored near that cell.
- Explicit slots, where metadata defines sheet, cell or range, size, fit mode, and associated token.

## Template Upload And Validation

`POST /api/xlsx-templates` accepts a `.xlsx` upload, validates that it is a readable OpenXML workbook, stores it, and extracts metadata.

Validation rejects or warns on:

- Non-`.xlsx` files.
- Corrupt or unreadable workbooks.
- Unsupported macros or macro-enabled files.
- Malformed Jinja tokens.
- Tokens not allowed by the document type schema.
- Image slots without a valid token, sheet, or anchor.
- Workbook size, sheet count, cell count, or embedded image count above configured limits.
- Template constructs the renderer cannot preserve deterministically.

Validation errors must include sheet, cell or range when available, a machine-readable problem type, a human-readable message, and a short suggestion.

## XLSX Rendering

The renderer loads the stored workbook with `openpyxl`, preserves workbook structure, and applies a sandboxed Jinja environment to supported cells and metadata.

It should preserve:

- Sheets and sheet order.
- Cell styles.
- Merged cells when not affected by unsupported row cloning.
- Column widths and row heights.
- Page setup, margins, print areas, and page breaks.
- Formulas when they do not need unsafe rewriting.
- Existing images when possible.

Simple text cells render Jinja expressions such as `{{cliente.nombre}}`, conditionals, filters, and loops supported by the sandboxed template environment.

Repeated tables require an explicit template convention rather than inference. A repeated row or range declares the list field it expands from. During rendering, the engine clones rows or ranges, applies item-scoped data, and preserves styles and basic formulas when safe. If merges or formulas cannot be shifted deterministically, generation fails with an actionable validation error.

## Image Handling

Images can come from:

- Existing stored image assets referenced by ID or storage key.
- Base64 or data URL values supplied in the generation payload.

Before rendering, images are normalized into an internal representation with MIME type, bytes, dimensions, source token, and size. The service validates allowed MIME types, maximum byte size, maximum dimensions, and base64 correctness.

Images are inserted through `openpyxl` into token-driven or explicit slots. Slot configuration controls anchor cell or range, width, height, and fit behavior. The first version should support contained fit and fixed dimensions.

## API

Add XLSX template endpoints:

- `POST /api/xlsx-templates`
- `GET /api/xlsx-templates`
- `GET /api/xlsx-templates/{id}`
- `POST /api/xlsx-templates/{id}/validate`
- `POST /api/xlsx-templates/{id}/preview`

Design endpoints expose and accept `output_format`. Document type endpoints expose and accept `allowed_output_formats`.

Issuance endpoints stay conceptually the same but become format-aware. For successful XLSX emissions, download uses:

- MIME type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Filename extension: `.xlsx`

Messages should use generic wording such as "document generation" instead of "PDF generation".

## Preview

The XLSX preview is approximate and read-only. It does not replace Excel or LibreOffice as the source of truth.

The backend returns a preview JSON model containing:

- Sheets.
- Visible cell values after render or mock render.
- Basic styles needed for inspection.
- Merged ranges.
- Row heights and column widths.
- Approximate image bounding boxes.
- Warnings and validation errors.

The frontend renders this as a spreadsheet-like grid for quick inspection. It should make clear through UI structure that download/open in Excel remains the authoritative verification path, without adding explanatory tutorial text inside the app.

## Data Flow

1. Admin configures a document type and allows XLSX in `allowed_output_formats`.
2. User uploads an XLSX template for that document type.
3. Backend stores the workbook, extracts tokens, sheets, print settings, image slots, and warnings.
4. User creates an XLSX document design selecting that template.
5. User previews the design with mock data.
6. Consumer requests document generation with JSON payload and optional image references or base64 image values.
7. Backend validates payload against the document type schema and image constraints.
8. Backend creates a queued issuance with `output_format = "xlsx"`.
9. Worker dispatches to XLSX generation.
10. XLSX service renders workbook, stores the generated `.xlsx`, and updates issuance metadata.
11. User or API consumer downloads or shares the generated workbook through existing issuance endpoints.

## Error Handling

Generation should fail before writing a final workbook when validation detects unsafe or ambiguous output. Common error types:

- `invalid_workbook`
- `unsupported_workbook_type`
- `invalid_template_token`
- `unknown_schema_token`
- `invalid_repeat_range`
- `unsupported_merge_in_repeat_range`
- `unsafe_formula_shift`
- `missing_image`
- `invalid_image_payload`
- `image_too_large`
- `render_limit_exceeded`

Each error should include location data when available.

## Security And Limits

Use Jinja sandboxing with an explicit allowlist of filters and functions. Do not expose arbitrary Python objects to templates.

Block macro-enabled formats. Do not execute formulas, external links, scripts, or workbook connections. Treat formula text as workbook content that can be preserved or shifted only when deterministic.

Configure limits for workbook size, sheets, cells inspected, repeated rows generated, images, image bytes, and base64 payload size.

## Testing

Backend tests should cover:

- Upload and metadata extraction for a valid workbook.
- Rejection of invalid extension and corrupt workbook.
- Token extraction and validation against document type schema.
- Jinja render of simple cells.
- Repeated row or range rendering.
- Style, sheet order, print area, and page setup preservation.
- Image normalization from asset and base64.
- Image insertion into token-driven and explicit slots.
- Async issuance generation and status transitions.
- Download/share/tracelog behavior with XLSX MIME type and filename.
- Preview JSON shape for sheets, cells, merges, images, and warnings.
- Failure cases for invalid token, invalid base64, missing image, unsafe repeat range, and render limits.

Frontend tests should cover:

- XLSX template upload flow.
- Validation warnings and errors display.
- XLSX design creation with output format selection.
- Approximate preview rendering for multiple sheets.
- Issuance library download links using format-aware labels and filenames.

## Implementation Notes

The backend currently has PDF-specific names and messages in issuance routes and worker code. The implementation plan should start by introducing format-aware fields and helper methods while preserving existing PDF behavior.

`openpyxl` should be added to `backend/pyproject.toml` if it is not already declared there, even if it appears in the repository-level lock file.
