from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload, selectinload

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models.content_template import HtmlTemplate
from app.models.document_design import DocumentDesign, DocumentDesignPage
from app.models.document_type import DocumentType
from app.models.static_pdf_asset import StaticPdfAsset
from app.models.user import User
from app.schemas.document_design import (
    AddStaticPdfPage,
    AddTemplatePage,
    DocumentDesignCreate,
    DocumentDesignDetail,
    DocumentDesignListItem,
    DocumentDesignPageOut,
    ReorderDesignPages,
    UpdateDesignPage,
)
from app.services.design_validation import (
    assert_static_pdf_compatible,
    assert_template_compatible,
    static_pdf_snapshot,
    template_snapshot,
    validate_design_activation,
)

router = APIRouter(prefix="/api/document-designs", tags=["document-designs"])


def _query_design(db: SQLAlchemySession, design_id: UUID) -> DocumentDesign | None:
    return (
        db.query(DocumentDesign)
        .options(
            joinedload(DocumentDesign.document_type).selectinload(DocumentType.fields),
            joinedload(DocumentDesign.created_by),
            selectinload(DocumentDesign.pages),
        )
        .filter(DocumentDesign.id == design_id)
        .first()
    )


def _require_design(db: SQLAlchemySession, design_id: UUID) -> DocumentDesign:
    design = _query_design(db, design_id)
    if design is None:
        raise HTTPException(status_code=404, detail="Document design not found")
    return design


def _page_out(page: DocumentDesignPage) -> DocumentDesignPageOut:
    return DocumentDesignPageOut(
        id=page.id,
        block_type=page.block_type,
        content_id=page.content_id,
        position=page.position,
        title=page.title,
        notes=page.notes,
        config=page.config or {},
        snapshot=page.snapshot or {},
        created_at=page.created_at,
    )


def _detail(design: DocumentDesign) -> DocumentDesignDetail:
    ordered_pages = sorted(design.pages, key=lambda page: page.position)
    return DocumentDesignDetail(
        id=design.id,
        name=design.name,
        description=design.description,
        status=design.status,
        document_type_id=design.document_type_id,
        document_type_name=design.document_type.name,
        created_by_email=design.created_by.email,
        created_at=design.created_at,
        pages=[_page_out(page) for page in ordered_pages],
    )


@router.post("", response_model=DocumentDesignDetail, status_code=201)
def create_document_design(
    payload: DocumentDesignCreate,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignDetail:
    document_type = db.query(DocumentType).filter(DocumentType.id == payload.document_type_id).first()
    if document_type is None:
        raise HTTPException(status_code=404, detail="Document type not found")

    design = DocumentDesign(
        document_type=document_type,
        name=payload.name,
        description=payload.description,
        status="draft",
        created_by=user,
    )
    db.add(design)
    db.commit()
    db.refresh(design)
    return _detail(_require_design(db, design.id))


@router.get("", response_model=list[DocumentDesignListItem])
def list_document_designs(
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> list[DocumentDesignListItem]:
    designs = (
        db.query(DocumentDesign)
        .options(
            joinedload(DocumentDesign.document_type),
            joinedload(DocumentDesign.created_by),
            selectinload(DocumentDesign.pages),
        )
        .order_by(DocumentDesign.created_at.desc())
        .all()
    )
    return [
        DocumentDesignListItem(
            id=design.id,
            name=design.name,
            description=design.description,
            status=design.status,
            document_type_id=design.document_type_id,
            document_type_name=design.document_type.name,
            page_count=len(design.pages),
            created_by_email=design.created_by.email,
            created_at=design.created_at,
        )
        for design in designs
    ]


@router.get("/{design_id}", response_model=DocumentDesignDetail)
def get_document_design(
    design_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignDetail:
    return _detail(_require_design(db, design_id))


@router.post("/{design_id}/pages/template", response_model=DocumentDesignPageOut, status_code=201)
def add_template_page(
    design_id: UUID,
    payload: AddTemplatePage,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignPageOut:
    design = _require_design(db, design_id)
    template = db.query(HtmlTemplate).filter(HtmlTemplate.id == payload.template_id).first()
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    assert_template_compatible(design, template)

    page = DocumentDesignPage(
        design=design,
        block_type="html_template",
        content_id=template.id,
        position=len(design.pages),
        title=payload.title,
        notes=payload.notes,
        config=payload.config or {},
        snapshot=template_snapshot(template),
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    return _page_out(page)


@router.post("/{design_id}/pages/static-pdf", response_model=DocumentDesignPageOut, status_code=201)
def add_static_pdf_page(
    design_id: UUID,
    payload: AddStaticPdfPage,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignPageOut:
    design = _require_design(db, design_id)
    asset = db.query(StaticPdfAsset).filter(StaticPdfAsset.id == payload.static_pdf_asset_id).first()
    if asset is None:
        raise HTTPException(status_code=404, detail="PDF asset not found")
    assert_static_pdf_compatible(design, asset)

    duplicate = any(
        page.block_type == "static_pdf" and page.content_id == asset.id for page in design.pages
    )
    if duplicate:
        raise HTTPException(status_code=400, detail="PDF asset already exists in this design")

    page = DocumentDesignPage(
        design=design,
        block_type="static_pdf",
        content_id=asset.id,
        position=len(design.pages),
        title=payload.title,
        notes=payload.notes,
        config=payload.config or {},
        snapshot=static_pdf_snapshot(asset),
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    return _page_out(page)


@router.patch("/{design_id}/pages/reorder", response_model=DocumentDesignDetail)
def reorder_design_pages(
    design_id: UUID,
    payload: ReorderDesignPages,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignDetail:
    design = _require_design(db, design_id)
    pages_by_id = {page.id: page for page in design.pages}
    if set(payload.page_ids) != set(pages_by_id):
        raise HTTPException(status_code=400, detail="Reorder payload must include every design page")

    for position, page_id in enumerate(payload.page_ids):
        pages_by_id[page_id].position = position
    db.commit()
    return _detail(_require_design(db, design_id))


@router.patch("/{design_id}/pages/{page_id}", response_model=DocumentDesignPageOut)
def update_design_page(
    design_id: UUID,
    page_id: UUID,
    payload: UpdateDesignPage,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignPageOut:
    design = _require_design(db, design_id)
    page = next((candidate for candidate in design.pages if candidate.id == page_id), None)
    if page is None:
        raise HTTPException(status_code=404, detail="Design page not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(page, field, value)
    db.commit()
    db.refresh(page)
    return _page_out(page)


@router.delete("/{design_id}/pages/{page_id}", status_code=204)
def delete_design_page(
    design_id: UUID,
    page_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> Response:
    design = _require_design(db, design_id)
    page = next((candidate for candidate in design.pages if candidate.id == page_id), None)
    if page is None:
        raise HTTPException(status_code=404, detail="Design page not found")

    db.delete(page)
    remaining = [candidate for candidate in design.pages if candidate.id != page_id]
    for position, candidate in enumerate(sorted(remaining, key=lambda item: item.position)):
        candidate.position = position
    db.commit()
    return Response(status_code=204)


@router.post("/{design_id}/activate", response_model=DocumentDesignDetail)
def activate_document_design(
    design_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignDetail:
    design = _require_design(db, design_id)
    validate_design_activation(design, db)
    design.status = "active"
    db.commit()
    return _detail(_require_design(db, design_id))
