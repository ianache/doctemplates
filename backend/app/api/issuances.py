from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models.document_design import DocumentDesign
from app.models.document_issuance import DocumentIssuance
from app.models.document_tracelog import DocumentTracelog
from app.models.user import User
from app.dependencies import get_storage_provider
from app.services.storage.base import StorageProvider
from app.schemas.document_issuance import (
    DocumentIssuanceLibraryItem,
    DocumentIssuanceShareOut,
    DocumentTracelogOut,
)
from app.utils.signature import generate_issuance_signature, verify_issuance_signature

router = APIRouter(prefix="/api/issuances", tags=["issuances"])
public_router = APIRouter(prefix="/api/public/document-issuances", tags=["public-issuances"])


def _request_metadata(request: Request, route: str) -> dict:
    return {
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "route": route,
    }


def _require_issuance(db: SQLAlchemySession, issuance_id: UUID) -> DocumentIssuance:
    issuance = (
        db.query(DocumentIssuance)
        .options(
            joinedload(DocumentIssuance.design_version),
            joinedload(DocumentIssuance.user),
        )
        .filter(DocumentIssuance.id == issuance_id)
        .first()
    )
    if issuance is None:
        raise HTTPException(status_code=404, detail="Document issuance not found")
    return issuance


def _issuance_out(issuance: DocumentIssuance) -> DocumentIssuanceLibraryItem:
    return DocumentIssuanceLibraryItem(
        id=issuance.id,
        design_version_id=issuance.design_version_id,
        design_name=issuance.design_version.name,
        output_format=issuance.output_format,
        mime_type=issuance.mime_type,
        filename=issuance.filename,
        preview_storage_key=issuance.preview_storage_key,
        status=issuance.status,
        design_status=issuance.design_version.status,
        design_version_number=issuance.design_version.version_number,
        user_id=issuance.user_id,
        generated_by_email=issuance.user.email,
        input_data=issuance.input_data,
        metadata_values=issuance.metadata_values,
        created_at=issuance.created_at,
        preview_url=f"/api/issuances/{issuance.id}/preview",
        download_url=f"/api/issuances/{issuance.id}/download",
        celery_task_id=issuance.celery_task_id,
        error_message=issuance.error_message,
        queued_at=issuance.queued_at,
        started_at=issuance.started_at,
        completed_at=issuance.completed_at,
        retry_count=issuance.retry_count,
    )


