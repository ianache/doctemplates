from dataclasses import dataclass

from sqlalchemy.orm import Session as SQLAlchemySession

from app.models.document_issuance import DocumentIssuance
from app.services.pdf_generator import generate_composed_pdf
from app.services.storage.base import StorageProvider
from app.services.xlsx_renderer import render_xlsx_template

PDF_MIME_TYPE = "application/pdf"
XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@dataclass(frozen=True)
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
        if design.xlsx_template is None:
            raise ValueError("XLSX design is missing its template")
        workbook_bytes = storage_provider.get(
            design.xlsx_template.storage_key,
            category="xlsx_templates",
        )
        image_values = _image_values_from_slots(
            design.xlsx_template.image_slots or [],
            issuance.input_data,
        )
        content = render_xlsx_template(workbook_bytes, issuance.input_data, image_values=image_values)
        return GeneratedDocument(
            content=content,
            mime_type=XLSX_MIME_TYPE,
            filename=f"{issuance.id}.xlsx",
            extension="xlsx",
        )

    content = generate_composed_pdf(
        design,
        issuance.input_data,
        db,
        storage_provider,
        mock_fallback=False,
    )
    return GeneratedDocument(
        content=content,
        mime_type=PDF_MIME_TYPE,
        filename=f"{issuance.id}.pdf",
        extension="pdf",
    )


def _image_values_from_slots(slots: list[dict], payload: dict) -> dict[str, object]:
    values: dict[str, object] = {}
    for slot in slots:
        sheet = slot.get("sheet")
        cell = slot.get("cell")
        field = slot.get("field")
        if not sheet or not cell or not field:
            continue
        value = _resolve_path(payload, str(field))
        if value is not None:
            values[f"{sheet}!{cell}"] = value
    return values


def _resolve_path(payload: dict, path: str) -> object | None:
    current: object = payload
    for segment in path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current
