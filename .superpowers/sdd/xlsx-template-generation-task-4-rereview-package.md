# Task 4 Re-Review Package
 M backend/app/api/document_designs.py
 M backend/app/schemas/document_design.py
 M backend/app/services/design_validation.py
?? .superpowers/sdd/xlsx-template-generation-task-4-report.md
?? backend/tests/test_xlsx_designs.py

## File: backend/app/api/document_designs.py
```
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
from app.models.document_type import DocumentType, DocumentTypeMetadataDefinition
from app.models.document_issuance import DocumentIssuance
from app.models.document_tracelog import DocumentTracelog
from app.models.static_pdf_asset import StaticPdfAsset
from app.models.user import User
from app.models.xlsx_template import XlsxTemplate
from app.schemas.document_issuance import DocumentIssuanceOut
from app.services.pdf_generator import generate_composed_pdf
from app.dependencies import get_storage_provider
from app.services.storage.base import StorageProvider

from app.schemas.document_design import (
    AddStaticPdfPage,
    AddTemplatePage,
    DocumentDesignCreate,
    DocumentDesignUpdate,
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


def _validate_design_output(
    db: SQLAlchemySession,
    document_type: DocumentType,
    output_format: str,
    xlsx_template_id: UUID | None,
) -> XlsxTemplate | None:
    allowed_formats = document_type.allowed_output_formats or ["pdf"]
    if output_format not in allowed_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Document type does not allow {output_format} output",
        )

    if output_format == "xlsx" and xlsx_template_id is None:
        raise HTTPException(status_code=400, detail="XLSX designs require xlsx_template_id")

    if output_format == "pdf" and xlsx_template_id is not None:
        raise HTTPException(
            status_code=400,
            detail="PDF designs cannot reference an XLSX template",
        )

    if xlsx_template_id is None:
        return None

    template = db.query(XlsxTemplate).filter(XlsxTemplate.id == xlsx_template_id).first()
    if template is None:
        raise HTTPException(status_code=404, detail="XLSX template not found")
    if template.document_type_id != document_type.id:
        raise HTTPException(
            status_code=400,
            detail="XLSX template must belong to the design document type",
        )
    return template


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


def _activate_design(design: DocumentDesign, db: SQLAlchemySession) -> None:
    validate_design_activation(design, db)

    if design.version_group_id is None:
        design.version_group_id = design.id
        design.version_number = 1
        design.status = "active"
        return

    old_current = (
        db.query(DocumentDesign)
        .filter(
            DocumentDesign.version_group_id == design.version_group_id,
            DocumentDesign.status == "active",
            DocumentDesign.id != design.id,
        )
        .first()
    )
    if old_current is not None:
        old_current.status = "superseded"
        db.flush()
    design.status = "active"


def _detail(design: DocumentDesign, db: SQLAlchemySession = None) -> DocumentDesignDetail:
    ordered_pages = sorted(design.pages, key=lambda page: page.position)
    warnings = []
    if design.status == "draft":
        warnings = get_design_warnings(design, db)
    return DocumentDesignDetail(
        id=design.id,
        name=design.name,
        description=design.description,
        output_format=design.output_format,
        xlsx_template_id=design.xlsx_template_id,
        status=design.status,
        version_group_id=design.version_group_id,
        version_number=design.version_number,
        document_type_id=design.document_type_id,
        document_type_name=design.document_type.name,
        created_by_email=design.created_by.email,
        created_at=design.created_at,
        pages=[_page_out(page) for page in ordered_pages],
        warnings=warnings,
        mock_data=design.mock_data,
    )


@router.post("", response_model=DocumentDesignDetail, status_code=201)
def create_document_design(
    payload: DocumentDesignCreate,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignDetail:
    document_type = require_document_type(db, payload.document_type_id)
    xlsx_template = _validate_design_output(
        db,
        document_type,
        payload.output_format,
        payload.xlsx_template_id,
    )

    design = DocumentDesign(
        document_type=document_type,
        name=payload.name,
        description=payload.description,
        output_format=payload.output_format,
        xlsx_template=xlsx_template,
        status="draft",
        created_by=user,
        mock_data=payload.mock_data,
    )
    db.add(design)
    db.commit()
    db.refresh(design)
    return _detail(design, db)


@router.put("/{design_id}", response_model=DocumentDesignDetail)
def update_document_design(
    design_id: UUID,
    payload: DocumentDesignUpdate,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignDetail:
    design = (
        db.query(DocumentDesign)
        .options(
            joinedload(DocumentDesign.document_type),
            joinedload(DocumentDesign.created_by),
            selectinload(DocumentDesign.pages),
        )
        .filter(DocumentDesign.id == design_id)
        .first()
    )
    if design is None:
        raise HTTPException(status_code=404, detail="Document design not found")
    xlsx_template = _validate_design_output(
        db,
        design.document_type,
        payload.output_format,
        payload.xlsx_template_id,
    )

    design.name = payload.name
    design.description = payload.description
    design.output_format = payload.output_format
    design.xlsx_template = xlsx_template
    design.mock_data = payload.mock_data

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
            output_format=design.output_format,
            xlsx_template_id=design.xlsx_template_id,
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
    _activate_design(design, db)

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
        output_format=current.output_format,
        xlsx_template_id=current.xlsx_template_id,
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
            output_format=design.output_format,
            xlsx_template_id=design.xlsx_template_id,
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


from datetime import datetime

def validate_metadata_values(
    values: dict,
    definitions: list[DocumentTypeMetadataDefinition]
) -> dict:
    """Validates metadata values against definitions.
    Raises HTTPException 400 if validation fails.
    Returns coerced metadata values dictionary.
    """
    coerced = {}
    
    # Case insensitive check for keys
    values_lower = {k.lower(): (k, v) for k, v in values.items()}
    
    for def_ in definitions:
        name_lower = def_.name.lower()
        
        # Check if present
        if name_lower not in values_lower:
            if def_.required:
                raise HTTPException(
                    status_code=400,
                    detail=f"Required metadata field '{def_.name}' is missing."
                )
            continue
            
        orig_key, val = values_lower[name_lower]
        
        if val is None or val == "":
            if def_.required:
                raise HTTPException(
                    status_code=400,
                    detail=f"Required metadata field '{def_.name}' cannot be empty."
                )
            coerced[def_.name] = None
            continue
            
        # Coerce based on type
        t = def_.type
        if t == "text":
            coerced[def_.name] = str(val)
        elif t == "number":
            try:
                if isinstance(val, bool):
                    coerced[def_.name] = float(1 if val else 0)
                else:
                    coerced[def_.name] = float(val)
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=400,
                    detail=f"Metadata field '{def_.name}' must be a number."
                )
        elif t == "boolean":
            if isinstance(val, bool):
                coerced[def_.name] = val
            elif str(val).lower() in ("true", "1", "yes", "on"):
                coerced[def_.name] = True
            elif str(val).lower() in ("false", "0", "no", "off"):
                coerced[def_.name] = False
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Metadata field '{def_.name}' must be a boolean."
                )
        elif t == "date":
            if isinstance(val, datetime):
                coerced[def_.name] = val.date().isoformat()
            elif isinstance(val, str):
                try:
                    datetime.strptime(val, "%Y-%m-%d")
                    coerced[def_.name] = val
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Metadata field '{def_.name}' must be a date in YYYY-MM-DD format."
                    )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Metadata field '{def_.name}' must be a date."
                )
        elif t == "datetime":
            if isinstance(val, datetime):
                coerced[def_.name] = val.isoformat()
            elif isinstance(val, str):
                try:
                    val_str = val
                    if val_str.endswith("Z"):
                        val_str = val_str[:-1] + "+00:00"
                    datetime.fromisoformat(val_str)
                    coerced[def_.name] = val
                except Exception:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Metadata field '{def_.name}' must be a valid datetime (ISO 8601 format)."
                    )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Metadata field '{def_.name}' must be a datetime."
                )
        else:
            coerced[def_.name] = val
            
    return coerced


@router.post("/{design_id}/generate", response_model=DocumentIssuanceOut, status_code=202)
def generate_document(
    design_id: UUID,
    payload: dict = Body(default={}),
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
    storage_provider: StorageProvider = Depends(get_storage_provider),
) -> DocumentIssuance:
    design = _require_design(db, design_id)
    if design.status == "draft":
        _activate_design(design, db)
        db.flush()

    # Split data and metadata
    data = payload.get("data", payload) if isinstance(payload, dict) else {}
    metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        data = {}
    if not isinstance(metadata, dict):
        metadata = {}

    # Validate metadata
    coerced_metadata = validate_metadata_values(metadata, design.document_type.metadata_definitions)

    # Validate and coerce input data payload against document type fields if fields are defined
    if design.document_type.fields:
        from app.services.pdf_generator import validate_and_coerce_payload
        from fastapi import HTTPException
        try:
            validate_and_coerce_payload(data, design.document_type.fields)
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    from datetime import datetime
    from app.services.issuance_jobs import enqueue_document_generation

    issuance_id = uuid.uuid4()
    issuance = DocumentIssuance(
        id=issuance_id,
        design_version_id=design.id,
        storage_key=None,
        user_id=user.id,
        input_data=data,
        metadata_values=coerced_metadata,
        status="queued",
        queued_at=datetime.utcnow(),
    )
    db.add(issuance)
    db.commit()
    db.refresh(issuance)

    # Enqueue task
    try:
        task_id = enqueue_document_generation(str(issuance.id))
        issuance.celery_task_id = task_id
        db.commit()
    except Exception as e:
        issuance.status = "failure"
        issuance.error_message = f"Failed to enqueue: {str(e)}"
        issuance.completed_at = datetime.utcnow()
        db.commit()

    db.refresh(issuance)
    return issuance


@router.post("/{design_id}/preview")
def preview_document(
    design_id: UUID,
    payload: dict = Body(default={}),
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
    storage_provider: StorageProvider = Depends(get_storage_provider),
) -> Response:
    design = _require_design(db, design_id)
    if design.status not in ("draft", "active"):
        raise HTTPException(status_code=400, detail="Preview only allowed for draft or active designs")

    # Split data and metadata
    data = payload.get("data", payload) if isinstance(payload, dict) else {}
    metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        data = {}
    if not isinstance(metadata, dict):
        metadata = {}

    # Validate metadata
    _ = validate_metadata_values(metadata, design.document_type.metadata_definitions)

    pdf_bytes = generate_composed_pdf(design, data, db, storage_provider, mock_fallback=True)
    return Response(content=pdf_bytes, media_type="application/pdf")

```

