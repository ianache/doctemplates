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
        "css": template.css,
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


def assert_no_duplicate_static_pdf(design: DocumentDesign, asset: StaticPdfAsset) -> None:
    duplicate = any(
        page.block_type == "static_pdf" and page.content_id == asset.id for page in design.pages
    )
    if duplicate:
        raise HTTPException(status_code=400, detail="PDF asset already exists in this design")


def get_design_warnings(design: DocumentDesign, db: SQLAlchemySession = None) -> list[str]:
    from app.services.content_validation import get_ancestor_paths, extract_template_tokens_ast_warnings

    allowed_tokens = {field.name for field in design.document_type.fields}
    valid_ancestors = set()
    for token in allowed_tokens:
        valid_ancestors.update(get_ancestor_paths(token))

    warnings = []

    template_page_ids = {page.content_id for page in design.pages if page.block_type == "html_template"}
    templates_by_id = {}
    if db is not None and template_page_ids:
        templates = db.query(HtmlTemplate).filter(HtmlTemplate.id.in_(template_page_ids)).all()
        templates_by_id = {template.id: template for template in templates}

    for page in design.pages:
        if page.block_type != "html_template":
            continue

        html = None
        template = templates_by_id.get(page.content_id)
        if template is not None:
            html = template.html
        else:
            snapshot = page.snapshot or {}
            html = snapshot.get("html")

        if html:
            page_warnings = extract_template_tokens_ast_warnings(html, valid_ancestors)
            warnings.extend(page_warnings)

    return sorted(list(set(warnings)))


def validate_design_activation(design: DocumentDesign, db: SQLAlchemySession) -> None:
    if not design.name or not design.document_type_id:
        raise HTTPException(status_code=400, detail="Design name and document type are required")
    if not design.pages:
        raise HTTPException(status_code=400, detail="Active designs require at least one page")

    warnings = get_design_warnings(design, db)
    if warnings:
        invalid_tokens = []
        for warning in warnings:
            if warning.startswith("Token '") and warning.endswith("' is not declared in schema"):
                token = warning[7:-27]
                invalid_tokens.append(token)
            else:
                invalid_tokens.append(warning)

        raise HTTPException(
            status_code=400,
            detail=f"Invalid template tokens: {', '.join(sorted(list(set(invalid_tokens))))}",
        )
