import io
import os
import uuid
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload, selectinload

from app.api.document_types import require_document_type
from app.auth.dependencies import get_current_user
from app.config import settings
from app.db import get_db
from app.models.content_template import HtmlTemplate
from app.models.document_design import DocumentDesign, DocumentDesignPage
from app.models.document_type import DocumentType
from app.models.document_issuance import DocumentIssuance
from app.models.document_tracelog import DocumentTracelog
from app.models.static_pdf_asset import StaticPdfAsset
from app.models.user import User
from app.schemas.document_issuance import DocumentIssuanceOut
from app.services.pdf_generator import generate_composed_pdf

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
    assert_no_duplicate_static_pdf,
    assert_static_pdf_compatible,
    assert_template_compatible,
    get_design_warnings,
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


def _require_page(design: DocumentDesign, page_id: UUID) -> DocumentDesignPage:
    page = next((candidate for candidate in design.pages if candidate.id == page_id), None)
    if page is None:
        raise HTTPException(status_code=404, detail="Design page not found")
    return page


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


def _detail(design: DocumentDesign, db: SQLAlchemySession = None) -> DocumentDesignDetail:
    ordered_pages = sorted(design.pages, key=lambda page: page.position)
    warnings = []
    if design.status == "draft":
        warnings = get_design_warnings(design, db)
    return DocumentDesignDetail(
        id=design.id,
        name=design.name,
        description=design.description,
        status=design.status,
        version_group_id=design.version_group_id,
        version_number=design.version_number,
        document_type_id=design.document_type_id,
        document_type_name=design.document_type.name,
        created_by_email=design.created_by.email,
        created_at=design.created_at,
        pages=[_page_out(page) for page in ordered_pages],
        warnings=warnings,
    )


