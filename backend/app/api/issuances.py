from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models.document_issuance import DocumentIssuance
from app.models.user import User
from app.utils.signature import verify_issuance_signature

router = APIRouter(prefix="/api/issuances", tags=["issuances"])
public_router = APIRouter(prefix="/api/public/document-issuances", tags=["public-issuances"])


@public_router.get("/{issuance_id}/download")
def public_download_issuance(
    issuance_id: UUID,
    signature: str,
    db: SQLAlchemySession = Depends(get_db),
):
    if not verify_issuance_signature(issuance_id, signature):
        raise HTTPException(status_code=403, detail="Invalid document signature")

    issuance = db.query(DocumentIssuance).filter(DocumentIssuance.id == issuance_id).first()
    if issuance is None:
        raise HTTPException(status_code=404, detail="Document issuance not found")

    file_path = Path(issuance.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Issued PDF file not found on disk")

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=f"{issuance.id}.pdf",
    )


@router.get("/{issuance_id}/download")
def download_issuance(
    issuance_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
):
    issuance = db.query(DocumentIssuance).filter(DocumentIssuance.id == issuance_id).first()
    if issuance is None:
        raise HTTPException(status_code=404, detail="Document issuance not found")

    file_path = Path(issuance.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Issued PDF file not found on disk")

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=f"{issuance.id}.pdf",
    )
