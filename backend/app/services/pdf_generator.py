import io
import os
import uuid
from datetime import datetime, timezone
from jinja2.sandbox import SandboxedEnvironment
from xhtml2pdf import pisa
from pypdf import PdfReader, PdfWriter
from fastapi import HTTPException
from sqlalchemy.orm import Session as SQLAlchemySession

from app.models.document_design import DocumentDesign
from app.models.content_template import HtmlTemplate
from app.models.static_pdf_asset import StaticPdfAsset
from app.models.document_type import DocumentTypeField


def date_format_filter(value: str, format_str: str = "%d/%m/%Y") -> str:
    """Formats an ISO 8601 YYYY-MM-DD date string into a custom format string."""
    if not value:
        return ""
    try:
        # Check standard date formats
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(value, fmt)
                return dt.strftime(format_str)
            except ValueError:
                continue
        return value
    except Exception:
        return value


def get_payload_value(payload: dict, path: str) -> tuple[bool, any]:
    """Helper to check and retrieve a value from flat dot-notation keys or nested dicts."""
    if path in payload:
        return True, payload[path]
    parts = path.split(".")
    d = payload
    for part in parts:
        if not isinstance(d, dict) or part not in d:
            return False, None
        d = d[part]
    return True, d


def coerce_value(val: any, field_type: str, field_name: str) -> any:
    """Coerces a value to the specified schema field type, raising ValueError on failure."""
    if val is None:
        raise ValueError(f"Value for field '{field_name}' cannot be null.")

    if field_type == "string":
        if isinstance(val, (dict, list)):
            raise ValueError(f"Cannot coerce object/list to string for field '{field_name}'.")
        return str(val)

    elif field_type == "number":
        try:
            if isinstance(val, (int, float)):
                return val
            f_val = float(val)
            if f_val.is_integer():
                return int(f_val)
            return f_val
        except (ValueError, TypeError):
            raise ValueError(f"Value '{val}' is not a valid number for field '{field_name}'.")

    elif field_type == "boolean":
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            if val == 1:
                return True
            if val == 0:
                return False
            raise ValueError(f"Value '{val}' is not a valid boolean for field '{field_name}'.")
        if isinstance(val, str):
            s = val.strip().lower()
            if s in ("true", "yes", "1", "t", "y"):
                return True
            if s in ("false", "no", "0", "f", "n"):
                return False
        raise ValueError(f"Value '{val}' is not a valid boolean for field '{field_name}'.")

    elif field_type == "date":
        if not isinstance(val, str):
            raise ValueError(f"Date value must be a string in YYYY-MM-DD format for field '{field_name}'.")
        try:
            datetime.strptime(val, "%Y-%m-%d")
            return val
        except ValueError:
            raise ValueError(f"Value '{val}' is not a valid ISO 8601 date (expected YYYY-MM-DD) for field '{field_name}'.")

    else:
        return val


def validate_and_coerce_payload(
    payload: dict,
    schema_fields: list[DocumentTypeField],
    mock_fallback: bool = False
) -> dict:
    """Validates payload against schema fields.
    
    If mock_fallback is True, missing fields are populated with mock values.
    Otherwise, missing fields raise HTTP 400. Extra fields are ignored.
    """
    coerced = {}
    for field in schema_fields:
        found, val = get_payload_value(payload, field.name)
        if not found:
            if mock_fallback:
                if field.type == "string":
                    coerced[field.name] = f"{field.name}_val"
                elif field.type == "number":
                    coerced[field.name] = 123.45
                elif field.type == "boolean":
                    coerced[field.name] = True
                elif field.type == "date":
                    coerced[field.name] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                else:
                    coerced[field.name] = None
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field '{field.name}' in payload."
                )
        else:
            try:
                coerced[field.name] = coerce_value(val, field.type, field.name)
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=str(e)
                )
    return coerced


def expand_flat_dict(flat: dict[str, any]) -> dict[str, any]:
    """Converts a flat dictionary with dot-notation keys into a nested dictionary structure."""
    nested = {}
    for key, val in flat.items():
        parts = key.split(".")
        d = nested
        for part in parts[:-1]:
            d = d.setdefault(part, {})
        d[parts[-1]] = val
    return nested


def render_html_page_to_pdf(html_content: str, context: dict) -> bytes:
    """Renders a Jinja2 template and compiles it to PDF bytes using xhtml2pdf."""
    env = SandboxedEnvironment(autoescape=True)
    env.filters["date_format"] = date_format_filter

    try:
        template = env.from_string(html_content)
        rendered_html = template.render(**context)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Template rendering failed: {str(e)}"
        )

    base_css = """
    <style>
        @page {
            size: letter portrait;
            margin: 1in;
        }
        body {
            font-family: Helvetica, Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.4;
        }
    </style>
    """
    final_html = base_css + rendered_html

    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(
        src=final_html,
        dest=pdf_buffer
    )
    if pisa_status.err:
        raise HTTPException(
            status_code=500,
            detail="HTML to PDF compilation failed."
        )
    return pdf_buffer.getvalue()


def generate_composed_pdf(
    design: DocumentDesign,
    payload: dict,
    db: SQLAlchemySession,
    mock_fallback: bool = False
) -> bytes:
    """Composes a single merged PDF from a design, its pages, and client data."""
    # 1. Validate and coerce payload fields
    coerced_payload = validate_and_coerce_payload(payload, design.document_type.fields, mock_fallback)

    # 2. Expand dot notation to nested dictionaries for Jinja context
    expanded_payload = expand_flat_dict(coerced_payload)

    # 3. Pre-fetch templates and static assets to minimize DB calls in rendering loop
    template_page_ids = {page.content_id for page in design.pages if page.block_type == "html_template"}
    templates_by_id = {}
    if template_page_ids:
        templates = db.query(HtmlTemplate).filter(HtmlTemplate.id.in_(template_page_ids)).all()
        templates_by_id = {template.id: template for template in templates}

    static_page_ids = {page.content_id for page in design.pages if page.block_type == "static_pdf"}
    assets_by_id = {}
    if static_page_ids:
        assets = db.query(StaticPdfAsset).filter(StaticPdfAsset.id.in_(static_page_ids)).all()
        assets_by_id = {asset.id: asset for asset in assets}

    # 4. Merging pages
    writer = PdfWriter()

    for page in design.pages:
        if page.block_type == "html_template":
            html_content = ""
            template = templates_by_id.get(page.content_id)
            if template:
                html_content = template.html
            else:
                html_content = (page.snapshot or {}).get("html", "")

            if not html_content:
                raise HTTPException(
                    status_code=400,
                    detail=f"HTML template content is empty for page position {page.position}."
                )

            pdf_bytes = render_html_page_to_pdf(html_content, expanded_payload)
            reader = PdfReader(io.BytesIO(pdf_bytes))
            for p in reader.pages:
                writer.add_page(p)

        elif page.block_type == "static_pdf":
            asset = assets_by_id.get(page.content_id)
            stored_path = ""
            if asset:
                stored_path = asset.stored_path
            else:
                stored_path = (page.snapshot or {}).get("stored_path", "")

            if not stored_path:
                raise HTTPException(
                    status_code=400,
                    detail=f"Static PDF asset path not specified for page position {page.position}."
                )

            if not os.path.exists(stored_path):
                raise HTTPException(
                    status_code=404,
                    detail=f"Static PDF file not found at {stored_path} for page position {page.position}."
                )

            reader = PdfReader(stored_path)
            for p in reader.pages:
                writer.add_page(p)

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported page block type '{page.block_type}' at position {page.position}."
            )

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