@router.post("", response_model=DocumentDesignDetail, status_code=201)
def create_document_design(
    payload: DocumentDesignCreate,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignDetail:
    document_type = require_document_type(db, payload.document_type_id)

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
    return _detail(design, db)


@router.get("", response_model=list[DocumentDesignListItem])
def list_document_designs(
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> list[DocumentDesignListItem]:
    rows = (
        db.query(DocumentDesign, func.count(DocumentDesignPage.id))
        .outerjoin(DocumentDesignPage, DocumentDesignPage.design_id == DocumentDesign.id)
        .options(
            selectinload(DocumentDesign.document_type),
            selectinload(DocumentDesign.created_by),
        )
        .group_by(DocumentDesign.id)
        .order_by(DocumentDesign.created_at.desc())
        .all()
    )
    return [
        DocumentDesignListItem(
            id=design.id,
            name=design.name,
            description=design.description,
            status=design.status,
            version_group_id=design.version_group_id,
            version_number=design.version_number,
            document_type_id=design.document_type_id,
            document_type_name=design.document_type.name,
            page_count=page_count,
            created_by_email=design.created_by.email,
            created_at=design.created_at,
        )
        for design, page_count in rows
    ]


@router.get("/{design_id}", response_model=DocumentDesignDetail)
def get_document_design(
    design_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignDetail:
    return _detail(_require_design(db, design_id), db)


@router.post("/{design_id}/pages/template", response_model=DocumentDesignPageOut, status_code=201)
def add_template_page(
    design_id: UUID,
    payload: AddTemplatePage,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignPageOut:
    design = _require_design(db, design_id)
    if design.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft designs can be modified")
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
    if design.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft designs can be modified")
    asset = db.query(StaticPdfAsset).filter(StaticPdfAsset.id == payload.static_pdf_asset_id).first()
    if asset is None:
        raise HTTPException(status_code=404, detail="PDF asset not found")
    assert_static_pdf_compatible(design, asset)
    assert_no_duplicate_static_pdf(design, asset)

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
    if design.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft designs can be modified")
    pages_by_id = {page.id: page for page in design.pages}
    if set(payload.page_ids) != set(pages_by_id):
        raise HTTPException(status_code=400, detail="Reorder payload must include every design page")

    for position, page_id in enumerate(payload.page_ids):
        pages_by_id[page_id].position = position
    db.commit()
    return _detail(design, db)


@router.patch("/{design_id}/pages/{page_id}", response_model=DocumentDesignPageOut)
def update_design_page(
    design_id: UUID,
    page_id: UUID,
    payload: UpdateDesignPage,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignPageOut:
    design = _require_design(db, design_id)
    if design.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft designs can be modified")
    page = _require_page(design, page_id)

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
    if design.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft designs can be modified")
    page = _require_page(design, page_id)

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

    if design.version_group_id is None:
        # First-ever activation (Phase 4 legacy path): becomes Version 1.
        design.version_group_id = design.id
        design.version_number = 1
        design.status = "active"
    else:
        # Forked draft becoming current.
        # Supersede the old active version first in the group.
        old_current = (
            db.query(DocumentDesign)
            .filter(
                DocumentDesign.version_group_id == design.version_group_id,
                DocumentDesign.status == "active",
                DocumentDesign.id != design.id
            )
            .first()
        )
        if old_current is not None:
            old_current.status = "superseded"
            db.flush()
        design.status = "active"

    db.commit()
    db.refresh(design)
    return _detail(design, db)


@router.post("/{design_id}/versions", response_model=DocumentDesignDetail, status_code=201)
def fork_document_design_version(
    design_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignDetail:
    from sqlalchemy.exc import IntegrityError

    current = _require_design(db, design_id)
    if current.status != "active":
        raise HTTPException(status_code=400, detail="Only the active version can be edited")

    group_id = current.version_group_id or current.id

    # Check for existing draft in the same group to resume (D-04)
    existing_draft = (
        db.query(DocumentDesign)
        .filter(DocumentDesign.version_group_id == group_id, DocumentDesign.status == "draft")
        .first()
    )
    if existing_draft is not None:
        return _detail(existing_draft, db)

    next_version = (
        db.query(func.max(DocumentDesign.version_number))
        .filter(DocumentDesign.version_group_id == group_id)
        .scalar() or 0
    ) + 1

    draft = DocumentDesign(
        document_type_id=current.document_type_id,
        name=current.name,
        description=current.description,
        status="draft",
        version_group_id=group_id,
        version_number=next_version,
        created_by=user,
    )

    # Deep copy pages
    for page in sorted(current.pages, key=lambda p: p.position):
        draft.pages.append(
            DocumentDesignPage(
                block_type=page.block_type,
                content_id=page.content_id,
                position=page.position,
                title=page.title,
                notes=page.notes,
                config=dict(page.config or {}),
                snapshot=dict(page.snapshot or {}),
            )
        )

    db.add(draft)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Fall back to the draft that was concurrently created
        existing_draft = (
            db.query(DocumentDesign)
            .filter(DocumentDesign.version_group_id == group_id, DocumentDesign.status == "draft")
            .first()
        )
        if existing_draft is not None:
            return _detail(existing_draft, db)
        raise

    db.refresh(draft)
    return _detail(draft, db)


@router.get("/{design_id}/versions", response_model=list[DocumentDesignListItem])
def list_document_design_versions(
    design_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> list[DocumentDesignListItem]:
    anchor = _require_design(db, design_id)
    group_id = anchor.version_group_id or anchor.id
    rows = (
        db.query(DocumentDesign, func.count(DocumentDesignPage.id))
        .outerjoin(DocumentDesignPage, DocumentDesignPage.design_id == DocumentDesign.id)
        .options(
            selectinload(DocumentDesign.document_type),
            selectinload(DocumentDesign.created_by),
        )
        .filter(DocumentDesign.version_group_id == group_id)
        .group_by(DocumentDesign.id)
        .order_by(DocumentDesign.version_number.desc())
        .all()
    )
    return [
        DocumentDesignListItem(
            id=design.id,
            name=design.name,
            description=design.description,
            status=design.status,
            version_group_id=design.version_group_id,
            version_number=design.version_number,
            document_type_id=design.document_type_id,
            document_type_name=design.document_type.name,
            page_count=page_count,
            created_by_email=design.created_by.email,
            created_at=design.created_at,
        )
        for design, page_count in rows
    ]


@router.delete("/{design_id}", status_code=204)
def discard_document_design_draft(
    design_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> Response:
    design = _require_design(db, design_id)
    if design.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft versions can be discarded")
    db.delete(design)
    db.commit()
    return Response(status_code=204)


@router.post("/{design_id}/generate", response_model=DocumentIssuanceOut, status_code=201)
def generate_document(
    design_id: UUID,
    payload: dict = Body(default={}),
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentIssuance:
    design = _require_design(db, design_id)
    if design.status == "draft":
        raise HTTPException(status_code=400, detail="Cannot generate documents from a draft design")

    # Generate PDF bytes
    pdf_bytes = generate_composed_pdf(design, payload, db, mock_fallback=False)

    # Ensure output directory exists
    os.makedirs(settings.issuance_storage_root, exist_ok=True)

    issuance_id = uuid.uuid4()
    filename = f"{issuance_id}.pdf"
    file_path = os.path.join(settings.issuance_storage_root, filename)

    with open(file_path, "wb") as f:
        f.write(pdf_bytes)

    issuance = DocumentIssuance(
        id=issuance_id,
        design_version_id=design.id,
        file_path=file_path,
        user_id=user.id,
        input_data=payload,
        status="success",
    )
    tracelog = DocumentTracelog(
        issuance=issuance,
        user_id=user.id,
        event_type="generation",
        metadata_={
            "source": "POST /api/document-designs/{design_id}/generate",
            "design_id": str(design.id),
        },
    )
    db.add_all([issuance, tracelog])
    db.commit()
    db.refresh(issuance)
    return issuance


@router.post("/{design_id}/preview")
def preview_document(
    design_id: UUID,
    payload: dict = Body(default={}),
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> Response:
    design = _require_design(db, design_id)
    if design.status not in ("draft", "active"):
        raise HTTPException(status_code=400, detail="Preview only allowed for draft or active designs")

    pdf_bytes = generate_composed_pdf(design, payload, db, mock_fallback=True)
    return Response(content=pdf_bytes, media_type="application/pdf")

