from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload, selectinload

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models.document_type import DocumentType, DocumentTypeField, DocumentTypeMetadataDefinition
from app.models.user import User
from app.schemas.document_type import (
    DocumentTypeCreate,
    DocumentTypeDetail,
    DocumentTypeFieldOut,
    DocumentTypeListItem,
    DocumentTypeMetadataOut,
)

router = APIRouter(prefix="/api/document-types", tags=["document-types"])


def require_document_type(db: SQLAlchemySession, document_type_id: UUID) -> DocumentType:
    document_type = db.query(DocumentType).filter(DocumentType.id == document_type_id).first()
    if document_type is None:
        raise HTTPException(status_code=404, detail="Document type not found")
    return document_type


def _to_detail(document_type: DocumentType) -> DocumentTypeDetail:
    return DocumentTypeDetail(
        id=document_type.id,
        name=document_type.name,
        description=document_type.description,
        allowed_output_formats=document_type.allowed_output_formats,
        fields=[
            DocumentTypeFieldOut(
                id=field.id,
                name=field.name,
                type=field.type,  # type: ignore[arg-type]
                description=field.description,
            )
            for field in document_type.fields
        ],
        metadata_definitions=[
            DocumentTypeMetadataOut(
                id=meta.id,
                name=meta.name,
                type=meta.type,  # type: ignore[arg-type]
                required=meta.required,
            )
            for meta in document_type.metadata_definitions
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
        allowed_output_formats=payload.allowed_output_formats,
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
        metadata_definitions=[
            DocumentTypeMetadataDefinition(
                name=meta.name,
                type=meta.type,
                required=meta.required,
            )
            for meta in payload.metadata_definitions
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
        .options(
            joinedload(DocumentType.created_by),
            selectinload(DocumentType.fields),
            selectinload(DocumentType.metadata_definitions),
        )
        .order_by(DocumentType.created_at.desc())
        .all()
    )
    return [
        DocumentTypeListItem(
            id=document_type.id,
            name=document_type.name,
            description=document_type.description,
            allowed_output_formats=document_type.allowed_output_formats,
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
        .options(
            joinedload(DocumentType.created_by),
            selectinload(DocumentType.fields),
            selectinload(DocumentType.metadata_definitions),
        )
        .filter(DocumentType.id == document_type_id)
        .first()
    )
    if document_type is None:
        raise HTTPException(status_code=404, detail="Document type not found")
    return _to_detail(document_type)


@router.put("/{document_type_id}", response_model=DocumentTypeDetail)
def update_document_type(
    document_type_id: UUID,
    payload: DocumentTypeCreate,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentTypeDetail:
    document_type = (
        db.query(DocumentType)
        .options(
            joinedload(DocumentType.created_by),
            selectinload(DocumentType.fields),
            selectinload(DocumentType.metadata_definitions),
        )
        .filter(DocumentType.id == document_type_id)
        .first()
    )
    if document_type is None:
        raise HTTPException(status_code=404, detail="Document type not found")

    document_type.name = payload.name
    document_type.description = payload.description
    document_type.allowed_output_formats = payload.allowed_output_formats

    # Clear existing associations first to trigger delete-orphan cascades
    document_type.fields.clear()
    document_type.metadata_definitions.clear()
    # Flush to ensure DELETEs are executed in database before new INSERTs
    db.flush()

    # Now append new fields
    document_type.fields = [
        DocumentTypeField(
            name=field.name,
            type=field.type,
            description=field.description,
            position=index,
        )
        for index, field in enumerate(payload.fields)
    ]

    # Now append new metadata definitions
    document_type.metadata_definitions = [
        DocumentTypeMetadataDefinition(
            name=meta.name,
            type=meta.type,
            required=meta.required,
        )
        for meta in payload.metadata_definitions
    ]

    db.commit()
    db.refresh(document_type)
    return _to_detail(document_type)
