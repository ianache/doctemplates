from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pathlib import Path
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload

from app.api.document_types import require_document_type
from app.auth.dependencies import get_current_user
from app.config import settings
from app.db import get_db
from app.models.static_pdf_asset import StaticPdfAsset
from app.models.user import User
from app.schemas.static_pdf_asset import StaticPdfAssetDetail, StaticPdfAssetListItem
from app.services.content_storage import save_static_pdf_asset
from app.dependencies import get_storage_provider

router = APIRouter(prefix="/api/content/static-pdfs", tags=["static-pdfs"])


def _detail(asset: StaticPdfAsset) -> StaticPdfAssetDetail:
    return StaticPdfAssetDetail(
        id=asset.id,
        filename=asset.original_filename,
        stored_filename=asset.stored_filename,
        stored_path=asset.stored_path,
        page_count=asset.page_count,
        page_start=asset.page_start,
        page_end=asset.page_end,
        file_size=asset.file_size,
        document_type_id=asset.document_type_id,
        document_type_name=asset.document_type.name if asset.document_type else None,
        created_by_email=asset.created_by.email,
        created_at=asset.created_at,
        download_url=f"/api/content/static-pdfs/{asset.id}/download",
    )


@router.post("", response_model=StaticPdfAssetDetail, status_code=201)
def upload_static_pdf_asset(
    file: UploadFile = File(...),
    page_start: int | None = Form(default=None),
    page_end: int | None = Form(default=None),
    document_type_id: UUID | None = Form(default=None),
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
    storage_provider = Depends(get_storage_provider),
) -> StaticPdfAssetDetail:
    document_type = require_document_type(db, document_type_id) if document_type_id is not None else None

    (
        asset_id,
        original_filename,
        stored_filename,
        storage_key,
        page_count,
        file_size,
        _source_page_count,
        stored_page_start,
        stored_page_end,
    ) = save_static_pdf_asset(
        file,
        storage_provider=storage_provider,
        page_start=page_start,
        page_end=page_end,
    )

    asset = StaticPdfAsset(
        id=UUID(asset_id),
        original_filename=original_filename,
        stored_filename=stored_filename,
        storage_key=storage_key,
        page_count=page_count,
        page_start=stored_page_start,
        page_end=stored_page_end,
        file_size=file_size,
        document_type=document_type,
        created_by=user,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    db.refresh(user)
    return _detail(asset)


@router.get("", response_model=list[StaticPdfAssetListItem])
def list_static_pdf_assets(
    document_type_id: UUID | None = None,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> list[StaticPdfAssetListItem]:
    query = (
        db.query(StaticPdfAsset)
        .options(joinedload(StaticPdfAsset.created_by), joinedload(StaticPdfAsset.document_type))
        .order_by(StaticPdfAsset.created_at.desc())
    )
    if document_type_id is not None:
        query = query.filter(
            (StaticPdfAsset.document_type_id.is_(None))
            | (StaticPdfAsset.document_type_id == document_type_id)
        )
    assets = query.all()
    return [
        StaticPdfAssetListItem(
            id=asset.id,
            filename=asset.original_filename,
            page_count=asset.page_count,
            document_type_id=asset.document_type_id,
            document_type_name=asset.document_type.name if asset.document_type else None,
            created_by_email=asset.created_by.email,
            created_at=asset.created_at,
        )
        for asset in assets
    ]


@router.get("/{asset_id}", response_model=StaticPdfAssetDetail)
def get_static_pdf_asset(
    asset_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> StaticPdfAssetDetail:
    asset = (
        db.query(StaticPdfAsset)
        .options(joinedload(StaticPdfAsset.created_by), joinedload(StaticPdfAsset.document_type))
        .filter(StaticPdfAsset.id == asset_id)
        .first()
    )
    if asset is None:
        raise HTTPException(status_code=404, detail="PDF asset not found")
    return _detail(asset)


@router.get("/{asset_id}/download")
def download_static_pdf_asset(
    asset_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
    storage_provider = Depends(get_storage_provider),
):
    asset = db.query(StaticPdfAsset).filter(StaticPdfAsset.id == asset_id).first()
    if asset is None:
        raise HTTPException(status_code=404, detail="PDF asset not found")
    return storage_provider.get_download_response(
        asset.storage_key,
        filename=asset.original_filename,
        category="static_pdfs",
    )
