from fastapi import HTTPException
from sqlalchemy.orm import Session as SQLAlchemySession

from app.models.content_template import HtmlTemplate
from app.models.document_design import DocumentDesign
from app.models.static_pdf_asset import StaticPdfAsset


def template_snapshot(template: HtmlTemplate) -> dict:
    return {
        "template_id": str(template.id),
        "name": template.name,
        "html": template.html,
        "token_names": list(template.token_names or []),
        "document_type_id": str(template.document_type_id),
    }


def static_pdf_snapshot(asset: StaticPdfAsset) -> dict:
    return {
        "asset_id": str(asset.id),
        "filename": asset.original_filename,
        "stored_filename": asset.stored_filename,
        "stored_path": asset.stored_path,
        "page_count": asset.page_count,
        "page_start": asset.page_start,
        "page_end": asset.page_end,
        "file_size": asset.file_size,
        "document_type_id": str(asset.document_type_id) if asset.document_type_id else None,
    }


def assert_template_compatible(design: DocumentDesign, template: HtmlTemplate) -> None:
    if template.document_type_id != design.document_type_id:
        raise HTTPException(
            status_code=400,
            detail="Template must belong to the design document type",
        )


def assert_static_pdf_compatible(design: DocumentDesign, asset: StaticPdfAsset) -> None:
    if asset.document_type_id is not None and asset.document_type_id != design.document_type_id:
        raise HTTPException(
            status_code=400,
            detail="PDF asset must be global or belong to the design document type",
        )


def validate_design_activation(design: DocumentDesign, db: SQLAlchemySession) -> None:
    if not design.name or not design.document_type_id:
        raise HTTPException(status_code=400, detail="Design name and document type are required")
    if not design.pages:
        raise HTTPException(status_code=400, detail="Active designs require at least one page")

    allowed_tokens = {field.name for field in design.document_type.fields}
    invalid_tokens: set[str] = set()

    for page in design.pages:
        if page.block_type != "html_template":
            continue

        template = db.query(HtmlTemplate).filter(HtmlTemplate.id == page.content_id).first()
        if template is not None:
            token_names = list(template.token_names or [])
        else:
            token_names = list((page.snapshot or {}).get("token_names") or [])
        invalid_tokens.update(token for token in token_names if token not in allowed_tokens)

    if invalid_tokens:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid template tokens: {', '.join(sorted(invalid_tokens))}",
        )
