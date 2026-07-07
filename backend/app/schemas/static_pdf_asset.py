from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StaticPdfAssetListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    page_count: int
    created_by_email: str
    created_at: datetime


class StaticPdfAssetDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    stored_filename: str
    stored_path: str
    page_count: int
    page_start: int | None
    page_end: int | None
    file_size: int
    created_by_email: str
    created_at: datetime
    download_url: str
