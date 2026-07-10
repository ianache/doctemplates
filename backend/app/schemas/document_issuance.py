from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class DocumentTracelogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    issuance_id: UUID
    event_type: str
    user_id: UUID | None
    metadata: dict = Field(validation_alias="metadata_")
    created_at: datetime


class DocumentIssuanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    design_version_id: UUID
    file_path: str
    user_id: UUID
    input_data: dict
    status: str
    created_at: datetime