## File: backend/app/services/design_validation.py
```
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

    allowed_formats = design.document_type.allowed_output_formats or ["pdf"]
    if design.output_format not in allowed_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Document type does not allow {design.output_format} output",
        )

    if design.output_format == "xlsx":
        if design.xlsx_template_id is None:
            raise HTTPException(
                status_code=400,
                detail="XLSX designs require a template before activation",
            )
        if design.xlsx_template is None:
            raise HTTPException(status_code=404, detail="XLSX template not found")
        if design.xlsx_template.document_type_id != design.document_type_id:
            raise HTTPException(
                status_code=400,
                detail="XLSX template must belong to the design document type",
            )
        if design.xlsx_template.validation_warnings:
            raise HTTPException(status_code=400, detail="XLSX template has validation warnings")
        return

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

```

## File: backend/app/schemas/document_design.py
```
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.document_type import OutputFormat


class DocumentDesignCreate(BaseModel):
    document_type_id: UUID
    name: str
    description: str | None = None
    output_format: OutputFormat = "pdf"
    xlsx_template_id: UUID | None = None
    mock_data: dict | None = None


class DocumentDesignUpdate(BaseModel):
    name: str
    description: str | None = None
    output_format: OutputFormat = "pdf"
    xlsx_template_id: UUID | None = None
    mock_data: dict | None = None


class AddTemplatePage(BaseModel):
    template_id: UUID
    title: str | None = None
    notes: str | None = None
    config: dict | None = None


class AddStaticPdfPage(BaseModel):
    static_pdf_asset_id: UUID
    title: str | None = None
    notes: str | None = None
    config: dict | None = None


class ReorderDesignPages(BaseModel):
    page_ids: list[UUID]


class UpdateDesignPage(BaseModel):
    title: str | None = None
    notes: str | None = None
    config: dict | None = None


class DocumentDesignPageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    block_type: str
    content_id: UUID
    position: int
    title: str | None
    notes: str | None
    config: dict
    snapshot: dict
    created_at: datetime


class DocumentDesignListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    output_format: OutputFormat = "pdf"
    xlsx_template_id: UUID | None = None
    status: str
    version_group_id: UUID | None = None
    version_number: int | None = None
    document_type_id: UUID
    document_type_name: str
    page_count: int
    created_by_email: str
    created_at: datetime


class DocumentDesignDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    output_format: OutputFormat = "pdf"
    xlsx_template_id: UUID | None = None
    status: str
    version_group_id: UUID | None = None
    version_number: int | None = None
    document_type_id: UUID
    document_type_name: str
    created_by_email: str
    created_at: datetime
    pages: list[DocumentDesignPageOut]
    warnings: list[str] = []
    mock_data: dict | None = None

```

