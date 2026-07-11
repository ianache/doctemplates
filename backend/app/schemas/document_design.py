from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentDesignCreate(BaseModel):
    document_type_id: UUID
    name: str
    description: str | None = None
    mock_data: dict | None = None


class DocumentDesignUpdate(BaseModel):
    name: str
    description: str | None = None
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
