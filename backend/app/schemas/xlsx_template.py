from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class XlsxTemplateListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_type_id: UUID
    document_type_name: str
    name: str
    description: str | None
    original_filename: str
    detected_sheets: list[dict]
    detected_tokens: list[str]
    image_slots: list[dict]
    validation_warnings: list[dict]
    mock_data: dict | None
    created_by_email: str
    created_at: datetime


class XlsxTemplateDetail(XlsxTemplateListItem):
    pass


class XlsxTemplatePreviewRequest(BaseModel):
    mock_data: dict | None = None


class XlsxPreviewCell(BaseModel):
    address: str
    value: str | int | float | bool | None
    style: dict = {}


class XlsxPreviewSheet(BaseModel):
    name: str
    max_row: int
    max_column: int
    merged_ranges: list[str]
    cells: list[XlsxPreviewCell]


class XlsxTemplatePreviewResponse(BaseModel):
    sheets: list[XlsxPreviewSheet]
    warnings: list[dict] = []
