from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class DocumentTracelogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    issuance_id: UUID
    event_type: str
    user_id: UUID | None
    metadata: dict = Field(validation_alias="metadata_", serialization_alias="metadata")
    created_at: datetime


class DocumentIssuanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    design_version_id: UUID
    file_path: str | None = None
    output_format: str = "pdf"
    mime_type: str | None = None
    filename: str | None = None
    preview_storage_key: str | None = None
    user_id: UUID
    input_data: dict
    metadata_values: dict | None = None
    status: str
    created_at: datetime

    celery_task_id: str | None = None
    error_message: str | None = None
    queued_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = 0


class DocumentIssuanceLibraryItem(BaseModel):
    id: UUID
    design_version_id: UUID
    design_name: str
    output_format: str = "pdf"
    mime_type: str | None = None
    filename: str | None = None
    preview_storage_key: str | None = None
    status: str
    design_status: str
    design_version_number: int | None
    user_id: UUID
    generated_by_email: str
    input_data: dict
    metadata_values: dict | None = None
    created_at: datetime
    preview_url: str
    download_url: str

    celery_task_id: str | None = None
    error_message: str | None = None
    queued_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = 0


class DocumentIssuanceShareOut(BaseModel):
    public_url: str