## File: backend/tests/test_xlsx_designs.py
```
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.session_service import create_session
from app.models.document_design import DocumentDesign
from app.models.document_type import DocumentType, DocumentTypeField
from app.models.user import User
from app.models.xlsx_template import XlsxTemplate


def _auth_client(client: TestClient, db_session: SQLAlchemySession) -> User:
    user = User(sub="xlsx-design-sub", email="xlsx-design@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)
    return user


def _document_type(
    db_session: SQLAlchemySession,
    user: User,
    name: str = "Workbook Type",
    allowed_output_formats: list[str] | None = None,
) -> DocumentType:
    document_type = DocumentType(
        name=name,
        description=f"{name} description",
        allowed_output_formats=allowed_output_formats or ["pdf"],
        created_by=user,
        fields=[
            DocumentTypeField(
                name="cliente.nombre",
                type="string",
                description="Customer name",
                position=0,
            )
        ],
    )
    db_session.add(document_type)
    db_session.commit()
    db_session.refresh(document_type)
    return document_type


def _xlsx_template(
    db_session: SQLAlchemySession,
    user: User,
    document_type: DocumentType,
    name: str = "Workbook Template",
    validation_warnings: list[dict] | None = None,
) -> XlsxTemplate:
    template = XlsxTemplate(
        document_type=document_type,
        name=name,
        description=None,
        storage_key=f"{name}.xlsx",
        original_filename=f"{name}.xlsx",
        detected_sheets=[],
        detected_tokens=["cliente.nombre"],
        image_slots=[],
        validation_warnings=validation_warnings or [],
        created_by=user,
    )
    db_session.add(template)
    db_session.commit()
    db_session.refresh(template)
    return template


def test_create_rejects_xlsx_when_document_type_allows_only_pdf(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user, allowed_output_formats=["pdf"])

    response = client.post(
        "/api/document-designs",
        json={
            "document_type_id": str(document_type.id),
            "name": "Workbook design",
            "output_format": "xlsx",
        },
    )

    assert response.status_code == 400
    assert "does not allow xlsx output" in response.json()["detail"]


def test_create_requires_template_for_xlsx_design(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user, allowed_output_formats=["pdf", "xlsx"])

    response = client.post(
        "/api/document-designs",
        json={
            "document_type_id": str(document_type.id),
            "name": "Workbook design",
            "output_format": "xlsx",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "XLSX designs require xlsx_template_id"


def test_create_rejects_xlsx_template_on_pdf_design(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user, allowed_output_formats=["pdf", "xlsx"])
    template = _xlsx_template(db_session, user, document_type)

    response = client.post(
        "/api/document-designs",
        json={
            "document_type_id": str(document_type.id),
            "name": "PDF design",
            "output_format": "pdf",
            "xlsx_template_id": str(template.id),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "PDF designs cannot reference an XLSX template"


def test_create_rejects_xlsx_template_from_another_document_type(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(
        db_session, user, name="Primary Type", allowed_output_formats=["pdf", "xlsx"]
    )
    other_type = _document_type(
        db_session, user, name="Other Type", allowed_output_formats=["pdf", "xlsx"]
    )
    template = _xlsx_template(db_session, user, other_type)

    response = client.post(
        "/api/document-designs",
        json={
            "document_type_id": str(document_type.id),
            "name": "Workbook design",
            "output_format": "xlsx",
            "xlsx_template_id": str(template.id),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "XLSX template must belong to the design document type"


def test_update_applies_xlsx_design_validation(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user, allowed_output_formats=["pdf", "xlsx"])
    template = _xlsx_template(db_session, user, document_type)
    create_response = client.post(
        "/api/document-designs",
        json={
            "document_type_id": str(document_type.id),
            "name": "PDF design",
            "output_format": "pdf",
        },
    )
    assert create_response.status_code == 201
    design_id = create_response.json()["id"]

    missing_template = client.put(
        f"/api/document-designs/{design_id}",
        json={
            "name": "Workbook design",
            "description": None,
            "output_format": "xlsx",
        },
    )
    assert missing_template.status_code == 400
    assert missing_template.json()["detail"] == "XLSX designs require xlsx_template_id"

    valid_update = client.put(
        f"/api/document-designs/{design_id}",
        json={
            "name": "Workbook design",
            "description": None,
            "output_format": "xlsx",
            "xlsx_template_id": str(template.id),
        },
    )
    assert valid_update.status_code == 200
    assert valid_update.json()["output_format"] == "xlsx"
    assert valid_update.json()["xlsx_template_id"] == str(template.id)


def test_activate_xlsx_design_succeeds_without_pdf_pages(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user, allowed_output_formats=["pdf", "xlsx"])
    template = _xlsx_template(db_session, user, document_type)
    design = DocumentDesign(
        document_type=document_type,
        name="Workbook design",
        output_format="xlsx",
        xlsx_template=template,
        status="draft",
        created_by=user,
    )
    db_session.add(design)
    db_session.commit()
    db_session.refresh(design)

    response = client.post(f"/api/document-designs/{design.id}/activate")

    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_activate_xlsx_design_fails_when_template_has_warnings(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user, allowed_output_formats=["pdf", "xlsx"])
    template = _xlsx_template(
        db_session,
        user,
        document_type,
        validation_warnings=[{"type": "unknown_schema_token", "cell": "A1"}],
    )
    design = DocumentDesign(
        document_type=document_type,
        name="Workbook design",
        output_format="xlsx",
        xlsx_template=template,
        status="draft",
        created_by=user,
    )
    db_session.add(design)
    db_session.commit()
    db_session.refresh(design)

    response = client.post(f"/api/document-designs/{design.id}/activate")

    assert response.status_code == 400
    assert response.json()["detail"] == "XLSX template has validation warnings"


def test_activate_xlsx_design_rechecks_allowed_output_formats(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user, allowed_output_formats=["pdf"])
    template = _xlsx_template(db_session, user, document_type)
    design = DocumentDesign(
        document_type=document_type,
        name="Workbook design",
        output_format="xlsx",
        xlsx_template=template,
        status="draft",
        created_by=user,
    )
    db_session.add(design)
    db_session.commit()
    db_session.refresh(design)

    response = client.post(f"/api/document-designs/{design.id}/activate")

    assert response.status_code == 400
    assert "does not allow xlsx output" in response.json()["detail"]


def test_activate_xlsx_design_rechecks_template_document_type(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(
        db_session, user, name="Primary Type", allowed_output_formats=["pdf", "xlsx"]
    )
    other_type = _document_type(
        db_session, user, name="Other Type", allowed_output_formats=["pdf", "xlsx"]
    )
    template = _xlsx_template(db_session, user, other_type)
    design = DocumentDesign(
        document_type=document_type,
        name="Workbook design",
        output_format="xlsx",
        xlsx_template=template,
        status="draft",
        created_by=user,
    )
    db_session.add(design)
    db_session.commit()
    db_session.refresh(design)

    response = client.post(f"/api/document-designs/{design.id}/activate")

    assert response.status_code == 400
    assert response.json()["detail"] == "XLSX template must belong to the design document type"

```

