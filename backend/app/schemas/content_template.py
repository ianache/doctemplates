from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HtmlTemplateCreate(BaseModel):
    document_type_id: UUID
    name: str
    html: str


class HtmlTemplateListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
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
    token_names: list[str]
    created_by_email: str
    created_at: datetime
