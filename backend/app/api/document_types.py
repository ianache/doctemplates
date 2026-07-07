from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload, selectinload

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models.document_type import DocumentType, DocumentTypeField
from app.models.user import User
from app.schemas.document_type import (
    DocumentTypeCreate,
    DocumentTypeDetail,
    DocumentTypeFieldOut,
    DocumentTypeListItem,
)

router = APIRouter(prefix="/api/document-types", tags=["document-types"])


def _to_detail(document_type: DocumentType) -> DocumentTypeDetail:
    return DocumentTypeDetail(
        id=document_type.id,
        name=document_type.name,
        description=document_type.description,
        fields=[
            DocumentTypeFieldOut(
                id=field.id,
                name=field.name,
                type=field.type,  # type: ignore[arg-type]
                description=field.description,
            )
            for field in document_type.fields
        ],
        created_by_email=document_type.created_by.email,
        created_at=document_type.created_at,
    )


@router.post("", response_model=DocumentTypeDetail, status_code=201)
def create_document_type(
    payload: DocumentTypeCreate,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentTypeDetail:
    document_type = DocumentType(
        name=payload.name,
        description=payload.description,
        created_by=user,
        fields=[
            DocumentTypeField(
                name=field.name,
                type=field.type,
                description=field.description,
                position=index,
            )
            for index, field in enumerate(payload.fields)
        ],
    )
    db.add(document_type)
    db.commit()
    db.refresh(document_type)
    db.refresh(user)
    return _to_detail(document_type)


@router.get("", response_model=list[DocumentTypeListItem])
def list_document_types(
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> list[DocumentTypeListItem]:
    rows = (
        db.query(DocumentType)
        .options(joinedload(DocumentType.created_by), selectinload(DocumentType.fields))
        .order_by(DocumentType.created_at.desc())
        .all()
    )
    return [
        DocumentTypeListItem(
            id=document_type.id,
            name=document_type.name,
            description=document_type.description,
            field_count=len(document_type.fields),
            created_by_email=document_type.created_by.email,
            created_at=document_type.created_at,
        )
        for document_type in rows
    ]


@router.get("/{document_type_id}", response_model=DocumentTypeDetail)
def get_document_type(
    document_type_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentTypeDetail:
    document_type = (
        db.query(DocumentType)
        .options(joinedload(DocumentType.created_by), selectinload(DocumentType.fields))
        .filter(DocumentType.id == document_type_id)
        .first()
    )
    if document_type is None:
        raise HTTPException(status_code=404, detail="Document type not found")
    return _to_detail(document_type)