def _document_response(
    issuance: DocumentIssuance,
    storage_provider: StorageProvider,
    disposition: str = "attachment",
) -> Response:
    try:
        return storage_provider.get_download_response(
            issuance.storage_key,
            filename=issuance.filename or f"{issuance.id}.pdf",
            category="issuances",
            disposition=disposition,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Issued document file not found on storage")


def _append_tracelog(
    db: SQLAlchemySession,
    issuance: DocumentIssuance,
    event_type: Literal["download", "share"],
    user_id: UUID | None,
    metadata: dict,
) -> None:
    db.add(
        DocumentTracelog(
            issuance_id=issuance.id,
            user_id=user_id,
            event_type=event_type,
            metadata_=metadata,
        )
    )
    db.commit()


def _verify_issuance_ready(issuance: DocumentIssuance) -> None:
    if issuance.status in ("queued", "processing"):
        raise HTTPException(
            status_code=409,
            detail="Document generation is not complete"
        )
    if issuance.status == "failure":
        raise HTTPException(
            status_code=409,
            detail=issuance.error_message or "Document generation failed"
        )
    if not issuance.storage_key:
        raise HTTPException(
            status_code=409,
            detail="Document file is not ready"
        )


@public_router.get("/{issuance_id}/download")
def public_download_issuance(
    issuance_id: UUID,
    signature: str,
    request: Request,
    db: SQLAlchemySession = Depends(get_db),
    storage_provider = Depends(get_storage_provider),
):
    if not verify_issuance_signature(issuance_id, signature):
        raise HTTPException(status_code=403, detail="Invalid document signature")

    issuance = _require_issuance(db, issuance_id)
    _verify_issuance_ready(issuance)
    response = _document_response(issuance, storage_provider)
    _append_tracelog(
        db,
        issuance,
        "download",
        None,
        _request_metadata(request, f"GET /api/public/document-issuances/{issuance.id}/download"),
    )
    return response


@router.get("", response_model=list[DocumentIssuanceLibraryItem])
def list_issuances(
    design_name: str | None = None,
    id: UUID | None = None,
    status: Literal["queued", "processing", "success", "failure"] | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    metadata_key: str | None = None,
    metadata_value: str | None = None,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> list[DocumentIssuanceLibraryItem]:
    query = (
        db.query(DocumentIssuance)
        .join(DocumentIssuance.design_version)
        .join(DocumentIssuance.user)
        .options(
            joinedload(DocumentIssuance.design_version),
            joinedload(DocumentIssuance.user),
        )
    )

    if design_name:
        query = query.filter(DocumentDesign.name.ilike(f"%{design_name}%"))
    if id is not None:
        query = query.filter(DocumentIssuance.id == id)
    if status is not None:
        query = query.filter(DocumentIssuance.status == status)
    if created_from is not None:
        query = query.filter(DocumentIssuance.created_at >= datetime.combine(created_from, time.min))
    if created_to is not None:
        query = query.filter(DocumentIssuance.created_at <= datetime.combine(created_to, time.max))
    if metadata_key and metadata_value is not None:
        query = query.filter(
            func.coalesce(func.json_extract_path_text(DocumentIssuance.metadata_values, metadata_key), "").ilike(
                f"%{metadata_value}%"
            )
        )

    issuances = query.order_by(DocumentIssuance.created_at.desc()).all()
    return [_issuance_out(issuance) for issuance in issuances]


@router.get("/{issuance_id}", response_model=DocumentIssuanceLibraryItem)
def get_issuance(
    issuance_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentIssuanceLibraryItem:
    return _issuance_out(_require_issuance(db, issuance_id))


@router.get("/{issuance_id}/preview")
def preview_issuance(
    issuance_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
    storage_provider = Depends(get_storage_provider),
):
    issuance = _require_issuance(db, issuance_id)
    _verify_issuance_ready(issuance)
    return _document_response(issuance, storage_provider, disposition="inline")


@router.get("/{issuance_id}/download")
def download_issuance(
    issuance_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
    storage_provider = Depends(get_storage_provider),
):
    issuance = _require_issuance(db, issuance_id)
    _verify_issuance_ready(issuance)
    response = _document_response(issuance, storage_provider)
    _append_tracelog(
        db,
        issuance,
        "download",
        user.id,
        _request_metadata(request, f"GET /api/issuances/{issuance.id}/download"),
    )
    return response


@router.post("/{issuance_id}/share", response_model=DocumentIssuanceShareOut)
def share_issuance(
    issuance_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentIssuanceShareOut:
    issuance = _require_issuance(db, issuance_id)
    _verify_issuance_ready(issuance)
    signature = generate_issuance_signature(issuance.id)
    public_url = f"/api/public/document-issuances/{issuance.id}/download?signature={signature}"
    _append_tracelog(
        db,
        issuance,
        "share",
        user.id,
        _request_metadata(request, f"POST /api/issuances/{issuance.id}/share"),
    )
    return DocumentIssuanceShareOut(public_url=public_url)


@router.get("/{issuance_id}/tracelogs", response_model=list[DocumentTracelogOut])
def list_issuance_tracelogs(
    issuance_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> list[DocumentTracelog]:
    _require_issuance(db, issuance_id)
    return (
        db.query(DocumentTracelog)
        .filter(DocumentTracelog.issuance_id == issuance_id)
        .order_by(DocumentTracelog.created_at.asc())
        .all()
    )
