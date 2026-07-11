from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HtmlTemplateCreate(BaseModel):
    document_type_id: UUID
    name: str
    html: str
    css: str | None = ""
    mock_data: dict | None = None


class HtmlTemplateListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    document_type_id: UUID
    document_type_name: str
    token_count: int
    created_by_email: str
    created_at: datetime


class HtmlTemplateDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    document_type_id: UUID
    document_type_name: str
    html: str
    css: str | None = ""
    token_names: list[str]
    mock_data: dict | None = None
    created_by_email: str
    created_at: datetime


class HtmlTemplatePreviewRequest(BaseModel):
    html: str
    css: str | None = ""
    mock_data: dict | None = None


class HtmlTemplatePreviewResponse(BaseModel):
    rendered_html: str