## File: .superpowers/sdd/xlsx-template-generation-task-4-report.md
```
# XLSX Template Generation Task 4 Report

## Status

Implemented XLSX document design validation paths for create, update, and activation.

## Changes

- Added `backend/tests/test_xlsx_designs.py` with focused API and activation coverage:
  - rejects XLSX designs when the document type only allows PDF
  - requires `xlsx_template_id` for XLSX designs
  - rejects XLSX template references on PDF designs
  - rejects XLSX templates from another document type
  - applies the same validation during update
  - activates XLSX designs through the template path without requiring PDF pages
  - rejects activation when the linked XLSX template has validation warnings
- Updated `backend/app/api/document_designs.py`:
  - validates selected output format against `DocumentType.allowed_output_formats`
  - validates XLSX template presence and ownership
  - rejects XLSX template references for PDF designs
- Updated `backend/app/services/design_validation.py`:
  - branches XLSX activation before existing PDF page validation
  - requires a linked template for XLSX activation
  - blocks activation when template validation warnings are present

## Verification

- `rtk pytest backend/tests/test_xlsx_designs.py -q` from repo root failed before running tests:
  - `pydantic_core._pydantic_core.ValidationError: 5 validation errors for Settings`
  - missing `oidc_issuer`, `oidc_api_audience`, `database_url`, `test_database_url`, `frontend_origin`
- `rtk .\.venv\Scripts\python.exe -m pytest tests/test_xlsx_designs.py -q` from `backend/` failed before running tests:
  - `ModuleNotFoundError: No module named 'openpyxl'`
- Attempted dependency repair with `rtk uv sync` from `backend/`; it failed:
  - `error: failed to open file C:\Users\ilver\AppData\Local\uv\cache\sdists-v9\.git: Access is denied. (os error 5)`
- Fallback syntax verification passed:
  - `rtk .\.venv\Scripts\python.exe -m compileall app/api/document_designs.py app/services/design_validation.py app/schemas/document_design.py tests/test_xlsx_designs.py tests/test_document_designs.py`

## Concerns

- Focused pytest could not be completed because the backend virtualenv is missing `openpyxl` and `uv sync` is blocked by local cache permissions.
- The repo has many unrelated dirty files, including pre-existing changes in backend format/XLSX files. Commit staging should avoid sweeping unrelated work into Task 4.
 
---

## Review Fix Report

Fixed Task 4 review findings:

- Activation now re-checks `design.output_format` against the current `design.document_type.allowed_output_formats`.
- Activation now verifies the linked XLSX template still belongs to the design document type.
- Added regression tests for stale disallowed XLSX format and stale cross-document-type template activation.

Verification:

- `rtk proxy python -m compileall -q backend/app/services/design_validation.py backend/tests/test_xlsx_designs.py`: passed.
- `rtk pytest backend/tests/test_xlsx_designs.py -q`: failed with no useful detail after filtering.
- `rtk proxy powershell -NoProfile -Command '& { Set-Location backend; uv run pytest tests/test_xlsx_designs.py -q }'`: blocked by `failed to open file C:\Users\ilver\AppData\Local\uv\cache\sdists-v9\.git: Access is denied. (os error 5)`.

```
