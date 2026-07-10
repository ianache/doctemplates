from pathlib import Path
from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models.document_design import DocumentDesign
from app.models.document_issuance import DocumentIssuance
from app.models.document_tracelog import DocumentTracelog
from app.models.user import User
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
        status=issuance.status,
        design_status=issuance.design_version.status,
        design_version_number=issuance.design_version.version_number,
        user_id=issuance.user_id,
        generated_by_email=issuance.user.email,
        input_data=issuance.input_data,
        created_at=issuance.created_at,
        preview_url=f"/api/issuances/{issuance.id}/preview",
        download_url=f"/api/issuances/{issuance.id}/download",
    )


def _pdf_response(issuance: DocumentIssuance) -> FileResponse:
    file_path = Path(issuance.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Issued PDF file not found on disk")

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=f"{issuance.id}.pdf",
    )


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


@public_router.get("/{issuance_id}/download")
def public_download_issuance(
    issuance_id: UUID,
    signature: str,
    request: Request,
    db: SQLAlchemySession = Depends(get_db),
):
    if not verify_issuance_signature(issuance_id, signature):
        raise HTTPException(status_code=403, detail="Invalid document signature")

    issuance = _require_issuance(db, issuance_id)
    response = _pdf_response(issuance)
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
    status: Literal["success", "failure"] | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
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
):
    issuance = _require_issuance(db, issuance_id)
    file_path = Path(issuance.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Issued PDF file not found on disk")
    return FileResponse(
        file_path,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )


@router.get("/{issuance_id}/download")
def download_issuance(
    issuance_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
):
    issuance = _require_issuance(db, issuance_id)
    response = _pdf_response(issuance)
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
